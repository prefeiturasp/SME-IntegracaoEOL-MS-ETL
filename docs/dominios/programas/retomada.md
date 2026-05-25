# Retomada de Execução — Domínio Programas

O ETL de programas suporta retomada a partir da última fase concluída,
evitando reprocessar fases já gravadas em caso de falha ou interrupção.

## Como funciona

O `BaseEtlCommand` persiste um checkpoint em `EtlCheckpoint` ao final de cada fase com:

- `dominio = "programas"`
- `ultima_pagina` = número da última fase concluída com sucesso (o campo no banco
  chama `ultima_pagina` por razões históricas — o atributo equivalente no service
  é `ultima_fase_concluida`)
- `token_parada` = token retornado pela fase
- `ultima_situacao` = `"concluido"` em caso de sucesso ou `"erro"` em caso de exceção

Ao iniciar com `--continuar`, o `_obter_ponto_partida` do `BaseEtlCommand`:

1. Lê o checkpoint mais recente para o domínio `"programas"`.
2. Se `ultima_situacao == "erro"` e `0 < ultima_pagina < fase_final` (`fase_final = 6` no `Command`), define `fase_inicial = ultima_pagina + 1`.
3. Caso contrário (checkpoint concluído ou inexistente), define `fase_inicial = 1`.
4. Chama `EtlProgramasService.executar(fase_inicial=N)`.

## Fases e retomada

| Falhou **durante** a fase | Última concluída (`ultima_pagina`) | Retomada com `--continuar` inicia em |
|---------------------------|------------------------------------|---------------------------------------|
| 1 (`tipo_programa`) | 0 | Fase 1 (recomeço) |
| 2 (`componente_curricular_programa`) | 1 | Fase 2 |
| 3 (`turma_programa`) | 2 | Fase 3 |
| 4 (`turma_programa_componente_curricular`) | 3 | Fase 4 |
| 5 (`matricula_turma_programa`) | 4 | Fase 5 |
| 6 (`matricula_turma_programa_historico`) | 5 | Fase 1 (`ultima_pagina < fase_final` é falso) |
| 7 (`aluno_pap_ano_letivo`) | 6 | Fase 1 (idem) |
| 8 (`aluno_pap_ano_letivo_historico`) | 7 | Fase 1 (idem) |

> **Atenção:** o `Command.fase_final = 6` faz a retomada automática só funcionar
> linearmente até a Fase 5. Falhas em fases ≥ 6 caem na cláusula `ultima_pagina < fase_final`
> falsa e o `--continuar` recomeça da Fase 1. Como todas as fases são idempotentes
> (controle por hash SHA-256), o re-processamento é seguro — só desperdiça leitura.
> Para retomar diretamente em uma fase ≥ 6, use `--fase N` explicitamente.

## Uso

```bash
# Primeira execução
python manage.py etl_programas --volume 500

# Retomar do ponto de falha (fases 1-5)
python manage.py etl_programas --volume 500 --continuar

# Forçar início numa fase específica (qualquer fase de 1 a 8)
python manage.py etl_programas --fase 7
```

## Comportamento em erro

Se uma exceção ocorrer durante uma fase:

1. O checkpoint é atualizado com `ultima_situacao="erro"` e a fase que falhou.
2. A exceção é repropagada para que o Celery registre a falha da task.
3. Na próxima execução com `--continuar`, o ETL reinicia a partir da fase que
   falhou (no intervalo coberto por `fase_final`), garantindo que nenhuma fase
   seja pulada mesmo em falha parcial.

## Idempotência

Todas as fases são **idempotentes** via controle de hash SHA-256
(`_upsert_incremental`). Reprocessar uma fase já concluída não gera duplicatas
nem sobrescreve dados sem mudança — apenas registros realmente alterados no
EOL são escritos novamente.

Ver {doc}`hash` para detalhes do controle incremental.
