# Retomada por Fase

A retomada é baseada em `EtlCheckpointDominio` e em `ultima_fase_concluida` do serviço.

## Regra real do comando

Se `--continuar`:
- lê checkpoint do domínio `institucional`
- se `ultima_situacao == "erro"` e `0 < ultima_pagina < 4`, define `fase_inicial = ultima_pagina + 1`
- caso contrário, reinicia em fase 1

## Em caso de erro
- `ultima_pagina` recebe `servico.ultima_fase_concluida`
- `token_parada` preserva o valor anterior
- `ultima_situacao` vira `erro`

## Em caso de sucesso
- `ultima_pagina` recebe a última fase concluída
- `token_parada` é atualizado com `token_anterior + total_alterado`
- `ultima_situacao` vira `concluido`

## Diagrama

```{graphviz}
digraph G {
    rankdir=TB;
    node [shape=box, style="rounded"];

    CP [label="Ler checkpoint"];
    DEC [label="Definir fase inicial"];
    RUN [label="Executar ETL"];
    OK [label="Checkpoint concluído"];
    ER [label="Checkpoint erro"];

    CP -> DEC -> RUN;
    RUN -> OK [label="sucesso"];
    RUN -> ER [label="erro"];
}
```
