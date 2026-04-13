# Ordem de Carga

A ordem abaixo é exatamente a que o método `executar` aplica em `EtlPedagogicoService`.

## Fase 1 — sem dependências internas
1. `componente_curricular`

## Fase 2 — sem dependências internas (usa lookups A2/A3)
2. `componente_curricular_por_turma`

## Fase 3 — sem dependências internas (agrupamento em Python)
3. `agrupamento_atribuicao_territorio_saber` + `componente_curricular_agrupamento`

## Fase 4 — sem dependências internas (usa lookup A3)
4. `componente_curricular_regencia`

## Fase 5 — sem dependências internas
5. `dados_aula_turma`

## Fase 6 — sem dependências internas
6. `componente_curricular_por_ano_letivo`

---

> **Nota:** as fases 2 a 6 são independentes entre si no banco de destino. A ordem é mantida por conveniência operacional e para garantir que os lookups A2/A3 (carregados uma vez antes das fases 2 e 4) sejam reutilizados sem recarga.

## Diagrama

```{graphviz}
digraph G {
    rankdir=LR;
    node [shape=box, style="rounded"];

    F1 [label="Fase 1\ncomponente_curricular"];
    F2 [label="Fase 2\ncomponente_por_turma"];
    F3 [label="Fase 3\nagrupamentos TS\n(2 tabelas)"];
    F4 [label="Fase 4\ncomponente_regencia"];
    F5 [label="Fase 5\ndados_aula_turma"];
    F6 [label="Fase 6\npor_ano_letivo"];

    F1 -> F2 -> F3 -> F4 -> F5 -> F6;
}
```
