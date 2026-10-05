# Repositório de Auditoria

Classe: `RepositorioAuditoriaPostgres`
Arquivo: `apps/controle_auditoria/libs/repositorio_auditoria.py`

Todas as operações usam o banco `default` via ORM Django.

---

## Métodos

### `iniciar_execucao(dominio: str) → UUID`

Cria um registro `EtlExecucao` com `situacao="em_execucao"` e `iniciado_em=now()`.
Retorna o `id_execucao` (UUID v4) gerado.

---

### `finalizar_execucao(id_execucao, situacao, mensagem_erro=None) → None`

Atualiza `EtlExecucao` com `situacao`, `finalizado_em=now()` e `mensagem_erro`.

Situações possíveis: `"concluido"`, `"erro"`, `"cancelado"`.

---

### `registrar_tabela_lida(id_execucao, tabela_origem, numero_pagina, linhas_lidas) → None`

Cria `EtlExecucaoTabelaLida`. Chamado pelo comando `etl_professores` após cada tabela
do resultado do serviço.

---

### `registrar_tabela_escrita(id_execucao, tabela_destino, linhas_escritas, modo_escrita="upsert") → None`

Cria `EtlExecucaoTabelaEscrita`. O campo `modo_escrita` recebe `"upsert"` ou `"full_refresh"`
conforme a constante `_TABELAS_UPSERT` do comando `etl_professores`.

---

### `obter_checkpoint_dominio(dominio: str) → dict | None`

Retorna o registro `EtlCheckpointDominio` do domínio como dicionário com os campos:

```
dominio, ultimo_id_execucao, ultima_pagina, token_parada,
indice_sincronizacao, ultima_situacao, ultimo_sucesso_em, atualizado_em
```

Retorna `None` se o domínio ainda não tiver checkpoint.

---

### `atualizar_checkpoint_dominio(...) → None`

Executa upsert transacional (`select_for_update` + `get_or_create`) no
`EtlCheckpointDominio`.

**Parâmetros:**

| Nome | Tipo | Descrição |
|---|---|---|
| `dominio` | str | Chave única do checkpoint |
| `ultimo_id_execucao` | UUID | UUID da execução recém-concluída |
| `ultima_pagina` | int | Número da última fase concluída |
| `token_parada` | str \| None | Total acumulado de linhas alteradas (como string) |
| `indice_sincronizacao` | str \| None | Reservado (sempre `None` para professores) |
| `ultima_situacao` | str | `"concluido"` ou `"erro"` |
| `sucesso` | bool | Se `True`, atualiza `ultimo_sucesso_em = now()` |

---

## Papel no domínio professores

O comando `etl_professores` usa este repositório para:

1. Gerar `id_execucao` antes de executar o serviço.
2. Registrar logs de leitura e escrita por tabela após a execução.
3. Atualizar o checkpoint com a fase atingida e o novo `token_parada`.
4. Em caso de erro: persistir o checkpoint antes de propagar a exceção,
   permitindo retomada precisa na próxima tentativa.
