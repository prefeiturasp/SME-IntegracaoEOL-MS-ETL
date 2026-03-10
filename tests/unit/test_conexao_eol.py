import importlib
import pytest
from sqlalchemy import text

import sme_pedagogico_etl.adapters.databases.conexao_eol as conexao_module

from sme_pedagogico_etl.adapters.databases.conexao_eol import (
    validar_consulta_somente_leitura,
    _string_contem_application_intent_readonly,
    OperacaoEscritaNaoPermitida,
)


def test_string_contem_readonly_variacoes():
    assert _string_contem_application_intent_readonly("ReadOnly=True") is True
    assert _string_contem_application_intent_readonly("readonly = true") is True
    assert _string_contem_application_intent_readonly(" ReadOnly =  True ;") is True
    assert _string_contem_application_intent_readonly("") is False
    assert _string_contem_application_intent_readonly("something else") is False


def test_application_intent_valor_invalido():
    assert _string_contem_application_intent_readonly(None) is False


def test_validar_consulta_sql_vazio():
    assert validar_consulta_somente_leitura("") is None
    assert validar_consulta_somente_leitura(None) is None


def test_validar_consulta_apenas_comentario():
    assert validar_consulta_somente_leitura("-- comentario") is None


def test_validar_consulta_parenteses_abertura():
    validar_consulta_somente_leitura("(((")


def test_validar_consulta_parenteses_vazios():
    validar_consulta_somente_leitura("()")


def test_validar_consulta_statement_vazio_apos_limpeza():
    validar_consulta_somente_leitura("(); SELECT 1")


def test_validar_consulta_proibe_select_into():
    with pytest.raises(OperacaoEscritaNaoPermitida):
        validar_consulta_somente_leitura("SELECT 1 INTO #tmp")


def test_validar_consulta_multi_statement_bloqueia():
    with pytest.raises(OperacaoEscritaNaoPermitida):
        validar_consulta_somente_leitura("SELECT 1; INSERT INTO x VALUES (1)")


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO t VALUES (1)",
        "UPDATE t SET a=1",
        "DELETE FROM t",
        "CREATE TABLE t(id int)",
        "ALTER TABLE t ADD c int",
        "DROP TABLE t",
        "TRUNCATE TABLE t",
        "MERGE INTO t USING x ON 1=1",
        "EXEC sp_help",
        "EXECUTE sp_help",
        "GRANT SELECT ON t TO user",
        "REVOKE SELECT ON t FROM user",
    ],
)
def test_bloqueia_comandos_de_escrita(sql):
    with pytest.raises(OperacaoEscritaNaoPermitida):
        validar_consulta_somente_leitura(sql)


def _recarregar_settings_com_env(monkeypatch, valor: str | None):
    import sme_pedagogico_etl.config.settings as settings_module

    if valor is None:
        monkeypatch.setattr(settings_module.settings, "EOL_DB", None, raising=False)
    else:
        monkeypatch.setattr(settings_module.settings, "EOL_DB", valor, raising=False)

    importlib.reload(conexao_module)


def test_variavel_nao_definida_levanta(monkeypatch):
    _recarregar_settings_com_env(monkeypatch, None)
    with pytest.raises(ValueError):
        conexao_module.ConexaoEOL()


def test_requer_application_intent_readonly(monkeypatch):
    _recarregar_settings_com_env(monkeypatch, "sqlite:///:memory:")
    with pytest.raises(ValueError):
        conexao_module.ConexaoEOL()


def test_healthcheck_sucesso_com_sqlite(monkeypatch):
    _recarregar_settings_com_env(monkeypatch, "sqlite:///:memory:?ReadOnly=True")
    conexao = conexao_module.ConexaoEOL()
    assert conexao.healthcheck() is True


def test_healthcheck_wrapper(monkeypatch):
    _recarregar_settings_com_env(monkeypatch, "sqlite:///:memory:?ReadOnly=True")
    assert conexao_module.healthcheck_eol() is True


def test_healthcheck_falha_lanca_excecao(monkeypatch):
    _recarregar_settings_com_env(monkeypatch, "sqlite:///:memory:?ReadOnly=True")
    conexao = conexao_module.ConexaoEOL()

    with pytest.raises(conexao_module.OperacaoEscritaNaoPermitida):
        conexao.healthcheck("INSERT INTO tabela VALUES (1)")


def test_listener_bloqueia_operacao_via_engine(monkeypatch):
    _recarregar_settings_com_env(monkeypatch, "sqlite:///:memory:?ReadOnly=True")
    conexao = conexao_module.ConexaoEOL()

    with pytest.raises(conexao_module.OperacaoEscritaNaoPermitida):
        with conexao._engine.connect() as conn:
            conn.execute(text("INSERT INTO tabela VALUES (1)"))


def test_executar_select_retorna_lista(monkeypatch):
    _recarregar_settings_com_env(monkeypatch, "sqlite:///:memory:?ReadOnly=True")
    conexao = conexao_module.ConexaoEOL()
    res = conexao.executar("SELECT 1")
    assert isinstance(res, list)


def test_executar_fetchall_falha_retorna_lista_vazia(monkeypatch):
    _recarregar_settings_com_env(monkeypatch, "sqlite:///:memory:?ReadOnly=True")
    conexao = conexao_module.ConexaoEOL()

    class ResultadoFake:
        def fetchall(self):
            raise RuntimeError("boom")

    class ConnFake:
        def execute(self, *args, **kwargs):
            return ResultadoFake()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def connect_fake():
        return ConnFake()

    monkeypatch.setattr(conexao._engine, "connect", connect_fake)

    assert conexao.executar("SELECT 1") == []


def test_aceita_string_odbc_sem_exigir_pyodbc(monkeypatch):
    """
    Para não depender de pyodbc instalado no ambiente de teste,
    mockamos create_engine e event.listen e validamos que a URL mssql+pyodbc é construída.
    """
    odbc = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=SQLSERVER;"
        "PORT=1433;"
        "DATABASE=se1426;"
        "UID=user;"
        "PWD=pass;"
        "ReadOnly=True;"
    )

    import sme_pedagogico_etl.config.settings as settings_module

    monkeypatch.setattr(settings_module.settings, "EOL_DB", odbc, raising=False)

    criado = {"url": None}

    class EngineFake:
        def connect(self):
            raise AssertionError("Não deve conectar nesse teste")

    def create_engine_fake(url, **kwargs):
        criado["url"] = url
        return EngineFake()

    monkeypatch.setattr(conexao_module, "create_engine", create_engine_fake)
    monkeypatch.setattr(conexao_module.event, "listen", lambda *a, **k: None)

    conexao = conexao_module.ConexaoEOL()

    assert conexao is not None
    assert criado["url"].startswith("mssql+pyodbc:///?odbc_connect=")