"""Testes para EtlInstitucionalService.

Cobre estrutura de fases, imutabilidade de PhaseConfig,
pipeline Producer-Consumer e enriquecimento SSO/cache da fase UE.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import TestCase

from apps.core.libs.base_etl_service import PipelineMetrics
from apps.institucional.dtos.model_in import (
    DREIn,
    SubprefeituraIn,
    TipoEscolaIn,
    UnidadeEducacionalIn,
)
from apps.institucional.models import DRE, TipoEscola, UnidadeEducacional
from apps.institucional.services import EtlInstitucionalService

_ROW_UE = (
    "000001",  # codigo_ue
    "UE 1",  # nome
    "UE 1",  # nome_nao_oficial
    "EMEF",  # tipo_ue
    3,  # codigo_tipo_unidade_educacao
    "R",  # tipo_logradouro
    19674,  # codigo_logradouro
    "Rua 1",  # logradouro
    "1",  # numero
    "B",  # bairro
    "000",  # cep
    "SP",  # municipio
    "D",  # distrito
    "e@e.com",  # email
    "123",  # telefone_1
    None,  # telefone_2
    2020,  # ano_construcao
    "P",  # propriedade
    False,  # organizacao_parceira
    False,  # eh_ceu
    None,  # data_atualizacao
    10,  # vagas_matutino
    10,  # vagas_vespertino
    0,  # vagas_noturno
    0,  # vagas_intermediario
    0,  # vagas_integral
    20,  # vagas_total
    5,  # quantidade_funcionarios
    123456,  # codigo_inep
    "A",  # status
    "108900",  # codigo_dre
    1,  # codigo_tipo_escola
    3,  # codigo_tp_equipamento
    1,  # codigo_sub_prefeitura
)


class EtlInstitucionalServiceTestCase(TestCase):
    """Testes para EtlInstitucionalService."""

    def setUp(self) -> None:
        self.mock_eol = MagicMock()
        self.mock_cache = MagicMock()
        self.mock_cache.get_hash.return_value = {}
        self.mock_cache.exist_hash_value.return_value = False
        self.mock_sso = MagicMock()
        self.service = EtlInstitucionalService(
            db_alias="institucional_db",
            eol=self.mock_eol,
            cache=self.mock_cache,
            core_sso=self.mock_sso,
            id_execucao=uuid4(),
        )

    def test_fases_contem_4_configs(self) -> None:
        """Valida quantidade e ordem das fases."""
        self.assertEqual(len(self.service._fases), 4)
        nomes = [f.nome for f in self.service._fases]
        self.assertEqual(
            nomes,
            [
                "dre",
                "tipo_escola",
                "sub_prefeitura",
                "unidade_educacional",
            ],
        )

    def test_phase_config_e_imutavel(self) -> None:
        """Valida que PhaseConfig é frozen."""
        config = self.service._fases[0]
        with self.assertRaises(AttributeError):
            config.nome = "mudar"  # type: ignore[misc]

    def test_init_sem_dependencias_usa_defaults(self) -> None:
        """Inicialização sem injeção instancia dependências padrão."""
        service = EtlInstitucionalService(db_alias="institucional_db")
        self.assertIsNotNone(service.eol)
        self.assertIsNotNone(service.cache)
        self.assertIsNotNone(service.core_sso)
        self.assertEqual(len(service._fases), 4)

    def test_criar_transform_tipo_escola_retorna_tripla(self) -> None:
        """Valida tripla (pk, hash SHA-256, obj) para TipoEscola."""
        config = self.service._fases[1]
        transform = self.service._criar_transform(config)

        pk, h, obj = transform((1, "EMEF", "Escola Municipal"))

        self.assertEqual(pk, "1")
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)
        self.assertIsInstance(obj, TipoEscola)
        self.assertEqual(obj.descricao, "Escola Municipal")

    def test_criar_transform_dre_retorna_tripla(self) -> None:
        """Valida tripla para DRE."""
        config = self.service._fases[0]
        transform = self.service._criar_transform(config)

        pk, h, obj = transform(("108900", "DRE BT", "BT", 1, "Regional"))

        self.assertEqual(pk, "108900")
        self.assertEqual(len(h), 64)
        self.assertIsInstance(obj, DRE)

    def test_criar_transform_ue_enriquece_com_cache(self) -> None:
        """Transform da UE busca código de integração do cache."""
        self.mock_cache.get_hash.return_value = {"000001": "INT-001"}
        config = self.service._fases[3]
        transform = self.service._criar_transform(config)

        pk, h, obj = transform(_ROW_UE)

        self.assertEqual(pk, "000001")
        self.assertEqual(len(h), 64)
        self.assertIsInstance(obj, UnidadeEducacional)
        self.assertEqual(obj.codigo_ue_integracao, "INT-001")

    def test_criar_transform_ue_sem_cache_define_none(self) -> None:
        """Integração fica None quando cache não tem o código da UE."""
        self.mock_cache.get_hash.return_value = {}
        config = self.service._fases[3]
        transform = self.service._criar_transform(config)

        _, _, obj = transform(_ROW_UE)

        self.assertIsNone(obj.codigo_ue_integracao)

    def test_criar_transform_ue_busca_cache_uma_vez_por_dre(self) -> None:
        """Cache é consultado uma vez por DRE, não por UE."""
        self.mock_cache.get_hash.return_value = {}
        config = self.service._fases[3]
        transform = self.service._criar_transform(config)

        transform(_ROW_UE)
        transform(_ROW_UE)

        self.mock_cache.get_hash.assert_called_once()

    @patch.object(EtlInstitucionalService, "sync_batch")
    def test_executar_fase_tipo_escola_chama_sync_batch(
        self, mock_sync: MagicMock
    ) -> None:
        """Fase tipo_escola chama sync_batch para cada chunk."""
        config = self.service._fases[1]
        self.mock_eol.iter_query.return_value = [
            [(1, "EMEF", "Escola Municipal")],
            [(2, "EMEI", "Escola de Educação Infantil")],
        ]
        mock_sync.return_value = (1, 0)

        metrics = self.service._executar_fase(config, numero_fase=2)

        self.assertEqual(mock_sync.call_count, 2)
        self.assertEqual(metrics.total_lidos, 2)
        self.assertEqual(metrics.total_escritos, 2)

    @patch.object(EtlInstitucionalService, "sync_batch")
    def test_executar_fase_dre_chama_sync_batch(
        self, mock_sync: MagicMock
    ) -> None:
        """Fase DRE chama sync_batch corretamente."""
        config = self.service._fases[0]
        self.mock_eol.iter_query.return_value = [
            [("108900", "DRE BT", "BT", 1, "Regional")]
        ]
        mock_sync.return_value = (1, 0)

        metrics = self.service._executar_fase(config, numero_fase=1)

        mock_sync.assert_called_once()
        self.assertEqual(metrics.total_escritos, 1)

    @patch.object(EtlInstitucionalService, "sync_batch")
    def test_sync_batch_recebe_meta_correta(
        self, mock_sync: MagicMock
    ) -> None:
        """sync_batch recebe model_class, update_fields e unique_fields."""
        config = self.service._fases[1]
        self.mock_eol.iter_query.return_value = [
            [(1, "EMEF", "Escola Municipal")]
        ]
        mock_sync.return_value = (1, 0)

        self.service._executar_fase(config)

        args, _ = mock_sync.call_args
        fase_meta = args[1]
        self.assertEqual(fase_meta["model_class"], config.model_class)
        self.assertEqual(
            fase_meta["update_fields"], list(config.update_fields)
        )
        self.assertEqual(
            fase_meta["unique_fields"], list(config.unique_fields)
        )
        self.assertEqual(fase_meta["modo_escrita"], config.modo_escrita)

    def test_executar_fase_erro_producer_propagado(self) -> None:
        """Erros na extração EOL são propagados ao caller."""
        config = self.service._fases[1]
        self.mock_eol.iter_query.side_effect = RuntimeError("Falha SQL")

        with self.assertRaises(RuntimeError):
            self.service._executar_fase(config)

    def test_executar_chama_cache_antes_da_fase1(self) -> None:
        """executar() pré-carrega cache SSO quando fase_inicial=1."""
        with (
            patch.object(
                self.service, "_popular_cache_integracao_ue"
            ) as mock_pop,
            patch.object(self.service, "_executar_fase") as mock_fase,
        ):
            mock_fase.return_value = PipelineMetrics(total_escritos=0)
            self.service.executar(fase_inicial=1)

        mock_pop.assert_called_once()

    def test_executar_nao_chama_cache_se_fase_apos_1(self) -> None:
        """executar() pula pré-carga do cache quando fase_inicial > 1."""
        with (
            patch.object(
                self.service, "_popular_cache_integracao_ue"
            ) as mock_pop,
            patch.object(self.service, "_executar_fase") as mock_fase,
        ):
            mock_fase.return_value = PipelineMetrics(total_escritos=0)
            self.service.executar(fase_inicial=2)

        mock_pop.assert_not_called()

    def test_executar_pula_fases_anteriores(self) -> None:
        """fase_inicial é respeitado — fases anteriores são ignoradas."""
        with patch.object(
            EtlInstitucionalService, "_executar_fase"
        ) as mock_fase:
            mock_fase.return_value = PipelineMetrics(total_escritos=5)
            res = self.service.executar(fase_inicial=3)

        self.assertNotIn("dre", res)
        self.assertNotIn("tipo_escola", res)
        self.assertIn("sub_prefeitura", res)
        self.assertIn("unidade_educacional", res)
        self.assertEqual(mock_fase.call_count, 2)

    def test_executar_completo_retorna_4_chaves(self) -> None:
        """Execução completa retorna resultado para cada fase."""
        with (
            patch.object(
                EtlInstitucionalService, "_executar_fase"
            ) as mock_fase,
            patch.object(self.service, "_popular_cache_integracao_ue"),
        ):
            mock_fase.return_value = PipelineMetrics(total_escritos=10)
            res = self.service.executar(fase_inicial=1)

        self.assertEqual(len(res), 4)
        self.assertEqual(mock_fase.call_count, 4)
        self.assertEqual(res["tipo_escola"], 10)

    def test_popular_cache_popula_mapeamentos(self) -> None:
        """Método pré-carrega cache com mapeamentos SSO para a DRE."""
        self.mock_eol.executar_query.side_effect = [
            [("108900", "DRE BT", "BT", 1, "Regional")],
            [("001",)],
        ]
        self.mock_sso.obter_codigos_integracao_ues.return_value = [
            ("001", "UE 1", "ABC-123")
        ]

        self.service._popular_cache_integracao_ue()

        self.mock_cache.set_hash.assert_called_once()
        call_kwargs = self.mock_cache.set_hash.call_args
        mapeamentos = call_kwargs.kwargs.get("mapping", {})
        self.assertIn("ABC-123", mapeamentos.values())

    def test_popular_cache_ignora_dre_ja_em_cache(self) -> None:
        """DRE já cacheada não gera nova consulta ao SSO."""
        self.mock_eol.executar_query.return_value = [
            ("108900", "DRE BT", "BT", 1, "Reg")
        ]
        self.mock_cache.exist_hash_value.return_value = True

        self.service._popular_cache_integracao_ue()

        self.mock_sso.obter_codigos_integracao_ues.assert_not_called()

    def test_popular_cache_ignora_dre_sem_ues(self) -> None:
        """DRE sem UEs no EOL não consulta SSO nem persiste cache."""
        self.mock_eol.executar_query.side_effect = [
            [("108900", "DRE BT", "BT", 1, "Reg")],
            [],
        ]

        self.service._popular_cache_integracao_ue()

        self.mock_sso.obter_codigos_integracao_ues.assert_not_called()
        self.mock_cache.set_hash.assert_not_called()

    def test_popular_cache_nao_persiste_se_sso_vazio(self) -> None:
        """SSO sem mapeamentos não gera escrita no cache."""
        self.mock_eol.executar_query.side_effect = [
            [("108900", "DRE BT", "BT", 1, "Reg")],
            [("001",)],
        ]
        self.mock_sso.obter_codigos_integracao_ues.return_value = []

        self.service._popular_cache_integracao_ue()

        self.mock_cache.set_hash.assert_not_called()

    def test_popular_cache_interrompe_se_sso_offline(self) -> None:
        """Falha no SSO para uma DRE impede tentativas nas demais."""
        self.mock_eol.executar_query.side_effect = [
            [
                ("108900", "DRE BT", "BT", 1, "Reg"),
                ("108901", "DRE IP", "IP", 1, "Reg"),
            ],
            [("001",)],
        ]
        self.mock_sso.obter_codigos_integracao_ues.side_effect = Exception(
            "SSO offline"
        )

        self.service._popular_cache_integracao_ue()

        self.assertEqual(
            self.mock_sso.obter_codigos_integracao_ues.call_count, 1
        )

    def test_popular_cache_ignora_falha_na_query_eol(self) -> None:
        """Falha na query EOL para DREs encerra silenciosamente."""
        self.mock_eol.executar_query.side_effect = Exception("EOL offline")

        self.service._popular_cache_integracao_ue()

        self.mock_sso.obter_codigos_integracao_ues.assert_not_called()

    def test_to_domain_dre_in(self) -> None:
        """DREIn.to_domain retorna campos corretos."""
        dto = DREIn("108900", "DRE BT", "BT", 1, "Regional")
        data = dto.to_domain()
        self.assertEqual(data["codigo_dre"], "108900")
        self.assertEqual(data["nome"], "DRE BT")
        self.assertEqual(data["sigla"], "BT")

    def test_to_domain_tipo_escola_in(self) -> None:
        """TipoEscolaIn.to_domain retorna campos corretos."""
        dto = TipoEscolaIn(1, "EMEF", "Escola Municipal")
        data = dto.to_domain()
        self.assertEqual(data["codigo_tipo_escola"], 1)
        self.assertEqual(data["sigla"], "EMEF")
        self.assertEqual(data["descricao"], "Escola Municipal")

    def test_to_domain_subprefeitura_in(self) -> None:
        """SubprefeituraIn.to_domain retorna campos corretos."""
        dto = SubprefeituraIn(10, "SÉ", "Subprefeitura da Sé")
        data = dto.to_domain()
        self.assertEqual(data["codigo_sub_prefeitura"], 10)
        self.assertEqual(data["nome"], "Subprefeitura da Sé")

    def test_to_domain_ue_in_sem_integracao(self) -> None:
        """UnidadeEducacionalIn.to_domain retorna None para integração."""
        dto = UnidadeEducacionalIn(*_ROW_UE)
        data = dto.to_domain()
        self.assertIsNone(data["codigo_ue_integracao"])
        self.assertEqual(data["codigo_ue"], "000001")

    def test_to_domain_ue_in_com_integracao(self) -> None:
        """UnidadeEducacionalIn.to_domain inclui código de integração."""
        dto = UnidadeEducacionalIn(*_ROW_UE)
        dto.codigo_ue_integracao = "INT-001"
        data = dto.to_domain()
        self.assertEqual(data["codigo_ue_integracao"], "INT-001")

    def test_to_domain_ue_in_fk_zero_vira_null(self) -> None:
        """FKs opcionais (tipo_escola, subprefeitura) com 0 viram NULL."""
        dto = UnidadeEducacionalIn(*_ROW_UE)
        # _ROW_UE traz códigos válidos (1) -> passam direto.
        data = dto.to_domain()
        self.assertEqual(data["subprefeitura_id"], 1)
        self.assertEqual(data["tipo_escola_id"], 1)
        # 0 é o sentinela do EOL para "sem vínculo" -> NULL (FK nullable).
        dto.codigo_sub_prefeitura = 0
        dto.codigo_tipo_escola = 0
        data = dto.to_domain()
        self.assertIsNone(data["subprefeitura_id"])
        self.assertIsNone(data["tipo_escola_id"])
