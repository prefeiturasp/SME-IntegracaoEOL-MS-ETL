"""Cliente de leitura no legado para dominio escolas."""

from typing import Any

import pyodbc
from django.conf import settings


class ClienteLegadoEscolas:
    """Acesso somente leitura a escolas no banco legado."""

    def __init__(self) -> None:
        """Inicia o servico de consulta de escolas."""
        self._string_conexao = settings.EOL_DB

    def listar_por_offset(self, limite: int, offset: int) -> list[dict[str, Any]]:
        """Lista escolas usando paginacao por offset/limit."""
        sql = """
            SELECT
                vue.cd_unidade_educacao AS codigo_escola,
                vue.nm_unidade_educacao AS nome_escola,
                vue.nm_exibicao_unidade AS nome_exibicao,
                vue.cd_unidade_administrativa_referencia AS codigo_dre,
                vue.tp_unidade_educacao AS tipo_unidade_educacao,
                vue.tp_situacao_unidade AS situacao_unidade,
                vue.dt_atualizacao_endereco AS atualizado_em
            FROM dbo.v_cadastro_unidade_educacao vue
            ORDER BY vue.cd_unidade_educacao ASC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        with pyodbc.connect(self._string_conexao) as conexao:
            cursor = conexao.cursor()
            linhas = cursor.execute(sql, [offset, limite]).fetchall()
            colunas = [coluna[0] for coluna in cursor.description]
        return [dict(zip(colunas, list(linha), strict=False)) for linha in linhas]
