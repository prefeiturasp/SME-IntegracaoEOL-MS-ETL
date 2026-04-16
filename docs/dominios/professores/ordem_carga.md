# Ordem de Carga

A ordem abaixo é exatamente a que o método `executar` aplica no serviço.

## Fase 1 — sem dependências internas
1. `unidade_educacional`
2. `turma_escola`
3. `professor`
4. `pessoa`

## Fase 2 — dependem da Fase 1
5. `serie_turma_grade`
6. `turma_escola_grade_programa`
7. `cargo_base_servidor`
8. `contrato_externo`

## Fase 3 — dependem da Fase 2
9. `turma_grade_territorio_experiencia`
10. `lotacao_servidor`
11. `cargo_sobreposto_servidor`
12. `funcao_atividade_cargo_servidor`
13. `laudo_medico`
14. `atribuicao_aula`
15. `atribuicao_externo`

## Fase 4 — dependem das Fases 1–3
16. `agrupamento_atribuicao_territorio_saber`

## Diagrama

```{graphviz}
digraph G {
    rankdir=LR;
    node [shape=box, style="rounded"];

    F1 [label="Fase 1"];
    F2 [label="Fase 2"];
    F3 [label="Fase 3"];
    F4 [label="Fase 4"];

    F1 -> F2 -> F3 -> F4;
}
```
