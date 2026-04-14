# Retomada de Execução — Domínio Programas

O ETL de programas suporta retomada a partir da última fase concluída,
evitando reprocessar fases já gravadas em caso de falha ou interrupção.

## Como funciona

O `BaseEtlCommand` persiste um checkpoint em `EtlCheckpoint` ao final de cada fase com:

- `dominio = "programas"`
- `ultima_pagina` = número da última fase concluída com sucesso (o campo no banco chama `ultima_pagina` por razões históricas — o atributo equivalente no service é `ultima_fase_concluida`)
- `token_parada` = token retornado pela fase
- `ultima_situacao` = `"concluido"` em caso de sucesso ou `"erro"` em caso de exceção

Ao iniciar com `--continuar`, o `_obter_ponto_partida` do `BaseEtlCommand`:

1. Lê o checkpoint mais recente para o domínio `"programas"`.
2. Se `ultima_situacao == "erro"` e `0 < ultima_pagina < fase_final (5)`, define `fase_inicial = ultima_pagina + 1`.
3. Caso contrário (checkpoint concluído ou inexistente), define `fase_inicial = 1`.
4. Chama `EtlProgramasService.executar(fase_inicial=N)`.

## Fases e retomada

| Falhou **durante** a fase | Última concluída (`ultima_pagina`) | Retomada inicia em |
|---------------------------|------------------------------------|--------------------|
| 1 (TipoPrograma) | 0 | Fase 1 (recomeço) |
| 2 (ComponenteCurricularPrograma) | 1 | Fase 2 |
| 3 (TurmaPrograma) | 2 | Fase 3 |
| 4 (TurmaProgramaComponenteCurricular) | 3 | Fase 4 |
| 5 (MatriculaTurmaPrograma) | 4 | Fase 5 |

> **Nota:** se a fase 5 concluir mas o pipeline falhar no `_finalizar_com_sucesso`, o checkpoint fica com `ultima_pagina=5 == fase_final` e o `--continuar` recomeça da fase 1 (porque a condição `ultima_pagina < fase_final` não é satisfeita). Isso é seguro por causa da idempotência.

## Uso

```bash
# Primeira execução
python manage.py etl_programas --volume 500

# Retomar do ponto de falha
python manage.py etl_programas --volume 500 --continuar
```

## Comportamento em erro

Se uma exceção ocorrer durante uma fase:

1. O checkpoint é atualizado com `ultima_situacao="erro"` e a fase que falhou.
2. A exceção é repropagada para que o Celery registre a falha da task.
3. Na próxima execução com `--continuar`, o ETL reinicia a partir da fase que falhou
   (não da seguinte), garantindo que nenhuma fase seja pulada mesmo em falha parcial.

## Idempotência

Todas as fases são **idempotentes** via controle de hash SHA-256 (`_upsert_incremental`).
Reprocessar uma fase já concluída não gera duplicatas nem sobrescreve dados sem mudança —
apenas registros realmente alterados no EOL são escritos novamente.

Ver {doc}`hash` para detalhes do controle incremental.
