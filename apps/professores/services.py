"""Servico ETL do dominio PROFESSORES_DB."""

import hashlib
import logging
from collections.abc import Callable, Iterator
from typing import Any

from django.db.models import Q

from apps.controle_auditoria.models import EtlAuditoriaLinha
from apps.core.libs.thread_processor import ThreadPoolProcessor
from apps.eol_connection.libs.servico_eol import EOLService
from apps.professores.dtos.model_in import (
    AtribuicaoAulaIn,
    AtribuicaoExternoIn,
    CargoBaseServidorIn,
    CargoSobrepostoServidorIn,
    ContratoExternoIn,
    FuncaoAtividadeCargoServidorIn,
    FuncionarioUnidadeEducacionalIn,
    LaudoMedicoIn,
    LotacaoServidorIn,
    PessoaIn,
    ProfessorIn,
)
from apps.professores.dtos.model_out import (
    AtribuicaoAulaOut,
    AtribuicaoExternoOut,
    CargoBaseServidorOut,
    ContratoExternoOut,
    FuncionarioUnidadeEducacionalOut,
    PessoaOut,
    ProfessorOut,
)
from apps.professores.models import (
    AtribuicaoAula,
    AtribuicaoExterno,
    CargoBaseServidor,
    CargoSobrepostoServidor,
    ContratoExterno,
    FuncaoAtividadeCargoServidor,
    FuncionarioUnidadeEducacional,
    LaudoMedico,
    LotacaoServidor,
    Pessoa,
    Professor,
)
from apps.professores.queries import (
    CARGOS_PROFESSOR,
    SQL_ATRIBUICOES_AULA,
    SQL_ATRIBUICOES_EXTERNO,
    SQL_CARGOS_BASE,
    SQL_CARGOS_SOBREPOSTOS,
    SQL_CONTRATOS_EXTERNOS,
    SQL_FUNCIONARIOS_UNIDADE_EDUCACIONAL,
    SQL_FUNCOES_ATIVIDADE,
    SQL_LAUDOS,
    SQL_LOTACOES,
    SQL_PESSOAS,
    SQL_PROFESSORES,
)

logger = logging.getLogger(__name__)


def _row_to_professor(row: tuple) -> dict:
    return ProfessorIn(*row).to_domain().to_dict()


def _row_to_cargo_base(row: tuple) -> dict:
    return CargoBaseServidorIn(*row).to_domain().to_dict()


def _row_to_lotacao(row: tuple) -> dict:
    return LotacaoServidorIn(*row).to_domain().to_dict()


def _row_to_cargo_sobreposto(row: tuple) -> dict:
    return CargoSobrepostoServidorIn(*row).to_domain().to_dict()


def _row_to_funcao_atividade(row: tuple) -> dict:
    return FuncaoAtividadeCargoServidorIn(*row).to_domain().to_dict()


def _row_to_laudo(row: tuple) -> dict:
    return LaudoMedicoIn(*row).to_domain().to_dict()


def _row_to_pessoa(row: tuple) -> dict:
    return PessoaIn(*row).to_domain().to_dict()


def _row_to_contrato_externo(row: tuple) -> dict:
    return ContratoExternoIn(*row).to_domain().to_dict()


def _row_to_atribuicao_aula(row: tuple) -> dict:
    return AtribuicaoAulaIn(*row).to_domain().to_dict()


def _row_to_atribuicao_externo(row: tuple) -> dict:
    return AtribuicaoExternoIn(*row).to_domain().to_dict()


def _row_to_funcionario(row: tuple) -> dict:
    """Converta linha de funcionario para dicionario de destino.

    Args:
        row: Linha retornada pela query consolidada.

    Returns:
        Dados prontos para persistencia no destino.
    """
    return FuncionarioUnidadeEducacionalIn(*row).to_domain().to_dict()


def _full_refresh_por_lote(
    model_class: Any,
    lotes: Iterator[list[Any]],
) -> int:
    """Recarrega a tabela destino removendo tudo e inserindo por lote."""
    # Remove todos os registros e faz bulk_create imediato a cada lote do
    # EOL. Sem transação global: a tabela fica vazia durante a carga,
    # comportamento idêntico ao full-refresh original.
    model_class.objects.using("professores_db").all().delete()
    total = 0
    for objs in lotes:
        if objs:
            criados = model_class.objects.using("professores_db").bulk_create(
                objs, batch_size=500
            )
            total += len(criados)
    return total


def _full_refresh(model_class: Any, objs: list[Any]) -> int:
    """Recarrega a tabela destino a partir de uma lista de objetos."""
    return _full_refresh_por_lote(model_class, iter([objs]))


def _params_cargo(repeticoes: int = 1) -> list[int]:
    """Retorna cargos de professor como parametros posicionais (%s).

    Args:
        repeticoes: Quantidade de grupos de placeholders na consulta.

    Returns:
        Lista de parametros para filtros de cargo.
    """
    return list(CARGOS_PROFESSOR) * repeticoes


_HASH_LOOKUP_BATCH = 1000


def _calcular_hash(campos: dict[str, Any]) -> str:
    """Calcula o SHA-256 dos campos para controle incremental de mudança."""
    # Serializa pares chave=valor em ordem alfabética antes do digest hex.
    conteudo = "|".join(f"{k}={v!r}" for k, v in sorted(campos.items()))
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def _reinsere_se_ausente(
    model_class: Any,
    unique_fields: list[str],
    chaves: list[tuple[Any, ...]],
    map_linha: dict[tuple[Any, ...], tuple[str, str, dict[str, Any]]],
    objs: list[Any],
    hashes: dict[str, str],
) -> None:
    """Força reinserção se o hash não mudou mas o registro sumiu do destino."""
    if not chaves:
        return
    existentes: set[tuple[Any, ...]] = set()
    for i in range(0, len(chaves), _HASH_LOOKUP_BATCH):
        lote = chaves[i : i + _HASH_LOOKUP_BATCH]
        if len(unique_fields) == 1:
            campo = unique_fields[0]
            existentes.update(
                (valor,)
                for valor in model_class.objects.using("professores_db")
                .filter(**{f"{campo}__in": [chave[0] for chave in lote]})
                .values_list(campo, flat=True)
            )
            continue

        filtro = Q()
        for chave in lote:
            filtro |= Q(**dict(zip(unique_fields, chave, strict=True)))
        existentes.update(
            tuple(valores)
            for valores in model_class.objects.using("professores_db")
            .filter(filtro)
            .values_list(*unique_fields)
        )
    for chave, (id_dest, novo_h, row_dict) in map_linha.items():
        if chave not in existentes:
            objs.append(model_class(**row_dict))
            hashes[id_dest] = novo_h


def _upsert_incremental(
    model_class: Any,
    tabela: str,
    rows: list[dict[str, Any]],
    update_fields: list[str],
    unique_fields: list[str] | None = None,
) -> int:
    """Upsert apenas registros cujo hash de linha mudou."""
    if not rows:
        return 0

    pk_name: str = model_class._meta.pk.name
    campos_unique = unique_fields or [pk_name]
    campos_update = [
        campo
        for campo in update_fields
        if campo not in campos_unique and campo != pk_name
    ]
    campos_hash = list(dict.fromkeys([*campos_unique, *update_fields]))

    linhas: list[tuple[str, str, dict[str, Any]]] = []
    for row_dict in rows:
        chave = tuple(row_dict[campo] for campo in campos_unique)
        chave_serializada = tuple(str(valor) for valor in chave)
        id_destino = f"{tabela}:{'|'.join(chave_serializada)}"
        valores_hash = {k: row_dict.get(k) for k in campos_hash}
        linhas.append((id_destino, _calcular_hash(valores_hash), row_dict))

    ids_destino = [item[0] for item in linhas]
    hashes_existentes: dict[str, str] = {}
    for i in range(0, len(ids_destino), _HASH_LOOKUP_BATCH):
        lote = ids_destino[i : i + _HASH_LOOKUP_BATCH]
        hashes_existentes.update(
            EtlAuditoriaLinha.objects.filter(id_destino__in=lote).values_list(
                "id_destino", "hash_controle"
            )
        )

    objs_para_salvar: list[Any] = []
    novos_hashes: dict[str, str] = {}
    chaves_hash_inalterado: list[tuple[Any, ...]] = []
    map_chave_para_linha: dict[
        tuple[Any, ...], tuple[str, str, dict[str, Any]]
    ] = {}
    for id_destino, novo_hash, row_dict in linhas:
        chave = tuple(row_dict[campo] for campo in campos_unique)
        if hashes_existentes.get(id_destino) != novo_hash:
            objs_para_salvar.append(model_class(**row_dict))
            novos_hashes[id_destino] = novo_hash
        else:
            chaves_hash_inalterado.append(chave)
            map_chave_para_linha[chave] = (id_destino, novo_hash, row_dict)

    _reinsere_se_ausente(
        model_class,
        campos_unique,
        chaves_hash_inalterado,
        map_chave_para_linha,
        objs_para_salvar,
        novos_hashes,
    )

    if not objs_para_salvar:
        return 0

    seen_chaves: set[tuple[Any, ...]] = set()
    objs_dedup: list[Any] = []
    for obj in objs_para_salvar:
        chave = tuple(getattr(obj, campo) for campo in campos_unique)
        if chave not in seen_chaves:
            seen_chaves.add(chave)
            objs_dedup.append(obj)
    objs_para_salvar = objs_dedup

    model_class.objects.using("professores_db").bulk_create(
        objs_para_salvar,
        update_conflicts=True,
        unique_fields=campos_unique,
        update_fields=campos_update,
        batch_size=500,
    )

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


_TABELAS_FULL_REFRESH: frozenset[str] = frozenset(
    {
        "lotacao_servidor",
        "cargo_sobreposto_servidor",
        "funcao_atividade_cargo_servidor",
        "laudo_medico",
    }
)

_ORDEM_TABELAS: tuple[str, ...] = (
    "professor",
    "pessoa",
    "cargo_base_servidor",
    "contrato_externo",
    "lotacao_servidor",
    "cargo_sobreposto_servidor",
    "funcao_atividade_cargo_servidor",
    "laudo_medico",
    "atribuicao_aula",
    "atribuicao_externo",
    "funcionario_unidade_educacional",
)


class EtlProfessoresService:
    """Orquestra o ETL completo do dominio PROFESSORES_DB."""

    def __init__(self, eol: EOLService | None = None) -> None:
        """Inicializa o serviço com instância de EOLService."""
        self.eol = eol or EOLService()
        self.ultima_fase_concluida: int = 0

    def popular_professores(self) -> int:
        """Popula a tabela Professor."""
        total = 0
        with ThreadPoolProcessor(prefixo_log="PROF:professor") as proc:
            for chunk in self.eol.iter_query(SQL_PROFESSORES, _params_cargo()):
                out_objs: list[ProfessorOut] = proc.processar(
                    chunk,
                    lambda r: ProfessorIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    Professor,
                    "professor",
                    [o.to_dict() for o in out_objs],
                    ["nome", "nome_social", "cpf"],
                )
        return total

    def popular_pessoas(self) -> int:
        """Popula a tabela Pessoa."""
        total = 0
        with ThreadPoolProcessor(prefixo_log="PROF:pessoa") as proc:
            for chunk in self.eol.iter_query(SQL_PESSOAS):
                out_objs: list[PessoaOut] = proc.processar(
                    chunk,
                    lambda r: PessoaIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    Pessoa,
                    "pessoa",
                    [o.to_dict() for o in out_objs],
                    ["cpf", "nome", "nome_social"],
                )
        return total

    def popular_cargos_base(self) -> int:
        """Popula a tabela CargoBaseServidor."""
        total = 0
        with ThreadPoolProcessor(
            prefixo_log="PROF:cargo_base_servidor"
        ) as proc:
            for chunk in self.eol.iter_query(SQL_CARGOS_BASE, _params_cargo()):
                out_objs: list[CargoBaseServidorOut] = proc.processar(
                    chunk,
                    lambda r: CargoBaseServidorIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    CargoBaseServidor,
                    "cargo_base_servidor",
                    [o.to_dict() for o in out_objs],
                    [
                        "professor_id",
                        "codigo_cargo",
                        "descricao_cargo",
                        "situacao_funcional",
                        "dt_posse",
                        "dt_fim_nomeacao",
                        "dt_cancelamento",
                    ],
                )
        return total

    def popular_contratos_externos(self) -> int:
        """Popula a tabela ContratoExterno."""
        total = 0
        with ThreadPoolProcessor(prefixo_log="PROF:contrato_externo") as proc:
            for chunk in self.eol.iter_query(SQL_CONTRATOS_EXTERNOS):
                out_objs: list[ContratoExternoOut] = proc.processar(
                    chunk,
                    lambda r: ContratoExternoIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    ContratoExterno,
                    "contrato_externo",
                    [o.to_dict() for o in out_objs],
                    [
                        "pessoa_id",
                        "codigo_tipo_funcao",
                        "codigo_unidade_educacao",
                        "dt_cancelamento",
                        "codigo_motivo_desligamento",
                    ],
                )
        return total

    def popular_lotacoes(self) -> int:
        """Popula a tabela LotacaoServidor por lote."""
        with ThreadPoolProcessor(prefixo_log="PROF:lotacao_servidor") as proc:
            return _full_refresh_por_lote(
                LotacaoServidor,
                (
                    [
                        LotacaoServidor(**o.to_dict())
                        for o in proc.processar(
                            chunk,
                            lambda r: LotacaoServidorIn(*r).to_domain(),
                        )
                    ]
                    for chunk in self.eol.iter_query(SQL_LOTACOES)
                ),
            )

    def popular_cargos_sobrepostos(self) -> int:
        """Popula a tabela CargoSobrepostoServidor por lote."""
        _dto_in = CargoSobrepostoServidorIn
        with ThreadPoolProcessor(
            prefixo_log="PROF:cargo_sobreposto_servidor"
        ) as proc:
            return _full_refresh_por_lote(
                CargoSobrepostoServidor,
                (
                    [
                        CargoSobrepostoServidor(**o.to_dict())
                        for o in proc.processar(
                            chunk,
                            lambda r: _dto_in(*r).to_domain(),
                        )
                    ]
                    for chunk in self.eol.iter_query(
                        SQL_CARGOS_SOBREPOSTOS, _params_cargo()
                    )
                ),
            )

    def popular_funcoes_atividade(self) -> int:
        """Popula a tabela FuncaoAtividadeCargoServidor por lote."""
        _dto_in = FuncaoAtividadeCargoServidorIn
        with ThreadPoolProcessor(
            prefixo_log="PROF:funcao_atividade_cargo_servidor"
        ) as proc:
            return _full_refresh_por_lote(
                FuncaoAtividadeCargoServidor,
                (
                    [
                        FuncaoAtividadeCargoServidor(**o.to_dict())
                        for o in proc.processar(
                            chunk,
                            lambda r: _dto_in(*r).to_domain(),
                        )
                    ]
                    for chunk in self.eol.iter_query(
                        SQL_FUNCOES_ATIVIDADE, _params_cargo()
                    )
                ),
            )

    def popular_laudos(self) -> int:
        """Popula a tabela LaudoMedico por lote."""
        with ThreadPoolProcessor(prefixo_log="PROF:laudo_medico") as proc:
            return _full_refresh_por_lote(
                LaudoMedico,
                (
                    [
                        LaudoMedico(**o.to_dict())
                        for o in proc.processar(
                            chunk,
                            lambda r: LaudoMedicoIn(*r).to_domain(),
                        )
                    ]
                    for chunk in self.eol.iter_query(
                        SQL_LAUDOS, _params_cargo()
                    )
                ),
            )

    def popular_atribuicoes_aula(self) -> int:
        """Popula a tabela AtribuicaoAula via hash incremental."""
        total = 0
        with ThreadPoolProcessor(prefixo_log="PROF:atribuicao_aula") as proc:
            for chunk in self.eol.iter_query(
                SQL_ATRIBUICOES_AULA, _params_cargo()
            ):
                out_objs: list[AtribuicaoAulaOut] = proc.processar(
                    chunk,
                    lambda r: AtribuicaoAulaIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    AtribuicaoAula,
                    "atribuicao_aula",
                    [o.to_dict() for o in out_objs],
                    [
                        "cargo_base_id",
                        "codigo_unidade_educacao",
                        "codigo_turma_escola",
                        "descricao_turma_escola",
                        "codigo_turma_escola_grade_programa",
                        "codigo_grade",
                        "codigo_componente_curricular",
                        "descricao_componente_curricular",
                        "codigo_serie_grade",
                        "ano_escolar",
                        "ano_atribuicao",
                        "codigo_etapa_ensino",
                        "dt_atribuicao_aula",
                        "dt_disponibilizacao_aulas",
                        "codigo_motivo_disponibilizacao",
                        "dt_cancelamento",
                    ],
                )
        return total

    def popular_atribuicoes_externo(self) -> int:
        """Popula a tabela AtribuicaoExterno via hash incremental."""
        total = 0
        with ThreadPoolProcessor(
            prefixo_log="PROF:atribuicao_externo"
        ) as proc:
            for chunk in self.eol.iter_query(SQL_ATRIBUICOES_EXTERNO):
                out_objs: list[AtribuicaoExternoOut] = proc.processar(
                    chunk,
                    lambda r: AtribuicaoExternoIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    AtribuicaoExterno,
                    "atribuicao_externo",
                    [o.to_dict() for o in out_objs],
                    [
                        "contrato_externo_id",
                        "codigo_unidade_educacao",
                        "codigo_turma_escola",
                        "descricao_turma_escola",
                        "codigo_grade",
                        "codigo_componente_curricular",
                        "descricao_componente_curricular",
                        "codigo_serie_grade",
                        "codigo_turma_escola_grade_programa",
                        "ano_escolar",
                        "ano_atribuicao",
                        "codigo_etapa_ensino",
                        "dt_atribuicao",
                        "dt_disponibilizacao",
                        "codigo_motivo_disponibilizacao_externo",
                        "dt_cancelamento",
                    ],
                )
        return total

    def popular_funcionarios(self) -> int:
        """Popula funcionario por UE via hash incremental.

        Returns:
            Quantidade de linhas inseridas ou atualizadas.
        """
        total = 0
        with ThreadPoolProcessor(
            prefixo_log="PROF:funcionario_unidade_educacional"
        ) as proc:
            for chunk in self.eol.iter_query(
                SQL_FUNCIONARIOS_UNIDADE_EDUCACIONAL, _params_cargo()
            ):
                out_objs: list[FuncionarioUnidadeEducacionalOut] = (
                    proc.processar(
                        chunk,
                        lambda r: FuncionarioUnidadeEducacionalIn(
                            *r
                        ).to_domain(),
                    )
                )
                total += _upsert_incremental(
                    FuncionarioUnidadeEducacional,
                    "funcionario_unidade_educacional",
                    [o.to_dict() for o in out_objs],
                    [
                        "nome",
                        "nome_social",
                        "cpf",
                        "codigo_ue",
                        "data_inicio",
                        "data_fim",
                        "codigo_cargo",
                        "cargo",
                        "codigo_tipo_funcao_atividade",
                        "eh_professor",
                        "esta_afastado",
                        "funcao_externo",
                        "tipo_funcao_externo",
                    ],
                    [
                        "codigo_rf",
                        "codigo_ue",
                        "codigo_cargo",
                        "codigo_tipo_funcao_atividade",
                        "data_inicio",
                        "data_fim",
                        "funcao_externo",
                        "tipo_funcao_externo",
                    ],
                )
        return total

    def _fase_1(
        self,
        executar_tabela: Callable[[str, Callable[[], int]], None],
    ) -> None:
        """Fase 1 — tabelas sem dependências internas."""
        logger.info("[ETL PROF] === Fase 1: Professores e Pessoas ===")
        executar_tabela("professor", self.popular_professores)
        executar_tabela("pessoa", self.popular_pessoas)
        self.ultima_fase_concluida = 1
        logger.info("[ETL PROF] Fase 1 concluída.")

    def _fase_2(
        self,
        executar_tabela: Callable[[str, Callable[[], int]], None],
    ) -> None:
        """Fase 2 — vínculos cargo/contrato (dependem da fase 1)."""
        logger.info("[ETL PROF] === Fase 2: Vínculos ===")
        executar_tabela("cargo_base_servidor", self.popular_cargos_base)
        executar_tabela("contrato_externo", self.popular_contratos_externos)
        self.ultima_fase_concluida = 2
        logger.info("[ETL PROF] Fase 2 concluída.")

    def _fase_3(
        self,
        executar_tabela: Callable[[str, Callable[[], int]], None],
    ) -> None:
        """Fase 3 — atribuições e bloqueios (dependem da fase 2)."""
        logger.info("[ETL PROF] === Fase 3: Atribuições e Bloqueios ===")
        executar_tabela("lotacao_servidor", self.popular_lotacoes)
        executar_tabela(
            "cargo_sobreposto_servidor", self.popular_cargos_sobrepostos
        )
        executar_tabela(
            "funcao_atividade_cargo_servidor",
            self.popular_funcoes_atividade,
        )
        executar_tabela("laudo_medico", self.popular_laudos)
        executar_tabela("atribuicao_aula", self.popular_atribuicoes_aula)
        executar_tabela("atribuicao_externo", self.popular_atribuicoes_externo)
        self.ultima_fase_concluida = 3
        logger.info("[ETL PROF] Fase 3 concluída.")

    def _fase_4(
        self,
        executar_tabela: Callable[[str, Callable[[], int]], None],
    ) -> None:
        """Executa fase final de funcionarios.

        Args:
            executar_tabela: Callback de execucao com auditoria/checkpoint.
        """
        logger.info("[ETL PROF] === Fase 4: Funcionarios ===")
        executar_tabela(
            "funcionario_unidade_educacional", self.popular_funcionarios
        )
        self.ultima_fase_concluida = 4
        logger.info("[ETL PROF] Fase 4 concluida.")

    def _iter_lotes(
        self,
        sql: str,
        parametros: list | dict | None,
        original: Callable,
        offset: int,
        nome: str,
        lote_counter: list[int],
        on_lote: Callable[[str, int], None] | None,
    ) -> Iterator[list[tuple[Any, ...]]]:
        """Itera chunks do EOL aplicando offset e disparando on_lote."""
        for i, chunk in enumerate(original(sql, parametros)):
            if i < offset:
                continue
            lote_counter[0] += 1
            yield chunk
            if on_lote is not None:
                on_lote(nome, lote_counter[0])

    def executar(
        self,
        fase_inicial: int = 1,
        pular_ate: str | None = None,
        lote_inicial: int = 0,
        on_lote: Callable[[str, int], None] | None = None,
        on_tabela_concluida: Callable[[str, int], None] | None = None,
    ) -> dict[str, int]:
        """Executa ETL_PROFESSORES a partir de ``fase_inicial``."""
        r: dict[str, int] = {}
        log = logger.info

        log("[ETL PROF] Iniciando carga a partir da fase %d...", fase_inicial)

        _pular = pular_ate
        _li = [lote_inicial]

        original_iter_query = self.eol.iter_query

        def _executar_tabela(nome: str, metodo: Callable[[], int]) -> None:
            """Executa tabela, pulando se ainda no intervalo a pular."""
            nonlocal _pular
            if _pular is not None:
                if _pular == nome:
                    _pular = None
                    _li[0] = 0
                log("[ETL PROF] Pulando %s (já concluída).", nome)
                return

            li = 0 if nome in _TABELAS_FULL_REFRESH else _li[0]
            _li[0] = 0

            if li:
                log(
                    "[ETL PROF] %s: retomando do lote %d.",
                    nome,
                    li + 1,
                )

            _lote_counter = [li]

            def _iter_rastreavel(
                sql: str,
                parametros: list | dict | None = None,
            ) -> Iterator[list[tuple[Any, ...]]]:
                return self._iter_lotes(
                    sql,
                    parametros,
                    original_iter_query,
                    li,
                    nome,
                    _lote_counter,
                    on_lote,
                )

            self.eol.iter_query = _iter_rastreavel  # type: ignore[method-assign]
            try:
                r[nome] = metodo()
            finally:
                self.eol.iter_query = original_iter_query  # type: ignore[method-assign]

            log("[ETL PROF] %s: %d", nome, r[nome])
            if on_tabela_concluida is not None:
                on_tabela_concluida(nome, r[nome])

        if fase_inicial <= 1:
            self._fase_1(_executar_tabela)
            _pular = None  # fases seguintes rodam completas

        if fase_inicial <= 2:
            self._fase_2(_executar_tabela)
            _pular = None

        if fase_inicial <= 3:
            self._fase_3(_executar_tabela)

        if fase_inicial <= 4:
            self._fase_4(_executar_tabela)

        total = sum(r.values())
        log(
            "[ETL PROF] Concluído. Linhas alteradas: %d (fases %d-4).",
            total,
            fase_inicial,
        )
        return r
