"""Serviço de ETL do domínio INSTITUCIONAL_DB.

Responsabilidade:
    Orquestrar a extração de dados do EOL (SQL Server) e a persistência
    incremental no banco institucional_db.

Estratégia:
    Usa processamento incremental baseado em Hash SHA-256 (EtlAuditoriaLinha)
    para minimizar escritas no banco destino.

Mapeamento:
    Utiliza DTOs (ModelIn/ModelOut) para garantir tipagem e garantir que
    a lógica de transformação esteja centralizada.
"""

import logging
from typing import Any

from apps.controle_auditoria.models import EtlAuditoriaLinha
from functools import partial

from apps.core.libs.thread_processor import ThreadPoolProcessor, decorar_para_hash
from apps.core.libs.cache import CacheService
from apps.eol_connection.libs.servico_eol import EOLService
from apps.institucional.dtos.model_in import (
    DREIn,
    SubprefeituraIn,
    TipoEscolaIn,
    UnidadeEducacionalIn,
)
from apps.institucional.dtos.model_out import (
    DREOut,
    SubprefeituraOut,
    TipoEscolaOut,
    UnidadeEducacionalOut,
)
from apps.institucional.libs.repositorio_core_sso import RepositorioCoreSSO
from apps.institucional.models import (
    DRE,
    SubPrefeitura,
    TipoEscola,
    UnidadeEducacional,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQLs — Extração Completa (Migrado de Offset para Full-Incremental)
# ---------------------------------------------------------------------------

SQL_TIPO_ESCOLA = """
SELECT
    tp_escola AS codigo_tipo_escola
  , LTRIM(RTRIM(sg_tp_escola)) AS sigla
  , LTRIM(RTRIM(dc_tipo_escola)) AS descricao
FROM tipo_escola
"""

SQL_SUBPREFEITURA = """
SELECT
    cd_sub_prefeitura AS codigo_sub_prefeitura
  , sg_sub_prefeitura AS sigla
  , dc_sub_prefeitura AS nome
FROM sub_prefeitura
"""

SQL_DRE = """
SELECT
    ua.cd_unidade_administrativa AS codigo_dre
  , vcue.nm_unidade_educacao AS nome
  , vcue.nm_exibicao_unidade AS sigla
  , ua.tp_unidade_administrativa AS tipo_unidade_adm
  , tua.dc_tipo_unidade_administrativa AS descricao_unidade_adm
FROM unidade_administrativa ua
INNER JOIN v_cadastro_unidade_educacao vcue
    ON vcue.cd_unidade_educacao = ua.cd_unidade_administrativa
LEFT JOIN tipo_unidade_administrativa tua
    ON tua.tp_unidade_administrativa = ua.tp_unidade_administrativa
WHERE ua.tp_unidade_administrativa = 24
"""

SQL_OBTER_CODIGOS_UES_POR_DRE = """
SELECT cd_unidade_educacao
FROM v_cadastro_unidade_educacao
WHERE cd_unidade_administrativa_referencia = %s
"""


SQL_UNIDADE_EDUCACIONAL = """
;WITH dispositivo AS (
    SELECT
        dcu.cd_unidade_educacao
      , cd_ddd
      , dc_dispositivo
      , tp_dispositivo_comunicacao
      , ROW_NUMBER() OVER (
            PARTITION BY dcu.cd_unidade_educacao, tp_dispositivo_comunicacao
            ORDER BY tp_dispositivo_comunicacao
        ) AS sequencia
    FROM dispositivo_comunicacao_unidade dcu
    WHERE tp_dispositivo_comunicacao IN (1, 9)
      AND dt_fim IS NULL
),
capacidadeVaga AS (
    SELECT
        t.cd_escola
      , SUM(qt_vaga_oferecida) AS quantidadeVagaTurno
      , grade.cd_tipo_turno
    FROM turma_escola t
    INNER JOIN serie_turma_escola
        ON serie_turma_escola.cd_turma_escola = t.cd_turma_escola
    INNER JOIN serie_turma_grade
        ON serie_turma_grade.cd_turma_escola = serie_turma_escola.cd_turma_escola
    INNER JOIN escola_grade
        ON serie_turma_grade.cd_escola_grade = escola_grade.cd_escola_grade
    INNER JOIN grade
        ON escola_grade.cd_grade = grade.cd_grade
    GROUP BY t.cd_escola, grade.cd_tipo_turno
),
funcionarios AS (
    SELECT
        dre.cd_unidade_educacao AS CodigoUnidade
      , COUNT(DISTINCT servidor.cd_registro_funcional) AS quantidade
    FROM v_servidor_cotic servidor
    INNER JOIN v_cargo_base_cotic AS cargoServidor
        ON cargoServidor.CD_SERVIDOR = servidor.cd_servidor
    INNER JOIN lotacao_servidor AS lotacao_servidor
        ON cargoServidor.cd_cargo_base_servidor
        = lotacao_servidor.cd_cargo_base_servidor
    INNER JOIN v_cadastro_unidade_educacao dre
        ON lotacao_servidor.cd_unidade_educacao = dre.cd_unidade_educacao
    WHERE lotacao_servidor.dt_fim IS NULL
    GROUP BY dre.cd_unidade_educacao
)
SELECT
    vcue.cd_unidade_educacao AS codigo_ue
  , vcue.nm_unidade_educacao AS nome
  , vcue.nm_exibicao_unidade AS nome_nao_oficial
  , tpue.dc_tipo_unidade_educacao AS tipo_ue
  , tpl.dc_tp_logradouro AS tipo_logradouro
  , vcue.nm_logradouro AS logradouro
  , vcue.cd_nr_endereco AS numero
  , vcue.nm_bairro AS bairro
  , vcue.cd_cep AS cep
  , mun.nm_municipio AS municipio
  , vuedg.nm_distrito_mec AS distrito
  , (SELECT dc_dispositivo FROM dispositivo
     WHERE tp_dispositivo_comunicacao = 9 AND sequencia = 1
       AND cd_unidade_educacao = vuedg.cd_unidade_educacao) AS email
  , (SELECT CONCAT('(', cd_ddd, ') ', dc_dispositivo) FROM dispositivo
     WHERE tp_dispositivo_comunicacao = 1 AND sequencia = 1
       AND cd_unidade_educacao = vuedg.cd_unidade_educacao) AS telefone_1
  , (SELECT CONCAT('(', cd_ddd, ') ', dc_dispositivo) FROM dispositivo
     WHERE tp_dispositivo_comunicacao = 1 AND sequencia = 2
       AND cd_unidade_educacao = vuedg.cd_unidade_educacao) AS telefone_2
  , escola.an_construcao AS ano_construcao
  , vuedg.dc_tipo_forma_ocupacao_predio AS propriedade
  , CASE WHEN vuedg.tp_escola IN (11, 12) THEN CAST(1 AS BIT)
         ELSE CAST(0 AS BIT) END AS organizacao_parceira
  , ISNULL((SELECT quantidadeVagaTurno FROM capacidadeVaga
            WHERE cd_escola = vuedg.cd_unidade_educacao
              AND cd_tipo_turno = 1), 0) AS vagas_matutino
  , ISNULL((SELECT SUM(quantidadeVagaTurno) FROM capacidadeVaga
            WHERE cd_escola = vuedg.cd_unidade_educacao
              AND cd_tipo_turno IN (3, 4)), 0) AS vagas_vespertino
  , ISNULL((SELECT quantidadeVagaTurno FROM capacidadeVaga
            WHERE cd_escola = vuedg.cd_unidade_educacao
              AND cd_tipo_turno = 5), 0) AS vagas_noturno
  , ISNULL((SELECT quantidadeVagaTurno FROM capacidadeVaga
            WHERE cd_escola = vuedg.cd_unidade_educacao
              AND cd_tipo_turno = 2), 0) AS vagas_intermediario
  , ISNULL((SELECT quantidadeVagaTurno FROM capacidadeVaga
            WHERE cd_escola = vuedg.cd_unidade_educacao
              AND cd_tipo_turno = 6), 0) AS vagas_integral
  , ISNULL((SELECT SUM(quantidadeVagaTurno) FROM capacidadeVaga
            WHERE cd_escola = vuedg.cd_unidade_educacao), 0) AS vagas_total
  , ISNULL((SELECT quantidade FROM funcionarios
            WHERE CodigoUnidade =
              vuedg.cd_unidade_educacao), 0) AS quantidade_funcionarios
  , vcue.cd_cie_unidade_educacao AS codigo_inep
  , vuedg.sg_tipo_situacao_unidade AS status
  , vcue.cd_unidade_administrativa_referencia AS codigo_dre
  , vuedg.tp_escola AS codigo_tipo_escola
  , vcue.cd_sub_prefeitura AS codigo_sub_prefeitura
FROM v_cadastro_unidade_educacao vcue
INNER JOIN unidade_administrativa dre
    ON dre.cd_unidade_administrativa = vcue.cd_unidade_administrativa_referencia
LEFT JOIN v_unidade_educacao_dados_gerais vuedg
    ON vuedg.cd_unidade_educacao = vcue.cd_unidade_educacao
LEFT JOIN escola
    ON escola.cd_escola = vcue.cd_unidade_educacao
LEFT JOIN tipo_unidade_educacao tpue
    ON tpue.tp_unidade_educacao = vcue.tp_unidade_educacao
LEFT JOIN tipo_logradouro tpl
    ON tpl.tp_logradouro = vcue.tp_logradouro
LEFT JOIN municipio mun
    ON mun.cd_municipio = vcue.cd_municipio
WHERE dre.tp_unidade_administrativa = 24
AND  vcue.tp_unidade_educacao  <> 15
ORDER BY codigo_ue
"""

# ---------------------------------------------------------------------------

# Helpers de Controle Incremental (Padrão Professores)
# ---------------------------------------------------------------------------


def _upsert_incremental(
    model_class: Any,
    tabela: str,
    objs: list[Any],
    update_fields: list[str],
) -> int:
    """Upsert incremental: salva apenas o que mudou comparando com EtlAuditoriaLinha."""
    if not objs:
        return 0

    pk_name = model_class._meta.pk.name

    # 1. Deduplicar por PK (garante que não enviamos duplicados no bulk_create)
    # se houver duplicados na origem, mantemos o último da lista.
    objs_unicos: dict[Any, Any] = {getattr(obj, pk_name): obj for obj in objs}

    processor = ThreadPoolProcessor(prefixo_log=f"ETL {tabela[:6].upper()}")
    func = partial(decorar_para_hash, tabela, update_fields)
    linhas_com_hash = processor.processar(list(objs_unicos.items()), func)

    # Busca hashes existentes no banco de auditoria (banco default)
    ids_destino = [item[0] for item in linhas_com_hash]
    hashes_existentes = dict(
        EtlAuditoriaLinha.objects.filter(id_destino__in=ids_destino).values_list(
            "id_destino", "hash_controle"
        )
    )

    # Filtra apenas o que mudou ou é novo
    objs_para_salvar = []
    novos_hashes = {}
    for id_destino, novo_hash, obj in linhas_com_hash:
        if hashes_existentes.get(id_destino) != novo_hash:
            objs_para_salvar.append(obj)
            novos_hashes[id_destino] = novo_hash

    if not objs_para_salvar:
        return 0

    # Gravar no banco destino (institucional_db)
    model_class.objects.using("institucional_db").bulk_create(
        objs_para_salvar,
        update_conflicts=True,
        unique_fields=[pk_name],
        update_fields=update_fields,
        batch_size=500,
    )

    # Atualizar hashes no banco de auditoria (banco default)
    hash_objs = [
        EtlAuditoriaLinha(id_destino=id_d, hash_controle=h)
        for id_d, h in novos_hashes.items()
    ]
    EtlAuditoriaLinha.objects.bulk_create(
        hash_objs,
        update_conflicts=True,
        unique_fields=["id_destino"],
        update_fields=["hash_controle"],
        batch_size=500,
    )

    return len(objs_para_salvar)


# ---------------------------------------------------------------------------
# Serviço Principal: EtlInstitucionalService
# ---------------------------------------------------------------------------


class EtlInstitucionalService:
    """Orquestra o ETL unificado para o domínio Institucional."""

    def __init__(
        self,
        eol: EOLService | None = None,
        core_sso: RepositorioCoreSSO | None = None,
        cache: CacheService | None = None,
    ) -> None:
        """Inicia o serviço injetando dependências mockáveis."""
        self.eol = eol or EOLService()
        self.core_sso = core_sso or RepositorioCoreSSO()
        self.cache = cache or CacheService()
        self.ultima_fase_concluida = 0

    def popular_dre(self) -> int:
        """Fase 1: Extrai e persiste DRE."""
        rows = self.eol.executar_query(SQL_DRE)
        objs = [DREOut.from_in(DREIn(*r)) for r in rows]

        # Tenta popular os códigos de integração das UEs
        sso_offline = False
        for obj in objs:
            if sso_offline:
                break

            try:
                codigo_dre = str(obj.codigo_dre)
                key_cache_dre = (
                    f"etl_institucional:dre:{codigo_dre}:codigos_ues_integracao"
                )

                if self.cache.exist_hash_value(key_cache_dre):
                    continue

                ue_rows = self.eol.executar_query(
                    SQL_OBTER_CODIGOS_UES_POR_DRE, parametros=[codigo_dre]
                )
                codigo_ues = [str(r[0]) for r in ue_rows]

                if codigo_ues:
                    sso_rows = self.core_sso.obter_codigos_integracao_ues(codigo_ues)
                    novos_mapeamentos = {str(r[0]): str(r[2]) for r in sso_rows if r[2]}

                    if novos_mapeamentos:
                        self.cache.set_hash(
                            key_cache_dre,
                            mapping=novos_mapeamentos,
                            expire_seconds=14400,
                        )
            except Exception as erro:
                logger.warning(
                    "[ETL] Falha ao popular cache de codigos de integração "
                    "das UEs para DRE %s: %s",
                    codigo_dre,
                    str(erro),
                )
                sso_offline = True

        update_fields = [
            "nome",
            "sigla",
            "tipo_unidade_adm",
            "descricao_unidade_adm",
        ]
        total = _upsert_incremental(DRE, "dre", objs, update_fields)
        logger.info("[ETL INST] dre: %d", total)
        return total

    def popular_tipos_escola(self) -> int:
        """Fase 2: Extrai e persiste TipoEscola."""
        rows = self.eol.executar_query(SQL_TIPO_ESCOLA)
        objs = [TipoEscolaOut.from_in(TipoEscolaIn(*r)) for r in rows]
        update_fields = ["sigla", "descricao"]
        total = _upsert_incremental(TipoEscola, "tipo_escola", objs, update_fields)
        logger.info("[ETL INST] tipo_escola: %d", total)
        return total

    def popular_subprefeituras(self) -> int:
        """Fase 3: Extrai e persiste SubPrefeitura."""
        rows = self.eol.executar_query(SQL_SUBPREFEITURA)
        objs = [SubprefeituraOut.from_in(SubprefeituraIn(*r)) for r in rows]
        update_fields = ["sigla", "nome"]
        total = _upsert_incremental(
            SubPrefeitura, "sub_prefeitura", objs, update_fields
        )
        logger.info("[ETL INST] sub_prefeitura: %d", total)
        return total

    def popular_unidades_educacionais(self) -> int:
        """Fase 4: Extrai e persiste UnidadeEducacional com enriquecimento.

        O processo é segmentado por DRE.
        """
        rows = self.eol.executar_query(SQL_UNIDADE_EDUCACIONAL)
        dto_ins = [UnidadeEducacionalIn(*r) for r in rows]

        # Agrupa UEs por DRE para carregar cache segmentado eficientemente
        ues_por_dre: dict[str, list[UnidadeEducacionalIn]] = {}
        for d in dto_ins:
            ues_por_dre.setdefault(str(d.codigo_dre), []).append(d)

        objs: list[UnidadeEducacionalOut] = []
        for codigo_dre, ues_lote in ues_por_dre.items():
            key_cache = f"etl_institucional:dre:{codigo_dre}:codigos_ues_integracao"
            cache_dre = self.cache.get_hash(key_cache)

            # Enriquece cada UE do lote da DRE
            for dto_in in ues_lote:
                codigo_integracao = cache_dre.get(str(dto_in.codigo_ue))
                objs.append(
                    UnidadeEducacionalOut.from_in(
                        dto_in, codigo_ue_integracao=codigo_integracao
                    )
                )

        update_fields = [
            "nome",
            "nome_nao_oficial",
            "tipo_ue",
            "tipo_logradouro",
            "logradouro",
            "numero",
            "bairro",
            "cep",
            "municipio",
            "distrito",
            "email",
            "telefone_1",
            "telefone_2",
            "ano_construcao",
            "propriedade",
            "organizacao_parceira",
            "vagas_matutino",
            "vagas_vespertino",
            "vagas_noturno",
            "vagas_intermediario",
            "vagas_integral",
            "vagas_total",
            "quantidade_funcionarios",
            "codigo_inep",
            "status",
            "dre_id",
            "tipo_escola_id",
            "subprefeitura_id",
            "codigo_ue_integracao",
        ]
        total = _upsert_incremental(
            UnidadeEducacional, "unidade_educacional", objs, update_fields
        )
        logger.info("[ETL INST] unidade_educacional: %d", total)
        return total

    def executar(self, fase_inicial: int = 1) -> dict[str, int]:
        """Executa as fases do ETL institucional em ordem de dependência."""
        resultados: dict[str, int] = {}
        log = logger.info

        log("[ETL INST] Iniciando carga a partir da fase %d...", fase_inicial)

        if fase_inicial <= 1:
            log("[ETL INST] === Fase 1: DRE / Cache SSO ===")
            resultados["dre"] = self.popular_dre()
            self.ultima_fase_concluida = 1
            log("[ETL INST] Fase 1 concluída.")

        if fase_inicial <= 2:
            log("[ETL INST] === Fase 2: Tipo Escola ===")
            resultados["tipo_escola"] = self.popular_tipos_escola()
            self.ultima_fase_concluida = 2
            log("[ETL INST] Fase 2 concluída.")

        if fase_inicial <= 3:
            log("[ETL INST] === Fase 3: Subprefeitura ===")
            resultados["sub_prefeitura"] = self.popular_subprefeituras()
            self.ultima_fase_concluida = 3
            log("[ETL INST] Fase 3 concluída.")

        if fase_inicial <= 4:
            log("[ETL INST] === Fase 4: Unidade Educacional ===")
            resultados["unidade_educacional"] = self.popular_unidades_educacionais()
            self.ultima_fase_concluida = 4
            log("[ETL INST] Fase 4 concluída.")

        total = sum(resultados.values())
        log(
            "[ETL INST] Concluído. Linhas alteradas: %d (fases %d–4).",
            total,
            fase_inicial,
        )
        return resultados
