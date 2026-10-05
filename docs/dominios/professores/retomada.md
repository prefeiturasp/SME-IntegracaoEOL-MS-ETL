# Retomada por Fase e Tabela

A retomada é baseada em `EtlCheckpointDominio` e em `ultima_fase_concluida` do serviço.

## Regra real do comando

Se `--continuar`:
- lê checkpoint do domínio `professores`
- se `ultima_pagina < 4`: `fase_inicial = ultima_pagina + 1`
- se `ultima_pagina == 4` (tudo concluído): reinicia em fase 1

Granularidade por tabela e lote via `indice_sincronizacao`:
- `"tabela:lote"` — tabela interrompida no meio; retoma do lote seguinte (exceto tabelas full-refresh, que sempre reprocessam do lote 0)
- `"tabela"` — tabela concluída; próxima tabela começa do lote 0
- `None` — execução concluída ou nunca iniciada; reinicia do zero

## Em caso de erro
- `ultima_pagina` recebe `servico.ultima_fase_concluida`
- `indice_sincronizacao` preserva o valor salvo pelo último callback (tabela ou tabela:lote)
- `token_parada` preserva o valor anterior
- `ultima_situacao` vira `"erro"`

## Em caso de sucesso
- `ultima_pagina` recebe a última fase concluída
- `indice_sincronizacao` vira `None`
- `token_parada` é atualizado com `token_anterior + total_alterado`
- `ultima_situacao` vira `"concluido"`

## Diagrama

```{graphviz}
digraph G {
    rankdir=TB;
    node [shape=box, style="rounded"];

    CP [label="Ler checkpoint"];
    DEC [label="Definir fase inicial\ne pular_ate / lote_inicial"];
    RUN [label="Executar ETL"];
    OK [label="Checkpoint concluído"];
    ER [label="Checkpoint erro\n(preserva indice_sincronizacao)"];

    CP -> DEC -> RUN;
    RUN -> OK [label="sucesso"];
    RUN -> ER [label="erro"];
}
```
