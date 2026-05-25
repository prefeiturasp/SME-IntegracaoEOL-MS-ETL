from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from apps.alunos.management.commands.etl_alunos import Command


class EtlAlunosCommandTest(TestCase):
    """Testes para o comando de management etl_alunos."""

    databases = {"default", "eol_db", "alunos_db"}

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
            cmd.get_modo_escrita(
                "matricula_componente_curricular_ano_letivo"
            ),
            "upsert",
        )
        self.assertEqual(
            cmd.get_modo_escrita("dados_aluno_acompanhamento_escolar"),
            "upsert",
        )

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
