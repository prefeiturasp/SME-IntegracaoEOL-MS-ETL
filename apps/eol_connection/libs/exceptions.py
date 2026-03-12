"""Excecoes customizadas do modulo eol_connection."""


class ConexaoSomenteLeituraError(Exception):
    """Erro disparado quando alguma operacao de escrita e tentada no banco EOL."""

    pass
