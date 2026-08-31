"""Servico ETL do dominio PROFESSORES_DB."""

import hashlib
import logging
import os
from collections.abc import Callable, Iterator
from inspect import Parameter, signature
from typing import Any, cast

from django.db.models import Q

from apps.controle_auditoria.models import EtlAuditoriaLinha
from apps.core.libs.base_etl_service import PhaseConfig
from apps.core.libs.thread_processor import ThreadPoolProcessor
from apps.eol_connection.libs.servico_eol import EOLService
from apps.institucional.libs.repositorio_core_sso import RepositorioCoreSSO
from apps.professores.dtos.model_in import (
    AtribuicaoAulaIn,
    AtribuicaoExternoIn,
    CargoBaseServidorIn,
    CargoSobrepostoServidorIn,
    ContratoExternoIn,
    DisciplinaTurmaAtribuidaUeIn,
    FuncaoAtividadeCargoServidorIn,
    FuncionarioCargoIn,
    FuncionarioConectaFormacaoIn,
    FuncionarioConectaModalidadeEscolaIn,
    FuncionarioSistemaPerfilIn,
    FuncionarioUnidadeEducacionalIn,
    FuncionarioVinculoFuncionalIn,
    LaudoMedicoIn,
    LotacaoServidorIn,
    PessoaIn,
    ProfessorEscolaAnoIn,
    ProfessorIn,
    TurmaAtribuidaUeIn,
)
from apps.professores.dtos.model_out import (
    AtribuicaoAulaOut,
    AtribuicaoExternoOut,
    CargoBaseServidorOut,
    FuncionarioSistemaPerfilOut,
    FuncionarioUnidadeEducacionalOut,
)
from apps.professores.models import (
    AdministradorEscola,
    AtribuicaoAula,
    AtribuicaoExterno,
    CargoBaseServidor,
    CargoSobrepostoServidor,
    ContratoExterno,
    DisciplinaTurmaAtribuidaUe,
    FuncaoAtividadeCargoServidor,
    FuncionarioCargo,
    FuncionarioConectaFormacao,
    FuncionarioConectaModalidadeEscola,
    FuncionarioSistemaPerfil,
    FuncionarioUnidadeEducacional,
    FuncionarioVinculoFuncional,
    LaudoMedico,
    LotacaoServidor,
    Pessoa,
    Professor,
    ProfessorEscolaAno,
    TurmaAtribuidaUe,
)
from apps.professores.queries import (
    CARGOS_PROFESSOR,
    SQL_ADMINISTRADORES_SGP,
    SQL_ATRIBUICOES_AULA,
    SQL_ATRIBUICOES_EXTERNO,
    SQL_CARGOS_BASE,
    SQL_CARGOS_SOBREPOSTOS,
    SQL_CODIGOS_ESCOLAS_PROFESSORES_ANO,
    SQL_CONTRATOS_EXTERNOS,
    SQL_DISCIPLINAS_TURMAS_ATRIBUIDAS_UE,
    SQL_FUNCIONARIO_SISTEMA_PERFIL,
    SQL_FUNCIONARIOS_CARGOS,
    SQL_FUNCIONARIOS_CONECTA_FORMACAO,
    SQL_FUNCIONARIOS_CONECTA_MODALIDADE_ESCOLA,
    SQL_FUNCIONARIOS_UNIDADE_EDUCACIONAL,
    SQL_FUNCIONARIOS_VINCULOS_FUNCIONAIS,
    SQL_FUNCOES_ATIVIDADE,
    SQL_LAUDOS,
    SQL_LOTACOES,
    SQL_PESSOAS,
    SQL_PROFESSORES,
    SQL_PROFESSORES_ESCOLA_ANO,
    SQL_TURMAS_ATRIBUIDAS_UE,
)

logger = logging.getLogger(__name__)

_QTD_CAMPOS_ATRIBUICAO_AULA_LEGADO = 18
_QTD_CAMPOS_ATRIBUICAO_AULA_ATUAL = 31
_QTD_CAMPOS_ATRIBUICAO_EXTERNO_LEGADO = 18
_QTD_CAMPOS_ATRIBUICAO_EXTERNO_ATUAL = 19
_QTD_CAMPOS_CARGO_BASE = 8

_MARCADORES_ANO_LETIVO = {
    "/*FILTRO_ANO_LETIVO_ATRIBUICAO_AULA*/": "",
    "/*FILTRO_ANO_LETIVO_ATRIBUICAO_EXTERNO*/": "",
    "/*FILTRO_ANO_LETIVO_TURMAS_ATRIBUIDAS_UE*/": "",
    "/*FILTRO_ANO_LETIVO_DISCIPLINAS_TURMAS_ATRIBUIDAS_UE*/": "",
    "/*FILTRO_ANO_LETIVO_ESCOLAS_PROFESSORES_ANO*/": "",
    "/*FILTRO_ANO_LETIVO_PROFESSORES_ESCOLA_ANO*/": "",
    "/*FILTRO_ESCOLA_PROFESSORES_ESCOLA_ANO*/": "",
}


def _row_to_professor(row: tuple) -> dict:
    return ProfessorIn(*row).to_domain().to_dict()


def _row_to_cargo_base(row: tuple) -> dict:
    return _cargo_base_in(row).to_domain().to_dict()


def _cargo_base_in(row: tuple) -> CargoBaseServidorIn:
    return CargoBaseServidorIn(*row[:_QTD_CAMPOS_CARGO_BASE])


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
    return _atribuicao_aula_in(row).to_domain().to_dict()


def _atribuicao_aula_in(row: tuple) -> AtribuicaoAulaIn:
    if len(row) == _QTD_CAMPOS_ATRIBUICAO_AULA_LEGADO:
        row = row + (None,) * (_QTD_CAMPOS_ATRIBUICAO_AULA_ATUAL - len(row))
    return AtribuicaoAulaIn(*row)


def _row_to_atribuicao_externo(row: tuple) -> dict:
    return _atribuicao_externo_in(row).to_domain().to_dict()


def _atribuicao_externo_in(row: tuple) -> AtribuicaoExternoIn:
    if len(row) == _QTD_CAMPOS_ATRIBUICAO_EXTERNO_LEGADO:
        row = row + (None,) * (_QTD_CAMPOS_ATRIBUICAO_EXTERNO_ATUAL - len(row))
    return AtribuicaoExternoIn(*row)


def _row_to_funcionario(row: tuple) -> dict:
    """Converta linha de funcionario para dicionario de destino.

    Args:
        row: Linha retornada pela query consolidada.

    Returns:
        Dados prontos para persistencia no destino.
    """
    return FuncionarioUnidadeEducacionalIn(*row).to_domain().to_dict()


def _row_to_funcionario_cargo(row: tuple) -> dict:
    """Monta o dicionário da linha de funcionário por cargo."""
    return cast(dict, FuncionarioCargoIn(*row).to_domain().to_dict())


def _row_to_professor_escola_ano(row: tuple) -> dict:
    """Monta o dicionário da linha de professor por escola e ano."""
    return cast(dict, ProfessorEscolaAnoIn(*row).to_domain().to_dict())


def _row_to_funcionario_vinculo_funcional(row: tuple) -> dict:
    """Monta o dicionário da linha de vínculo funcional."""
    return cast(
        dict,
        FuncionarioVinculoFuncionalIn(*row).to_domain().to_dict(),
    )


def _row_to_funcionario_conecta_formacao(row: tuple) -> dict:
    """Monta o dicionário da linha do Conecta Formação."""
    return cast(
        dict,
        FuncionarioConectaFormacaoIn(*row).to_domain().to_dict(),
    )


def _row_to_funcionario_conecta_modalidade_escola(row: tuple) -> dict:
    """Monta o dicionário da linha de modalidade por unidade."""
    return cast(
        dict,
        FuncionarioConectaModalidadeEscolaIn(*row).to_domain().to_dict(),
    )


def _row_to_funcionario_sistema_perfil(row: tuple) -> dict:
    """Monta o dicionário da linha de perfil de sistema."""
    return cast(dict, FuncionarioSistemaPerfilIn(*row).to_domain().to_dict())


def _row_to_turma_atribuida_ue(row: tuple) -> dict:
    """Monta o dicionário da linha de turma atribuída por UE."""
    return cast(dict, TurmaAtribuidaUeIn(*row).to_domain().to_dict())


def _row_to_disciplina_turma_atribuida_ue(row: tuple) -> dict:
    """Monta o dicionário da linha de disciplina atribuída por UE."""
    return cast(dict, DisciplinaTurmaAtribuidaUeIn(*row).to_domain().to_dict())


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


def _linhas_com_hash(
    tabela: str,
    rows: list[dict[str, Any]],
    campos_unique: list[str],
    campos_hash: list[str],
) -> list[tuple[str, str, dict[str, Any]]]:
    """Monta linhas com identificador e hash de controle.

    Args:
        tabela: Nome da tabela processada.
        rows: Registros recebidos para carga.
        campos_unique: Campos usados para identificar o registro.
        campos_hash: Campos usados no controle de mudança.

    Returns:
        Linhas com identificador, hash e dados originais.
    """
    linhas: list[tuple[str, str, dict[str, Any]]] = []
    for row_dict in rows:
        chave = tuple(row_dict[campo] for campo in campos_unique)
        chave_serializada = tuple(str(valor) for valor in chave)
        id_destino = f"{tabela}:{'|'.join(chave_serializada)}"
        valores_hash = {k: row_dict.get(k) for k in campos_hash}
        linhas.append((id_destino, _calcular_hash(valores_hash), row_dict))
    return linhas


def _buscar_hashes_existentes(ids_destino: list[str]) -> dict[str, str]:
    """Retorna hashes existentes para os registros informados.

    Args:
        ids_destino: Identificadores dos registros.

    Returns:
        Hashes encontrados por identificador.
    """
    if os.getenv("ETL_SKIP_AUDIT_HASH") == "1":
        return {}

    hashes_existentes: dict[str, str] = {}
    for i in range(0, len(ids_destino), _HASH_LOOKUP_BATCH):
        lote = ids_destino[i : i + _HASH_LOOKUP_BATCH]
        hashes_existentes.update(
            EtlAuditoriaLinha.objects.filter(id_destino__in=lote).values_list(
                "id_destino", "hash_controle"
            )
        )
    return hashes_existentes


def _deduplicar_objetos(
    objs: list[Any],
    campos_unique: list[str],
) -> list[Any]:
    """Remove objetos repetidos pela chave da carga.

    Args:
        objs: Objetos preparados para gravação.
        campos_unique: Campos usados para identificar o objeto.

    Returns:
        Objetos sem repetição pela chave informada.
    """
    vistos: set[tuple[Any, ...]] = set()
    deduplicados: list[Any] = []
    for obj in objs:
        chave = tuple(getattr(obj, campo) for campo in campos_unique)
        if chave in vistos:
            continue
        vistos.add(chave)
        deduplicados.append(obj)
    return deduplicados


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

    linhas = _linhas_com_hash(tabela, rows, campos_unique, campos_hash)
    ids_destino = [item[0] for item in linhas]
    hashes_existentes = _buscar_hashes_existentes(ids_destino)

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

    objs_para_salvar = _deduplicar_objetos(objs_para_salvar, campos_unique)

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
    if os.getenv("ETL_SKIP_AUDIT_HASH") == "1":
        return len(objs_para_salvar)

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
        "funcionario_cargo",
        "funcionario_vinculo_funcional",
        "funcionario_conecta_modalidade_escola",
        "funcionario_conecta_formacao",
        "turma_atribuida_ue",
        "disciplina_turma_atribuida_ue",
        "administrador_escola",
    }
)

_ORDEM_TABELAS: tuple[str, ...] = (
    "professor",
    "pessoa",
    "administrador_escola",
    "cargo_base_servidor",
    "contrato_externo",
    "lotacao_servidor",
    "cargo_sobreposto_servidor",
    "funcao_atividade_cargo_servidor",
    "laudo_medico",
    "atribuicao_aula",
    "atribuicao_externo",
    "funcionario_unidade_educacional",
    "funcionario_cargo",
    "funcionario_vinculo_funcional",
    "funcionario_conecta_modalidade_escola",
    "funcionario_conecta_formacao",
    "funcionario_sistema_perfil",
    "turma_atribuida_ue",
    "disciplina_turma_atribuida_ue",
    "professor_escola_ano",
)


def _callback_aceita_linhas_lidas(callback: Callable[..., None]) -> bool:
    """Indica se callback de lote aceita o tamanho do chunk."""
    try:
        parametros = signature(callback).parameters.values()
    except (TypeError, ValueError):
        return True

    posicionais = {
        Parameter.POSITIONAL_ONLY,
        Parameter.POSITIONAL_OR_KEYWORD,
    }
    total = 0
    for parametro in parametros:
        if parametro.kind == Parameter.VAR_POSITIONAL:
            return True
        if parametro.kind in posicionais:
            total += 1
    return total >= 3


class EtlProfessoresService:
    """Orquestra o ETL completo do dominio PROFESSORES_DB."""

    def __init__(
        self,
        eol: EOLService | None = None,
        anos_letivos: list[int] | None = None,
        core_sso: RepositorioCoreSSO | None = None,
    ) -> None:
        """Inicializa o serviço.

        Args:
            eol: Cliente EOL; instanciado sob demanda quando omitido.
            anos_letivos: Anos letivos aplicados ao filtro incremental.
            core_sso: Repositório CoreSSO.
        """
        self.eol = eol or EOLService()
        self.core_sso = core_sso or RepositorioCoreSSO()
        self._anos_letivos = (
            [int(ano) for ano in anos_letivos] if anos_letivos else None
        )
        self.ultima_fase_concluida: int = 0
        self._fases = self._init_fases()
        self._fases_por_nome = {fase.nome: fase for fase in self._fases}

    def _init_fases(self) -> list[PhaseConfig]:
        """Retorna as fases padronizáveis do domínio professores."""
        return [
            PhaseConfig(
                nome="professor",
                sql=SQL_PROFESSORES,
                table_name="professor",
                source_table="v_servidor_cotic",
                model_class=Professor,
                dto_in=ProfessorIn,
                pk_field="codigo_rf",
                update_fields=("nome", "nome_social", "cpf"),
                unique_fields=("codigo_rf",),
                modo_escrita="upsert",
            ),
            PhaseConfig(
                nome="pessoa",
                sql=SQL_PESSOAS,
                table_name="pessoa",
                source_table="v_pessoa_cotic",
                model_class=Pessoa,
                dto_in=PessoaIn,
                pk_field="codigo_pessoa",
                update_fields=(
                    "cpf",
                    "nome",
                    "nome_social",
                    "nome_pai",
                    "nome_mae",
                    "data_nascimento",
                    "rg",
                    "titulo_eleitoral",
                    "pis_pasep",
                ),
                unique_fields=("codigo_pessoa",),
                modo_escrita="upsert",
            ),
            PhaseConfig(
                nome="contrato_externo",
                sql=SQL_CONTRATOS_EXTERNOS,
                table_name="contrato_externo",
                source_table="contrato_externo",
                model_class=ContratoExterno,
                dto_in=ContratoExternoIn,
                pk_field="codigo_contrato",
                update_fields=(
                    "pessoa_id",
                    "codigo_tipo_funcao",
                    "codigo_unidade_educacao",
                    "dt_cancelamento",
                    "codigo_motivo_desligamento",
                ),
                unique_fields=("codigo_contrato",),
                modo_escrita="upsert",
            ),
            PhaseConfig(
                nome="lotacao_servidor",
                sql=SQL_LOTACOES,
                table_name="lotacao_servidor",
                source_table="lotacao_servidor",
                model_class=LotacaoServidor,
                dto_in=LotacaoServidorIn,
                pk_field="id",
                update_fields=(),
                unique_fields=(),
                modo_escrita="full_refresh",
            ),
            PhaseConfig(
                nome="cargo_sobreposto_servidor",
                sql=SQL_CARGOS_SOBREPOSTOS,
                table_name="cargo_sobreposto_servidor",
                source_table="cargo_sobreposto_servidor",
                model_class=CargoSobrepostoServidor,
                dto_in=CargoSobrepostoServidorIn,
                pk_field="id",
                update_fields=(),
                unique_fields=(),
                modo_escrita="full_refresh",
            ),
            PhaseConfig(
                nome="funcao_atividade_cargo_servidor",
                sql=SQL_FUNCOES_ATIVIDADE,
                table_name="funcao_atividade_cargo_servidor",
                source_table="funcao_atividade_cargo_servidor",
                model_class=FuncaoAtividadeCargoServidor,
                dto_in=FuncaoAtividadeCargoServidorIn,
                pk_field="id",
                update_fields=(),
                unique_fields=(),
                modo_escrita="full_refresh",
            ),
            PhaseConfig(
                nome="laudo_medico",
                sql=SQL_LAUDOS,
                table_name="laudo_medico",
                source_table="laudo_medico",
                model_class=LaudoMedico,
                dto_in=LaudoMedicoIn,
                pk_field="id",
                update_fields=(),
                unique_fields=(),
                modo_escrita="full_refresh",
            ),
            PhaseConfig(
                nome="funcionario_cargo",
                sql=SQL_FUNCIONARIOS_CARGOS,
                table_name="funcionario_cargo",
                source_table="funcionario_cargo",
                model_class=FuncionarioCargo,
                dto_in=FuncionarioCargoIn,
                pk_field="id",
                update_fields=(),
                unique_fields=(),
                modo_escrita="full_refresh",
            ),
            PhaseConfig(
                nome="funcionario_vinculo_funcional",
                sql=SQL_FUNCIONARIOS_VINCULOS_FUNCIONAIS,
                table_name="funcionario_vinculo_funcional",
                source_table="funcionario_vinculo_funcional",
                model_class=FuncionarioVinculoFuncional,
                dto_in=FuncionarioVinculoFuncionalIn,
                pk_field="id",
                update_fields=(),
                unique_fields=(),
                modo_escrita="full_refresh",
            ),
            PhaseConfig(
                nome="funcionario_conecta_modalidade_escola",
                sql=SQL_FUNCIONARIOS_CONECTA_MODALIDADE_ESCOLA,
                table_name="funcionario_conecta_modalidade_escola",
                source_table="funcionario_conecta_modalidade_escola",
                model_class=FuncionarioConectaModalidadeEscola,
                dto_in=FuncionarioConectaModalidadeEscolaIn,
                pk_field="id",
                update_fields=(),
                unique_fields=(),
                modo_escrita="full_refresh",
            ),
            PhaseConfig(
                nome="funcionario_conecta_formacao",
                sql=SQL_FUNCIONARIOS_CONECTA_FORMACAO,
                table_name="funcionario_conecta_formacao",
                source_table="funcionario_conecta_formacao",
                model_class=FuncionarioConectaFormacao,
                dto_in=FuncionarioConectaFormacaoIn,
                pk_field="id",
                update_fields=(),
                unique_fields=(),
                modo_escrita="full_refresh",
            ),
            PhaseConfig(
                nome="turma_atribuida_ue",
                sql=SQL_TURMAS_ATRIBUIDAS_UE,
                table_name="turma_atribuida_ue",
                source_table="turma_atribuida_ue",
                model_class=TurmaAtribuidaUe,
                dto_in=TurmaAtribuidaUeIn,
                pk_field="id",
                update_fields=(),
                unique_fields=(),
                modo_escrita="full_refresh",
            ),
            PhaseConfig(
                nome="disciplina_turma_atribuida_ue",
                sql=SQL_DISCIPLINAS_TURMAS_ATRIBUIDAS_UE,
                table_name="disciplina_turma_atribuida_ue",
                source_table="disciplina_turma_atribuida_ue",
                model_class=DisciplinaTurmaAtribuidaUe,
                dto_in=DisciplinaTurmaAtribuidaUeIn,
                pk_field="id",
                update_fields=(),
                unique_fields=(),
                modo_escrita="full_refresh",
            ),
        ]

    def _sql_com_filtro_ano_letivo(self, consulta: str) -> str:
        """Aplica o recorte de anos letivos quando informado.

        Args:
            consulta: Texto base usado na carga.

        Returns:
            Texto com recorte aplicado quando houver anos letivos.
        """
        filtros = _MARCADORES_ANO_LETIVO
        if self._anos_letivos is not None:
            anos = ", ".join(str(ano) for ano in self._anos_letivos)
            filtros = {
                "/*FILTRO_ANO_LETIVO_ATRIBUICAO_AULA*/": (
                    f"AND aa.an_atribuicao IN ({anos})"
                ),
                "/*FILTRO_ANO_LETIVO_ATRIBUICAO_EXTERNO*/": (
                    f"AND ae.an_atribuicao IN ({anos})"
                ),
                "/*FILTRO_ANO_LETIVO_TURMAS_ATRIBUIDAS_UE*/": (
                    f"AND AnoLetivo IN ({anos})"
                ),
                "/*FILTRO_ANO_LETIVO_DISCIPLINAS_TURMAS_ATRIBUIDAS_UE*/": (
                    f"AND tau.AnoLetivo IN ({anos})"
                ),
                "/*FILTRO_ANO_LETIVO_PROFESSORES_ESCOLA_ANO*/": (
                    f"AND turma_escola.an_letivo IN ({anos})"
                ),
                "/*FILTRO_ANO_LETIVO_ESCOLAS_PROFESSORES_ANO*/": (
                    f"AND turma_escola.an_letivo IN ({anos})"
                ),
            }
        for marcador, filtro in filtros.items():
            consulta = consulta.replace(marcador, filtro)
        return consulta

    def _sql_professores_escola_ano(
        self, codigo_escola: str | None = None
    ) -> str:
        """Monta consulta de professores por escola e ano.

        Args:
            codigo_escola: Código EOL da escola consultada.

        Returns:
            Consulta com os filtros aplicáveis.
        """
        consulta = self._sql_com_filtro_ano_letivo(SQL_PROFESSORES_ESCOLA_ANO)
        filtro = "AND turma_escola.cd_escola = %s" if codigo_escola else ""
        return consulta.replace(
            "/*FILTRO_ESCOLA_PROFESSORES_ESCOLA_ANO*/", filtro
        )

    def _codigos_escolas_professores_ano(self) -> list[str]:
        """Lista escolas para carga de professores por escola e ano.

        Returns:
            Códigos EOL das escolas encontradas.
        """
        consulta = self._sql_com_filtro_ano_letivo(
            SQL_CODIGOS_ESCOLAS_PROFESSORES_ANO
        )
        return [
            str(row[0]).strip() for row in self.eol.executar_query(consulta)
        ]

    def _parametros_fase(self, nome: str) -> list[int] | None:
        """Retorna parâmetros posicionais da fase, quando existirem."""
        if nome in {
            "professor",
            "cargo_base_servidor",
            "cargo_sobreposto_servidor",
            "funcao_atividade_cargo_servidor",
            "laudo_medico",
        }:
            return _params_cargo()
        return None

    def _sql_fase(self, config: PhaseConfig) -> str:
        """Retorna SQL da fase com filtros anuais aplicáveis."""
        if config.nome in {
            "turma_atribuida_ue",
            "disciplina_turma_atribuida_ue",
        }:
            return self._sql_com_filtro_ano_letivo(config.sql)
        return config.sql

    def _popular_config(self, nome: str) -> int:
        """Executa uma fase padronizada por PhaseConfig."""
        config = self._fases_por_nome[nome]
        if config.modo_escrita == "full_refresh":
            return self._popular_config_full_refresh(config)
        return self._popular_config_upsert(config)

    def _popular_config_upsert(self, config: PhaseConfig) -> int:
        """Executa carga incremental descrita por PhaseConfig."""
        total = 0
        parametros = self._parametros_fase(config.nome)
        with ThreadPoolProcessor(prefixo_log=f"PROF:{config.nome}") as proc:
            for chunk in self.eol.iter_query(
                self._sql_fase(config), parametros
            ):
                out_objs = proc.processar(
                    chunk,
                    lambda r: config.dto_in(*r).to_domain(),
                )
                total += _upsert_incremental(
                    config.model_class,
                    config.table_name,
                    [o.to_dict() for o in out_objs],
                    list(config.update_fields),
                    list(config.unique_fields),
                )
        return total

    def _popular_config_full_refresh(self, config: PhaseConfig) -> int:
        """Executa carga full-refresh descrita por PhaseConfig."""
        parametros = self._parametros_fase(config.nome)
        with ThreadPoolProcessor(prefixo_log=f"PROF:{config.nome}") as proc:
            return _full_refresh_por_lote(
                config.model_class,
                (
                    [
                        config.model_class(**o.to_dict())
                        for o in proc.processar(
                            chunk,
                            lambda r: config.dto_in(*r).to_domain(),
                        )
                    ]
                    for chunk in self.eol.iter_query(
                        self._sql_fase(config), parametros
                    )
                ),
            )

    def popular_professores(self) -> int:
        """Popula a tabela Professor."""
        return self._popular_config("professor")

    def popular_pessoas(self) -> int:
        """Popula a tabela Pessoa."""
        return self._popular_config("pessoa")

    def popular_cargos_base(self) -> int:
        """Popula a tabela CargoBaseServidor."""
        total = 0
        with ThreadPoolProcessor(
            prefixo_log="PROF:cargo_base_servidor"
        ) as proc:
            for chunk in self.eol.iter_query(SQL_CARGOS_BASE, _params_cargo()):
                out_objs: list[CargoBaseServidorOut] = proc.processar(
                    chunk,
                    lambda r: _cargo_base_in(r).to_domain(),
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
        return self._popular_config("contrato_externo")

    def popular_lotacoes(self) -> int:
        """Popula a tabela LotacaoServidor por lote."""
        return self._popular_config("lotacao_servidor")

    def popular_cargos_sobrepostos(self) -> int:
        """Popula a tabela CargoSobrepostoServidor por lote."""
        return self._popular_config("cargo_sobreposto_servidor")

    def popular_funcoes_atividade(self) -> int:
        """Popula a tabela FuncaoAtividadeCargoServidor por lote."""
        return self._popular_config("funcao_atividade_cargo_servidor")

    def popular_laudos(self) -> int:
        """Popula a tabela LaudoMedico por lote."""
        return self._popular_config("laudo_medico")

    def popular_atribuicoes_aula(self) -> int:
        """Popula a tabela AtribuicaoAula via hash incremental."""
        total = 0
        with ThreadPoolProcessor(prefixo_log="PROF:atribuicao_aula") as proc:
            for chunk in self.eol.iter_query(
                self._sql_com_filtro_ano_letivo(SQL_ATRIBUICOES_AULA),
                _params_cargo(),
            ):
                out_objs: list[AtribuicaoAulaOut] = proc.processar(
                    chunk,
                    lambda r: _atribuicao_aula_in(r).to_domain(),
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
                        "dt_disponibilizacao_aulas_origem",
                        "dt_inicio_turma",
                        "dt_fim_turma",
                        "codigo_motivo_disponibilizacao",
                        "dt_cancelamento",
                        "codigo_dre",
                        "nome_dre",
                        "abreviacao_dre",
                        "nome_unidade_educacional",
                        "codigo_tipo_escola",
                        "codigo_tipo_turma",
                        "modalidade",
                        "codigo_modalidade",
                        "semestre",
                        "duracao_turno",
                        "tipo_turno",
                    ],
                )
        return total

    def popular_atribuicoes_externo(self) -> int:
        """Popula a tabela AtribuicaoExterno via hash incremental."""
        total = 0
        with ThreadPoolProcessor(
            prefixo_log="PROF:atribuicao_externo"
        ) as proc:
            for chunk in self.eol.iter_query(
                self._sql_com_filtro_ano_letivo(SQL_ATRIBUICOES_EXTERNO)
            ):
                out_objs: list[AtribuicaoExternoOut] = proc.processar(
                    chunk,
                    lambda r: _atribuicao_externo_in(r).to_domain(),
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
                        "dt_inicio_turma",
                        "dt_fim_turma",
                        "codigo_motivo_disponibilizacao_externo",
                        "dt_cancelamento",
                    ],
                )
        return total

    def popular_funcionarios(self) -> int:
        """Popula funcionario por UE.

        Returns:
            Quantidade de linhas inseridas.
        """
        total = 0
        FuncionarioUnidadeEducacional.objects.using(
            "professores_db"
        ).all().delete()
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
                        "codigo_dre",
                        "data_inicio",
                        "data_fim",
                        "dt_fim_nomeacao",
                        "dt_fim_funcao_atividade",
                        "origem_vinculo",
                        "codigo_cargo",
                        "cargo",
                        "codigo_tipo_funcao_atividade",
                        "pessoa_id",
                        "nome_ue",
                        "tipo_funcionario_externo",
                        "dc_funcao_externo",
                        "supervisor_dre",
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

    def popular_funcionarios_cargos(self) -> int:
        """Popula funcionários por cargo."""
        return self._popular_config("funcionario_cargo")

    def popular_professores_escola_ano(self) -> int:
        """Popula professores por escola e ano."""
        destino = ProfessorEscolaAno.objects.using("professores_db")
        consultas: list[tuple[str, list[str] | None]]
        if self._anos_letivos is None:
            destino.all().delete()
            consultas = [(self._sql_professores_escola_ano(), None)]
        else:
            destino.filter(ano_letivo__in=self._anos_letivos).delete()
            consultas = [
                (
                    self._sql_professores_escola_ano(codigo_escola),
                    [codigo_escola, codigo_escola],
                )
                for codigo_escola in self._codigos_escolas_professores_ano()
            ]

        total = 0
        for consulta, parametros in consultas:
            for chunk in self.eol.iter_query(consulta, parametros):
                objs = [
                    ProfessorEscolaAno(**_row_to_professor_escola_ano(row))
                    for row in chunk
                ]
                if objs:
                    criados = destino.bulk_create(
                        objs,
                        batch_size=500,
                        ignore_conflicts=True,
                    )
                    total += len(criados)
        return total

    def popular_funcionarios_vinculos_funcionais(self) -> int:
        """Popula vínculos funcionais consolidados por funcionário.

        A carga materializa cargo base, cargo sobreposto e função atividade
        em uma mesma linha para consultas por RF. A origem permanece no EOL e
        os filtros de vínculos ativos seguem o comportamento legado desse
        contrato.

        Returns:
            Quantidade de vínculos funcionais gravados.
        """
        return self._popular_config("funcionario_vinculo_funcional")

    def popular_funcionarios_conecta_modalidade_escola(self) -> int:
        """Popula modalidades por unidade para o Conecta Formação.

        Returns:
            Quantidade de modalidades por unidade gravadas.
        """
        return self._popular_config("funcionario_conecta_modalidade_escola")

    def popular_funcionarios_conecta_formacao(self) -> int:
        """Popula funcionários elegíveis para o Conecta Formação.

        Returns:
            Quantidade de funcionários gravados.
        """
        return self._popular_config("funcionario_conecta_formacao")

    def popular_funcionarios_sistema_perfil(self) -> int:
        """Popula perfis de sistema usados por contratos legados."""
        rows = self.core_sso.factory.executar_consulta(
            SQL_FUNCIONARIO_SISTEMA_PERFIL
        )
        with ThreadPoolProcessor(
            prefixo_log="PROF:funcionario_sistema_perfil"
        ) as proc:
            out_objs: list[FuncionarioSistemaPerfilOut] = proc.processar(
                rows,
                lambda r: FuncionarioSistemaPerfilIn(*r).to_domain(),
            )
        return _upsert_incremental(
            FuncionarioSistemaPerfil,
            "funcionario_sistema_perfil",
            [o.to_dict() for o in out_objs],
            ["nome_servidor", "cpf", "email", "uad_codigo"],
            ["login", "perfil", "sis_id"],
        )

    def popular_turmas_atribuidas_ue(self) -> int:
        """Popula turmas atribuídas por vínculo do funcionário com UE."""
        return self._popular_config("turma_atribuida_ue")

    def popular_disciplinas_turmas_atribuidas_ue(self) -> int:
        """Popula disciplinas atribuídas por vínculo do funcionário com UE."""
        return self._popular_config("disciplina_turma_atribuida_ue")

    def popular_administradores_sgp(self) -> int:
        """Popula administradores SGP do CoreSSO.

        Returns:
            Quantidade de registros inseridos.
        """
        try:
            logger.info(
                "Iniciando sincronização de administradores SGP do CoreSSO"
            )

            rows = self.core_sso.factory.executar_consulta(
                SQL_ADMINISTRADORES_SGP
            )

            dados = [
                AdministradorEscola(codigo_ue=str(row[0]), rf_login=row[1])
                for row in rows
            ]

            total = _full_refresh(AdministradorEscola, dados)
            total_escolas = len({d.codigo_ue for d in dados})

            logger.info(
                f"Sincronizados {total} administradores "
                f"em {total_escolas} escolas"
            )

            return total

        except Exception:
            logger.exception("Erro ao sincronizar administradores SGP")
            return 0

    def _fase_1(
        self,
        executar_tabela: Callable[[str, Callable[[], int]], None],
    ) -> None:
        """Fase 1 — tabelas sem dependências internas."""
        logger.info("[ETL PROF] === Fase 1: Professores e Pessoas ===")
        executar_tabela("professor", self.popular_professores)
        executar_tabela("pessoa", self.popular_pessoas)
        executar_tabela(
            "administrador_escola", self.popular_administradores_sgp
        )
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
        executar_tabela("funcionario_cargo", self.popular_funcionarios_cargos)
        executar_tabela(
            "funcionario_vinculo_funcional",
            self.popular_funcionarios_vinculos_funcionais,
        )
        executar_tabela(
            "funcionario_conecta_modalidade_escola",
            self.popular_funcionarios_conecta_modalidade_escola,
        )
        executar_tabela(
            "funcionario_conecta_formacao",
            self.popular_funcionarios_conecta_formacao,
        )
        executar_tabela(
            "funcionario_sistema_perfil",
            self.popular_funcionarios_sistema_perfil,
        )
        executar_tabela(
            "turma_atribuida_ue", self.popular_turmas_atribuidas_ue
        )
        executar_tabela(
            "disciplina_turma_atribuida_ue",
            self.popular_disciplinas_turmas_atribuidas_ue,
        )
        executar_tabela(
            "professor_escola_ano", self.popular_professores_escola_ano
        )
        self.ultima_fase_concluida = 4
        logger.info("[ETL PROF] Fase 4 concluida.")

    def _iter_lotes(
        self,
        sql: str,
        parametros: list | dict | None,
        original: Callable,
        lotes_ignorados: int,
        nome: str,
        lote_counter: list[int],
        on_lote: Callable[..., None] | None,
    ) -> Iterator[list[tuple[Any, ...]]]:
        """Itera chunks do EOL pulando lotes já salvos no checkpoint."""
        for i, chunk in enumerate(original(sql, parametros)):
            if i < lotes_ignorados:
                continue
            lote_counter[0] += 1
            yield chunk
            if on_lote is not None:
                if _callback_aceita_linhas_lidas(on_lote):
                    on_lote(nome, lote_counter[0], len(chunk))
                else:
                    on_lote(nome, lote_counter[0])

    def _executar_tabela_rastreada(
        self,
        nome: str,
        metodo: Callable[[], int],
        resultados: dict[str, int],
        pular_ref: dict[str, str | None],
        lote_ref: list[int],
        original_iter_query: Callable,
        on_lote: Callable[..., None] | None,
        on_tabela_iniciada: Callable[[str], None] | None,
        on_tabela_concluida: Callable[[str, int], None] | None,
    ) -> None:
        """Executa uma tabela com suporte a checkpoint por lote."""
        if pular_ref["nome"] is not None:
            if pular_ref["nome"] == nome:
                pular_ref["nome"] = None
                lote_ref[0] = 0
            logger.info("[ETL PROF] Pulando %s (já concluída).", nome)
            return

        lote_inicial = 0 if nome in _TABELAS_FULL_REFRESH else lote_ref[0]
        lote_ref[0] = 0

        if lote_inicial:
            logger.info(
                "[ETL PROF] %s: retomando do lote %d.",
                nome,
                lote_inicial + 1,
            )

        lote_counter = [lote_inicial]
        if on_tabela_iniciada is not None:
            on_tabela_iniciada(nome)

        def _iter_rastreavel(
            sql: str,
            parametros: list | dict | None = None,
        ) -> Iterator[list[tuple[Any, ...]]]:
            return self._iter_lotes(
                sql,
                parametros,
                original_iter_query,
                lote_inicial,
                nome,
                lote_counter,
                on_lote,
            )

        self.eol.iter_query = _iter_rastreavel  # type: ignore[method-assign]
        try:
            resultados[nome] = metodo()
        finally:
            self.eol.iter_query = original_iter_query  # type: ignore[method-assign]

        logger.info("[ETL PROF] %s: %d", nome, resultados[nome])
        if on_tabela_concluida is not None:
            on_tabela_concluida(nome, resultados[nome])

    def executar(
        self,
        fase_inicial: int = 1,
        pular_ate: str | None = None,
        lote_inicial: int = 0,
        on_lote: Callable[..., None] | None = None,
        on_tabela_iniciada: Callable[[str], None] | None = None,
        on_tabela_concluida: Callable[[str, int], None] | None = None,
    ) -> dict[str, int]:
        """Executa ETL_PROFESSORES a partir de ``fase_inicial``."""
        r: dict[str, int] = {}

        logger.info(
            "[ETL PROF] Iniciando carga a partir da fase %d...", fase_inicial
        )

        pular_ref = {"nome": pular_ate}
        lote_ref = [lote_inicial]

        original_iter_query = self.eol.iter_query

        def _executar_tabela(nome: str, metodo: Callable[[], int]) -> None:
            """Executa tabela usando rastreamento de checkpoint."""
            self._executar_tabela_rastreada(
                nome,
                metodo,
                r,
                pular_ref,
                lote_ref,
                original_iter_query,
                on_lote,
                on_tabela_iniciada,
                on_tabela_concluida,
            )

        if fase_inicial <= 1:
            self._fase_1(_executar_tabela)
            pular_ref["nome"] = None  # fases seguintes rodam completas

        if fase_inicial <= 2:
            self._fase_2(_executar_tabela)
            pular_ref["nome"] = None

        if fase_inicial <= 3:
            self._fase_3(_executar_tabela)

        if fase_inicial <= 4:
            self._fase_4(_executar_tabela)

        total = sum(r.values())
        logger.info(
            "[ETL PROF] Concluído. Linhas alteradas: %d (fases %d-4).",
            total,
            fase_inicial,
        )
        return r
