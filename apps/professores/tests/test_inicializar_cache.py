"""Valida a inicialização operacional após carga concluída."""

from uuid import uuid4

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from apps.controle_auditoria.models import EtlExecucao
from apps.professores.models import ControleCargaProfessores


class InicializarCacheTest(TestCase):
    """Rejeita fontes desconhecidas ou ainda em carga."""

    databases = ["default", "professores_db"]

    def test_exige_confirmacao_e_ultima_execucao_concluida(self):
        with self.assertRaises(CommandError):
            call_command("inicializar_cache_professores")
        with self.assertRaises(CommandError):
            call_command(
                "inicializar_cache_professores",
                confirmar_fontes_completas=True,
            )
        self.assertFalse(
            ControleCargaProfessores.objects.using("professores_db").exists()
        )

    def test_inicializa_geracao_apos_conclusao(self):
        EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="professores",
            situacao="concluido",
            iniciado_em=timezone.now(),
            finalizado_em=timezone.now(),
        )
        call_command(
            "inicializar_cache_professores",
            confirmar_fontes_completas=True,
        )
        estado = ControleCargaProfessores.objects.using("professores_db").get(
            pk=1
        )
        self.assertFalse(estado.falha)
        self.assertEqual(estado.cargas_ativas, [])

    def test_nao_apaga_carga_ativa(self):
        EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="professores",
            situacao="concluido",
            iniciado_em=timezone.now(),
        )
        ControleCargaProfessores.objects.using("professores_db").create(
            cargas_ativas=["execucao-ativa"],
        )
        with self.assertRaises(CommandError):
            call_command(
                "inicializar_cache_professores",
                confirmar_fontes_completas=True,
            )

    def test_rejeita_auditoria_com_outra_execucao_em_andamento(self):
        EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="professores",
            situacao="em_execucao",
            iniciado_em=timezone.now(),
        )
        EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="professores",
            situacao="concluido",
            iniciado_em=timezone.now(),
        )
        with self.assertRaises(CommandError):
            call_command(
                "inicializar_cache_professores",
                confirmar_fontes_completas=True,
            )
