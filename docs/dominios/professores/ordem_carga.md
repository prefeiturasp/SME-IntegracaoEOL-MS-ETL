# Ordem de Carga

A ordem abaixo é exatamente a que o método `executar` aplica no serviço.

## Fase 1
1. `dre`
2. `tipo_escola`
3. `componente_curricular`
4. `serie_ensino`
5. `territorio_saber`
6. `tipo_experiencia_pedagogica`
7. `grade`
8. `cargo`
9. `funcao_funcionario_externo`

## Fase 2
10. `unidade_educacional`
11. `escola_grade`
12. `turma_escola`
13. `professor`
14. `pessoa`

## Fase 3
15. `serie_turma_grade`
16. `turma_escola_grade_programa`
17. `cargo_base_servidor`
18. `contrato_externo`
19. `turma_grade_territorio_experiencia`
20. `lotacao_servidor`
21. `cargo_sobreposto_servidor`
22. `funcao_atividade_cargo_servidor`
23. `laudo_medico`

## Fase 4
24. `atribuicao_aula`
25. `atribuicao_externo`

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
