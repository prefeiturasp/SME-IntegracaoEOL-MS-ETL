# Retomada de Execução — Domínio Programas

O ETL de programas suporta retomada a partir da última fase concluída,
evitando reprocessar fases já gravadas em caso de falha ou interrupção.

## Como funciona

O `BaseEtlCommand` persiste um `EtlCheckpoint` ao final de cada fase com:

- `dominio = "programas"`
- `ultima_fase_concluida` = número da última fase concluída com sucesso
- `ultima_situacao` = `"em_andamento"` durante a execução, `"concluido"` ao fim,
  `"erro"` em caso de exceção

Ao iniciar com `--continuar`, o comando:

1. Lê o checkpoint mais recente para o domínio `"programas"`.
2. Define `fase_inicial = ultima_fase_concluida + 1`.
3. Chama `EtlProgramasService.executar(fase_inicial=N)`.

## Fases e retomada

| Falhou na fase | Retomada inicia em |
|---------------|--------------------|
| 1 (TipoPrograma) | Fase 1 |
| 2 (ComponenteCurricularPrograma) | Fase 2 |
| 3 (TurmaPrograma) | Fase 3 |
| 4 (TurmaProgramaComponenteCurricular) | Fase 4 |
| 5 (MatriculaTurmaPrograma) | Fase 5 |

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
