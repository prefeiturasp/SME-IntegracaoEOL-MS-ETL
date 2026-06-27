from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from apps.alunos.management.commands.etl_alunos import Command


class EtlAlunosCommandTest(TestCase):
    """Testes para o comando de management etl_alunos."""

    databases = {"default"}

    def setUp(self) -> None:
        """Evita envio de logs para handlers externos durante os testes."""
        patcher = patch(
            "apps.core.libs.base_etl_command.ContextualLogger.get_etl_logger"
        )
        self.mock_get_logger = patcher.start()
        self.mock_get_logger.return_value = MagicMock()
        self.addCleanup(patcher.stop)

    def test_command_setup(self) -> None:
        """Valida configuração básica do comando."""
        cmd = Command()
        self.assertEqual(cmd.dominio, "alunos")
        self.assertEqual(cmd.fase_final, 9)
        self.assertEqual(cmd.get_modo_escrita("aluno"), "upsert")
        self.assertEqual(cmd.get_modo_escrita("unknown"), "full_refresh")

    def test_novas_tabelas_em_upsert(self) -> None:
        """Valida modo de escrita das tabelas agregadas e acompanhamento."""
        cmd = Command()
        self.assertEqual(
            cmd.get_modo_escrita("matricula_ano_letivo"), "upsert"
        )
        self.assertEqual(
            cmd.get_modo_escrita("matricula_componente_curricular_ano_letivo"),
            "upsert",
        )
        self.assertEqual(
            cmd.get_modo_escrita("dados_aluno_acompanhamento_escolar"),
            "upsert",
        )

    def test_extra_service_kwargs_com_anos_letivos(self) -> None:
        """Valida repasse de anos_letivos para o service."""
        cmd = Command()
        self.assertEqual(
            cmd._extra_service_kwargs(anos_letivos=[2024, 2025]),
            {"anos_letivos": [2024, 2025]},
        )
        self.assertEqual(cmd._extra_service_kwargs(anos_letivos=None), {})
        self.assertEqual(cmd._extra_service_kwargs(), {})

    @patch(
        "apps.alunos.management.commands.etl_alunos"
        ".EtlAlunosOrquestrador.lancar"
    )
    @patch("apps.core.libs.base_etl_command.RepositorioAuditoriaPostgres")
    def test_command_execution_com_fase(
        self, _mock_repo: MagicMock, mock_lancar: MagicMock
    ) -> None:
        """Valida que o argumento --fase força o início da fase específica."""
        out = StringIO()
        call_command("etl_alunos", "--fase", "3", "--celery", stdout=out)
        mock_lancar.assert_called_with(fase_inicial=3)

    @patch(
        "apps.alunos.management.commands.etl_alunos"
        ".EtlAlunosOrquestrador.lancar"
    )
    @patch("apps.core.libs.base_etl_command.RepositorioAuditoriaPostgres")
    @patch(
        "apps.alunos.management.commands.etl_alunos"
        ".EtlAlunosOrquestrador.__init__"
    )
    def test_command_execution_com_carga_inicial(
        self,
        mock_init: MagicMock,
        _mock_repo: MagicMock,
        _mock_lancar: MagicMock,
    ) -> None:
        """Valida que o argumento --carga-inicial passa primeiro_run=True."""
        mock_init.return_value = None
        call_command("etl_alunos", "--carga-inicial", "--celery")

        _, kwargs = mock_init.call_args
        self.assertTrue(kwargs["primeiro_run"])

    @patch(
        "apps.alunos.management.commands.etl_alunos"
        ".EtlAlunosOrquestrador.lancar"
    )
    @patch("apps.core.libs.base_etl_command.RepositorioAuditoriaPostgres")
    @patch(
        "apps.alunos.management.commands.etl_alunos"
        ".EtlAlunosOrquestrador.__init__"
    )
    def test_command_celery_repassa_fases_para_service(
        self,
        mock_init: MagicMock,
        _mock_repo: MagicMock,
        _mock_lancar: MagicMock,
    ) -> None:
        """Valida que o caminho Celery monta service com fases filtradas."""
        mock_init.return_value = None

        call_command("etl_alunos", "--fases", "aluno", "--celery")

        _, kwargs = mock_init.call_args
        servico = kwargs["service_class"]
        self.assertEqual(servico._fases_selecionadas, ["aluno"])
