"""Verificadores de compatibilidade: FuncionarioRepository e ValidadeProf.

Cobre:
    FuncionarioRepository.BuscaFuncionarioPorRfAsync
        Valida que CargoBaseServidor replica corretamente dt_posse,
        dt_fim_nomeacao e situacao_funcional do servidor.

    ProfessorRepository.VerificarValidadeProfessorAsync
        Valida que os campos de bloqueio (LaudoMedico, CargoSobrepostoServidor)
        e situacao_funcional estão presentes para a lógica de elegibilidade.
"""

from typing import Any

from apps.professores.compat.base import (
    VerificadorBase,
    _formatar_data,
)
from apps.professores.models import CargoBaseServidor, LaudoMedico
from apps.professores.services import _PLACEHOLDERS_CARGO, CARGOS_PROFESSOR

# ---------------------------------------------------------------------------
# Consultas SQL Server (origem)
# ---------------------------------------------------------------------------

_SQL_CARGO_BASE_ATIVO = f"""
    SELECT DISTINCT TOP {{limite}}
        cbs.cd_cargo_base_servidor  AS id_cargo_base,
        sc.cd_registro_funcional    AS codigo_rf,
        cbs.cd_cargo                AS codigo_cargo,
        cbs.cd_situacao_funcional   AS situacao_funcional,
        cbs.dt_posse,
        cbs.dt_fim_nomeacao
    FROM v_cargo_base_cotic cbs
    INNER JOIN v_servidor_cotic sc ON sc.cd_servidor = cbs.cd_servidor
    WHERE cbs.dt_fim_nomeacao IS NULL
      AND cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
    ORDER BY cbs.cd_cargo_base_servidor
"""

_CARGOS_VALIDADE = list(CARGOS_PROFESSOR)
_PLACEHOLDERS_VALIDADE = ",".join(["%s"] * len(_CARGOS_VALIDADE))

_SQL_VALIDADE = f"""
    SELECT DISTINCT TOP {{limite}}
        cba.cd_cargo_base_servidor  AS id_cargo_base,
        serv.cd_registro_funcional  AS codigo_rf,
        cba.cd_situacao_funcional   AS situacao_funcional,
        CAST(
            CASE
                WHEN NOT EXISTS (
                    SELECT 1 FROM laudo_medico lm
                    WHERE lm.cd_cargo_base_servidor =
                          cba.cd_cargo_base_servidor
                ) THEN 1 ELSE 0
            END
        AS BIT) AS sem_laudo,
        CAST(
            CASE
                WHEN NOT EXISTS (
                    SELECT 1 FROM cargo_sobreposto_servidor css
                    WHERE css.cd_cargo_base_servidor =
                          cba.cd_cargo_base_servidor
                      AND (css.dt_fim_cargo_sobreposto IS NULL
                           OR css.dt_fim_cargo_sobreposto > GETDATE())
                      AND css.cd_cargo NOT IN (3379, 3085, 3360)
                ) THEN 1 ELSE 0
            END
        AS BIT) AS sem_sobreposto
    FROM v_servidor_cotic serv
    INNER JOIN v_cargo_base_cotic cba
        ON cba.cd_servidor = serv.cd_servidor
    INNER JOIN cargo car ON cba.cd_cargo = car.cd_cargo
    LEFT JOIN lotacao_servidor ls
        ON cba.cd_cargo_base_servidor = ls.cd_cargo_base_servidor
    WHERE car.cd_cargo IN ({_PLACEHOLDERS_VALIDADE})
      AND (ls.dt_fim IS NULL
           OR (ls.dt_fim IS NOT NULL AND ls.dt_fim < GETDATE()))
    ORDER BY cba.cd_cargo_base_servidor
"""


# ---------------------------------------------------------------------------
# Verificador 1: BuscaFuncionarioPorRfAsync
# ---------------------------------------------------------------------------


class VerificadorCargoBaseAtivo(VerificadorBase):
    """Valida CargoBaseServidor — BuscaFuncionarioPorRfAsync.

    Chave: (id_cargo_base, codigo_rf, codigo_cargo, dt_posse).
    """

    nome = "FuncionarioRepository"
    nome_consulta = "BuscaFuncionarioPorRfAsync"

    def buscar_origem(self, eol: Any, limite: int) -> list[dict[str, Any]]:
        """Busca cargos base ativos na origem com dt_fim_nomeacao IS NULL."""
        sql = _SQL_CARGO_BASE_ATIVO.format(limite=limite)
        linhas = eol.executar_query(sql, list(CARGOS_PROFESSOR))
        return [
            {
                "id_cargo_base": r[0],
                "codigo_rf": str(r[1]).strip(),
                "codigo_cargo": r[2],
                "situacao_funcional": r[3],
                "dt_posse": _formatar_data(r[4]),
                "dt_fim_nomeacao": _formatar_data(r[5]),
            }
            for r in linhas
        ]

    def buscar_destino(
        self, linhas_origem: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Busca os mesmos cargos base no professores_db."""
        pks = [r["id_cargo_base"] for r in linhas_origem]
        consulta = (
            CargoBaseServidor.objects.using("professores_db")
            .filter(pk__in=pks)
            .values(
                "id",
                "professor_id",
                "codigo_cargo",
                "situacao_funcional",
                "dt_posse",
                "dt_fim_nomeacao",
            )
        )
        return [
            {
                "id_cargo_base": linha["id"],
                "codigo_rf": linha["professor_id"],
                "codigo_cargo": linha["codigo_cargo"],
                "situacao_funcional": linha["situacao_funcional"],
                "dt_posse": _formatar_data(linha["dt_posse"]),
                "dt_fim_nomeacao": _formatar_data(linha["dt_fim_nomeacao"]),
            }
            for linha in consulta
        ]

    def chave_comparacao(self, linha: dict[str, Any]) -> tuple:
        """Chave: id_cargo_base + codigo_rf + codigo_cargo + dt_posse."""
        return (
            linha["id_cargo_base"],
            linha["codigo_rf"],
            linha["codigo_cargo"],
            linha["dt_posse"],
        )


# ---------------------------------------------------------------------------
# Verificador 2: VerificarValidadeProfessorAsync — campos de bloqueio
# ---------------------------------------------------------------------------


class VerificadorValidadeProf(VerificadorBase):
    """Valida campos de bloqueio de elegibilidade.

    VerificarValidadeProfessorAsync — verifica que:
      - situacao_funcional está armazenado corretamente.
      - A ausência de laudo_medico no destino é consistente com a origem.

    Chave: (id_cargo_base, situacao_funcional, sem_laudo).
    """

    nome = "ProfessorRepository"
    nome_consulta = "VerificarValidadeProfessorAsync"

    def buscar_origem(self, eol: Any, limite: int) -> list[dict[str, Any]]:
        """Busca cargos com campos de bloqueio calculados na origem."""
        sql = _SQL_VALIDADE.format(limite=limite)
        linhas = eol.executar_query(sql, _CARGOS_VALIDADE)
        return [
            {
                "id_cargo_base": r[0],
                "codigo_rf": str(r[1]).strip(),
                "situacao_funcional": r[2],
                "sem_laudo": bool(r[3]),
            }
            for r in linhas
        ]

    def buscar_destino(
        self, linhas_origem: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Reconstrói o estado de bloqueio a partir do professores_db."""
        pks = [r["id_cargo_base"] for r in linhas_origem]
        cargos = (
            CargoBaseServidor.objects.using("professores_db")
            .filter(pk__in=pks)
            .values("id", "professor_id", "situacao_funcional")
        )
        ids_com_laudo = set(
            LaudoMedico.objects.using("professores_db")
            .filter(cargo_base_id__in=pks)
            .values_list("cargo_base_id", flat=True)
        )
        return [
            {
                "id_cargo_base": linha["id"],
                "codigo_rf": linha["professor_id"],
                "situacao_funcional": linha["situacao_funcional"],
                "sem_laudo": linha["id"] not in ids_com_laudo,
            }
            for linha in cargos
        ]

    def chave_comparacao(self, linha: dict[str, Any]) -> tuple:
        """Chave: id_cargo_base + situacao_funcional + sem_laudo."""
        return (
            linha["id_cargo_base"],
            linha["situacao_funcional"],
            linha["sem_laudo"],
        )
