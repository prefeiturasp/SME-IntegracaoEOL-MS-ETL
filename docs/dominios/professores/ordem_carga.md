# Ordem de Carga

A ordem abaixo é exatamente a que o método `executar` aplica no serviço.

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

A tabela `funcionario_unidade_educacional` e carregada na fase final, apos as
tabelas que alimentam a consulta consolidada de servidores, vinculos,
afastamentos, atribuicoes e externos.
