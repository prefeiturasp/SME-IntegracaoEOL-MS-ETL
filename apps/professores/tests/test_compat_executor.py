"""Testes para compat/executor.py — ExecutorCompatibilidade."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.professores.compat.base import ResultadoCompatibilidade
from apps.professores.compat.executor import ExecutorCompatibilidade

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resultado_aprovado(
    verificador: str = "V", consulta: str = "C"
) -> ResultadoCompatibilidade:
    r = ResultadoCompatibilidade(verificador=verificador, consulta=consulta)
    r.total_origem = 5
    r.correspondencias = 5
    return r


def _resultado_reprovado(
    verificador: str = "V", consulta: str = "C"
) -> ResultadoCompatibilidade:
    r = ResultadoCompatibilidade(verificador=verificador, consulta=consulta)
    r.total_origem = 10
    r.correspondencias = 0
    return r


def _resultado_ignorado(
    verificador: str = "V", consulta: str = "C"
) -> ResultadoCompatibilidade:
    r = ResultadoCompatibilidade(verificador=verificador, consulta=consulta)
    r.ignorado = True
    r.motivo_ignorado = "sem dados na origem"
    return r


def _resultado_com_erro(
    verificador: str = "V", consulta: str = "C"
) -> ResultadoCompatibilidade:
    r = ResultadoCompatibilidade(verificador=verificador, consulta=consulta)
    r.erro = "conexão recusada"
    return r


# ---------------------------------------------------------------------------
# executar_todos
# ---------------------------------------------------------------------------


class ExecutorCompatibilidadeExecutarTodosTest(TestCase):
    """Testes para ExecutorCompatibilidade.executar_todos."""

    def _make_mock_cls(self, resultado: ResultadoCompatibilidade) -> MagicMock:
        """Cria um MagicMock simulando uma classe de verificador."""
        mock_instance = MagicMock()
        mock_instance.nome = resultado.verificador
        mock_instance.nome_consulta = resultado.consulta
        mock_instance.executar.return_value = resultado
        mock_cls = MagicMock(return_value=mock_instance)
        return mock_cls

    def test_executar_todos_retorna_lista_com_um_resultado(self) -> None:
        """Verifica que executar_todos retorna a lista de resultados."""
        r = _resultado_aprovado()
        mock_cls = self._make_mock_cls(r)

        with patch(
            "apps.professores.compat.executor._TODOS_VERIFICADORES", [mock_cls]
        ):
            executor = ExecutorCompatibilidade(MagicMock(), limite=5)
            resultados = executor.executar_todos()

        self.assertEqual(len(resultados), 1)
        self.assertIs(resultados[0], r)

    def test_executar_todos_chama_todos_os_verificadores(self) -> None:
        """Verifica que cada verificador registrado é executado."""
        resultados_esperados = [_resultado_aprovado(str(i)) for i in range(3)]
        mock_classes = [self._make_mock_cls(r) for r in resultados_esperados]

        with patch(
            "apps.professores.compat.executor._TODOS_VERIFICADORES",
            mock_classes,
        ):
            executor = ExecutorCompatibilidade(MagicMock(), limite=10)
            resultados = executor.executar_todos()

        self.assertEqual(len(resultados), 3)

    def test_executar_todos_passa_limite_correto(self) -> None:
        """Verifica que o limite configurado é repassado a cada verificador."""
        limites_recebidos: list = []

        mock_instance = MagicMock()
        mock_instance.nome = "V"
        mock_instance.nome_consulta = "Q"

        def captura_execute(
            eol: object, limite: int
        ) -> ResultadoCompatibilidade:
            limites_recebidos.append(limite)
            return _resultado_aprovado()

        mock_instance.executar.side_effect = captura_execute
        mock_cls = MagicMock(return_value=mock_instance)

        with patch(
            "apps.professores.compat.executor._TODOS_VERIFICADORES", [mock_cls]
        ):
            executor = ExecutorCompatibilidade(MagicMock(), limite=77)
            executor.executar_todos()

        self.assertEqual(limites_recebidos, [77])

    def test_executar_todos_passa_eol_correto(self) -> None:
        """Verifica que o EOL configurado é repassado a cada verificador."""
        eol_recebidos: list = []
        eol_mock = MagicMock()

        mock_instance = MagicMock()
        mock_instance.nome = "V"
        mock_instance.nome_consulta = "Q"

        def captura(eol: object, limite: int) -> ResultadoCompatibilidade:
            eol_recebidos.append(eol)
            return _resultado_aprovado()

        mock_instance.executar.side_effect = captura
        mock_cls = MagicMock(return_value=mock_instance)

        with patch(
            "apps.professores.compat.executor._TODOS_VERIFICADORES", [mock_cls]
        ):
            executor = ExecutorCompatibilidade(eol_mock, limite=5)
            executor.executar_todos()

        self.assertIs(eol_recebidos[0], eol_mock)


# ---------------------------------------------------------------------------
# resumo
# ---------------------------------------------------------------------------


class ExecutorCompatibilidadeResumoTest(TestCase):
    """Testes para ExecutorCompatibilidade.resumo."""

    def setUp(self) -> None:
        self.executor = ExecutorCompatibilidade(MagicMock())

    def test_resumo_todos_aprovados(self) -> None:
        """Verifica resumo com todos aprovados."""
        resultados = [_resultado_aprovado() for _ in range(3)]
        sumario = self.executor.resumo(resultados)
        self.assertEqual(sumario["total"], 3)
        self.assertEqual(sumario["aprovados"], 3)
        self.assertEqual(sumario["reprovados"], 0)
        self.assertEqual(sumario["ignorados"], 0)
        self.assertEqual(sumario["erros"], 0)
        self.assertTrue(sumario["compativel"])

    def test_resumo_com_reprovado_marca_incompativel(self) -> None:
        """Verifica que um reprovado torna compativel=False."""
        resultados = [_resultado_aprovado(), _resultado_reprovado()]
        sumario = self.executor.resumo(resultados)
        self.assertEqual(sumario["reprovados"], 1)
        self.assertFalse(sumario["compativel"])

    def test_resumo_com_reprovado_inclui_falha_no_campo_falhas(self) -> None:
        """Verifica que falhas é preenchido com os resultados reprovados."""
        resultados = [_resultado_reprovado("RepV", "RepQ")]
        sumario = self.executor.resumo(resultados)
        self.assertEqual(len(sumario["falhas"]), 1)
        self.assertIn("RepV", sumario["falhas"][0])

    def test_resumo_ignorado_nao_conta_como_aprovado_ou_reprovado(
        self,
    ) -> None:
        """Verifica que ignorado não incrementa aprovados nem reprovados."""
        resultados = [_resultado_ignorado()]
        sumario = self.executor.resumo(resultados)
        self.assertEqual(sumario["ignorados"], 1)
        self.assertEqual(sumario["aprovados"], 0)
        self.assertEqual(sumario["reprovados"], 0)

    def test_resumo_ignorado_nao_torna_incompativel(self) -> None:
        """Verifica que ignorado não afeta compativel."""
        resultados = [_resultado_ignorado()]
        sumario = self.executor.resumo(resultados)
        self.assertTrue(sumario["compativel"])

    def test_resumo_com_erro_marca_incompativel(self) -> None:
        """Verifica que erro torna compativel=False."""
        resultados = [_resultado_com_erro()]
        sumario = self.executor.resumo(resultados)
        self.assertEqual(sumario["erros"], 1)
        self.assertFalse(sumario["compativel"])

    def test_resumo_detalhes_contem_str_de_cada_resultado(self) -> None:
        """Verifica que detalhes contém a representação de cada resultado."""
        resultados = [
            _resultado_aprovado("V1", "Q1"),
            _resultado_aprovado("V2", "Q2"),
        ]
        sumario = self.executor.resumo(resultados)
        self.assertEqual(len(sumario["detalhes"]), 2)
        for d in sumario["detalhes"]:
            self.assertIsInstance(d, str)

    def test_resumo_lista_vazia(self) -> None:
        """Verifica resumo com lista vazia."""
        sumario = self.executor.resumo([])
        self.assertEqual(sumario["total"], 0)
        self.assertTrue(sumario["compativel"])

    def test_resumo_mix_aprovado_ignorado_erro(self) -> None:
        """Verifica resumo com mix de estados.

        _resultado_com_erro() tem aprovado=True (propriedade retorna True
        quando há erro) e ignorado=False, portanto entra em aprovados além
        de erros.
        Resultado esperado: aprovados=2 (aprovado + erro),
        ignorados=1, erros=1.
        """
        resultados = [
            _resultado_aprovado(),
            _resultado_ignorado(),
            _resultado_com_erro(),
        ]
        sumario = self.executor.resumo(resultados)
        self.assertEqual(sumario["total"], 3)
        self.assertEqual(
            sumario["aprovados"], 2
        )  # aprovado puro + erro (aprovado=True)
        self.assertEqual(sumario["ignorados"], 1)
        self.assertEqual(sumario["erros"], 1)
        self.assertFalse(sumario["compativel"])
