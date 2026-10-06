# Comando `etl_professores`

Arquivo: `apps/professores/management/commands/etl_professores.py`

## Argumentos suportados

- `--continuar`
- `--anos-letivos ANO [ANO ...]` — processa apenas os anos letivos informados
  nas fases com recorte anual. Sem o argumento, faz carga completa.
- `--skip-audit-hash` (alias `--skip-salvar-dados-auditoria`) — pula a gravação dos
  hashes de auditoria por linha. Útil em recargas amplas em que a auditoria por
  linha não é necessária.

## Comportamento real

1. lê checkpoint se `--continuar`
2. decide `fase_inicial`
3. cria `id_execucao` via `RepositorioAuditoriaPostgres.iniciar_execucao`
4. executa `EtlProfessoresService.executar`
5. registra tabelas lidas e escritas
6. soma `total_alterado`
7. atualiza `token_parada`
8. atualiza checkpoint como `concluido`
9. em erro, salva checkpoint com `ultima_situacao="erro"` e repropaga exceção

## Estratégia de log

As tabelas em `_TABELAS_UPSERT` recebem `modo_escrita="upsert"`; as demais, `full_refresh`.

## Exemplo

```bash
python manage.py etl_professores
python manage.py etl_professores --continuar
python manage.py etl_professores --anos-letivos 2025 2026
```

## FuncionarioUnidadeEducacional

`funcionario_unidade_educacional` e carregada na fase final por
`popular_funcionarios`, usa
`upsert` incremental e registra leitura, escrita e checkpoint como as demais
tabelas incrementais do dominio.
