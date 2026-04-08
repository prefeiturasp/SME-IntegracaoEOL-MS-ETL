# Ordem de Carga ETL — Domínio Programas

A execução é feita pelo método `EtlProgramasService.executar()` em `apps/programas/services.py`,
seguindo a hierarquia de dependências dos modelos.

## Diagrama de dependências

```
TipoPrograma (Fase 1)
    └── TurmaPrograma (Fase 3)
            ├── TurmaProgramaComponenteCurricular (Fase 4)
            └── MatriculaTurmaPrograma (Fase 5)

ComponenteCurricularPrograma (Fase 2)
    ├── TurmaProgramaComponenteCurricular (Fase 4)  ← referência lógica
    └── MatriculaTurmaPrograma (Fase 5)             ← referência lógica
```

## Tabela de fases

| Fase | Modelo | Método | Tipo | Depende de |
|------|--------|--------|------|-----------|
| 1 | `TipoPrograma` | `popular_tipos_programa` | Seed | — |
| 2 | `ComponenteCurricularPrograma` | `popular_componentes_curriculares` | Seed | — |
| 3 | `TurmaPrograma` | `popular_turmas_programa` | ETL incremental | Fase 1 |
| 4 | `TurmaProgramaComponenteCurricular` | `popular_turmas_programa_componentes` | ETL incremental | Fases 2 e 3 |
| 5 | `MatriculaTurmaPrograma` | `popular_matriculas_turma_programa` | ETL incremental | Fases 2 e 3 |

## Observações

- As fases 1 e 2 são **seeds** — dados estáticos com baixa frequência de alteração.
  Continuam usando `_upsert_incremental` com controle de hash, portanto são idempotentes.
- As fases 3, 4 e 5 são **ETL incremental** — volumes maiores, executadas a cada ciclo.
- A retomada via `--continuar` permite iniciar a partir de uma `fase_inicial` específica,
  evitando reprocessar fases já concluídas. Ver {doc}`retomada`.
- Sem FK física entre os modelos — a integridade é garantida pela ordem de execução.
  Carregar a Fase 4 antes da Fase 3 produziria `codigo_turma` órfão.
