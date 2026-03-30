"""Testes do RepositorioAuditoriaPostgres."""

import uuid

from django.test import TestCase

from apps.controle_auditoria.libs.repositorio_auditoria import (
    RepositorioAuditoriaPostgres,
)
from apps.controle_auditoria.models import (
    EtlCheckpointDominio,
    EtlExecucao,
    EtlExecucaoTabelaEscrita,
    EtlExecucaoTabelaLida,
)


class IniciarExecucaoTest(TestCase):
    """Testes para o método iniciar_execucao do repositório."""

    def test_cria_registro_em_andamento(self) -> None:
        """Verifica que iniciar_execucao cria um registro com situacao em_execucao."""
        repo = RepositorioAuditoriaPostgres()
        id_exec = repo.iniciar_execucao("professores")

        execucao = EtlExecucao.objects.get(id_execucao=id_exec)
        self.assertEqual(execucao.dominio, "professores")
        self.assertEqual(execucao.situacao, "em_execucao")
        self.assertIsNone(execucao.finalizado_em)

    def test_retorna_uuid(self) -> None:
        """Verifica que iniciar_execucao retorna um UUID."""
        repo = RepositorioAuditoriaPostgres()
        id_exec = repo.iniciar_execucao("escolas")
        self.assertIsInstance(id_exec, uuid.UUID)


class FinalizarExecucaoTest(TestCase):
    """Testes para o método finalizar_execucao do repositório."""

    def setUp(self) -> None:
        """Cria uma execução inicial para uso nos testes."""
        self.repo = RepositorioAuditoriaPostgres()
        self.id_exec = self.repo.iniciar_execucao("professores")

    def test_finaliza_com_sucesso(self) -> None:
        """Verifica que finalizar_execucao atualiza situacao e finalizado_em."""
        self.repo.finalizar_execucao(self.id_exec, situacao="concluido")
        execucao = EtlExecucao.objects.get(id_execucao=self.id_exec)
        self.assertEqual(execucao.situacao, "concluido")
        self.assertIsNotNone(execucao.finalizado_em)

    def test_finaliza_com_erro_e_mensagem(self) -> None:
        """Verifica que finalizar_execucao persiste mensagem de erro."""
        self.repo.finalizar_execucao(
            self.id_exec, situacao="erro", mensagem_erro="falha de conexão"
        )
        execucao = EtlExecucao.objects.get(id_execucao=self.id_exec)
        self.assertEqual(execucao.situacao, "erro")
        self.assertEqual(execucao.mensagem_erro, "falha de conexão")


class RegistrarTabelaLidaTest(TestCase):
    """Testes para o método registrar_tabela_lida do repositório."""

    def setUp(self) -> None:
        """Cria uma execução inicial para uso nos testes."""
        self.repo = RepositorioAuditoriaPostgres()
        self.id_exec = self.repo.iniciar_execucao("professores")

    def test_cria_registro_de_leitura(self) -> None:
        """Verifica que registrar_tabela_lida cria o registro com os campos corretos."""
        self.repo.registrar_tabela_lida(
            id_execucao=self.id_exec,
            tabela_origem="professor",
            numero_pagina=1,
            linhas_lidas=250,
        )
        registro = EtlExecucaoTabelaLida.objects.get(id_execucao=self.id_exec)
        self.assertEqual(registro.tabela_origem, "professor")
        self.assertEqual(registro.linhas_lidas, 250)
        self.assertEqual(registro.numero_pagina, 1)


class RegistrarTabelaEscritaTest(TestCase):
    """Testes para o método registrar_tabela_escrita do repositório."""

    def setUp(self) -> None:
        """Cria uma execução inicial para uso nos testes."""
        self.repo = RepositorioAuditoriaPostgres()
        self.id_exec = self.repo.iniciar_execucao("professores")

    def test_cria_registro_de_escrita_upsert(self) -> None:
        """Verifica que registrar_tabela_escrita cria registro com modo upsert."""
        self.repo.registrar_tabela_escrita(
            id_execucao=self.id_exec,
            tabela_destino="professor",
            linhas_escritas=100,
            modo_escrita="upsert",
        )
        registro = EtlExecucaoTabelaEscrita.objects.get(id_execucao=self.id_exec)
        self.assertEqual(registro.tabela_destino, "professor")
        self.assertEqual(registro.linhas_escritas, 100)
        self.assertEqual(registro.modo_escrita, "upsert")

    def test_modo_escrita_padrao_e_upsert(self) -> None:
        """Verifica que o modo de escrita padrão é upsert quando não informado."""
        self.repo.registrar_tabela_escrita(
            id_execucao=self.id_exec,
            tabela_destino="cargo",
            linhas_escritas=16,
        )
        registro = EtlExecucaoTabelaEscrita.objects.get(id_execucao=self.id_exec)
        self.assertEqual(registro.modo_escrita, "upsert")


class CheckpointDominioTest(TestCase):
    """Testes para os métodos de checkpoint de domínio do repositório."""

    def setUp(self) -> None:
        """Inicializa o repositório e um ID de execução para os testes."""
        self.repo = RepositorioAuditoriaPostgres()
        self.id_exec = uuid.uuid4()

    def test_checkpoint_inexistente_retorna_none(self) -> None:
        """obter_checkpoint_dominio retorna None para domínio inexistente."""
        resultado = self.repo.obter_checkpoint_dominio("dominio_inexistente")
        self.assertIsNone(resultado)

    def test_cria_checkpoint_novo(self) -> None:
        """Verifica que atualizar_checkpoint_dominio cria um novo checkpoint."""
        self.repo.atualizar_checkpoint_dominio(
            dominio="professores",
            ultimo_id_execucao=self.id_exec,
            ultima_pagina=2,
            token_parada="150",
            indice_sincronizacao=None,
            ultima_situacao="concluido",
            sucesso=True,
        )
        checkpoint = EtlCheckpointDominio.objects.get(dominio="professores")
        self.assertEqual(checkpoint.ultima_pagina, 2)
        self.assertEqual(checkpoint.token_parada, "150")
        self.assertEqual(checkpoint.ultima_situacao, "concluido")
        self.assertIsNotNone(checkpoint.ultimo_sucesso_em)

    def test_atualiza_checkpoint_existente(self) -> None:
        """atualizar_checkpoint_dominio atualiza um checkpoint existente."""
        self.repo.atualizar_checkpoint_dominio(
            dominio="professores",
            ultimo_id_execucao=self.id_exec,
            ultima_pagina=1,
            token_parada="50",
            indice_sincronizacao=None,
            ultima_situacao="concluido",
            sucesso=True,
        )
        novo_id = uuid.uuid4()
        self.repo.atualizar_checkpoint_dominio(
            dominio="professores",
            ultimo_id_execucao=novo_id,
            ultima_pagina=4,
            token_parada="350",
            indice_sincronizacao=None,
            ultima_situacao="concluido",
            sucesso=True,
        )
        self.assertEqual(
            EtlCheckpointDominio.objects.filter(dominio="professores").count(), 1
        )
        checkpoint = EtlCheckpointDominio.objects.get(dominio="professores")
        self.assertEqual(checkpoint.ultima_pagina, 4)
        self.assertEqual(checkpoint.token_parada, "350")

    def test_obter_checkpoint_retorna_dict(self) -> None:
        """obter_checkpoint_dominio retorna dicionário com dados do checkpoint."""
        self.repo.atualizar_checkpoint_dominio(
            dominio="professores",
            ultimo_id_execucao=self.id_exec,
            ultima_pagina=3,
            token_parada="200",
            indice_sincronizacao=None,
            ultima_situacao="erro",
            sucesso=False,
        )
        resultado = self.repo.obter_checkpoint_dominio("professores")
        self.assertIsNotNone(resultado)
        assert resultado is not None
        self.assertEqual(resultado["dominio"], "professores")
        self.assertEqual(resultado["ultima_pagina"], 3)
        self.assertEqual(resultado["ultima_situacao"], "erro")

    def test_checkpoint_erro_nao_atualiza_ultimo_sucesso(self) -> None:
        """Verifica que um checkpoint com erro não atualiza ultimo_sucesso_em."""
        self.repo.atualizar_checkpoint_dominio(
            dominio="professores",
            ultimo_id_execucao=self.id_exec,
            ultima_pagina=1,
            token_parada="0",
            indice_sincronizacao=None,
            ultima_situacao="erro",
            sucesso=False,
        )
        checkpoint = EtlCheckpointDominio.objects.get(dominio="professores")
        self.assertIsNone(checkpoint.ultimo_sucesso_em)
