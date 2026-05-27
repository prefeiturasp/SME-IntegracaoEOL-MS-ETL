# Ordem de Carga ETL — Domínio Programas

As fases estão registradas em `EtlProgramasService._init_fases()`
(`apps/programas/services.py`) como lista de `PhaseConfig`, executadas em sequência
pelo `BaseEtlService.executar()` herdado.

## Diagrama de dependências

```
TipoPrograma (Fase 1)
    └── TurmaPrograma (Fase 3)
            ├── TurmaProgramaComponenteCurricular (Fase 4)
            ├── MatriculaTurmaPrograma (Fase 5)
            ├── MatriculaTurmaProgramaHistorico (Fase 6)
            ├── AlunoPapAnoLetivo (Fase 7)
            └── AlunoPapAnoLetivoHistorico (Fase 8)

ComponenteCurricularPrograma (Fase 2)
    ├── TurmaProgramaComponenteCurricular (Fase 4)
    ├── MatriculaTurmaPrograma (Fase 5)
    ├── MatriculaTurmaProgramaHistorico (Fase 6)
    ├── AlunoPapAnoLetivo (Fase 7)
    └── AlunoPapAnoLetivoHistorico (Fase 8)
```

## Tabela de fases

| Fase | `PhaseConfig.nome` | Modelo | Source EOL | Depende de |
|------|-----|--------|-----------|-----------|
| 1 | `tipo_programa` | `TipoPrograma` | `tipo_programa` | — |
| 2 | `componente_curricular_programa` | `ComponenteCurricularPrograma` | `componente_curricular` | — |
| 3 | `turma_programa` | `TurmaPrograma` | `turma_escola` | Fase 1 |
| 4 | `turma_programa_componente_curricular` | `TurmaProgramaComponenteCurricular` | `turma_escola_grade_programa` | Fases 2 e 3 |
| 5 | `matricula_turma_programa` | `MatriculaTurmaPrograma` | `matricula_turma_escola` | Fases 2 e 3 |
| 6 | `matricula_turma_programa_historico` | `MatriculaTurmaProgramaHistorico` | `v_historico_matricula_cotic` | Fases 2 e 3 |
| 7 | `aluno_pap_ano_letivo` | `AlunoPapAnoLetivo` | `v_matricula_cotic` | Fases 2 e 3 |
| 8 | `aluno_pap_ano_letivo_historico` | `AlunoPapAnoLetivoHistorico` | `v_historico_matricula_cotic` | Fases 2 e 3 |

Todas as fases declaram `modo_escrita="upsert"` no `PhaseConfig`.

## Observações

- As fases 1 e 2 são leves (poucas linhas) e funcionam como configuração;
  ainda assim usam o mesmo caminho de upsert incremental por hash.
- A Fase 3 (`TurmaPrograma`) é pré-requisito lógico para 4 a 8 — todas usam
  `codigo_turma` como FK lógica.
- A Fase 2 (`ComponenteCurricularPrograma`) é pré-requisito lógico para 4 a 8 —
  todas referenciam `codigo_componente_curricular`.
- As fases 6 e 8 leem do **histórico** (`v_historico_matricula_cotic` /
  `historico_matricula_turma_escola`). Não dependem da execução das fases 5 e 7;
  a ordem é só posicional para deixar o checkpoint linear.
- A retomada via `--continuar` permite iniciar a partir de uma `fase_inicial`
  específica, evitando reprocessar fases já concluídas. Ver {doc}`retomada`.
- Sem FK física entre os modelos — a integridade é garantida pela ordem de execução.
  Carregar a Fase 4 antes da Fase 3 produziria `codigo_turma` órfão.
