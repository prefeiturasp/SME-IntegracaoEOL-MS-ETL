# Comando `etl_pedagogico`

Arquivo: `apps/pedagogico/management/commands/etl_pedagogico.py`

Herda de `BaseEtlCommand`. Toda a lógica de argumentos, checkpoint e auditoria está no base.

## Argumentos suportados

Herdados de `BaseEtlCommand`:

- `--volume` — tamanho do batch de leitura
- `--offset` — offset inicial
- `--continuar` — retoma a partir do último checkpoint salvo
- `--primeiro-run` — sinaliza primeiro run (sem filtro incremental)
- `--ano-letivo` — processa apenas anos letivos a partir do valor informado

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

- Fases do pipeline: `11`
- Tabelas persistidas pelo ETL:
  - `componente_curricular`
  - `componente_turma`
  - `atribuicao_componente`
  - `atribuicao_territorio_saber`
  - `componente_curricular_hierarquia`
  - `componente_curricular_pap`
  - `componente_curricular_planejamento_regencia`
  - `turma_itinerario_ensino_medio`
  - `agrupamento_atribuicao_territorio_saber`
  - `grade_componente_curricular`
  - `turma`

Estado atual do código em `etl_pedagogico.py`:

- `fase_final` está em `11`.
- O modo real de escrita de cada fase é definido no `PhaseConfig` do serviço.
- As tabelas auxiliares da API EOL e `agrupamento_atribuicao_territorio_saber` usam `full_refresh` no `PhaseConfig`.
- A fase backup `agrupamento_territorio_saber_gerado` só é executada quando selecionada explicitamente por nome.

## Exemplos

```bash
python manage.py etl_pedagogico
python manage.py etl_pedagogico --continuar
python manage.py etl_pedagogico --primeiro-run
python manage.py etl_pedagogico --fases agrupamento_atribuicao_territorio_saber
```
