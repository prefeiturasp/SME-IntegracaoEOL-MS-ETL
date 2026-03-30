# Estratégia por Tabela

## Incremental (`_upsert_incremental`)

- `dre`
- `tipo_escola`
- `componente_curricular`
- `serie_ensino`
- `territorio_saber`
- `tipo_experiencia_pedagogica`
- `grade`
- `cargo`
- `funcao_funcionario_externo`
- `escola_grade`
- `turma_escola`
- `professor`
- `pessoa`
- `serie_turma_grade`
- `turma_escola_grade_programa`
- `cargo_base_servidor`
- `contrato_externo`
- `atribuicao_aula`
- `atribuicao_externo`

## Full Refresh (`_full_refresh`)

- `unidades_educacionais`
- `turma_grade_territorio_experiencia`
- `lotacoes`
- `cargos_sobrepostos`
- `funcoes_atividade`
- `laudos`

## Regras reais do código

- `_full_refresh` faz `delete()` seguido de `bulk_create()` em transação usando `professores_db`.
- `_upsert_incremental` calcula hash com SHA-256, consulta `EtlAuditoriaLinha`, filtra apenas o que mudou e faz `bulk_create(update_conflicts=True)`.
- o comando registra `modo_escrita` como `upsert` ou `full_refresh` em `EtlExecucaoTabelaEscrita`.
