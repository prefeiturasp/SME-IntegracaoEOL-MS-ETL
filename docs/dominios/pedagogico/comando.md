# Comando `etl_pedagogico`

Arquivo: `apps/pedagogico/management/commands/etl_pedagogico.py`

Herda de `BaseEtlCommand`. Toda a lógica de argumentos, checkpoint e auditoria está no base.

## Argumentos suportados

Herdados de `BaseEtlCommand`:

- `--volume` — tamanho do batch de leitura
- `--offset` — offset inicial
- `--continuar` — retoma a partir do último checkpoint salvo
- `--primeiro-run` — sinaliza primeiro run (sem filtro incremental)

## Comportamento

1. Lê checkpoint se `--continuar`
2. Decide `fase_inicial`
3. Cria `id_execucao` via `RepositorioAuditoriaPostgres.iniciar_execucao`
4. Instancia `EtlPedagogicoService` e chama `executar(fase_inicial)`
5. Registra tabelas lidas e escritas em `EtlExecucaoTabelaEscrita`
6. Atualiza `token_parada`
7. Salva checkpoint como `concluido`
8. Em erro: salva checkpoint com `ultima_situacao="erro"` e repropaga exceção

## Modo de escrita

Documentação alvo do domínio:

- Fases do pipeline: `5`
- Tabelas persistidas pelo ETL:
  - `componente_curricular`
  - `componente_curricular_por_turma`
  - `agrupamento_atribuicao_territorio_saber`
  - `componente_curricular_agrupamento`
  - `componente_inicio_turma`
  - `grade_curricular_serie`

Estado atual do código em `etl_pedagogico.py`:

- `_TABELAS_UPSERT` ainda lista nomes antigos:
  - `componente_curricular_regencia`
  - `dados_aula_turma`
  - `componente_curricular_por_ano_letivo`
- `fase_final` ainda está em `6`

Essa é uma divergência conhecida do código em relação ao pipeline atual documentado aqui.

## Exemplos

```bash
python manage.py etl_pedagogico
python manage.py etl_pedagogico --continuar
python manage.py etl_pedagogico --primeiro-run
```
