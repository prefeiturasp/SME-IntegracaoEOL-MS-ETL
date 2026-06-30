# Retomada por Fase

A retomada é baseada em `EtlCheckpointDominio` e em `ultima_fase_concluida` do serviço.

## Regra real do comando

Se `--continuar`:
- Lê checkpoint do domínio `pedagogico`
- Se `ultima_situacao == "erro"` e `0 < ultima_pagina < 11`, define `fase_inicial = ultima_pagina + 1`
- Caso contrário, reinicia em fase 1

## Em caso de erro
- `ultima_pagina` recebe `servico.ultima_fase_concluida`
- `token_parada` preserva o valor anterior
- `ultima_situacao` vira `"erro"`

## Em caso de sucesso
- `ultima_pagina` recebe `11` (última fase)
- `token_parada` é atualizado com `token_anterior + total_alterado`
- `ultima_situacao` vira `"concluido"`

## Fases `full_refresh` e retomada

As fases vindas da API EOL usam `full_refresh`. Se uma dessas fases falhar, a retomada reexecuta a fase inteira. Como a fase trunca e recarrega a tabela de destino, o resultado esperado é espelhar novamente a origem completa.

A fase opcional `agrupamento_territorio_saber_gerado` escreve em duas tabelas (`agrupamento_atribuicao_territorio_saber` e `componente_curricular_agrupamento`) e só entra na ordem quando selecionada explicitamente.

## Diagrama

```{graphviz}
digraph G {
    rankdir=TB;
    node [shape=box, style="rounded"];

    CP [label="Ler checkpoint"];
    DEC [label="Definir fase inicial\n(1–11)"];
    RUN [label="Executar ETL"];
    OK [label="Checkpoint concluído"];
    ER [label="Checkpoint erro\n(salva ultima_fase_concluida)"];

    CP -> DEC -> RUN;
    RUN -> OK [label="sucesso"];
    RUN -> ER [label="erro"];
}
```
