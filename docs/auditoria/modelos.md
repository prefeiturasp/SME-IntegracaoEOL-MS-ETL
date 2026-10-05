# Modelos de Auditoria

Modelos atuais em `apps/controle_auditoria/models.py`.

## EtlExecucao

- **db_table:** `etl_execucao`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `id_execucao` | `UUIDField` | unique=True |
| `dominio` | `CharField` | max_length=120 |
| `situacao` | `CharField` | max_length=30 |
| `iniciado_em` | `DateTimeField` |  |
| `finalizado_em` | `DateTimeField` | null=True |
| `mensagem_erro` | `TextField` | null=True |
| `criado_em` | `DateTimeField` |  |

## EtlExecucaoTabelaLida

- **db_table:** `etl_execucao_tabela_lida`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `id_execucao` | `UUIDField` |  |
| `tabela_origem` | `CharField` | max_length=200 |
| `numero_pagina` | `IntegerField` | default=0 |
| `linhas_lidas` | `IntegerField` | default=0 |
| `lido_em` | `DateTimeField` |  |

## EtlExecucaoTabelaEscrita

- **db_table:** `etl_execucao_tabela_escrita`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `id_execucao` | `UUIDField` |  |
| `tabela_destino` | `CharField` | max_length=200 |
| `linhas_escritas` | `IntegerField` | default=0 |
| `modo_escrita` | `CharField` | max_length=30; default='upsert' |
| `escrito_em` | `DateTimeField` |  |

## EtlCheckpointDominio

- **db_table:** `etl_checkpoint_dominio`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `dominio` | `CharField` | max_length=120; unique=True |
| `ultimo_id_execucao` | `UUIDField` | null=True |
| `ultima_pagina` | `IntegerField` | default=0 |
| `token_parada` | `CharField` | max_length=255; null=True |
| `indice_sincronizacao` | `CharField` | max_length=120; null=True |
| `ultima_situacao` | `CharField` | max_length=30; default='pendente' |
| `ultimo_sucesso_em` | `DateTimeField` | null=True |
| `atualizado_em` | `DateTimeField` |  |

## EtlAuditoriaLinha

- **db_table:** `etl_auditoria_linha`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id_destino` | `CharField` | max_length=255; primary_key=True; help_text="Chave composta '{tabela_destino}:{id_origem}'" |
| `hash_controle` | `CharField` | max_length=64; help_text='SHA-256 hex dos dados relevantes da linha de origem.' |
| `atualizado_em` | `DateTimeField` |  |
