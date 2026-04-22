"""Testes dos commands do app controle_auditoria."""

from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from kombu.exceptions import OperationalError


class ExecutarDominioCommandTestCase(TestCase):
    """Valida o roteamento do command executar_dominio."""

    @patch("apps.controle_auditoria.management.commands.executar_dominio.call_command")
    def test_deve_executar_dominio_institucional(
        self, call_command_mock: MagicMock
    ) -> None:
        """Encaminha para listar_institucional_offset com argumentos."""
        call_command(
            "executar_dominio",
            "--dominio",
            "institucional",
            "--volume",
            "200",
            "--offset",
            "100",
            "--continuar",
        )
        call_command_mock.assert_called_once_with(
            "etl_institucional",
            "--volume",
            "200",
            "--offset",
            "100",
            "--continuar",
        )

    @patch(
        "apps.controle_auditoria.management.commands."
        "executar_dominio.exibir_validacao_sinc_rec_db"
    )
    def test_deve_executar_dominio_sinc_rec_db(
        self,
        validacao_mock: MagicMock,
    ) -> None:
        """Executa validacao do dominio de controle."""
        call_command("executar_dominio", "--dominio", "sinc_rec_db")
        validacao_mock.assert_called_once_with()

    def test_deve_falhar_com_dominio_invalido(self) -> None:
        """Retorna erro quando dominio nao e reconhecido."""
        with self.assertRaises(CommandError):
            call_command("executar_dominio", "--dominio", "invalido")


class AgendarDominioCommandTestCase(TestCase):
    """Valida command de agendamento/enfileiramento no Celery."""

    @patch(
        "apps.controle_auditoria.management.commands.agendar_dominio.executar_dominio_task"
    )
    def test_deve_enfileirar_task_imediata(self, task_mock: MagicMock) -> None:
        """Sem data/hora, usa delay diretamente."""
        resultado = MagicMock()
        resultado.id = "task-imediata-1"
        task_mock.delay.return_value = resultado

        call_command(
            "agendar_dominio",
            "--dominio",
            "institucional",
            "--volume",
            "120",
            "--offset",
            "10",
            "--continuar",
        )

        task_mock.delay.assert_called_once_with(
            dominio="institucional",
            volume=120,
            offset=10,
            continuar=True,
        )

    @patch(
        "apps.controle_auditoria.management.commands.agendar_dominio.executar_dominio_task"
    )
    def test_deve_agendar_task_com_data_hora(self, task_mock: MagicMock) -> None:
        """Com executar-em, usa apply_async com eta."""
        resultado = MagicMock()
        resultado.id = "task-agendada-1"
        task_mock.apply_async.return_value = resultado

        call_command(
            "agendar_dominio",
            "--dominio",
            "institucional",
            "--executar-em",
            "2026-03-10T23:00:00-03:00",
        )

        self.assertTrue(task_mock.apply_async.called)
        kwargs_apply = task_mock.apply_async.call_args.kwargs
        self.assertEqual(
            kwargs_apply["kwargs"],
            {
                "dominio": "institucional",
                "volume": 100,
                "offset": 0,
                "continuar": False,
            },
        )
        self.assertIn("eta", kwargs_apply)

    def test_deve_falhar_quando_data_hora_invalida(self) -> None:
        """Data inválida retorna erro de comando."""
        with self.assertRaises(CommandError):
            call_command(
                "agendar_dominio",
                "--dominio",
                "institucional",
                "--executar-em",
                "data-invalida",
            )

    @patch(
        "apps.controle_auditoria.management.commands.agendar_dominio.executar_dominio_task"
    )
    def test_falha_broker_delay_nao_derruba_processo(
        self, task_mock: MagicMock
    ) -> None:
        """OperationalError no broker vira CommandError, não exception fatal."""
        task_mock.delay.side_effect = OperationalError("broker indisponível")

        with self.assertRaises(CommandError):
            call_command("agendar_dominio", "--dominio", "institucional")

    @patch(
        "apps.controle_auditoria.management.commands.agendar_dominio.executar_dominio_task"
    )
    def test_falha_broker_apply_async_nao_derruba_processo(
        self, task_mock: MagicMock
    ) -> None:
        """OperationalError no broker ao agendar vira CommandError."""
        task_mock.apply_async.side_effect = OperationalError("broker indisponível")

        with self.assertRaises(CommandError):
            call_command(
                "agendar_dominio",
                "--dominio",
                "institucional",
                "--executar-em",
                "2026-03-10T23:00:00-03:00",
            )


class ExecutarDominiosCommandTestCase(TestCase):
    """Valida command que executa o conjunto de domínios ativos."""

    @patch("apps.controle_auditoria.management.commands.executar_dominios.call_command")
    def test_deve_executar_dominios_sem_continuar(
        self, call_command_mock: MagicMock
    ) -> None:
        """Executa sinc_rec_db e institucional sem flag continuar."""
        call_command("executar_dominios", "--volume", "200")

        self.assertEqual(call_command_mock.call_count, 2)
        self.assertEqual(
            call_command_mock.call_args_list[0].args,
            ("executar_dominio", "--dominio", "sinc_rec_db"),
        )
        self.assertEqual(
            call_command_mock.call_args_list[1].args,
            (
                "executar_dominio",
                "--dominio",
                "institucional",
                "--volume",
                "200",
            ),
        )

    @patch("apps.controle_auditoria.management.commands.executar_dominios.call_command")
    def test_deve_executar_dominios_com_continuar(
        self, call_command_mock: MagicMock
    ) -> None:
        """Inclui flag continuar no domínio institucional."""
        call_command("executar_dominios", "--volume", "100", "--continuar")

        self.assertEqual(
            call_command_mock.call_args_list[1].args,
            (
                "executar_dominio",
                "--dominio",
                "institucional",
                "--volume",
                "100",
                "--continuar",
            ),
        )


class ExecutarDominiosLoopCommandTestCase(TestCase):
    """Valida command de loop contínuo com checkpoint de progresso."""

    def test_deve_falhar_com_limite_linhas_invalido(self) -> None:
        """Rejeita limite-linhas menor ou igual a zero."""
        with self.assertRaises(CommandError):
            call_command("executar_dominios_loop", "--limite-linhas", "0")

    @patch(
        "apps.controle_auditoria.management.commands.executar_dominios_loop.time.sleep"
    )
    @patch(
        "apps.controle_auditoria.management.commands.executar_dominios_loop.call_command"
    )
    @patch(
        "apps.controle_auditoria.management.commands."
        "executar_dominios_loop.RepositorioAuditoriaPostgres"
    )
    def test_deve_parar_quando_sem_avanco(
        self,
        repositorio_cls_mock: MagicMock,
        call_command_mock: MagicMock,
        sleep_mock: MagicMock,
    ) -> None:
        """Se token não avança, encerra loop sem aguardar."""
        repositorio = MagicMock()
        repositorio.obter_checkpoint_dominio.side_effect = [
            {"token_parada": "100"},
            {"token_parada": "100"},
        ]
        repositorio_cls_mock.return_value = repositorio

        call_command("executar_dominios_loop", "--volume", "100", "--intervalo", "1")

        call_command_mock.assert_called_once_with(
            "executar_dominios", "--volume", "100"
        )
        sleep_mock.assert_not_called()

    @patch(
        "apps.controle_auditoria.management.commands.executar_dominios_loop.time.sleep"
    )
    @patch(
        "apps.controle_auditoria.management.commands.executar_dominios_loop.call_command"
    )
    @patch(
        "apps.controle_auditoria.management.commands."
        "executar_dominios_loop.RepositorioAuditoriaPostgres"
    )
    def test_deve_respeitar_limite_linhas_com_paginacao(
        self,
        repositorio_cls_mock: MagicMock,
        call_command_mock: MagicMock,
        sleep_mock: MagicMock,
    ) -> None:
        """Calcula volume da execução com base no restante do limite."""
        repositorio = MagicMock()
        repositorio.obter_checkpoint_dominio.side_effect = [
            {"token_parada": "0"},
            {"token_parada": "100"},
            {"token_parada": "100"},
            {"token_parada": "150"},
        ]
        repositorio_cls_mock.return_value = repositorio

        call_command(
            "executar_dominios_loop",
            "--volume",
            "100",
            "--intervalo",
            "1",
            "--limite-linhas",
            "150",
            "--continuar",
        )

        self.assertEqual(call_command_mock.call_count, 2)
        self.assertEqual(
            call_command_mock.call_args_list[0].args,
            ("executar_dominios", "--volume", "100", "--continuar"),
        )
        self.assertEqual(
            call_command_mock.call_args_list[1].args,
            ("executar_dominios", "--volume", "50", "--continuar"),
        )
        sleep_mock.assert_called_once_with(1)

    def test_deve_retornar_volume_restante_no_limite_linhas(self) -> None:
        """Verifica cálculo do volume quando restam menos linhas que o volume total."""
        from apps.controle_auditoria.management.commands.executar_dominios_loop import (
            Command,
        )

        cmd = Command()
        # limite 100, total 70 -> volume restante 30
        self.assertEqual(cmd._calcular_volume(100, 100, 70), 30)


class CancelarExecucoesCommandTestCase(TestCase):
    """Testes para o comando de cancelamento de execuções ETL."""

    def test_deve_cancelar_execucoes_em_andamento(self) -> None:
        """Marca execuções em aberto como canceladas."""
        import uuid

        from django.utils import timezone

        from apps.controle_auditoria.models import EtlExecucao

        EtlExecucao.objects.create(
            id_execucao=uuid.uuid4(),
            dominio="institucional",
            situacao="em_execucao",
            iniciado_em=timezone.now(),
        )

        call_command("cancelar_execucoes")

        exec_obj = EtlExecucao.objects.get(dominio="institucional")
        self.assertEqual(exec_obj.situacao, "cancelado")

    def test_deve_filtrar_por_dominio(self) -> None:
        """Apenas o domínio solicitado deve ser cancelado."""
        import uuid

        from django.utils import timezone

        from apps.controle_auditoria.models import EtlExecucao

        EtlExecucao.objects.create(
            id_execucao=uuid.uuid4(),
            dominio="institucional",
            situacao="em_execucao",
            iniciado_em=timezone.now(),
        )
        EtlExecucao.objects.create(
            id_execucao=uuid.uuid4(),
            dominio="professores",
            situacao="em_execucao",
            iniciado_em=timezone.now(),
        )

        call_command("cancelar_execucoes", "--dominio", "institucional")

        self.assertEqual(EtlExecucao.objects.filter(situacao="cancelado").count(), 1)
        self.assertEqual(
            EtlExecucao.objects.filter(
                dominio="institucional", situacao="cancelado"
            ).count(),
            1,
        )
        self.assertEqual(
            EtlExecucao.objects.filter(
                dominio="professores", situacao="em_execucao"
            ).count(),
            1,
        )
