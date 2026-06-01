# Enums do Domínio Programas

Arquivo: `apps/programas/enums.py`

Centraliza os valores do EOL usados pelo domínio, eliminando constantes hardcoded nas SQLs e no mapeamento DTO → modelo. É a **fonte única de verdade** para: categorias PAP/PAEE/OUTROS, `cd_tipo_programa`, `cd_componente_curricular`, situação de turma e situação de matrícula.

---

## `CategoriaPrograma`

```python
class CategoriaPrograma(models.TextChoices):
    PAP = "PAP", "PAP"
    PAEE = "PAEE", "PAEE"
    OUTROS = "OUTROS", "Outros"
```

Usado no campo `categoria` de `TipoPrograma`, `ComponenteCurricularPrograma`,
`TurmaPrograma`, `MatriculaTurmaPrograma` e `MatriculaTurmaProgramaHistorico`.

> `OUTROS` foi adicionado para acomodar tipos de programa do EOL referenciados
> por turmas com `cd_tipo_turma = 3` que não pertencem a PAP nem PAEE.

---

## `TipoProgramaEOL`

Subset histórico de `cd_tipo_programa` do EOL — usado para retrocompatibilidade.
Hoje o ETL **não filtra** turmas por essa lista; carrega qualquer `cd_tipo_programa`
referenciado por turmas com `cd_tipo_turma = 3`, e a categoria é derivada da sigla
ou descrição do tipo.

| Membro | Valor | Categoria histórica |
|--------|-------|---------------------|
| `PAP_RECUPERACAO` | 649 | PAP |
| `PAP_COLABORATIVO` | 650 | PAP |
| `PAEE_SRM` | 656 | PAEE |
| `PAEE_COLABORATIVO` | 657 | PAEE |
| `PAEE_ITINERANTE` | 658 | PAEE |

### Métodos

- `TipoProgramaEOL.categoria_por_sigla(sigla, descricao) → CategoriaPrograma` —
  resolve PAP/PAEE/OUTROS a partir do conteúdo de `sg_tipo_programa` e
  `dc_tipo_programa`:
  - contém `"PAEE"` ou `"SRM"` → `PAEE`
  - contém `"PAP"` → `PAP`
  - caso contrário → `OUTROS`
- `TipoProgramaEOL.codigos() → tuple[int, ...]` — retorna os códigos históricos
  canônicos. Usado em testes; **não** é referenciado pela SQL atual (a SQL não
  filtra por `IN (...)` no `tipo_programa`).

---

## `ComponenteCurricularEOL`

`cd_componente_curricular` do EOL para os componentes de PAP/PAEE.

| Membro | Valor | Categoria | Vigente |
|--------|-------|-----------|---------|
| `PAP_RECUPERACAO_APRENDIZAGENS` | 1322 | PAP | ✓ |
| `PAP_PROJETO_COLABORATIVO` | 1770 | PAP | ✓ |
| `PAP_2ANO_ALFABETIZACAO` | 1804 | PAP | ✓ |
| `PAP_2ANO_COLABORATIVO_ALFABETIZACAO` | 1805 | PAP | ✓ |
| `PAP_LEGADO_MATEMATICA` | 1033 | PAP | ✗ |
| `PAP_LEGADO_CIENCIAS` | 1051 | PAP | ✗ |
| `PAP_LEGADO_GEOGRAFIA` | 1052 | PAP | ✗ |
| `PAP_LEGADO_HISTORIA` | 1053 | PAP | ✗ |
| `PAP_LEGADO_PORTUGUES` | 1054 | PAP | ✗ |
| `PAEE_SALA_RECURSOS_MULTIFUNCIONAIS` | 1030 | PAEE | ✓ |

### Métodos

- `ComponenteCurricularEOL.categoria(codigo) → CategoriaPrograma` — retorna `PAEE`,
  `PAP` ou `OUTROS` para qualquer `cd_componente_curricular` (códigos
  desconhecidos retornam `OUTROS`).
- `ComponenteCurricularEOL.vigente(codigo) → bool` — `True` para componentes
  ativos; `False` para legados (PAP antigos de 2014-2019) e códigos desconhecidos.
- `ComponenteCurricularEOL.codigos() → tuple[int, ...]` — todos os códigos do
  enum como tupla.
- `ComponenteCurricularEOL.codigos_pap_vigentes() → tuple[int, ...]` —
  apenas códigos vigentes de PAP (exclui PAEE e legados). Usado pelas
  Fases 7 e 8 (`SQL_ALUNO_PAP_ANO_LETIVO` / `_HISTORICO`) para filtrar a query
  agregada.

> O flag `vigente` é persistido no modelo `ComponenteCurricularPrograma` e substitui a constante `IDS_COMPONENTES_CURRICULARES_PAP_NOVO` do Pedagogico-API legado.

> O `SQL_TURMA_PROGRAMA` também usa `_COMPONENTES_PAP_CONHECIDOS` (privado a `enums.py`)
> e `PAEE_SALA_RECURSOS_MULTIFUNCIONAIS` para o `CASE WHEN` que deriva a categoria da turma.

---

## `SituacaoTurma`

Valores de `st_turma_escola` do EOL (campo `situacao` em `TurmaPrograma`).

| Membro | Valor | Descrição |
|--------|-------|-----------|
| `ORGANIZADA` | `"O"` | Turma organizada |
| `NAO_ORGANIZADA` | `"A"` | Não organizada |
| `CONCLUIDA` | `"C"` | Concluída |
| `EXTINTA` | `"E"` | Extinta |

- `SituacaoTurma.get_descricao(codigo) → str` — retorna o texto amigável (`"Organizada"`, `"Não Organizada"`, etc.); `"Não Informada"` para `None`; `"Desconhecido"` para valores fora do enum.

---

## `SituacaoMatricula`

Valores de `cd_situacao_aluno` / `st_matricula` do EOL (campo `codigo_situacao_matricula` em `MatriculaTurmaPrograma` e `MatriculaTurmaProgramaHistorico`).

| Código | Membro | Descrição |
|--------|--------|-----------|
| 1 | `ATIVO` | Ativo |
| 2 | `DESISTENTE` | Desistente |
| 3 | `TRANSFERIDO` | Transferido |
| 4 | `VINCULO_INDEVIDO` | Vínculo Indevido |
| 5 | `CONCLUIDO` | Concluído |
| 6 | `PENDENTE_REMATRICULA` | Pendente de Rematrícula |
| 7 | `FALECIDO` | Falecido |
| 8 | `NAO_COMPARECEU` | Não Compareceu |
| 10 | `REMATRICULADO` | Rematriculado |
| 11 | `DESLOCAMENTO` | Deslocamento |
| 12 | `CESSADO` | Cessado |
| 13 | `SEM_CONTINUIDADE` | Sem continuidade |
| 14 | `REMANEJADO_SAIDA` | Remanejado Saída |
| 15 | `RECLASSIFICADO_SAIDA` | Reclassificado Saída |
| 16 | `TRANSFERIDO_SED` | Transferido SED |
| 17 | `DISPENSADO_ED_FISICA` | Dispensado Ed. Física |

### Método

- `SituacaoMatricula.get_descricao(codigo) → str`

Espelha `apps.alunos.enums.SituacaoMatricula`. Foi replicado (e não importado) para preservar independência entre domínios.

> **Impacto no ETL:** o `MatriculaTurmaProgramaIn.to_domain()` usa `SituacaoMatricula.get_descricao()` para derivar `descricao_situacao_matricula` em Python. A SQL não contém `CASE WHEN` para tradução de situação — a regra vive em um único lugar (`enums.py`).

---

## Por que enums (e não constantes soltas)

1. **Fonte única de verdade** — adicionar um novo componente é uma linha no enum; o `SQL_TURMA_PROGRAMA` e os filtros `IN (...)` das Fases 7/8 se ajustam automaticamente via `_COMPONENTES_PAP_CONHECIDOS` e `ComponenteCurricularEOL.codigos_pap_vigentes()`.
2. **Simplifica o SQL** — o `CASE WHEN` de situação de matrícula virou Python puro.
3. **Reaproveitável na API** — quando o DRF expor endpoints de leitura, os enums já dão validação e serialização prontas.
4. **Testável isoladamente** — `tests/test_dtos.py` cobre `categoria_por_sigla`, `categoria`, `vigente`, `codigos_pap_vigentes`, `get_descricao`.
