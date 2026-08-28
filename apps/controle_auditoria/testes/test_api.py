"""Testes dos endpoints e autenticacao da API de controle_auditoria."""

from datetime import timedelta
from typing import Any
from unittest.mock import ANY, patch
from uuid import uuid4

from django.test import Client, TestCase, override_settings
from django.utils import timezone
from django.utils.timezone import localtime
from rest_framework.test import APIClient

from apps.controle_auditoria.api.authentication import ApiKeyAuthentication
from apps.controle_auditoria.models import (
    EtlCheckpointDominio,
    EtlExecucao,
    EtlExecucaoTabelaEscrita,
    EtlExecucaoTabelaLida,
    EtlProgressoExecucao,
)


class ApiKeyAuthenticationTestCase(TestCase):
    """Valida autenticação por API key."""

    def setUp(self) -> None:
        """Configura autenticação."""
        self.authentication = ApiKeyAuthentication()

    @override_settings(API_KEY="")
    def test_deve_falhar_sem_api_key_configurada(self) -> None:
        """Falha quando API key esperada não está configurada."""
        request = type("Request", (), {"headers": {}})()
        with self.assertRaisesMessage(Exception, "API key nao configurada"):
            self.authentication.authenticate(request)

    @override_settings(API_KEY="segredo")
    def test_deve_retornar_none_sem_header(self) -> None:
        """Sem header de chave, autenticação retorna None."""
        request = type("Request", (), {"headers": {}})()
        self.assertIsNone(self.authentication.authenticate(request))

    @override_settings(API_KEY="segredo")
    def test_deve_falhar_com_header_invalido(self) -> None:
        """Com chave inválida, autenticação falha."""
        request = type(
            "Request",
            (),
            {"headers": {"X-API-Key": "invalida"}},
        )()
        with self.assertRaisesMessage(Exception, "API key invalida"):
            self.authentication.authenticate(request)

    @override_settings(API_KEY="segredo")
    def test_deve_autenticar_com_header_valido(self) -> None:
        """Com chave válida, autenticação retorna usuário autenticado."""
        request = type(
            "Request",
            (),
            {"headers": {"X-API-Key": "segredo"}},
        )()
        resultado = self.authentication.authenticate(request)
        assert resultado is not None

        usuario, _ = resultado
        self.assertTrue(usuario.is_authenticated)


@override_settings(API_KEY="segredo")
class ViewsApiControleAuditoriaTestCase(TestCase):
    """Valida endpoints DRF de checkpoints, execuções e disparo."""

    def setUp(self) -> None:
        """Configura client e headers de autenticação."""
        self.client = APIClient()
        self.headers = {"HTTP_X_API_KEY": "segredo"}

    def test_deve_listar_checkpoints(self) -> None:
        """Retorna lista de checkpoints."""
        EtlCheckpointDominio.objects.create(
            dominio="institucional",
            ultimo_id_execucao=uuid4(),
            ultima_pagina=2,
            token_parada="200",
            indice_sincronizacao="institucional:offset:200",
            ultima_situacao="sucesso",
        )

        resposta = self.client.get("/api/v1/checkpoints/", **self.headers)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 1)

    def test_deve_listar_execucoes(self) -> None:
        """Retorna execuções mais recentes."""
        EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="institucional",
            situacao="sucesso",
            iniciado_em=timezone.now(),
        )

        resposta = self.client.get("/api/v1/execucoes/", **self.headers)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 1)

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_deve_enfileirar_execucao_imediata(self, tarefa_mock: Any) -> None:
        """POST sem data agenda execução imediata."""
        tarefa_mock.apply_async.return_value = type(
            "Result", (), {"id": "task-1"}
        )()
        resposta = self.client.post(
            "/api/v1/dominios/institucional/executar/",
            data={"volume": 10, "offset": 1, "continuar": True},
            format="json",
            **self.headers,
        )
        self.assertEqual(resposta.status_code, 202)
        self.assertEqual(resposta.json()["task_id"], "task-1")
        tarefa_mock.apply_async.assert_called_once_with(
            kwargs={
                "dominio": "institucional",
                "volume": 10,
                "offset": 1,
                "continuar": True,
                "parametros_disparo": {
                    "origem": "api",
                    "prioridade": 5,
                    "executar_em": None,
                    "celery_task_id": ANY,
                },
            },
            priority=5,
            task_id=ANY,
        )

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_deve_enfileirar_alunos_com_anos_letivos(
        self, tarefa_mock: Any
    ) -> None:
        """POST em alunos aceita anos_letivos e repassa para a task."""
        tarefa_mock.apply_async.return_value = type(
            "Result", (), {"id": "task-alunos"}
        )()
        resposta = self.client.post(
            "/api/v1/dominios/alunos/executar/",
            data={"anos_letivos": [2021, 2022, 2023, 2024, 2025]},
            format="json",
            **self.headers,
        )
        self.assertEqual(resposta.status_code, 202)
        tarefa_mock.apply_async.assert_called_once_with(
            kwargs={
                "dominio": "alunos",
                "volume": 100,
                "offset": 0,
                "continuar": False,
                "anos_letivos": [2021, 2022, 2023, 2024, 2025],
                "parametros_disparo": {
                    "origem": "api",
                    "prioridade": 5,
                    "executar_em": None,
                    "celery_task_id": ANY,
                },
            },
            priority=5,
            task_id=ANY,
        )

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_deve_enfileirar_pedagogico_com_anos_letivos(
        self, tarefa_mock: Any
    ) -> None:
        """POST em pedagógico aceita anos_letivos e repassa para a task."""
        tarefa_mock.apply_async.return_value = type(
            "Result", (), {"id": "task-pedagogico"}
        )()
        resposta = self.client.post(
            "/api/v1/dominios/pedagogico/executar/",
            data={"anos_letivos": [2024]},
            format="json",
            **self.headers,
        )
        self.assertEqual(resposta.status_code, 202)
        tarefa_mock.apply_async.assert_called_once_with(
            kwargs={
                "dominio": "pedagogico",
                "volume": 100,
                "offset": 0,
                "continuar": False,
                "anos_letivos": [2024],
                "parametros_disparo": {
                    "origem": "api",
                    "prioridade": 5,
                    "executar_em": None,
                    "celery_task_id": ANY,
                },
            },
            priority=5,
            task_id=ANY,
        )

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_deve_enfileirar_programas_com_anos_letivos(
        self, tarefa_mock: Any
    ) -> None:
        """POST em programas aceita anos_letivos e repassa para a task."""
        tarefa_mock.apply_async.return_value = type(
            "Result", (), {"id": "task-programas"}
        )()
        resposta = self.client.post(
            "/api/v1/dominios/programas/executar/",
            data={"anos_letivos": [2025, 2026]},
            format="json",
            **self.headers,
        )
        self.assertEqual(resposta.status_code, 202)
        tarefa_mock.apply_async.assert_called_once_with(
            kwargs={
                "dominio": "programas",
                "volume": 100,
                "offset": 0,
                "continuar": False,
                "anos_letivos": [2025, 2026],
                "parametros_disparo": {
                    "origem": "api",
                    "prioridade": 5,
                    "executar_em": None,
                    "celery_task_id": ANY,
                },
            },
            priority=5,
            task_id=ANY,
        )

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_deve_normalizar_ano_letivo_unico_em_programas(
        self, tarefa_mock: Any
    ) -> None:
        """POST em programas aceita ano único em anos_letivos."""
        tarefa_mock.apply_async.return_value = type(
            "Result", (), {"id": "task-programas"}
        )()
        resposta = self.client.post(
            "/api/v1/dominios/programas/executar/",
            data={"anos_letivos": 2026},
            format="json",
            **self.headers,
        )
        self.assertEqual(resposta.status_code, 202)
        tarefa_mock.apply_async.assert_called_once_with(
            kwargs={
                "dominio": "programas",
                "volume": 100,
                "offset": 0,
                "continuar": False,
                "anos_letivos": [2026],
                "parametros_disparo": {
                    "origem": "api",
                    "prioridade": 5,
                    "executar_em": None,
                    "celery_task_id": ANY,
                },
            },
            priority=5,
            task_id=ANY,
        )

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_deve_agendar_execucao_com_data_hora(
        self, tarefa_mock: Any
    ) -> None:
        """POST com executar_em usa apply_async com eta."""
        tarefa_mock.apply_async.return_value = type(
            "Result",
            (),
            {"id": "task-2"},
        )()
        resposta = self.client.post(
            "/api/v1/dominios/institucional/executar/",
            data={
                "volume": 20,
                "offset": 2,
                "continuar": False,
                "executar_em": "2026-03-10T23:00:00-03:00",
            },
            format="json",
            **self.headers,
        )
        self.assertEqual(resposta.status_code, 202)
        self.assertEqual(resposta.json()["task_id"], "task-2")
        self.assertTrue(tarefa_mock.apply_async.called)

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_deve_rejeitar_data_hora_invalida(self, tarefa_mock: Any) -> None:
        """Retorna 400 quando executar_em está inválido."""
        resposta = self.client.post(
            "/api/v1/dominios/institucional/executar/",
            data={"executar_em": "nao-e-data"},
            format="json",
            **self.headers,
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("erro", resposta.json())
        tarefa_mock.apply_async.assert_not_called()

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_deve_rejeitar_ano_letivo_em_dominio_sem_suporte(
        self,
        tarefa_mock: Any,
    ) -> None:
        """Retorna 400 quando domínio não aceita ano_letivo."""
        resposta = self.client.post(
            "/api/v1/dominios/programas/executar/",
            data={"ano_letivo": 2025},
            format="json",
            **self.headers,
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("ano_letivo", resposta.json()["erro"])
        tarefa_mock.apply_async.assert_not_called()

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_deve_rejeitar_ano_letivo_em_alunos(
        self,
        tarefa_mock: Any,
    ) -> None:
        """Retorna 400 quando domínio alunos recebe ano_letivo."""
        resposta = self.client.post(
            "/api/v1/dominios/alunos/executar/",
            data={"ano_letivo": 2024},
            format="json",
            **self.headers,
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("ano_letivo", resposta.json()["erro"])
        tarefa_mock.apply_async.assert_not_called()

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_deve_rejeitar_fases_em_dominio_sem_suporte(
        self,
        tarefa_mock: Any,
    ) -> None:
        """Retorna 400 quando domínio não aceita fases."""
        resposta = self.client.post(
            "/api/v1/dominios/programas/executar/",
            data={"fases": ["turma"]},
            format="json",
            **self.headers,
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("fases", resposta.json()["erro"])
        tarefa_mock.apply_async.assert_not_called()

    def test_docs_e_schema_devem_ser_publicos(self) -> None:
        """Swagger e schema devem responder sem autenticação."""
        schema = self.client.get("/api/v1/schema/")
        docs = self.client.get("/api/v1/docs/")
        self.assertEqual(schema.status_code, 200)
        self.assertEqual(docs.status_code, 200)

    def test_endpoints_protegidos_sem_api_key(self) -> None:
        """Sem API key, endpoints da API devem negar acesso."""
        resposta = self.client.get("/api/v1/checkpoints/")
        self.assertEqual(resposta.status_code, 403)

    def test_deve_retornar_detalhe_de_execucao_com_tabelas(self) -> None:
        """Retorna execução com tabelas lidas e escritas aninhadas."""
        id_exec = uuid4()
        EtlExecucao.objects.create(
            id_execucao=id_exec,
            dominio="institucional",
            situacao="sucesso",
            iniciado_em=timezone.now(),
        )
        EtlExecucaoTabelaLida.objects.create(
            id_execucao=id_exec,
            tabela_origem="dbo.v_cadastro",
            numero_pagina=1,
            linhas_lidas=100,
        )
        EtlExecucaoTabelaEscrita.objects.create(
            id_execucao=id_exec,
            tabela_destino="institucional",
            linhas_escritas=100,
            modo_escrita="upsert",
        )

        resposta = self.client.get(
            f"/api/v1/execucoes/{id_exec}/", **self.headers
        )
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertEqual(dados["id_execucao"], str(id_exec))
        self.assertEqual(len(dados["tabelas_lidas"]), 1)
        self.assertEqual(len(dados["tabelas_escritas"]), 1)
        self.assertEqual(
            dados["tabelas_lidas"][0]["tabela_origem"], "dbo.v_cadastro"
        )
        self.assertEqual(
            dados["tabelas_escritas"][0]["tabela_destino"], "institucional"
        )

    def test_deve_retornar_404_para_execucao_inexistente(self) -> None:
        """Retorna 404 quando id_execucao não existe."""
        resposta = self.client.get(
            f"/api/v1/execucoes/{uuid4()}/", **self.headers
        )
        self.assertEqual(resposta.status_code, 404)
        self.assertIn("erro", resposta.json())

    def test_deve_cancelar_execucao_em_andamento(self) -> None:
        """DELETE marca execução em_execucao como cancelado."""
        exec_id = uuid4()
        EtlExecucao.objects.create(
            id_execucao=exec_id,
            dominio="alunos",
            situacao="em_execucao",
            iniciado_em=timezone.now(),
        )

        resposta = self.client.delete(
            f"/api/v1/execucoes/{exec_id}/", **self.headers
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["cancelado"], str(exec_id))
        execucao = EtlExecucao.objects.get(id_execucao=exec_id)
        self.assertEqual(execucao.situacao, "cancelado")
        self.assertIsNotNone(execucao.finalizado_em)

    def test_deve_retornar_409_ao_cancelar_execucao_finalizada(self) -> None:
        """DELETE retorna 409 quando execução já está finalizada."""
        exec_id = uuid4()
        EtlExecucao.objects.create(
            id_execucao=exec_id,
            dominio="alunos",
            situacao="sucesso",
            iniciado_em=timezone.now(),
            finalizado_em=timezone.now(),
        )

        resposta = self.client.delete(
            f"/api/v1/execucoes/{exec_id}/", **self.headers
        )

        self.assertEqual(resposta.status_code, 409)
        self.assertIn("erro", resposta.json())

    def test_deve_retornar_404_ao_cancelar_execucao_inexistente(self) -> None:
        """DELETE retorna 404 quando id_execucao não existe."""
        resposta = self.client.delete(
            f"/api/v1/execucoes/{uuid4()}/", **self.headers
        )
        self.assertEqual(resposta.status_code, 404)
        self.assertIn("erro", resposta.json())

    def test_deve_listar_tabelas_lidas(self) -> None:
        """Retorna registros de tabelas lidas."""
        EtlExecucaoTabelaLida.objects.create(
            id_execucao=uuid4(),
            tabela_origem="dbo.v_cadastro",
            numero_pagina=1,
            linhas_lidas=50,
        )

        resposta = self.client.get(
            "/api/v1/execucoes/tabelas-lidas/", **self.headers
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 1)

    def test_deve_listar_tabelas_escritas(self) -> None:
        """Retorna registros de tabelas escritas."""
        EtlExecucaoTabelaEscrita.objects.create(
            id_execucao=uuid4(),
            tabela_destino="institucional",
            linhas_escritas=50,
            modo_escrita="upsert",
        )

        resposta = self.client.get(
            "/api/v1/execucoes/tabelas-escritas/", **self.headers
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 1)

    @patch("apps.controle_auditoria.api.views.aplicacao_celery")
    def test_deve_marcar_execucao_orfa_como_interrompida(
        self, celery_mock: Any
    ) -> None:
        """Limpeza marca em_execucao sem heartbeat recente."""
        celery_mock.control.inspect.return_value.active.return_value = {}
        celery_mock.control.inspect.return_value.reserved.return_value = {}
        celery_mock.control.inspect.return_value.scheduled.return_value = {}
        id_exec = uuid4()
        EtlExecucao.objects.create(
            id_execucao=id_exec,
            dominio="programas",
            situacao="em_execucao",
            iniciado_em=timezone.now() - timedelta(hours=2),
        )

        resposta = self.client.post(
            "/api/v1/execucoes/limpar-orfas/",
            data={},
            format="json",
            **self.headers,
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["total_interrompido"], 1)
        execucao = EtlExecucao.objects.get(id_execucao=id_exec)
        self.assertEqual(execucao.situacao, "interrompido")
        self.assertIsNotNone(execucao.finalizado_em)

    @patch("apps.controle_auditoria.api.views.aplicacao_celery")
    def test_deve_interromper_execucao_sem_task_mesmo_com_heartbeat_recente(
        self, celery_mock: Any
    ) -> None:
        """Limpeza usa Celery como fonte da verdade, não janela de tempo."""
        celery_mock.control.inspect.return_value.active.return_value = {}
        celery_mock.control.inspect.return_value.reserved.return_value = {}
        celery_mock.control.inspect.return_value.scheduled.return_value = {}
        id_exec = uuid4()
        EtlExecucao.objects.create(
            id_execucao=id_exec,
            dominio="programas",
            situacao="em_execucao",
            iniciado_em=timezone.now() - timedelta(hours=2),
        )
        EtlProgressoExecucao.objects.create(
            id_execucao=id_exec,
            dominio="programas",
            fase_numero=1,
            total_fases=8,
            fase_nome="tipo_programa",
            etapa="processando_chunk",
        )

        resposta = self.client.post(
            "/api/v1/execucoes/limpar-orfas/",
            data={},
            format="json",
            **self.headers,
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["total_interrompido"], 1)
        self.assertEqual(resposta.json()["total_preservado"], 0)
        self.assertEqual(resposta.json()["itens"][0]["motivo"], "sem_task_id")
        execucao = EtlExecucao.objects.get(id_execucao=id_exec)
        self.assertEqual(execucao.situacao, "interrompido")

    @patch("apps.controle_auditoria.api.views.aplicacao_celery")
    def test_nao_deve_interromper_execucao_com_task_celery_viva(
        self, celery_mock: Any
    ) -> None:
        """Limpeza preserva execução se task_id ainda está ativo no Celery."""
        task_id = "task-viva"
        celery_mock.control.inspect.return_value.active.return_value = {
            "worker@1": [{"id": task_id, "name": "etl.executar_dominio"}]
        }
        celery_mock.control.inspect.return_value.reserved.return_value = {}
        celery_mock.control.inspect.return_value.scheduled.return_value = {}
        id_exec = uuid4()
        EtlExecucao.objects.create(
            id_execucao=id_exec,
            dominio="programas",
            situacao="em_execucao",
            iniciado_em=timezone.now() - timedelta(hours=2),
            parametros={"disparo": {"celery_task_id": task_id}},
        )

        resposta = self.client.post(
            "/api/v1/execucoes/limpar-orfas/",
            data={},
            format="json",
            **self.headers,
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["total_interrompido"], 0)
        self.assertEqual(resposta.json()["total_preservado"], 1)
        self.assertEqual(
            resposta.json()["itens"][0]["motivo"], "task_celery_viva"
        )
        execucao = EtlExecucao.objects.get(id_execucao=id_exec)
        self.assertEqual(execucao.situacao, "em_execucao")

    @patch("apps.controle_auditoria.api.views.aplicacao_celery")
    def test_nao_deve_limpar_orfas_sem_resposta_do_celery(
        self, celery_mock: Any
    ) -> None:
        """Limpeza falha fechada quando nenhum worker responde."""
        celery_mock.control.inspect.return_value.active.return_value = None
        celery_mock.control.inspect.return_value.reserved.return_value = None
        celery_mock.control.inspect.return_value.scheduled.return_value = None
        id_exec = uuid4()
        EtlExecucao.objects.create(
            id_execucao=id_exec,
            dominio="programas",
            situacao="em_execucao",
            iniciado_em=timezone.now() - timedelta(hours=2),
        )

        resposta = self.client.post(
            "/api/v1/execucoes/limpar-orfas/",
            data={},
            format="json",
            **self.headers,
        )

        self.assertEqual(resposta.status_code, 503)
        execucao = EtlExecucao.objects.get(id_execucao=id_exec)
        self.assertEqual(execucao.situacao, "em_execucao")

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_deve_reprocessar_ultima_execucao_com_erro(
        self, tarefa_mock: Any
    ) -> None:
        """Recovery reusa parâmetros da execução com erro e força continuar."""
        id_exec = uuid4()
        tarefa_mock.apply_async.return_value = type(
            "Result", (), {"id": "task-recovery"}
        )()
        EtlExecucao.objects.create(
            id_execucao=id_exec,
            dominio="pedagogico",
            situacao="erro",
            iniciado_em=timezone.now(),
            parametros={
                "execucao": {
                    "volume": 500,
                    "offset": 0,
                    "anos_letivos": [2026],
                },
                "disparo": {"origem": "api"},
            },
        )

        resposta = self.client.post(
            "/api/v1/execucoes/reprocessar-erros/",
            data={"max_tentativas": 3},
            format="json",
            **self.headers,
        )

        self.assertEqual(resposta.status_code, 202)
        self.assertEqual(resposta.json()["total_reprocessado"], 1)
        tarefa_mock.apply_async.assert_called_once_with(
            kwargs={
                "dominio": "pedagogico",
                "volume": 500,
                "offset": 0,
                "continuar": True,
                "parametros_disparo": {
                    "origem": "recovery",
                    "execucao_origem": str(id_exec),
                    "execucao_erro": str(id_exec),
                    "tentativa": 1,
                    "prioridade": 3,
                    "continuar": True,
                    "celery_task_id": ANY,
                },
                "anos_letivos": [2026],
            },
            priority=3,
            task_id=ANY,
        )

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_reprocessamento_deve_respeitar_limite_tentativas(
        self, tarefa_mock: Any
    ) -> None:
        """Recovery ignora execução que atingiu limite de tentativas."""
        id_origem = uuid4()
        id_erro = uuid4()
        EtlExecucao.objects.create(
            id_execucao=id_erro,
            dominio="programas",
            situacao="erro",
            iniciado_em=timezone.now(),
            parametros={
                "execucao": {"volume": 100, "anos_letivos": [2026]},
                "disparo": {"execucao_origem": str(id_origem)},
            },
        )
        for tentativa in range(3):
            EtlExecucao.objects.create(
                id_execucao=uuid4(),
                dominio="programas",
                situacao="erro",
                iniciado_em=timezone.now() - timedelta(minutes=tentativa + 1),
                parametros={
                    "disparo": {
                        "origem": "recovery",
                        "execucao_origem": str(id_origem),
                    }
                },
            )

        resposta = self.client.post(
            "/api/v1/execucoes/reprocessar-erros/",
            data={"max_tentativas": 3},
            format="json",
            **self.headers,
        )

        self.assertEqual(resposta.status_code, 202)
        dados = resposta.json()
        self.assertEqual(dados["total_reprocessado"], 0)
        self.assertEqual(dados["itens"][0]["status"], "ignorado")
        self.assertEqual(dados["itens"][0]["motivo"], "limite_tentativas")
        tarefa_mock.apply_async.assert_not_called()

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_reprocessamento_ignora_erro_antigo_com_sucesso_recente(
        self, tarefa_mock: Any
    ) -> None:
        """Recovery considera apenas a última execução por domínio."""
        EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="alunos",
            situacao="erro",
            iniciado_em=timezone.now() - timedelta(hours=1),
        )
        EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="alunos",
            situacao="concluido",
            iniciado_em=timezone.now(),
        )

        resposta = self.client.post(
            "/api/v1/execucoes/reprocessar-erros/",
            data={"max_tentativas": 3},
            format="json",
            **self.headers,
        )

        self.assertEqual(resposta.status_code, 202)
        self.assertEqual(resposta.json()["total_analisado"], 0)
        tarefa_mock.apply_async.assert_not_called()

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_deve_reprocessar_execucao_interrompida(
        self, tarefa_mock: Any
    ) -> None:
        """Recovery também considera execução interrompida."""
        tarefa_mock.apply_async.return_value = type(
            "Result", (), {"id": "task-interrompido"}
        )()
        EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="programas",
            situacao="interrompido",
            iniciado_em=timezone.now(),
            parametros={
                "execucao": {"volume": 500, "anos_letivos": [2026]},
                "disparo": {"origem": "api"},
            },
        )

        resposta = self.client.post(
            "/api/v1/execucoes/reprocessar-erros/",
            data={"max_tentativas": 3},
            format="json",
            **self.headers,
        )

        self.assertEqual(resposta.status_code, 202)
        self.assertEqual(resposta.json()["total_reprocessado"], 1)
        self.assertTrue(tarefa_mock.apply_async.called)


class MonitoramentoViewsTestCase(TestCase):
    """Valida endpoints públicos de monitoramento."""

    def setUp(self) -> None:
        """Cria execuções de teste."""
        self.client = APIClient()
        self.id_exec_a = uuid4()
        self.id_exec_b = uuid4()
        EtlExecucao.objects.create(
            id_execucao=self.id_exec_a,
            dominio="institucional",
            situacao="sucesso",
            iniciado_em=timezone.now(),
        )
        EtlExecucao.objects.create(
            id_execucao=self.id_exec_b,
            dominio="sinc_rec_db",
            situacao="erro",
            iniciado_em=timezone.now(),
        )

    def test_monitoramento_deve_listar_execucoes_sem_auth(self) -> None:
        """Endpoint de monitoramento retorna execuções sem autenticação."""
        resposta = self.client.get("/api/v1/monitoramento/execucoes/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 2)

    def test_monitoramento_deve_filtrar_por_dominio(self) -> None:
        """Filtro por dominio retorna apenas execuções do domínio."""
        resposta = self.client.get(
            "/api/v1/monitoramento/execucoes/?dominio=institucional"
        )
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["dominio"], "institucional")

    def test_monitoramento_deve_filtrar_por_situacao(self) -> None:
        """Filtro por situacao retorna execuções da situação."""
        resposta = self.client.get(
            "/api/v1/monitoramento/execucoes/?situacao=erro"
        )
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["situacao"], "erro")

    def test_monitoramento_deve_filtrar_por_data_inicio(self) -> None:
        """Filtro por data_inicio retorna execuções a partir daquela data."""
        hoje = localtime(timezone.now()).date().isoformat()
        resposta = self.client.get(
            f"/api/v1/monitoramento/execucoes/?data_inicio={hoje}"
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 2)

    def test_monitoramento_deve_filtrar_por_data_fim(self) -> None:
        """Filtro por data_fim retorna execuções até aquela data."""
        hoje = timezone.now().date().isoformat()
        resposta = self.client.get(
            f"/api/v1/monitoramento/execucoes/?data_fim={hoje}"
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 2)

    def test_monitoramento_deve_retornar_resumo_por_dominio(self) -> None:
        """Resumo retorna a última execução de cada domínio."""
        resposta = self.client.get("/api/v1/monitoramento/resumo/")
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        dominios = [d["dominio"] for d in dados]
        self.assertIn("institucional", dominios)
        self.assertIn("sinc_rec_db", dominios)

    def test_monitoramento_resumo_retorna_apenas_ultima_por_dominio(
        self,
    ) -> None:
        """Resumo retorna somente 1 entrada por domínio."""
        EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="institucional",
            situacao="erro",
            iniciado_em=timezone.now(),
        )
        resposta = self.client.get("/api/v1/monitoramento/resumo/")
        self.assertEqual(resposta.status_code, 200)
        dominios = [d["dominio"] for d in resposta.json()]
        self.assertEqual(dominios.count("institucional"), 1)


class DashboardViewTestCase(TestCase):
    """Valida o dashboard público."""

    def setUp(self) -> None:
        """Cria execuções para o dashboard."""
        self.client = Client()
        EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="institucional",
            situacao="sucesso",
            iniciado_em=timezone.now(),
        )

    def test_dashboard_deve_responder_sem_auth(self) -> None:
        """Dashboard retorna 200 sem autenticação."""
        resposta = self.client.get("/dashboard/")
        self.assertEqual(resposta.status_code, 200)

    def test_dashboard_deve_responder_com_filtro_dominio(self) -> None:
        """Dashboard com filtro de domínio retorna 200."""
        resposta = self.client.get("/dashboard/?dominio=institucional")
        self.assertEqual(resposta.status_code, 200)

    def test_dashboard_deve_responder_com_filtro_situacao(self) -> None:
        """Dashboard com filtro de situação retorna 200."""
        resposta = self.client.get("/dashboard/?situacao=sucesso")
        self.assertEqual(resposta.status_code, 200)

    def test_dashboard_deve_responder_com_todos_os_filtros(self) -> None:
        """Dashboard com todos os filtros combinados retorna 200."""
        hoje = timezone.now().date().isoformat()
        resposta = self.client.get(
            f"/dashboard/?dominio=institucional&situacao=sucesso"
            f"&data_inicio={hoje}&data_fim={hoje}"
        )
        self.assertEqual(resposta.status_code, 200)

    def test_dashboard_sem_execucoes(self) -> None:
        """Dashboard responde 200 mesmo sem execuções registradas."""
        EtlExecucao.objects.all().delete()
        resposta = self.client.get("/dashboard/")
        self.assertEqual(resposta.status_code, 200)

    def test_dashboard_usa_escrita_mais_recente_para_tabela_repetida(
        self,
    ) -> None:
        """Dashboard ignora registros antigos repetidos da mesma tabela."""
        execucao = EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="pedagogico",
            situacao="concluido",
            iniciado_em=timezone.now() + timedelta(minutes=1),
        )
        EtlExecucaoTabelaEscrita.objects.create(
            id_execucao=execucao.id_execucao,
            tabela_destino="componente_curricular",
            linhas_escritas=10,
            modo_escrita="upsert",
        )
        EtlExecucaoTabelaEscrita.objects.create(
            id_execucao=execucao.id_execucao,
            tabela_destino="componente_curricular",
            linhas_escritas=5,
            modo_escrita="upsert",
        )

        resposta = self.client.get("/dashboard/?dominio=pedagogico")

        self.assertEqual(resposta.status_code, 200)
        tabelas = resposta.context["ultimas_10"][0]["tabelas"]
        self.assertEqual(len(tabelas), 1)
        self.assertEqual(tabelas[0]["tabela_destino"], "componente_curricular")
        self.assertEqual(tabelas[0]["linhas_escritas"], 5)


class KanbanViewTestCase(TestCase):
    """Valida o kanban público."""

    def setUp(self) -> None:
        """Cria execuções para o kanban."""
        self.client = Client()
        agora = timezone.now()
        self.exec_institucional_antiga = EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="institucional",
            situacao="erro",
            iniciado_em=agora - timedelta(hours=2),
        )
        self.exec_institucional_atual = EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="institucional",
            situacao="concluido",
            iniciado_em=agora - timedelta(hours=1),
        )
        self.exec_pedagogico = EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="pedagogico",
            situacao="concluido",
            iniciado_em=agora,
        )
        EtlExecucaoTabelaLida.objects.create(
            id_execucao=self.exec_institucional_antiga.id_execucao,
            tabela_origem="tabela_antiga",
            numero_pagina=1,
            linhas_lidas=10,
        )

    def test_kanban_sem_filtro_mantem_ultima_execucao_por_dominio(
        self,
    ) -> None:
        """Sem filtros, kanban exibe a última execução de cada domínio."""
        resposta = self.client.get("/dashboard/kanban/")
        self.assertEqual(resposta.status_code, 200)

        ids = {
            item["exec"].id_execucao
            for item in resposta.context["dominios_kanban"]
        }

        self.assertIn(self.exec_institucional_atual.id_execucao, ids)
        self.assertIn(self.exec_pedagogico.id_execucao, ids)
        self.assertNotIn(self.exec_institucional_antiga.id_execucao, ids)

    def test_kanban_com_id_execucao_renderiza_execucao_especifica(
        self,
    ) -> None:
        """Filtro por id_execucao exibe a execução selecionada."""
        resposta = self.client.get(
            f"/dashboard/kanban/?id_execucao="
            f"{self.exec_institucional_antiga.id_execucao}"
        )
        self.assertEqual(resposta.status_code, 200)

        dominios_kanban = resposta.context["dominios_kanban"]
        self.assertEqual(len(dominios_kanban), 1)
        self.assertEqual(
            dominios_kanban[0]["exec"].id_execucao,
            self.exec_institucional_antiga.id_execucao,
        )
        self.assertEqual(dominios_kanban[0]["total_lido"], 10)

    def test_kanban_select_execucoes_respeita_dominio_filtrado(
        self,
    ) -> None:
        """Lista de execuções deve respeitar o domínio filtrado."""
        resposta = self.client.get("/dashboard/kanban/?dominio=pedagogico")
        self.assertEqual(resposta.status_code, 200)

        execucoes = resposta.context["execucoes_disponiveis"]
        self.assertTrue(execucoes)
        self.assertTrue(all(e.dominio == "pedagogico" for e in execucoes))

    def test_kanban_combinacao_dominio_execucao_invalida_exibe_vazio(
        self,
    ) -> None:
        """Execução fora do domínio filtrado não deve ser exibida."""
        resposta = self.client.get(
            f"/dashboard/kanban/?dominio=pedagogico&id_execucao="
            f"{self.exec_institucional_antiga.id_execucao}"
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["dominios_kanban"], [])
        self.assertContains(
            resposta,
            "Execução não encontrada para os filtros aplicados.",
        )

    def test_kanban_com_id_execucao_invalido_exibe_vazio(self) -> None:
        """UUID inválido deve retornar página vazia com mensagem clara."""
        resposta = self.client.get("/dashboard/kanban/?id_execucao=invalido")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["dominios_kanban"], [])
        self.assertContains(
            resposta,
            "Execução não encontrada para os filtros aplicados.",
        )


class HealthSincRecViewTestCase(TestCase):
    """Testes para endpoints do HealthSincRecView."""

    def setUp(self) -> None:
        """Prepara cliente API para testes."""
        self.client = APIClient()

    def test_health_banco_ok(self) -> None:
        """Retorna 200 quando banco esta acessivel."""
        response = self.client.get("/api/v1/sinc_rec/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    @patch("apps.controle_auditoria.api.views.connections")
    def test_health_banco_erro(self, connections_mock: Any) -> None:
        """Retorna 503 quando banco lança excecao."""
        connections_mock.__getitem__.return_value.cursor.side_effect = (
            Exception()
        )

        response = self.client.get("/api/v1/sinc_rec/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "unhealthy")
