# Ordem de Carga

A ordem abaixo é exatamente a que o método `executar` aplica em `EtlPedagogicoService`.

## Fase 1 — sem dependências internas
1. `componente_curricular`

## Fase 2 — sem dependências internas
2. `componente_turma`

## Fase 3 — sem dependências internas
3. `atribuicao_componente`

## Fase 4 — sem dependências internas (agrupamento em Python)
4. `agrupamento_atribuicao_territorio_saber` + `componente_curricular_agrupamento`

## Fase 5 — sem dependências internas
5. `grade_componente_curricular`

## Fase 6 — sem dependências internas
6. `turma`

---

> **Nota:** as fases 2 a 6 são independentes entre si no banco de destino. A ordem é mantida por conveniência operacional e por compatibilidade com a auditoria por fase.

## Diagrama

```{graphviz}
digraph G {
    rankdir=LR;
    node [shape=box, style="rounded"];

    F1 [label="Fase 1\ncomponente_curricular"];
    F2 [label="Fase 2\ncomponente_turma"];
    F3 [label="Fase 3\natribuicao_componente"];
    F4 [label="Fase 4\nagrupamentos TS\n(2 tabelas)"];
    F5 [label="Fase 5\ngrade_componente_curricular"];
    F6 [label="Fase 6\nturma"];

    F1 -> F2 -> F3 -> F4 -> F5 -> F6;
}
```
