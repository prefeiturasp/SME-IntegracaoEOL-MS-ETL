# Ordem de Carga

A ordem abaixo é exatamente a que o método `executar` aplica no serviço.

## Fase 1 — sem dependências internas
1. `dre`

## Fase 2
2. `tipo_escola`

## Fase 3
3. `sub_prefeitura`

## Fase 4 — depende das Fases anteriores
4. `unidade_educacional`

## Fase 5 — read model de compatibilidade
5. `dre_abrangencia`

## Diagrama

```{graphviz}
digraph G {
    rankdir=LR;
    node [shape=box, style="rounded"];

    F1 [label="Fase 1"];
    F2 [label="Fase 2"];
    F3 [label="Fase 3"];
    F4 [label="Fase 4"];
    F5 [label="Fase 5"];

    F1 -> F2 -> F3 -> F4 -> F5;
}
```
