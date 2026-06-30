# Ordem de Carga

A ordem abaixo é exatamente a que o método `executar` aplica em `EtlPedagogicoService`.

## Fase 1 — sem dependências internas
1. `componente_curricular`

## Fase 2 — sem dependências internas
2. `componente_turma`

## Fase 3 — sem dependências internas
3. `atribuicao_componente`

## Fase 4 — sem dependências internas
4. `atribuicao_territorio_saber`

## Fases 5 a 8 — API EOL (`full_refresh`)
5. `componente_curricular_hierarquia`
6. `componente_curricular_pap`
7. `componente_curricular_planejamento_regencia`
8. `turma_itinerario_ensino_medio`

## Fase 9 — API EOL (`full_refresh`)
9. `agrupamento_atribuicao_territorio_saber`

## Fase 10 — sem dependências internas
10. `grade_componente_curricular`

## Fase 11 — sem dependências internas
11. `turma`

---

> **Nota:** as fases 2 a 11 são independentes entre si no banco de destino. A ordem é mantida por conveniência operacional e por compatibilidade com a auditoria por fase.
> A fase `agrupamento_territorio_saber_gerado` é backup selecionável e não faz parte da execução padrão.

## Diagrama

```{graphviz}
digraph G {
    rankdir=LR;
    node [shape=box, style="rounded"];

    F1 [label="Fase 1\ncomponente_curricular"];
    F2 [label="Fase 2\ncomponente_turma"];
    F3 [label="Fase 3\natribuicao_componente"];
    F4 [label="Fase 4\natribuicao_territorio_saber"];
    F5 [label="Fases 5-8\napoio API EOL"];
    F9 [label="Fase 9\nagrupamentos TS\nAPI EOL"];
    F10 [label="Fase 10\ngrade_componente_curricular"];
    F11 [label="Fase 11\nturma"];

    F1 -> F2 -> F3 -> F4 -> F5 -> F9 -> F10 -> F11;
}
```
