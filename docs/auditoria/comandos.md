# Comandos de Controle/Auditoria

## `executar_dominio`
Executa um domínio específico.

Suporta:
- `sinc_rec_db`
- `escola` / `escolas`
- `professores`

## `executar_dominios`
Executa os domínios ativos definidos hoje no comando.

## `executar_dominios_loop`
Presente no projeto para execução em loop.

## `agendar_dominio`
Enfileira ou agenda uma execução na fila Celery.

Parâmetros relevantes:
- `--dominio`
- `--volume`
- `--offset`
- `--continuar`
- `--executar-em`
