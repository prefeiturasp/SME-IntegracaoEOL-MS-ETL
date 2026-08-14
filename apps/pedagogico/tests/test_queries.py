"""Valida a projeção de colunas da query SQL_TURMAS."""

from django.test import SimpleTestCase

from apps.pedagogico.queries import (
    SQL_API_EOL_COMPONENTE_CURRICULAR,
    SQL_ETAPA_ENSINO,
    SQL_TURMAS,
)


class SqlEtapaEnsinoProjecaoTest(SimpleTestCase):
    """Valida que SQL_ETAPA_ENSINO projeta código e descrição sem filtro."""

    def test_projeta_codigo_e_descricao(self) -> None:
        self.assertIn("cd_etapa_ensino AS Codigo", SQL_ETAPA_ENSINO)
        self.assertIn("AS Descricao", SQL_ETAPA_ENSINO)
        self.assertIn("FROM etapa_ensino", SQL_ETAPA_ENSINO)
        self.assertNotIn("WHERE", SQL_ETAPA_ENSINO)


class SqlApiEolComponenteCurricularTest(SimpleTestCase):
    """Valida a consulta consolidada de componentes da API EOL."""

    def test_preserva_left_join_e_ordem_das_colunas(self) -> None:
        colunas = (
            "ccp.id",
            "cc.idcomponentecurricular",
            "cc.ehregencia",
            "cc.ehterritorio",
            "cc.descricao",
            "ccp.idcomponentecurricularpai",
            "ccp.vigencia",
        )

        posicoes = [
            SQL_API_EOL_COMPONENTE_CURRICULAR.index(coluna)
            for coluna in colunas
        ]

        self.assertEqual(posicoes, sorted(posicoes))
        self.assertIn(
            "LEFT JOIN componentecurricularpai",
            SQL_API_EOL_COMPONENTE_CURRICULAR,
        )


class SqlTurmasProjecaoTest(SimpleTestCase):
    """Valida que SQL_TURMAS projeta etapa e ciclo de ensino."""

    def test_projeta_codigo_etapa_e_ciclo_ensino(self) -> None:
        """Verifica que a query expõe cd_etapa_ensino e cd_ciclo_ensino."""
        self.assertIn("ee.cd_etapa_ensino", SQL_TURMAS)
        self.assertIn("AS CodigoEtapaEnsino", SQL_TURMAS)
        self.assertIn("se.cd_ciclo_ensino", SQL_TURMAS)
        self.assertIn("AS CodigoCicloEnsino", SQL_TURMAS)

    def test_etapa_e_ciclo_vem_apos_ensino_especial(self) -> None:
        """Garante a ordem das colunas (mapeamento posicional de TurmaIn)."""
        pos_especial = SQL_TURMAS.index("AS EnsinoEspecial")
        pos_etapa = SQL_TURMAS.index("AS CodigoEtapaEnsino")
        pos_ciclo = SQL_TURMAS.index("AS CodigoCicloEnsino")
        self.assertLess(pos_especial, pos_etapa)
        self.assertLess(pos_etapa, pos_ciclo)
