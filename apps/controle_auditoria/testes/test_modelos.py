"""Testes basicos de CRUD dos modelos de auditoria."""

from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from apps.controle_auditoria.models import (
    EtlCheckpointDominio,
    EtlExecucao,
    EtlExecucaoTabelaEscrita,
    EtlExecucaoTabelaLida,
)


class ModelosAuditoriaCrudTestCase(TestCase):
    """Valida operacoes basicas de persistencia dos modelos."""

    def test_crud_etl_execucao(self) -> None:
        """Cria, atualiza e remove registro de execucao."""
        execucao = EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="institucional",
            situacao="em_execucao",
            iniciado_em=timezone.now(),
        )
        execucao.situacao = "sucesso"
        execucao.finalizado_em = timezone.now()
        execucao.save()

        self.assertEqual(
            EtlExecucao.objects.get(pk=execucao.pk).situacao,
            "sucesso",
        )

        execucao.delete()
        self.assertFalse(EtlExecucao.objects.filter(pk=execucao.pk).exists())

    def test_crud_etl_execucao_tabela_lida(self) -> None:
        """Cria, atualiza e remove registro de tabela lida."""
        registro = EtlExecucaoTabelaLida.objects.create(
            id_execucao=uuid4(),
            tabela_origem="dbo.v_cadastro_unidade_educacao",
            numero_pagina=1,
            linhas_lidas=100,
        )
        registro.numero_pagina = 2
        registro.linhas_lidas = 200
        registro.save()

        salvo = EtlExecucaoTabelaLida.objects.get(pk=registro.pk)
        self.assertEqual(salvo.numero_pagina, 2)
        self.assertEqual(salvo.linhas_lidas, 200)

        registro.delete()
        self.assertFalse(EtlExecucaoTabelaLida.objects.filter(pk=registro.pk).exists())

    def test_crud_etl_execucao_tabela_escrita(self) -> None:
        """Cria, atualiza e remove registro de tabela escrita."""
        registro = EtlExecucaoTabelaEscrita.objects.create(
            id_execucao=uuid4(),
            tabela_destino="public.institucional",
            linhas_escritas=10,
            modo_escrita="upsert",
        )
        registro.linhas_escritas = 15
        registro.modo_escrita = "insert"
        registro.save()

        salvo = EtlExecucaoTabelaEscrita.objects.get(pk=registro.pk)
        self.assertEqual(salvo.linhas_escritas, 15)
        self.assertEqual(salvo.modo_escrita, "insert")

        registro.delete()
        self.assertFalse(
            EtlExecucaoTabelaEscrita.objects.filter(pk=registro.pk).exists()
        )

    def test_crud_etl_checkpoint_dominio(self) -> None:
        """Cria, atualiza e remove checkpoint por dominio."""
        checkpoint = EtlCheckpointDominio.objects.create(
            dominio="institucional",
            ultimo_id_execucao=uuid4(),
            ultima_pagina=1,
            token_parada="100",
            indice_sincronizacao="institucional:offset:100",
            ultima_situacao="sucesso",
        )
        checkpoint.ultima_pagina = 2
        checkpoint.token_parada = "200"
        checkpoint.save()

        salvo = EtlCheckpointDominio.objects.get(pk=checkpoint.pk)
        self.assertEqual(salvo.ultima_pagina, 2)
        self.assertEqual(salvo.token_parada, "200")

        checkpoint.delete()
        self.assertFalse(EtlCheckpointDominio.objects.filter(pk=checkpoint.pk).exists())
