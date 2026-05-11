# Retomada por Fase

A retomada é baseada em `EtlCheckpointDominio` e em `ultima_fase_concluida` do serviço.

## Regra real do comando

Se `--continuar`:
- Lê checkpoint do domínio `pedagogico`
- Se `ultima_situacao == "erro"` e `0 < ultima_pagina < 6`, define `fase_inicial = ultima_pagina + 1`
- Caso contrário, reinicia em fase 1

## Em caso de erro
- `ultima_pagina` recebe `servico.ultima_fase_concluida`
- `token_parada` preserva o valor anterior
- `ultima_situacao` vira `"erro"`

## Em caso de sucesso
- `ultima_pagina` recebe `6` (última fase)
- `token_parada` é atualizado com `token_anterior + total_alterado`
- `ultima_situacao` vira `"concluido"`

## Fase 4 e retomada

A fase 4 escreve em duas tabelas (`agrupamento_atribuicao_territorio_saber` e `componente_curricular_agrupamento`). Se falhar após gravar a primeira tabela, a retomada reexecutará a fase inteira — o upsert incremental garante idempotência.

## Diagrama

```{graphviz}
digraph G {
    rankdir=TB;
    node [shape=box, style="rounded"];

    CP [label="Ler checkpoint"];
    DEC [label="Definir fase inicial\n(1–6)"];
    RUN [label="Executar ETL"];
    OK [label="Checkpoint concluído"];
    ER [label="Checkpoint erro\n(salva ultima_fase_concluida)"];

    CP -> DEC -> RUN;
    RUN -> OK [label="sucesso"];
    RUN -> ER [label="erro"];
}
```
