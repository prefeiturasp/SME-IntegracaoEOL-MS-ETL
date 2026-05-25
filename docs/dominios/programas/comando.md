# Comando `etl_programas`

Arquivo: `apps/programas/management/commands/etl_programas.py`

```python
class Command(BaseEtlCommand):
    dominio = "programas"
    fase_final = 6
    service_class = EtlProgramasService
    orquestrador_class = EtlProgramasOrquestrador
```

> O atributo `fase_final = 6` controla a janela de retomada do `BaseEtlCommand`
> (limite superior da condição `0 < ultima_pagina < fase_final`). Não bate
> 1-para-1 com o número total de fases registradas em `EtlProgramasService`
> (que hoje são 8); é um valor de configuração da retomada, não a contagem
> efetiva de fases executadas.

## Argumentos suportados (via `BaseEtlCommand`)

| Flag | Descrição |
|------|-----------|
| `--volume N` | Tamanho do chunk lido do EOL |
| `--offset N` | Offset inicial |
| `--fase N` | Força início a partir da fase N. Ignora checkpoint |
| `--continuar` | Lê o checkpoint mais recente; se `ultima_situacao == "erro"`, retoma em `ultima_pagina + 1` |
| `--carga-inicial` | Passa `primeiro_run=True` para o service |

## Comportamento real

1. lê checkpoint se `--continuar`
2. decide `fase_inicial`
3. cria `id_execucao` via `RepositorioAuditoriaPostgres.iniciar_execucao`
4. executa `EtlProgramasService.executar` (ou despacha para o
   `EtlProgramasOrquestrador` quando configurado para Celery)
5. registra tabelas lidas e escritas
6. soma `total_alterado`
7. atualiza `token_parada`
8. atualiza checkpoint como `concluido`
9. em erro, salva checkpoint com `ultima_situacao="erro"` e repropaga a exceção

## Estratégia de log

As tabelas em `_TABELAS_UPSERT` recebem `modo_escrita="upsert"`; as demais,
`full_refresh`. Set atual:

```python
_TABELAS_UPSERT = frozenset({
    "tipo_programa",
    "componente_curricular_programa",
    "turma_programa",
    "turma_programa_componente_curricular",
    "matricula_turma_programa",
    "matricula_turma_programa_historico",
})
```

> As tabelas `aluno_pap_ano_letivo` e `aluno_pap_ano_letivo_historico` **não**
> estão em `_TABELAS_UPSERT` e portanto seriam logadas como `full_refresh`
> pelo `get_modo_escrita()`, embora o `PhaseConfig` correspondente em `services.py`
> declare `modo_escrita="upsert"` (esta é a fonte de verdade para a execução —
> a divergência afeta apenas o rótulo gravado em `EtlExecucaoTabelaEscrita`).

## Exemplo

```bash
python manage.py etl_programas --volume 500
python manage.py etl_programas --volume 500 --continuar
python manage.py etl_programas --fase 5
```
