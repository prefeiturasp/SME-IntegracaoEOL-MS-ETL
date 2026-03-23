"""Servico ETL do dominio PROFESSORES_DB.

Responsabilidade:
    Ler dados do EOL (SQL Server via EOLService) e popular todos os models
    do app professores no banco professores_db, incluindo as tabelas de
    referência embarcadas para tornar o domínio autossuficiente.

Estrategia de escrita por tabela:
    upsert (bulk_create update_conflicts):
        DRE, TipoEscola, ComponenteCurricular, SerieEnsino,
        TerritorioSaber, TipoExperienciaPedagogica, Grade,
        EscolaGrade, TurmaEscola, SerieTurmaGrade,
        TurmaEscolaGradePrograma,
        Cargo, Professor, FuncaoFuncionarioExterno, Pessoa,
        CargoBaseServidor, ContratoExterno

    full-refresh (delete + bulk_create em transação):
        UnidadeEducacional (desnormalizada — mais simples regenerar)
        TurmaGradeTerritorioExperiencia (PK auto-gerada — sem chave natural)
        LotacaoServidor, CargoSobrepostoServidor,
        FuncaoAtividadeCargoServidor, LaudoMedico,
        AtribuicaoAula, AtribuicaoExterno

    pendente (ApiEolConnection — PostgreSQL separado):
        AgrupamentoAtribuicaoTerritorioSaber

Cargos de professor reconhecidos pelo EOL:
    3239, 3247, 3255, 3263, 3271, 3280, 3298, 3301,
    3336, 3344, 3840, 3859, 3867, 3874, 3883, 3884
"""

import logging
from typing import Any

from django.db import transaction

from apps.eol_connection.libs.servico_eol import EOLService
from apps.professores.models import (
    DRE,
    AtribuicaoAula,
    AtribuicaoExterno,
    Cargo,
    CargoBaseServidor,
    CargoSobrepostoServidor,
    ComponenteCurricular,
    ContratoExterno,
    EscolaGrade,
    FuncaoAtividadeCargoServidor,
    FuncaoFuncionarioExterno,
    Grade,
    LaudoMedico,
    LotacaoServidor,
    Pessoa,
    Professor,
    SerieEnsino,
    SerieTurmaGrade,
    TerritorioSaber,
    TipoEscola,
    TipoExperienciaPedagogica,
    TurmaEscola,
    TurmaEscolaGradePrograma,
    TurmaGradeTerritorioExperiencia,
    UnidadeEducacional,
)

logger = logging.getLogger(__name__)

CARGOS_PROFESSOR = (
    3239,
    3247,
    3255,
    3263,
    3271,
    3280,
    3298,
    3301,
    3336,
    3344,
    3840,
    3859,
    3867,
    3874,
    3883,
    3884,
)

_PLACEHOLDERS_CARGO = ",".join("?" * len(CARGOS_PROFESSOR))

# ---------------------------------------------------------------------------
# SQLs — Tabelas de referência embarcadas
# ---------------------------------------------------------------------------

SQL_DRE = """
    SELECT
        cd_unidade_administrativa,
        nm_unidade_administrativa,
        sg_unidade_administrativa
    FROM unidade_administrativa
    WHERE tp_unidade_administrativa = 24
"""

SQL_TIPO_ESCOLA = """
    SELECT
        cd_tipo_escola,
        nm_tp_escola,
        sg_tp_escola
    FROM tipo_escola
"""

# v_cadastro_unidade_educacao com DRE e tipo_escola desnormalizados
SQL_UNIDADES_EDUCACIONAIS = """
    SELECT
        ue.cd_unidade_educacao,
        ue.nm_unidade_educacao,
        ue.sg_unidade_educacao,
        ue.cd_dre,
        dre.nm_unidade_administrativa AS nm_dre,
        dre.sg_unidade_administrativa AS sg_dre,
        ue.cd_tipo_escola,
        te.sg_tp_escola
    FROM v_cadastro_unidade_educacao ue
    LEFT JOIN unidade_administrativa dre
        ON dre.cd_unidade_administrativa = ue.cd_dre
        AND dre.tp_unidade_administrativa = 24
    LEFT JOIN tipo_escola te
        ON te.cd_tipo_escola = ue.cd_tipo_escola
"""

SQL_COMPONENTES_CURRICULARES = """
    SELECT
        cd_componente_curricular,
        dc_componente_curricular,
        dt_cancelamento
    FROM componente_curricular
"""

SQL_SERIES_ENSINO = """
    SELECT cd_serie_ensino, sg_resumida_serie
    FROM serie_ensino
"""

# Tabela com acento: ajustar nome se necessário no SQL Server
SQL_TERRITORIOS_SABER = """
    SELECT
        cd_territorio_saber,
        dc_territorio_saber
    FROM [território_saber]
"""

SQL_TIPOS_EXPERIENCIA = """
    SELECT
        cd_tipo_experiencia_pedagogica,
        dc_tipo_experiencia_pedagogica
    FROM tipo_experiencia_pedagogica
"""

SQL_GRADES = """
    SELECT
        cd_grade,
        cd_serie_ensino,
        cd_tipo_turno
    FROM grade
"""

SQL_ESCOLA_GRADES = """
    SELECT
        cd_escola_grade,
        cd_unidade_educacao,
        cd_grade
    FROM escola_grade
"""

SQL_TURMAS_ESCOLA = """
    SELECT
        cd_turma_escola,
        cd_unidade_educacao,
        an_letivo,
        nm_turma,
        cd_tipo_turma,
        cd_duracao,
        cd_tipo_turno,
        st_turma_escola,
        dt_inicio_turma,
        dt_fim_turma,
        dt_fim
    FROM turma_escola
"""

SQL_SERIE_TURMA_GRADE = """
    SELECT
        cd_serie_grade,
        cd_turma_escola,
        cd_unidade_educacao,
        cd_escola_grade,
        dt_fim
    FROM serie_turma_grade
"""

SQL_TURMA_ESCOLA_GRADE_PROGRAMA = """
    SELECT
        cd_turma_escola_grade_programa,
        cd_turma_escola,
        cd_escola_grade,
        dt_fim
    FROM turma_escola_grade_programa
"""

SQL_TURMA_GRADE_TERRITORIO = """
    SELECT
        cd_serie_grade,
        cd_componente_curricular,
        cd_territorio_saber,
        cd_tipo_experiencia_pedagogica,
        dt_inicio
    FROM turma_grade_territorio_experiencia
"""

# ---------------------------------------------------------------------------
# SQLs — Dados de professores (EolConnection SQL Server)
# ---------------------------------------------------------------------------

SQL_CARGOS = f"""
    SELECT cd_cargo, dc_cargo
    FROM cargo
    WHERE cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_PROFESSORES = f"""
    SELECT DISTINCT cd_registro_funcional, nm_pessoa, nm_social_pessoa
    FROM v_servidor_cotic
    WHERE cd_cargo IN ({_PLACEHOLDERS_CARGO})
      AND dt_cancelamento IS NULL
"""

SQL_CARGOS_BASE = f"""
    SELECT
        cd_cargo_base_servidor,
        cd_registro_funcional,
        cd_cargo,
        dt_posse,
        dt_fim_nomeacao,
        dt_cancelamento
    FROM v_cargo_base_cotic
    WHERE cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_LOTACOES = """
    SELECT
        ls.cd_cargo_base_servidor,
        ls.cd_unidade_educacao,
        ls.dt_inicio_lotacao,
        ls.dt_fim_lotacao
    FROM lotacao_servidor ls
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = ls.cd_cargo_base_servidor
"""

SQL_CARGOS_SOBREPOSTOS = f"""
    SELECT
        css.cd_cargo_base_servidor,
        css.cd_cargo,
        css.cd_unidade_local_servico,
        css.dt_fim_cargo_sobreposto
    FROM cargo_sobreposto_servidor css
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = css.cd_cargo_base_servidor
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_FUNCOES_ATIVIDADE = f"""
    SELECT
        facs.cd_cargo_base_servidor,
        facs.cd_unidade_local_servico,
        facs.dt_fim_funcao_atividade
    FROM funcao_atividade_cargo_servidor facs
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = facs.cd_cargo_base_servidor
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_LAUDOS = f"""
    SELECT lm.cd_cargo_base_servidor
    FROM laudo_medico lm
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = lm.cd_cargo_base_servidor
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_FUNCOES_EXTERNO = """
    SELECT
        cd_tipo_funcao_funcionario_externo,
        dc_tipo_funcao,
        dt_cancelamento
    FROM funcao_funcionario_externo
"""

SQL_PESSOAS = """
    SELECT
        cd_pessoa,
        cd_cpf_pessoa,
        nm_pessoa,
        nm_social_pessoa
    FROM pessoa
    WHERE cd_pessoa IN (
        SELECT DISTINCT cd_pessoa
        FROM contrato_externo
        WHERE dt_cancelamento IS NULL
    )
"""

SQL_CONTRATOS_EXTERNOS = """
    SELECT
        cd_contrato_externo,
        cd_pessoa,
        cd_tipo_funcao_funcionario_externo,
        cd_unidade_educacao,
        dt_cancelamento,
        cd_motivo_desligamento_externo
    FROM contrato_externo
"""

SQL_ATRIBUICOES_AULA = f"""
    SELECT
        aa.cd_atribuicao_aula,
        aa.cd_cargo_base_servidor,
        aa.cd_unidade_educacao,
        aa.cd_turma_escola,
        aa.cd_turma_escola_grade_programa,
        aa.cd_grade,
        aa.cd_componente_curricular,
        aa.cd_serie_grade,
        aa.an_atribuicao,
        aa.dt_atribuicao_aula,
        aa.dt_disponibilizacao_aulas,
        aa.cd_motivo_disponibilizacao,
        aa.dt_cancelamento
    FROM atribuicao_aula aa
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_ATRIBUICOES_EXTERNO = """
    SELECT
        ae.cd_atribuicao_externo,
        ae.cd_contrato_externo,
        ae.cd_unidade_educacao,
        ae.cd_grade,
        ae.cd_componente_curricular,
        ae.cd_serie_grade,
        ae.cd_turma_escola_grade_programa,
        ae.an_atribuicao,
        ae.dt_atribuicao,
        ae.dt_disponibilizacao,
        ae.cd_motivo_disponibilizacao_externo,
        ae.dt_cancelamento
    FROM atribuicao_externo ae
    INNER JOIN contrato_externo ce
        ON ce.cd_contrato_externo = ae.cd_contrato_externo
    WHERE ce.dt_cancelamento IS NULL
"""


# ---------------------------------------------------------------------------
# Transformadores: tupla EOL → dict de campos do model
# ---------------------------------------------------------------------------


def _row_to_dre(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_dre": str(row[0]).strip(),
        "nome": row[1] or "",
        "sigla": row[2] or None,
    }


def _row_to_tipo_escola(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_tipo_escola": row[0],
        "descricao": row[1] or "",
        "sigla": row[2] or None,
    }


def _row_to_unidade_educacional(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_ue": str(row[0]).strip(),
        "nome": row[1] or "",
        "sigla": row[2] or None,
        "dre_id": str(row[3]).strip() if row[3] else None,
        "nome_dre": row[4] or "",
        "sigla_dre": row[5] or None,
        "tipo_escola_id": row[6] or None,
        "sigla_tipo_escola": row[7] or None,
    }


def _row_to_componente_curricular(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo": row[0],
        "descricao": row[1] or "",
        "dt_cancelamento": row[2],
    }


def _row_to_serie_ensino(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_serie": row[0],
        "sigla_resumida": row[1] or None,
    }


def _row_to_territorio_saber(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_territorio": row[0],
        "descricao": row[1] or "",
    }


def _row_to_tipo_experiencia(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_experiencia": row[0],
        "descricao": row[1] or "",
    }


def _row_to_grade(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_grade": row[0],
        "codigo_serie_ensino": row[1],
        "codigo_tipo_turno": row[2],
    }


def _row_to_escola_grade(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_escola_grade": row[0],
        "codigo_escola": str(row[1]).strip(),
        "grade_id": row[2],
    }


def _row_to_turma_escola(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_turma": row[0],
        "codigo_escola": str(row[1]).strip(),
        "ano_letivo": row[2],
        "nome_turma": row[3] or "",
        "codigo_tipo_turma": row[4],
        "codigo_duracao": row[5],
        "codigo_tipo_turno": row[6],
        "status": row[7] or "",
        "dt_inicio_turma": row[8],
        "dt_fim_turma": row[9],
        "dt_fim": row[10],
    }


def _row_to_serie_turma_grade(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_serie_grade": row[0],
        "turma_id": row[1],
        "codigo_escola": str(row[2]).strip(),
        "escola_grade_id": row[3],
        "dt_fim": row[4],
    }


def _row_to_turma_escola_grade_programa(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo": row[0],
        "turma_id": row[1],
        "escola_grade_id": row[2],
        "dt_fim": row[3],
    }


def _row_to_turma_grade_territorio(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "serie_grade_id": row[0],
        "codigo_componente_curricular": row[1],
        "territorio_saber_id": row[2],
        "experiencia_pedagogica_id": row[3],
        "dt_inicio": row[4],
    }


def _row_to_cargo(row: tuple[Any, ...]) -> dict[str, Any]:
    return {"codigo_cargo": row[0], "descricao": row[1] or ""}


def _row_to_professor(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_rf": str(row[0]).strip(),
        "nome": row[1] or "",
        "nome_social": row[2] or None,
    }


def _row_to_cargo_base(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "professor_id": str(row[1]).strip(),
        "cargo_id": row[2],
        "dt_posse": row[3],
        "dt_fim_nomeacao": row[4],
        "dt_cancelamento": row[5],
    }


def _row_to_lotacao(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "cargo_base_id": row[0],
        "codigo_unidade_educacao": str(row[1]).strip(),
        "dt_inicio": row[2],
        "dt_fim": row[3],
    }


def _row_to_cargo_sobreposto(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "cargo_base_id": row[0],
        "cargo_id": row[1],
        "codigo_unidade_local_servico": str(row[2]).strip(),
        "dt_fim_cargo_sobreposto": row[3],
    }


def _row_to_funcao_atividade(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "cargo_base_id": row[0],
        "codigo_unidade_local_servico": str(row[1]).strip(),
        "dt_fim_funcao_atividade": row[2],
    }


def _row_to_laudo(row: tuple[Any, ...]) -> dict[str, Any]:
    return {"cargo_base_id": row[0]}


def _row_to_funcao_externo(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_tipo_funcao": row[0],
        "descricao": row[1] or "",
        "dt_cancelamento": row[2],
    }


def _row_to_pessoa(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_pessoa": row[0],
        "cpf": str(row[1]).strip(),
        "nome": row[2] or "",
        "nome_social": row[3] or None,
    }


def _row_to_contrato_externo(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_contrato": row[0],
        "pessoa_id": row[1],
        "tipo_funcao_id": row[2],
        "codigo_unidade_educacao": str(row[3]).strip(),
        "dt_cancelamento": row[4],
        "codigo_motivo_desligamento": row[5],
    }


def _row_to_atribuicao_aula(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "cargo_base_id": row[1],
        "codigo_unidade_educacao": str(row[2]).strip(),
        "codigo_turma_escola": row[3],
        "codigo_turma_escola_grade_programa": row[4],
        "codigo_grade": row[5],
        "codigo_componente_curricular": row[6],
        "codigo_serie_grade": row[7],
        "ano_atribuicao": row[8],
        "dt_atribuicao_aula": row[9],
        "dt_disponibilizacao_aulas": row[10],
        "codigo_motivo_disponibilizacao": row[11],
        "dt_cancelamento": row[12],
    }


def _row_to_atribuicao_externo(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "contrato_externo_id": row[1],
        "codigo_unidade_educacao": str(row[2]).strip(),
        "codigo_grade": row[3],
        "codigo_componente_curricular": row[4],
        "codigo_serie_grade": row[5],
        "codigo_turma_escola_grade_programa": row[6],
        "ano_atribuicao": row[7],
        "dt_atribuicao": row[8],
        "dt_disponibilizacao": row[9],
        "codigo_motivo_disponibilizacao_externo": row[10],
        "dt_cancelamento": row[11],
    }


# ---------------------------------------------------------------------------
# Helpers de escrita
# ---------------------------------------------------------------------------


def _upsert(
    model_class: Any,
    objs: list[Any],
    update_fields: list[str],
) -> int:
    """bulk_create com update_conflicts — upsert por PK."""
    if not objs:
        return 0
    pk_name = model_class._meta.pk.name
    criados = model_class.objects.using("professores_db").bulk_create(
        objs,
        update_conflicts=True,
        unique_fields=[pk_name],
        update_fields=update_fields,
    )
    return len(criados)


def _full_refresh(model_class: Any, objs: list[Any]) -> int:
    """Delete + bulk_create em transação atômica."""
    if not objs:
        return 0
    with transaction.atomic(using="professores_db"):
        model_class.objects.using("professores_db").all().delete()
        criados = model_class.objects.using("professores_db").bulk_create(
            objs, batch_size=500
        )
    return len(criados)


def _params_cargo() -> dict[int, int]:
    """Retorna dict de parâmetros posicionais para os cargos de professor."""
    return dict(enumerate(CARGOS_PROFESSOR))


# ---------------------------------------------------------------------------
# Servico principal
# ---------------------------------------------------------------------------


class EtlProfessoresService:
    """Orquestra o ETL completo do dominio PROFESSORES_DB.

    Popula todas as 26 tabelas do banco (13 de referência embarcadas +
    12 de professores + AgrupamentoAtribuicaoTerritorioSaber pendente).
    """

    def __init__(self, eol: EOLService | None = None) -> None:
        """Inicializa o serviço com instância de EOLService."""
        self.eol = eol or EOLService()

    # ------------------------------------------------------------------
    # Fase 1 — Referências sem dependências internas
    # ------------------------------------------------------------------

    def popular_dre(self) -> int:
        """Popula a tabela DRE."""
        rows = self.eol.executar_query(SQL_DRE)
        objs = [DRE(**_row_to_dre(r)) for r in rows]
        return _upsert(DRE, objs, ["nome", "sigla"])

    def popular_tipos_escola(self) -> int:
        """Popula a tabela TipoEscola."""
        rows = self.eol.executar_query(SQL_TIPO_ESCOLA)
        objs = [TipoEscola(**_row_to_tipo_escola(r)) for r in rows]
        return _upsert(TipoEscola, objs, ["descricao", "sigla"])

    def popular_componentes_curriculares(self) -> int:
        """Popula a tabela ComponenteCurricular."""
        rows = self.eol.executar_query(SQL_COMPONENTES_CURRICULARES)
        objs = [ComponenteCurricular(**_row_to_componente_curricular(r)) for r in rows]
        return _upsert(
            ComponenteCurricular,
            objs,
            ["descricao", "dt_cancelamento"],
        )

    def popular_series_ensino(self) -> int:
        """Popula a tabela SerieEnsino."""
        rows = self.eol.executar_query(SQL_SERIES_ENSINO)
        objs = [SerieEnsino(**_row_to_serie_ensino(r)) for r in rows]
        return _upsert(SerieEnsino, objs, ["sigla_resumida"])

    def popular_territorios_saber(self) -> int:
        """Popula a tabela TerritorioSaber."""
        rows = self.eol.executar_query(SQL_TERRITORIOS_SABER)
        objs = [TerritorioSaber(**_row_to_territorio_saber(r)) for r in rows]
        return _upsert(TerritorioSaber, objs, ["descricao"])

    def popular_tipos_experiencia(self) -> int:
        """Popula a tabela TipoExperienciaPedagogica."""
        rows = self.eol.executar_query(SQL_TIPOS_EXPERIENCIA)
        objs = [TipoExperienciaPedagogica(**_row_to_tipo_experiencia(r)) for r in rows]
        return _upsert(TipoExperienciaPedagogica, objs, ["descricao"])

    def popular_grades(self) -> int:
        """Popula a tabela Grade."""
        rows = self.eol.executar_query(SQL_GRADES)
        objs = [Grade(**_row_to_grade(r)) for r in rows]
        return _upsert(Grade, objs, ["codigo_serie_ensino", "codigo_tipo_turno"])

    def popular_cargos(self) -> int:
        """Popula a tabela Cargo."""
        rows = self.eol.executar_query(SQL_CARGOS, _params_cargo())
        objs = [Cargo(**_row_to_cargo(r)) for r in rows]
        return _upsert(Cargo, objs, ["descricao"])

    def popular_funcoes_funcionario_externo(self) -> int:
        """Popula a tabela FuncaoFuncionarioExterno."""
        rows = self.eol.executar_query(SQL_FUNCOES_EXTERNO)
        objs = [FuncaoFuncionarioExterno(**_row_to_funcao_externo(r)) for r in rows]
        return _upsert(
            FuncaoFuncionarioExterno,
            objs,
            ["descricao", "dt_cancelamento"],
        )

    # ------------------------------------------------------------------
    # Fase 2 — Dependem de fase 1
    # ------------------------------------------------------------------

    def popular_unidades_educacionais(self) -> int:
        """Full-refresh: desnormaliza DRE + TipoEscola em cada registro."""
        rows = self.eol.executar_query(SQL_UNIDADES_EDUCACIONAIS)
        objs = [UnidadeEducacional(**_row_to_unidade_educacional(r)) for r in rows]
        return _full_refresh(UnidadeEducacional, objs)

    def popular_escola_grades(self) -> int:
        """Popula a tabela EscolaGrade."""
        rows = self.eol.executar_query(SQL_ESCOLA_GRADES)
        objs = [EscolaGrade(**_row_to_escola_grade(r)) for r in rows]
        return _upsert(EscolaGrade, objs, ["codigo_escola", "grade_id"])

    def popular_turmas_escola(self) -> int:
        """Popula a tabela TurmaEscola."""
        rows = self.eol.executar_query(SQL_TURMAS_ESCOLA)
        objs = [TurmaEscola(**_row_to_turma_escola(r)) for r in rows]
        return _upsert(
            TurmaEscola,
            objs,
            [
                "codigo_escola",
                "ano_letivo",
                "nome_turma",
                "codigo_tipo_turma",
                "codigo_duracao",
                "codigo_tipo_turno",
                "status",
                "dt_inicio_turma",
                "dt_fim_turma",
                "dt_fim",
            ],
        )

    def popular_professores(self) -> int:
        """Popula a tabela Professor."""
        rows = self.eol.executar_query(SQL_PROFESSORES, _params_cargo())
        objs = [Professor(**_row_to_professor(r)) for r in rows]
        return _upsert(Professor, objs, ["nome", "nome_social"])

    def popular_pessoas(self) -> int:
        """Popula a tabela Pessoa."""
        rows = self.eol.executar_query(SQL_PESSOAS)
        objs = [Pessoa(**_row_to_pessoa(r)) for r in rows]
        return _upsert(Pessoa, objs, ["cpf", "nome", "nome_social"])

    # ------------------------------------------------------------------
    # Fase 3 — Dependem de fase 2
    # ------------------------------------------------------------------

    def popular_serie_turma_grade(self) -> int:
        """Popula a tabela SerieTurmaGrade."""
        rows = self.eol.executar_query(SQL_SERIE_TURMA_GRADE)
        objs = [SerieTurmaGrade(**_row_to_serie_turma_grade(r)) for r in rows]
        return _upsert(
            SerieTurmaGrade,
            objs,
            ["turma_id", "codigo_escola", "escola_grade_id", "dt_fim"],
        )

    def popular_turma_escola_grade_programa(self) -> int:
        """Popula a tabela TurmaEscolaGradePrograma."""
        rows = self.eol.executar_query(SQL_TURMA_ESCOLA_GRADE_PROGRAMA)
        objs = [
            TurmaEscolaGradePrograma(**_row_to_turma_escola_grade_programa(r))
            for r in rows
        ]
        return _upsert(
            TurmaEscolaGradePrograma,
            objs,
            ["turma_id", "escola_grade_id", "dt_fim"],
        )

    def popular_cargos_base(self) -> int:
        """Popula a tabela CargoBaseServidor."""
        rows = self.eol.executar_query(SQL_CARGOS_BASE, _params_cargo())
        objs = [CargoBaseServidor(**_row_to_cargo_base(r)) for r in rows]
        return _upsert(
            CargoBaseServidor,
            objs,
            [
                "professor_id",
                "cargo_id",
                "dt_posse",
                "dt_fim_nomeacao",
                "dt_cancelamento",
            ],
        )

    def popular_contratos_externos(self) -> int:
        """Popula a tabela ContratoExterno."""
        rows = self.eol.executar_query(SQL_CONTRATOS_EXTERNOS)
        objs = [ContratoExterno(**_row_to_contrato_externo(r)) for r in rows]
        return _upsert(
            ContratoExterno,
            objs,
            [
                "pessoa_id",
                "tipo_funcao_id",
                "codigo_unidade_educacao",
                "dt_cancelamento",
                "codigo_motivo_desligamento",
            ],
        )

    # ------------------------------------------------------------------
    # Fase 4 — Dependem de fase 3
    # ------------------------------------------------------------------

    def popular_turma_grade_territorio_experiencia(self) -> int:
        """Full-refresh: PK auto-gerada, sem chave natural para upsert."""
        rows = self.eol.executar_query(SQL_TURMA_GRADE_TERRITORIO)
        objs = [
            TurmaGradeTerritorioExperiencia(**_row_to_turma_grade_territorio(r))
            for r in rows
        ]
        return _full_refresh(TurmaGradeTerritorioExperiencia, objs)

    def popular_lotacoes(self) -> int:
        """Popula a tabela LotacaoServidor."""
        rows = self.eol.executar_query(SQL_LOTACOES)
        objs = [LotacaoServidor(**_row_to_lotacao(r)) for r in rows]
        return _full_refresh(LotacaoServidor, objs)

    def popular_cargos_sobrepostos(self) -> int:
        """Popula a tabela CargoSobrepostoServidor."""
        rows = self.eol.executar_query(SQL_CARGOS_SOBREPOSTOS, _params_cargo())
        objs = [CargoSobrepostoServidor(**_row_to_cargo_sobreposto(r)) for r in rows]
        return _full_refresh(CargoSobrepostoServidor, objs)

    def popular_funcoes_atividade(self) -> int:
        """Popula a tabela FuncaoAtividadeCargoServidor."""
        rows = self.eol.executar_query(SQL_FUNCOES_ATIVIDADE, _params_cargo())
        objs = [
            FuncaoAtividadeCargoServidor(**_row_to_funcao_atividade(r)) for r in rows
        ]
        return _full_refresh(FuncaoAtividadeCargoServidor, objs)

    def popular_laudos(self) -> int:
        """Popula a tabela LaudoMedico."""
        rows = self.eol.executar_query(SQL_LAUDOS, _params_cargo())
        objs = [LaudoMedico(**_row_to_laudo(r)) for r in rows]
        return _full_refresh(LaudoMedico, objs)

    def popular_atribuicoes_aula(self) -> int:
        """Popula a tabela AtribuicaoAula."""
        rows = self.eol.executar_query(SQL_ATRIBUICOES_AULA, _params_cargo())
        objs = [AtribuicaoAula(**_row_to_atribuicao_aula(r)) for r in rows]
        return _full_refresh(AtribuicaoAula, objs)

    def popular_atribuicoes_externo(self) -> int:
        """Popula a tabela AtribuicaoExterno."""
        rows = self.eol.executar_query(SQL_ATRIBUICOES_EXTERNO)
        objs = [AtribuicaoExterno(**_row_to_atribuicao_externo(r)) for r in rows]
        return _full_refresh(AtribuicaoExterno, objs)

    # ------------------------------------------------------------------
    # Execucao completa na ordem correta (respeitando FKs internas)
    # ------------------------------------------------------------------

    def executar(self) -> dict[str, int]:
        """Executa ETL completo do dominio PROFESSORES_DB.

        Retorna dict com contagem de registros escritos por tabela.
        AgrupamentoAtribuicaoTerritorioSaber está pendente —
        requer ApiEolConnection (PostgreSQL separado).
        """
        r: dict[str, int] = {}
        log = logger.info

        log("[ETL PROF] Iniciando carga...")

        # Fase 1 — sem dependências
        r["dre"] = self.popular_dre()
        log("[ETL PROF] dre: %d", r["dre"])

        r["tipo_escola"] = self.popular_tipos_escola()
        log("[ETL PROF] tipo_escola: %d", r["tipo_escola"])

        r["componente_curricular"] = self.popular_componentes_curriculares()
        log(
            "[ETL PROF] componente_curricular: %d",
            r["componente_curricular"],
        )

        r["serie_ensino"] = self.popular_series_ensino()
        log("[ETL PROF] serie_ensino: %d", r["serie_ensino"])

        r["territorio_saber"] = self.popular_territorios_saber()
        log("[ETL PROF] territorio_saber: %d", r["territorio_saber"])

        r["tipo_experiencia_pedagogica"] = self.popular_tipos_experiencia()
        log(
            "[ETL PROF] tipo_experiencia_pedagogica: %d",
            r["tipo_experiencia_pedagogica"],
        )

        r["grade"] = self.popular_grades()
        log("[ETL PROF] grade: %d", r["grade"])

        r["cargo"] = self.popular_cargos()
        log("[ETL PROF] cargo: %d", r["cargo"])

        r["funcao_funcionario_externo"] = self.popular_funcoes_funcionario_externo()
        log(
            "[ETL PROF] funcao_funcionario_externo: %d",
            r["funcao_funcionario_externo"],
        )

        # Fase 2 — dependem de fase 1
        r["unidade_educacional"] = self.popular_unidades_educacionais()
        log("[ETL PROF] unidade_educacional: %d", r["unidade_educacional"])

        r["escola_grade"] = self.popular_escola_grades()
        log("[ETL PROF] escola_grade: %d", r["escola_grade"])

        r["turma_escola"] = self.popular_turmas_escola()
        log("[ETL PROF] turma_escola: %d", r["turma_escola"])

        r["professor"] = self.popular_professores()
        log("[ETL PROF] professor: %d", r["professor"])

        r["pessoa"] = self.popular_pessoas()
        log("[ETL PROF] pessoa: %d", r["pessoa"])

        # Fase 3 — dependem de fase 2
        r["serie_turma_grade"] = self.popular_serie_turma_grade()
        log("[ETL PROF] serie_turma_grade: %d", r["serie_turma_grade"])

        r["turma_escola_grade_programa"] = self.popular_turma_escola_grade_programa()
        log(
            "[ETL PROF] turma_escola_grade_programa: %d",
            r["turma_escola_grade_programa"],
        )

        r["cargo_base_servidor"] = self.popular_cargos_base()
        log("[ETL PROF] cargo_base_servidor: %d", r["cargo_base_servidor"])

        r["contrato_externo"] = self.popular_contratos_externos()
        log("[ETL PROF] contrato_externo: %d", r["contrato_externo"])

        # Fase 4 — dependem de fase 3
        r["turma_grade_territorio_experiencia"] = (
            self.popular_turma_grade_territorio_experiencia()
        )
        log(
            "[ETL PROF] turma_grade_territorio_experiencia: %d",
            r["turma_grade_territorio_experiencia"],
        )

        r["lotacao_servidor"] = self.popular_lotacoes()
        log("[ETL PROF] lotacao_servidor: %d", r["lotacao_servidor"])

        r["cargo_sobreposto_servidor"] = self.popular_cargos_sobrepostos()
        log(
            "[ETL PROF] cargo_sobreposto_servidor: %d",
            r["cargo_sobreposto_servidor"],
        )

        r["funcao_atividade_cargo_servidor"] = self.popular_funcoes_atividade()
        log(
            "[ETL PROF] funcao_atividade_cargo_servidor: %d",
            r["funcao_atividade_cargo_servidor"],
        )

        r["laudo_medico"] = self.popular_laudos()
        log("[ETL PROF] laudo_medico: %d", r["laudo_medico"])

        r["atribuicao_aula"] = self.popular_atribuicoes_aula()
        log("[ETL PROF] atribuicao_aula: %d", r["atribuicao_aula"])

        r["atribuicao_externo"] = self.popular_atribuicoes_externo()
        log("[ETL PROF] atribuicao_externo: %d", r["atribuicao_externo"])

        # Pendente: agrupamento_atribuicao_territorio_saber
        # Requer ApiEolConnection (PostgreSQL API EOL — não implementado).
        # Implementar quando EtlApiEolService estiver disponível.

        total = sum(r.values())
        log("[ETL PROF] Concluido. Total: %d registros.", total)
        return r
