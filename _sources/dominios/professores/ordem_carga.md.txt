# Ordem de Carga

A ordem abaixo preserva as dependencias entre os grupos de dados do dominio.

## Fase 1 — sem dependências internas
1. `professor`
2. `pessoa`

## Fase 2 — dependem da Fase 1
3. `cargo_base_servidor`
4. `contrato_externo`

## Fase 3 — dependem da Fase 2
5. `lotacao_servidor`
6. `cargo_sobreposto_servidor`
7. `funcao_atividade_cargo_servidor`
8. `laudo_medico`
9. `atribuicao_aula`
10. `atribuicao_externo`

## Fase 4 — dependem das Fases 1–3
11. `funcionario_unidade_educacional`
12. `funcionario_sistema_perfil`
13. `turma_atribuida_ue`
14. `disciplina_turma_atribuida_ue`

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

## FuncionarioUnidadeEducacional

O vinculo do funcionario com a unidade e consolidado depois dos dados de
servidor, cargo, afastamento, atribuicao e contrato externo.

## FuncionarioSistemaPerfil

O perfil de sistema do funcionario e consolidado por login, perfil e sistema
na fase final. A carga contempla os sistemas usados pelos contratos legados e
preserva `cpf` e `uad_codigo` quando a origem informar.

## TurmaAtribuidaUe

As turmas sob abrangencia de unidade sao consolidadas na fase final. Esse grupo
representa a visao de turmas que nasce do vinculo com a unidade educacional.

## DisciplinaTurmaAtribuidaUe

Os componentes das turmas abrangidas tambem sao consolidados na fase final,
depois que a relacao entre funcionario e turma esta definida.
