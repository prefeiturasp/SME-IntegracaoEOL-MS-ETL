"""Testes de processamento incremental do EtlInstitucionalService.

Utiliza mocks para o EOLService e executa operações reais no banco
institucional_db (SQLite em memória) para validar o upsert por hash.
"""

from unittest.mock import MagicMock

from django.test import TestCase

from apps.institucional.models import (
    DRE,
    SubPrefeitura,
    TipoEscola,
    UnidadeEducacional,
)
from apps.institucional.services import EtlInstitucionalService


class EtlInstitucionalServiceTestCase(TestCase):
    """Testes para o EtlInstitucionalService."""

    databases = ["institucional_db", "default"]

    def setUp(self) -> None:
        """Configura o ambiente de teste com mocks."""
        self.mock_eol = MagicMock()
        self.mock_sso = MagicMock()
        self.mock_cache = MagicMock()
        # Mock para evitar retornos None em gets de hash
        self.mock_cache.get_hash.return_value = {}
        self.mock_cache.exist_hash_value.return_value = False

        self.service = EtlInstitucionalService(
            eol=self.mock_eol, core_sso=self.mock_sso, cache=self.mock_cache
        )

    def test_popular_tipos_escola_insere_novos(self) -> None:
        """Valida que novos tipos de escola são inseridos."""
        self.mock_eol.executar_query.return_value = [(1, "EMEF", "Escola Municipal")]

        resultado = self.service.popular_tipos_escola()

        self.assertEqual(resultado, 1)
        self.assertTrue(
            TipoEscola.objects.using("institucional_db")
            .filter(codigo_tipo_escola=1)
            .exists()
        )

    def test_popular_dre_insere_novos(self) -> None:
        """Valida que novas DREs são inseridas com enriquecimento."""
        self.mock_eol.executar_query.side_effect = [
            [("108900", "DRE BUTANTÃ", "BT", 1, "Regional")],  # Query DRE
            [("001",)],  # Query UEs da DRE
        ]
        self.mock_sso.obter_codigos_integracao_ues.return_value = [
            ("001", "UE 1", "ABC-123")
        ]

        resultado = self.service.popular_dre()

        self.assertEqual(resultado, 1)
        self.assertTrue(
            DRE.objects.using("institucional_db").filter(codigo_dre="108900").exists()
        )
        self.mock_cache.set_hash.assert_called()

    def test_popular_unidades_educacionais_incremental_por_hash(self) -> None:
        """Valida que UE só é atualizada se o hash mudar."""
        # Setup pre-existente
        DRE.objects.using("institucional_db").create(
            codigo_dre="108900", nome="DRE BT", sigla="BT"
        )
        TipoEscola.objects.using("institucional_db").create(
            codigo_tipo_escola=1, sigla="EMEF", descricao="EMEF"
        )
        SubPrefeitura.objects.using("institucional_db").create(
            codigo_sub_prefeitura=1, sigla="CE", nome="Centro"
        )

        # Mock cache para retornar o código de integração
        self.mock_cache.get_hash.return_value = {"000001": "INT-001"}

        # Dados base (v28 campos conforme SQL_UNIDADE_EDUCACIONAL)
        row_original = (
            "000001",
            "UE 1",
            "UE 1",
            "EMEF",
            "R",
            "Rua 1",
            "1",
            "B",
            "000",
            "SP",
            "D",
            "e@e.com",
            "123",
            None,
            2020,
            "P",
            False,
            10,
            10,
            0,
            0,
            0,
            20,
            5,
            123456,
            "A",
            "108900",
            1,
            1,
        )
        row_alterada = (
            "000001",
            "UE 1 ALTERADA",
            "UE 1",
            "EMEF",
            "R",
            "Rua 1",
            "1",
            "B",
            "000",
            "SP",
            "D",
            "e@e.com",
            "123",
            None,
            2020,
            "P",
            False,
            10,
            10,
            0,
            0,
            0,
            20,
            5,
            123456,
            "A",
            "108900",
            1,
            1,
        )

        # Primeira carga
        self.mock_eol.executar_query.return_value = [row_original]
        self.service.popular_unidades_educacionais()

        # Segunda carga com MESMOS dados (não deve contar como alterada)
        self.mock_eol.executar_query.return_value = [row_original]
        resultado = self.service.popular_unidades_educacionais()
        self.assertEqual(resultado, 0)

        # Terceira carga com dado ALTERADO (muda o nome)
        self.mock_eol.executar_query.return_value = [row_alterada]
        resultado = self.service.popular_unidades_educacionais()
        self.assertEqual(resultado, 1)

        ue = UnidadeEducacional.objects.using("institucional_db").get(
            codigo_ue="000001"
        )
        self.assertEqual(ue.nome, "UE 1 ALTERADA")
        self.assertEqual(ue.codigo_inep, 123456)
        self.assertEqual(ue.codigo_ue_integracao, "INT-001")

    def test_popular_subprefeituras_insere_novos(self) -> None:
        """Valida que novas subprefeituras são inseridas."""
        self.mock_eol.executar_query.return_value = [(10, "SÉ", "SUBPREFEITURA DA SÉ")]

        resultado = self.service.popular_subprefeituras()

        self.assertEqual(resultado, 1)
        self.assertTrue(
            SubPrefeitura.objects.using("institucional_db")
            .filter(codigo_sub_prefeitura=10)
            .exists()
        )

    def test_executar_fluxo_completo(self) -> None:
        """Valida que o método principal chama todas as fases."""
        # Setup mocks para todas as queries (agora 5 chamadas no EOL)
        self.mock_eol.executar_query.side_effect = [
            [("108900", "DRE BT", "BT", 1, "Regional")],  # 1: SQL_DRE
            [("001",)],  # 1: SQL_OBTER_CODIGOS_UES_POR_DRE
            [(1, "EMEF", "EMEF")],  # 2: SQL_TIPO_ESCOLA
            [(10, "SÉ", "SÉ")],  # 3: SQL_SUBPREFEITURA
            [
                (
                    "001",
                    "UE",
                    "UE",
                    "T",
                    "L",
                    "LOG",
                    "1",
                    "B",
                    "00",
                    "SP",
                    "D",
                    "e",
                    "1",
                    None,
                    2020,
                    "P",
                    False,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    123456,
                    "A",
                    "108900",
                    1,
                    10,
                )
            ],  # 4: SQL_UNIDADE_EDUCACIONAL
        ]
        self.mock_sso.obter_codigos_integracao_ues.return_value = [
            ("001", "UE", "INT-001")
        ]
        self.mock_cache.get_hash.return_value = {"001": "INT-001"}

        resultados = self.service.executar()

        self.assertEqual(len(resultados), 4)
        self.assertEqual(resultados["dre"], 1)
        self.assertEqual(resultados["tipo_escola"], 1)
        self.assertEqual(resultados["sub_prefeitura"], 1)
        self.assertEqual(resultados["unidade_educacional"], 1)
        self.assertEqual(self.service.ultima_fase_concluida, 4)

    def test_upsert_incremental_sem_dados(self) -> None:
        """Garante cobertura de retorno antecipado se lista vazia."""
        self.mock_eol.executar_query.return_value = []
        resultado = self.service.popular_dre()
        self.assertEqual(resultado, 0)

    def test_popular_dre_trata_erro_sso(self) -> None:
        """Garante que falha no Core_SSO não interrompe o ETL das DREs (cobertura)."""
        self.mock_eol.executar_query.side_effect = [
            [("108900", "DRE BT", "BT", 1, "Reg")],
            [("001",)],
        ]
        # Simula erro no repositório legado
        self.mock_sso.obter_codigos_integracao_ues.side_effect = Exception(
            "Banco offline"
        )

        resultado = self.service.popular_dre()

        # Deve persistir a DRE normalmente apesar do erro no enriquecimento
        self.assertEqual(resultado, 1)
        self.assertTrue(
            DRE.objects.using("institucional_db").filter(codigo_dre="108900").exists()
        )

    def test_popular_dre_interrompe_tentativas_se_sso_offline(self) -> None:
        """Garante que falha no Core_SSO interrompe tentativas nos demais."""
        self.mock_eol.executar_query.side_effect = [
            [
                ("108900", "DRE BT", "BT", 1, "Reg"),
                ("108901", "DRE IP", "IP", 1, "Reg"),
            ],
            [("001",)],  # UEs da primeira DRE
        ]
        # Simula erro no repositório legado no primeiro DRE
        self.mock_sso.obter_codigos_integracao_ues.side_effect = Exception(
            "Banco offline"
        )

        # O popular_dre deve tentar processar a primeira DRE, falhar no SSO,
        # marcar como offline e BREAK no segundo item.
        resultado = self.service.popular_dre()

        # Ambos DREs devem ser persistidos (o erro de SSO não para o insert
        # das DREs, só o enriquecimento do cache)
        self.assertEqual(resultado, 2)
        # O obter_codigos_integracao_ues deve ter sido chamado apenas UMA vez
        self.assertEqual(self.mock_sso.obter_codigos_integracao_ues.call_count, 1)

    def test_executar_pula_fases(self) -> None:
        """Valida que o parâmetro fase_inicial é respeitado."""
        # Se iniciar na fase 3, não deve chamar DRE nem TipoEscola
        self.mock_eol.executar_query.side_effect = [[(10, "SÉ", "SÉ")], []]  # 3  # 4

        resultados = self.service.executar(fase_inicial=3)

        self.assertNotIn("dre", resultados)
        self.assertNotIn("tipo_escola", resultados)
        self.assertIn("sub_prefeitura", resultados)
        self.assertEqual(self.service.ultima_fase_concluida, 4)

    def test_popular_dre_usa_cache_se_existir(self) -> None:
        """Garante que se DRE já estiver em cache, não consulta EOL/SSO."""
        self.mock_eol.executar_query.return_value = [
            ("108900", "DRE BT", "BT", 1, "Reg")
        ]
        self.mock_cache.exist_hash_value.return_value = True

        self.service.popular_dre()

        # Não deve ter chamado a query de UEs (segunda chamada do EOL)
        self.assertEqual(self.mock_eol.executar_query.call_count, 1)
        self.mock_sso.obter_codigos_integracao_ues.assert_not_called()

    def test_popular_dre_ignora_se_sem_ue_na_dre(self) -> None:
        """Garante que se DRE não tiver UEs no EOL, não consulta SSO."""
        self.mock_eol.executar_query.side_effect = [
            [("108900", "DRE BT", "BT", 1, "Reg")],
            [],  # Lista vazia de UEs
        ]

        self.service.popular_dre()

        self.mock_sso.obter_codigos_integracao_ues.assert_not_called()

    def test_popular_dre_ignora_se_sso_vazio(self) -> None:
        """Garante que se SSO não retornar mapeamentos, não tenta setar no cache."""
        self.mock_eol.executar_query.side_effect = [
            [("108900", "DRE BT", "BT", 1, "Reg")],
            [("001",)],
        ]
        self.mock_sso.obter_codigos_integracao_ues.return_value = []  # SSO vazio

        self.service.popular_dre()

        self.mock_cache.set_hash.assert_not_called()

    def test_upsert_incremental_com_duplicados_na_origem(self) -> None:
        """Valida que a deduplicação por PK funciona no upsert incremental."""
        # Se o EOL retornar 2 linhas com o mesmo código TipoEscola
        self.mock_eol.executar_query.return_value = [
            (1, "A", "Desc A"),
            (1, "B", "Desc B"),  # Mesmo ID
        ]

        resultado = self.service.popular_tipos_escola()

        # Deve persistir apenas 1 (o último)
        self.assertEqual(resultado, 1)
        self.assertEqual(TipoEscola.objects.using("institucional_db").count(), 1)
        tipo = TipoEscola.objects.using("institucional_db").get(codigo_tipo_escola=1)
        self.assertEqual(tipo.sigla, "B")

    def test_init_com_defaults(self) -> None:
        """Garante cobertura da inicialização sem parâmetros (injeção default)."""
        service = EtlInstitucionalService()
        self.assertIsNotNone(service.eol)
        self.assertIsNotNone(service.core_sso)
        self.assertIsNotNone(service.cache)
