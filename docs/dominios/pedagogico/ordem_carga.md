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

## Fases 5 a 9 — API EOL (`full_refresh`)
5. `componente_curricular_api_eol`
6. `componente_curricular_hierarquia`
7. `componente_curricular_pap`
8. `componente_curricular_planejamento_regencia`
9. `turma_itinerario_ensino_medio`

## Fase 10 — API EOL (`full_refresh`)
10. `agrupamento_atribuicao_territorio_saber`

## Fase 11 — sem dependências internas
11. `grade_componente_curricular`

## Fase 12 — sem dependências internas
12. `turma`

## Fase 13 — sem dependências internas
13. `turma_atribuida_dre_ue`

## Fases 14 e 15 — catálogos do EOL (`full_refresh`)
14. `etapa_ensino`
15. `ciclo_ensino`

---

> **Nota:** as fases 2 a 15 são independentes entre si no banco de destino. A ordem é mantida por conveniência operacional e por compatibilidade com a auditoria por fase.
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
    F5 [label="Fases 5-9\napoio API EOL"];
    F10 [label="Fase 10\nagrupamentos TS\nAPI EOL"];
    F11 [label="Fase 11\ngrade_componente_curricular"];
    F12 [label="Fase 12\nturma"];
    F13 [label="Fase 13\nturma_atribuida_dre_ue"];
    F14 [label="Fase 14\netapa_ensino"];
    F15 [label="Fase 15\nciclo_ensino"];

    F1 -> F2 -> F3 -> F4 -> F5 -> F10 -> F11 -> F12 -> F13 -> F14 -> F15;
}
```
