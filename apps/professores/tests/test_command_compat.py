"""Testes para management/commands/compat_professores.py."""

import json
import os
import tempfile
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from apps.professores.compat.base import ResultadoCompatibilidade

_CMD = "compat_professores"
_PATCH_EOL = (
    "apps.professores.management.commands.compat_professores.EOLService"
)
_PATCH_EXECUTOR = (
    "apps.professores.management.commands.compat_professores."
    "ExecutorCompatibilidade"
)
_PATCH_ETL = "apps.professores.services.EtlProfessoresService"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_resultado(
    verificador: str = "V",
    consulta: str = "C",
    aprovado: bool = True,
    ignorado: bool = False,
    erro: str = "",
) -> ResultadoCompatibilidade:
    r = ResultadoCompatibilidade(verificador=verificador, consulta=consulta)
    r.total_origem = 5
    r.correspondencias = 5 if aprovado else 0
    r.ignorado = ignorado
    r.erro = erro
    return r


def _sumario_compativel() -> dict:
    return {
        "total": 1,
        "aprovados": 1,
        "reprovados": 0,
        "ignorados": 0,
        "erros": 0,
        "compativel": True,
        "detalhes": ["[OK] V.C: 5/5 (100%) | destino=5"],
        "falhas": [],
    }


def _sumario_incompativel() -> dict:
    return {
        "total": 1,
        "aprovados": 0,
        "reprovados": 1,
        "ignorados": 0,
        "erros": 0,
        "compativel": False,
        "detalhes": ["[FALHA] V.C: 0/5 (0%) | destino=5"],
        "falhas": ["[FALHA] V.C: 0/5 (0%) | destino=5"],
    }


# ---------------------------------------------------------------------------
# Execução normal
# ---------------------------------------------------------------------------


class CompatProfessoresHandleTest(TestCase):
    """Testes para o fluxo principal do comando compat_professores."""

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    def test_execucao_compativel_nao_sai_com_erro(
        self, mock_eol: MagicMock, mock_executor_cls: MagicMock
    ) -> None:
        """Verifica que a execução não levanta SystemExit quando compatível."""
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = [_make_resultado()]
        mock_executor.resumo.return_value = _sumario_compativel()

        out = StringIO()
        call_command(_CMD, stdout=out)  # não deve levantar SystemExit

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    def test_execucao_incompativel_levanta_system_exit_1(
        self, mock_eol: MagicMock, mock_executor_cls: MagicMock
    ) -> None:
        """Verifica que SystemExit(1) é levantado quando há reprovados."""
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = [
            _make_resultado(aprovado=False)
        ]
        mock_executor.resumo.return_value = _sumario_incompativel()

        out = StringIO()
        with self.assertRaises(SystemExit) as ctx:
            call_command(_CMD, stdout=out)
        self.assertEqual(ctx.exception.code, 1)

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    def test_limite_padrao_e_30(
        self, mock_eol: MagicMock, mock_executor_cls: MagicMock
    ) -> None:
        """Verifica que o limite padrão é 30."""
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = []
        mock_executor.resumo.return_value = {
            "total": 0,
            "aprovados": 0,
            "reprovados": 0,
            "ignorados": 0,
            "erros": 0,
            "compativel": True,
            "detalhes": [],
            "falhas": [],
        }

        out = StringIO()
        call_command(_CMD, stdout=out)
        mock_executor_cls.assert_called_once_with(
            mock_eol.return_value, limite=30
        )

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    def test_limite_customizado_e_repassado(
        self, mock_eol: MagicMock, mock_executor_cls: MagicMock
    ) -> None:
        """Verifica que --limite repassa o valor customizado ao executor."""
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = []
        mock_executor.resumo.return_value = {
            "total": 0,
            "aprovados": 0,
            "reprovados": 0,
            "ignorados": 0,
            "erros": 0,
            "compativel": True,
            "detalhes": [],
            "falhas": [],
        }

        out = StringIO()
        call_command(_CMD, "--limite", "50", stdout=out)
        mock_executor_cls.assert_called_once_with(
            mock_eol.return_value, limite=50
        )

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    def test_saida_exibe_relatorio(
        self, mock_eol: MagicMock, mock_executor_cls: MagicMock
    ) -> None:
        """Verifica que o relatório é escrito na saída."""
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = [_make_resultado()]
        mock_executor.resumo.return_value = _sumario_compativel()

        out = StringIO()
        call_command(_CMD, stdout=out)
        output = out.getvalue()
        self.assertIn("RELATÓRIO DE COMPATIBILIDADE", output)
        self.assertIn("Total:", output)


# ---------------------------------------------------------------------------
# Flag --detalhes
# ---------------------------------------------------------------------------


class CompatProfessoresDetalhesTest(TestCase):
    """Testes para o flag --detalhes."""

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    def test_detalhes_exibe_divergencias(
        self, mock_eol: MagicMock, mock_executor_cls: MagicMock
    ) -> None:
        """Verifica que --detalhes exibe exemplos de divergências."""
        r = _make_resultado(aprovado=False)
        r.divergencias = [{"chave": (1, "rf"), "linha": {"id": 1}}]

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = [r]
        mock_executor.resumo.return_value = _sumario_incompativel()

        out = StringIO()
        with self.assertRaises(SystemExit):
            call_command(_CMD, "--detalhes", stdout=out)
        output = out.getvalue()
        self.assertIn("Divergências", output)

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    def test_sem_detalhes_nao_exibe_divergencias(
        self, mock_eol: MagicMock, mock_executor_cls: MagicMock
    ) -> None:
        """Verifica que sem --detalhes as divergências não aparecem."""
        r = _make_resultado(aprovado=False)
        r.divergencias = [{"chave": (1, "rf"), "linha": {"id": 1}}]

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = [r]
        mock_executor.resumo.return_value = _sumario_incompativel()

        out = StringIO()
        with self.assertRaises(SystemExit):
            call_command(_CMD, stdout=out)
        output = out.getvalue()
        self.assertNotIn("Divergências", output)


# ---------------------------------------------------------------------------
# Flag --saida
# ---------------------------------------------------------------------------


class CompatProfessoresSaidaTest(TestCase):
    """Testes para o flag --saida."""

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    def test_saida_cria_arquivo_json(
        self, mock_eol: MagicMock, mock_executor_cls: MagicMock
    ) -> None:
        """Verifica que --saida cria arquivo JSON válido."""
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = [_make_resultado()]
        mock_executor.resumo.return_value = _sumario_compativel()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            caminho = f.name

        try:
            out = StringIO()
            call_command(_CMD, "--saida", caminho, stdout=out)
            self.assertTrue(os.path.exists(caminho))
            with open(caminho, encoding="utf-8") as fp:
                payload = json.load(fp)
            self.assertIn("resultados", payload)
            self.assertIn("compativel", payload)
        finally:
            os.unlink(caminho)

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    def test_saida_json_contem_campos_de_resultado(
        self, mock_eol: MagicMock, mock_executor_cls: MagicMock
    ) -> None:
        """Verifica que o JSON de saída contém os campos esperados."""
        r = _make_resultado("MeuVer", "MinhaConsulta")
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = [r]
        mock_executor.resumo.return_value = _sumario_compativel()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            caminho = f.name

        try:
            out = StringIO()
            call_command(_CMD, "--saida", caminho, stdout=out)
            with open(caminho, encoding="utf-8") as fp:
                payload = json.load(fp)
            resultado_json = payload["resultados"][0]
            self.assertEqual(resultado_json["verificador"], "MeuVer")
            self.assertEqual(resultado_json["consulta"], "MinhaConsulta")
            self.assertIn("taxa_correspondencia", resultado_json)
            self.assertIn("aprovado", resultado_json)
        finally:
            os.unlink(caminho)

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    def test_saida_exibe_mensagem_de_arquivo_salvo(
        self, mock_eol: MagicMock, mock_executor_cls: MagicMock
    ) -> None:
        """Verifica que a mensagem de arquivo salvo aparece na saída."""
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = []
        mock_executor.resumo.return_value = {
            "total": 0,
            "aprovados": 0,
            "reprovados": 0,
            "ignorados": 0,
            "erros": 0,
            "compativel": True,
            "detalhes": [],
            "falhas": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            caminho = f.name

        try:
            out = StringIO()
            call_command(_CMD, "--saida", caminho, stdout=out)
            self.assertIn(caminho, out.getvalue())
        finally:
            os.unlink(caminho)


# ---------------------------------------------------------------------------
# Flag --rodar-etl
# ---------------------------------------------------------------------------


class CompatProfessoresRodarEtlTest(TestCase):
    """Testes para o flag --rodar-etl."""

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    @patch(_PATCH_ETL)
    def test_rodar_etl_chama_etl_service(
        self,
        mock_etl_cls: MagicMock,
        mock_eol: MagicMock,
        mock_executor_cls: MagicMock,
    ) -> None:
        """Verifica --rodar-etl e executa o EtlProfessoresService."""
        mock_etl = MagicMock()
        mock_etl_cls.return_value = mock_etl
        mock_etl.executar.return_value = {"unidade_educacional": 5}

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = []
        mock_executor.resumo.return_value = {
            "total": 0,
            "aprovados": 0,
            "reprovados": 0,
            "ignorados": 0,
            "erros": 0,
            "compativel": True,
            "detalhes": [],
            "falhas": [],
        }

        out = StringIO()
        call_command(_CMD, "--rodar-etl", stdout=out)
        mock_etl.executar.assert_called_once_with(fase_inicial=1)

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    @patch(_PATCH_ETL)
    def test_rodar_etl_define_env_vars(
        self,
        mock_etl_cls: MagicMock,
        mock_eol: MagicMock,
        mock_executor_cls: MagicMock,
    ) -> None:
        """Configura as variáveis de ambiente corretas."""
        env_vars_capturadas: dict = {}

        def captura_etl_executar(*args: object, **kwargs: object) -> dict:
            env_vars_capturadas["chunk"] = os.environ.get("EOL_CHUNK_SIZE")
            env_vars_capturadas["lote"] = os.environ.get("EOL_LOTE_MAXIMO")
            return {"unidade_educacional": 0}

        mock_etl = MagicMock()
        mock_etl_cls.return_value = mock_etl
        mock_etl.executar.side_effect = captura_etl_executar

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = []
        mock_executor.resumo.return_value = {
            "total": 0,
            "aprovados": 0,
            "reprovados": 0,
            "ignorados": 0,
            "erros": 0,
            "compativel": True,
            "detalhes": [],
            "falhas": [],
        }

        out = StringIO()
        call_command(_CMD, "--rodar-etl", "--limite", "15", stdout=out)
        self.assertEqual(env_vars_capturadas["chunk"], "15")
        self.assertEqual(env_vars_capturadas["lote"], "1")

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    @patch(_PATCH_ETL)
    def test_rodar_etl_restaura_env_vars_apos_execucao(
        self,
        mock_etl_cls: MagicMock,
        mock_eol: MagicMock,
        mock_executor_cls: MagicMock,
    ) -> None:
        """Verifica que as env vars são removidas após execução do ETL."""
        mock_etl = MagicMock()
        mock_etl_cls.return_value = mock_etl
        mock_etl.executar.return_value = {}

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = []
        mock_executor.resumo.return_value = {
            "total": 0,
            "aprovados": 0,
            "reprovados": 0,
            "ignorados": 0,
            "erros": 0,
            "compativel": True,
            "detalhes": [],
            "falhas": [],
        }

        out = StringIO()
        call_command(_CMD, "--rodar-etl", stdout=out)
        self.assertNotIn("EOL_CHUNK_SIZE", os.environ)
        self.assertNotIn("EOL_LOTE_MAXIMO", os.environ)

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    @patch(_PATCH_ETL)
    def test_rodar_etl_restaura_env_vars_mesmo_com_excecao(
        self,
        mock_etl_cls: MagicMock,
        mock_eol: MagicMock,
        mock_executor_cls: MagicMock,
    ) -> None:
        """Se env vars são restauradas mesmo se o ETL levantar exceção."""
        mock_etl = MagicMock()
        mock_etl_cls.return_value = mock_etl
        mock_etl.executar.side_effect = RuntimeError("ETL falhou")

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = []
        mock_executor.resumo.return_value = {
            "total": 0,
            "aprovados": 0,
            "reprovados": 0,
            "ignorados": 0,
            "erros": 0,
            "compativel": True,
            "detalhes": [],
            "falhas": [],
        }

        out = StringIO()
        with self.assertRaises(RuntimeError):
            call_command(_CMD, "--rodar-etl", stdout=out)

        self.assertNotIn("EOL_CHUNK_SIZE", os.environ)
        self.assertNotIn("EOL_LOTE_MAXIMO", os.environ)


# ---------------------------------------------------------------------------
# Exibição de resultados ignorados e com erro
# ---------------------------------------------------------------------------


class CompatProfessoresExibicaoTest(TestCase):
    """Testes de exibição de resultados variados."""

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    def test_resultado_ignorado_exibido(
        self, mock_eol: MagicMock, mock_executor_cls: MagicMock
    ) -> None:
        """Verifica que resultado ignorado é exibido corretamente."""
        r = _make_resultado(ignorado=True)

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = [r]
        mock_executor.resumo.return_value = {
            "total": 1,
            "aprovados": 0,
            "reprovados": 0,
            "ignorados": 1,
            "erros": 0,
            "compativel": True,
            "detalhes": [str(r)],
            "falhas": [],
        }

        out = StringIO()
        call_command(_CMD, stdout=out)
        output = out.getvalue()
        self.assertIn("IGNORADO", output)

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    def test_resultado_com_erro_exibido(
        self, mock_eol: MagicMock, mock_executor_cls: MagicMock
    ) -> None:
        """Result de erro é exibido sem causar SystemExit sem reprovados."""
        r = _make_resultado(erro="timeout")

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = [r]
        mock_executor.resumo.return_value = {
            "total": 1,
            "aprovados": 0,
            "reprovados": 0,
            "ignorados": 0,
            "erros": 1,
            "compativel": False,
            "detalhes": [str(r)],
            "falhas": [],
        }

        out = StringIO()
        with self.assertRaises(SystemExit) as ctx:
            call_command(_CMD, stdout=out)
        self.assertEqual(ctx.exception.code, 1)

    @patch(_PATCH_EXECUTOR)
    @patch(_PATCH_EOL)
    def test_queries_reprovadas_listadas_quando_incompativel(
        self, mock_eol: MagicMock, mock_executor_cls: MagicMock
    ) -> None:
        """Queries reprovadas são listadas quando compativel=False."""
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor
        mock_executor.executar_todos.return_value = [
            _make_resultado(aprovado=False)
        ]
        mock_executor.resumo.return_value = {
            **_sumario_incompativel(),
            "falhas": ["[FALHA] V.C: 0/5 (0%) | destino=5"],
        }

        out = StringIO()
        with self.assertRaises(SystemExit):
            call_command(_CMD, stdout=out)
        output = out.getvalue()
        self.assertIn("Queries reprovadas", output)
