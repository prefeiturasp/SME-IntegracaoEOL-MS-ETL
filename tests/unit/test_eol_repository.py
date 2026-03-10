import importlib

import pytest
from sme_pedagogico_etl.adapters.databases.eol_repository import EOLRepository
from sme_pedagogico_etl.adapters.databases.conexao_eol import OperacaoEscritaNaoPermitida

def test_repo_bloqueia_insert(monkeypatch):

    class FakeCon:
        def executar(self, sql, params=None):
            if "INSERT" in sql.upper():
                raise OperacaoEscritaNaoPermitida(sql)
            return [{"a": 1}]

    repo_mod = importlib.import_module(
        "sme_pedagogico_etl.adapters.databases.eol_repository"
    )
    importlib.reload(repo_mod)

    repo = EOLRepository(conexao=FakeCon())

    # leitura ok
    assert repo.executar_consulta("SELECT 1") == [{"a": 1}]

    # tentativa de escrita
    with pytest.raises(OperacaoEscritaNaoPermitida):
        repo.executar_consulta("INSERT INTO t VALUES (1)")


def test_repo_bloqueia_insert(monkeypatch):
    class FakeCon:
        def executar(self, sql, params=None):
            if "INSERT" in sql.upper():

                raise OperacaoEscritaNaoPermitida(sql)
            return [{"a": 1}]

    repo_mod = importlib.import_module("sme_pedagogico_etl.adapters.databases.eol_repository")
    importlib.reload(repo_mod)

    repo = EOLRepository(conexao=FakeCon())
    assert repo.executar_consulta("SELECT 1") == [{"a": 1}]

    try:
        repo.executar_consulta("INSERT INTO t VALUES (1)")
        assert False, "deveria ter lançado"
    except OperacaoEscritaNaoPermitida:
        pass
