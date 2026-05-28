"""Serviço de ETL do domínio INSTITUCIONAL_DB."""

import logging
from collections.abc import Callable, Iterator
from typing import Any
from uuid import UUID

from apps.core.libs.base_etl_service import (
    BaseEtlService,
    PhaseConfig,
)
from apps.core.libs.cache import CacheService
from apps.core.libs.thread_processor import calcular_hash
from apps.eol_connection.libs.servico_eol import EOLService
from apps.institucional.dtos.model_in import (
    DREIn,
    SubprefeituraIn,
    TipoEscolaIn,
    UnidadeEducacionalIn,
)
from apps.institucional.libs.repositorio_core_sso import RepositorioCoreSSO
from apps.institucional.models import (
    DRE,
    SubPrefeitura,
    TipoEscola,
    UnidadeEducacional,
)

logger = logging.getLogger(__name__)

SQL_TIPO_ESCOLA = """
SELECT
    tp_escola AS codigo_tipo_escola
  , LTRIM(RTRIM(sg_tp_escola)) AS sigla
  , LTRIM(RTRIM(dc_tipo_escola)) AS descricao
  , dt_atualizacao_tabela AS data_atualizacao
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
        ON serie_turma_grade.cd_turma_escola
        = serie_turma_escola.cd_turma_escola
    INNER JOIN escola_grade
        ON serie_turma_grade.cd_escola_grade = escola_grade.cd_escola_grade
    INNER JOIN grade
        ON escola_grade.cd_grade = grade.cd_grade
    GROUP BY t.cd_escola, grade.cd_tipo_turno
),
funcionarios AS (
    SELECT COUNT(DISTINCT CodigoRF) AS quantidade, CodigoUnidade
    FROM (
        SELECT DISTINCT
            servidor.cd_registro_funcional AS CodigoRF
          , dre.cd_unidade_educacao        AS CodigoUnidade
        FROM v_servidor_cotic servidor
        INNER JOIN v_cargo_base_cotic AS cargoServidor
            ON cargoServidor.CD_SERVIDOR = servidor.cd_servidor
        INNER JOIN cargo AS cargo
            ON cargoServidor.cd_cargo = cargo.cd_cargo
        LEFT JOIN lotacao_servidor AS lotacao_servidor
            ON cargoServidor.cd_cargo_base_servidor
            = lotacao_servidor.cd_cargo_base_servidor
        LEFT JOIN funcao_atividade_cargo_servidor funcao
            ON cargoServidor.cd_cargo_base_servidor
            = funcao.cd_cargo_base_servidor
            AND funcao.dt_fim_funcao_atividade IS NULL
        INNER JOIN v_cadastro_unidade_educacao dre
            ON lotacao_servidor.cd_unidade_educacao = dre.cd_unidade_educacao
        WHERE lotacao_servidor.dt_fim IS NULL

        UNION

        SELECT DISTINCT
            servidor.cd_registro_funcional AS CodigoRF
          , dre.cd_unidade_educacao        AS CodigoUnidade
        FROM v_servidor_cotic servidor
        INNER JOIN v_cargo_base_cotic AS cargoServidor
            ON cargoServidor.CD_SERVIDOR = servidor.cd_servidor
        LEFT JOIN lotacao_servidor AS lotacao_servidor
            ON cargoServidor.cd_cargo_base_servidor
            = lotacao_servidor.cd_cargo_base_servidor
        LEFT JOIN funcao_atividade_cargo_servidor funcao
            ON cargoServidor.cd_cargo_base_servidor
            = funcao.cd_cargo_base_servidor
            AND funcao.dt_fim_funcao_atividade IS NULL
        INNER JOIN cargo_sobreposto_servidor AS cargo_sobreposto_servidor
            ON cargo_sobreposto_servidor.cd_cargo_base_servidor
            = cargoServidor.cd_cargo_base_servidor
            AND (
                cargo_sobreposto_servidor.dt_fim_cargo_sobreposto IS NULL
                OR cargo_sobreposto_servidor.dt_fim_cargo_sobreposto
                > GETDATE()
            )
        INNER JOIN cargo AS cargo
            ON cargo_sobreposto_servidor.cd_cargo = cargo.cd_cargo
        INNER JOIN v_cadastro_unidade_educacao dre
            ON cargo_sobreposto_servidor.cd_unidade_local_servico
            = dre.cd_unidade_educacao
        WHERE lotacao_servidor.dt_fim IS NULL
          AND cargoServidor.dt_fim_nomeacao IS NULL

        UNION

        SELECT DISTINCT
            servidor.cd_registro_funcional AS CodigoRF
          , dre.cd_unidade_educacao        AS CodigoUnidade
        FROM v_servidor_cotic servidor
        INNER JOIN v_cargo_base_cotic AS cargoServidor
            ON cargoServidor.CD_SERVIDOR = servidor.cd_servidor
        LEFT JOIN funcao_atividade_cargo_servidor funcao
            ON cargoServidor.cd_cargo_base_servidor
            = funcao.cd_cargo_base_servidor
            AND funcao.dt_fim_funcao_atividade IS NULL
        INNER JOIN cargo AS cargo
            ON cargoServidor.cd_cargo = cargo.cd_cargo
        INNER JOIN atribuicao_aula atribuicao
            ON atribuicao.cd_cargo_base_servidor
            = cargoServidor.cd_cargo_base_servidor
        INNER JOIN v_cadastro_unidade_educacao dre
            ON atribuicao.cd_unidade_educacao = dre.cd_unidade_educacao
        WHERE atribuicao.dt_cancelamento IS NULL
          AND cargoServidor.dt_fim_nomeacao IS NULL
          AND atribuicao.dt_disponibilizacao_aulas IS NULL
          AND YEAR(atribuicao.dt_atribuicao_aula) = YEAR(GETDATE())

        UNION

        SELECT DISTINCT
            servidor.cd_registro_funcional AS CodigoRF
          , dre.cd_unidade_educacao        AS CodigoUnidade
        FROM v_servidor_cotic servidor
        INNER JOIN v_cargo_base_cotic AS cargoServidor
            ON cargoServidor.CD_SERVIDOR = servidor.cd_servidor
        LEFT JOIN funcao_atividade_cargo_servidor funcao
            ON cargoServidor.cd_cargo_base_servidor
            = funcao.cd_cargo_base_servidor
            AND funcao.dt_fim_funcao_atividade IS NULL
        INNER JOIN cargo AS cargo
            ON cargoServidor.cd_cargo = cargo.cd_cargo
        INNER JOIN funcao_atividade_cargo_servidor atividade
            ON atividade.cd_cargo_base_servidor
            = cargoServidor.cd_cargo_base_servidor
        INNER JOIN v_cadastro_unidade_educacao dre
            ON atividade.cd_unidade_local_servico = dre.cd_unidade_educacao
        WHERE atividade.dt_fim_funcao_atividade IS NULL
          AND cargoServidor.dt_fim_nomeacao IS NULL

        UNION

        SELECT DISTINCT
            p.cd_cpf_pessoa   AS CodigoRF
          , dre.cd_unidade_educacao AS CodigoUnidade
        FROM contrato_externo ce
        INNER JOIN pessoa p
            ON ce.cd_pessoa = p.cd_pessoa
        INNER JOIN funcao_funcionario_externo ffe
            ON ce.cd_tipo_funcao_funcionario_externo
            = ffe.cd_tipo_funcao_funcionario_externo
        INNER JOIN v_cadastro_unidade_educacao dre
            ON dre.cd_unidade_educacao = ce.cd_unidade_educacao
        WHERE ce.dt_cancelamento IS NULL
    ) func
    GROUP BY CodigoUnidade
)
SELECT
    vcue.cd_unidade_educacao AS codigo_ue
  , vcue.nm_unidade_educacao AS nome
  , vcue.nm_exibicao_unidade AS nome_nao_oficial
  , tpue.dc_tipo_unidade_educacao AS tipo_ue
  , vcue.tp_unidade_educacao AS codigo_tipo_unidade_educacao
  , tpl.dc_tp_logradouro AS tipo_logradouro
  , vcue.cd_logradouro AS codigo_logradouro
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
  , CASE WHEN COALESCE(vuedg.tp_escola, escola.tp_escola) = 5
         THEN CAST(1 AS BIT) ELSE CAST(0 AS BIT) END AS eh_ceu
  , vcue.dt_atualizacao_endereco AS data_atualizacao
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
  , te.tp_escola AS codigo_tipo_escola
  , COALESCE(vuedg.tp_escola, escola.tp_escola) AS codigo_tp_equipamento
  , vcue.cd_sub_prefeitura AS codigo_sub_prefeitura
FROM v_cadastro_unidade_educacao vcue
INNER JOIN unidade_administrativa dre
    ON dre.cd_unidade_administrativa
    = vcue.cd_unidade_administrativa_referencia
LEFT JOIN v_unidade_educacao_dados_gerais vuedg
    ON vuedg.cd_unidade_educacao = vcue.cd_unidade_educacao
LEFT JOIN escola
    ON escola.cd_escola = vcue.cd_unidade_educacao
LEFT JOIN tipo_escola te
    ON te.tp_escola = COALESCE(vuedg.tp_escola, escola.tp_escola)
LEFT JOIN tipo_unidade_educacao tpue
    ON tpue.tp_unidade_educacao = vcue.tp_unidade_educacao
LEFT JOIN tipo_logradouro tpl
    ON tpl.tp_logradouro = vcue.tp_logradouro
LEFT JOIN municipio mun
    ON mun.cd_municipio = vcue.cd_municipio
WHERE dre.tp_unidade_administrativa = 24
AND  vcue.tp_unidade_educacao  <> 15
"""


class EtlInstitucionalService(BaseEtlService):
    """Serviço de ETL do domínio Institucional.

    Orquestra 4 fases: DRE, TipoEscola, SubPrefeitura,
    UnidadeEducacional. A fase 4 enriquece cada UE com o
    código de integração obtido via Core SSO (pré-cacheado).
    """

    _dominio = "INSTITUCIONAL"

    def __init__(
        self,
        db_alias: str,
        id_execucao: UUID | None = None,
        repositorio_auditoria: Any | None = None,
        primeiro_run: bool = False,
        eol: EOLService | None = None,
        cache: CacheService | None = None,
        core_sso: RepositorioCoreSSO | None = None,
    ) -> None:
        super().__init__(
            db_alias=db_alias,
            id_execucao=id_execucao,
            repositorio_auditoria=repositorio_auditoria,
            primeiro_run=primeiro_run,
        )
        self.eol = eol or EOLService()
        self.cache = cache or CacheService()
        self.core_sso = core_sso or RepositorioCoreSSO()
        self._fases = self._init_fases()

    def _iter_chunks(self, sql: str) -> Iterator[list[tuple]]:
        return self.eol.iter_query(sql)

    def _init_fases(self) -> list[PhaseConfig]:
        return [
            PhaseConfig(
                nome="dre",
                sql=SQL_DRE,
                table_name="dre",
                source_table="unidade_administrativa",
                model_class=DRE,
                dto_in=DREIn,
                pk_field="codigo_dre",
                update_fields=(
                    "nome",
                    "sigla",
                    "tipo_unidade_adm",
                    "descricao_unidade_adm",
                ),
                unique_fields=("codigo_dre",),
                modo_escrita="upsert",
            ),
            PhaseConfig(
                nome="tipo_escola",
                sql=SQL_TIPO_ESCOLA,
                table_name="tipo_escola",
                source_table="tipo_escola",
                model_class=TipoEscola,
                dto_in=TipoEscolaIn,
                pk_field="codigo_tipo_escola",
                update_fields=("sigla", "descricao", "data_atualizacao"),
                unique_fields=("codigo_tipo_escola",),
                modo_escrita="upsert",
            ),
            PhaseConfig(
                nome="sub_prefeitura",
                sql=SQL_SUBPREFEITURA,
                table_name="sub_prefeitura",
                source_table="sub_prefeitura",
                model_class=SubPrefeitura,
                dto_in=SubprefeituraIn,
                pk_field="codigo_sub_prefeitura",
                update_fields=("sigla", "nome"),
                unique_fields=("codigo_sub_prefeitura",),
                modo_escrita="upsert",
            ),
            PhaseConfig(
                nome="unidade_educacional",
                sql=SQL_UNIDADE_EDUCACIONAL,
                table_name="unidade_educacional",
                source_table="v_cadastro_unidade_educacao",
                model_class=UnidadeEducacional,
                dto_in=UnidadeEducacionalIn,
                pk_field="codigo_ue",
                update_fields=(
                    "nome",
                    "nome_nao_oficial",
                    "tipo_ue",
                    "tipo_logradouro",
                    "codigo_logradouro",
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
                    "eh_ceu",
                    "data_atualizacao",
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
                    "codigo_tp_equipamento",
                    "codigo_tipo_unidade_educacao",
                    "subprefeitura_id",
                    "codigo_ue_integracao",
                ),
                unique_fields=("codigo_ue",),
                modo_escrita="upsert",
            ),
        ]

    def executar(self, fase_inicial: int = 1) -> dict[str, int]:
        """Executa as fases, pré-carregando cache SSO antes da fase 1."""
        if fase_inicial <= 1:
            self._popular_cache_integracao_ue()
        return super().executar(fase_inicial)

    def _popular_cache_integracao_ue(self) -> None:
        """Pré-carrega no cache os códigos de integração das UEs por DRE."""
        sso_offline = False
        try:
            rows = self.eol.executar_query(SQL_DRE)
        except Exception:
            return

        for row in rows:
            if sso_offline:
                break
            dre = DREIn(*row)
            codigo_dre = str(dre.codigo_dre)
            key_cache = (
                f"etl_institucional:dre:{codigo_dre}" ":codigos_ues_integracao"
            )
            if self.cache.exist_hash_value(key_cache):
                continue
            try:
                ue_rows = self.eol.executar_query(
                    SQL_OBTER_CODIGOS_UES_POR_DRE, [codigo_dre]
                )
                codigos_ues = [str(r[0]) for r in ue_rows]
                if not codigos_ues:
                    continue
                sso_rows = self.core_sso.obter_codigos_integracao_ues(
                    codigos_ues
                )
                mapeamentos = {str(r[0]): str(r[2]) for r in sso_rows if r[2]}
                if mapeamentos:
                    self.cache.set_hash(
                        key_cache,
                        mapping=mapeamentos,
                        expire_seconds=14400,
                    )
            except Exception as erro:
                logger.warning(
                    "[ETL INST] Falha SSO para DRE %s: %s",
                    codigo_dre,
                    erro,
                )
                sso_offline = True

    def _criar_transform(self, config: PhaseConfig) -> Callable:
        """Delegado ao base, exceto para a fase UE."""
        if config.nome != "unidade_educacional":
            return super()._criar_transform(config)
        return self._build_transform_ue(config)

    def _build_transform_ue(self, config: PhaseConfig) -> Callable:
        """Transform para UE com código integração."""
        hf = sorted(config.update_fields)
        cache_por_dre: dict[str, dict[str, str]] = {}

        def transform(row: tuple) -> tuple:
            dto = UnidadeEducacionalIn(*row)
            codigo_dre = str(dto.codigo_dre) if dto.codigo_dre else ""
            if codigo_dre not in cache_por_dre:
                key = (
                    f"etl_institucional:dre:{codigo_dre}"
                    ":codigos_ues_integracao"
                )
                cache_por_dre[codigo_dre] = self.cache.get_hash(key)
            dto.codigo_ue_integracao = cache_por_dre[codigo_dre].get(
                str(dto.codigo_ue)
            )
            data = dto.to_domain()
            obj = UnidadeEducacional(**data)
            return str(dto.codigo_ue), calcular_hash(obj, hf), obj

        return transform
