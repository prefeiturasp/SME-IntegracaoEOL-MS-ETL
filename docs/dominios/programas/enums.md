# Enums do Domínio Programas

Arquivo: `apps/programas/enums.py`

Centraliza os valores do EOL usados pelo domínio, eliminando constantes hardcoded nas SQLs e no mapeamento In/Out. É a **fonte única de verdade** para: categorias PAP/PAEE, `cd_tipo_programa`, `cd_componente_curricular`, situação de turma e situação de matrícula.

---

## `CategoriaPrograma`

```python
class CategoriaPrograma(StrEnum):
    PAP = "PAP"
    PAEE = "PAEE"
```

Usado no campo `categoria` de `TipoPrograma`, `ComponenteCurricularPrograma`, `TurmaPrograma` e `MatriculaTurmaPrograma`.

---

## `TipoProgramaEOL`

`cd_tipo_programa` do EOL para turmas com `cd_tipo_turma = 3`.

| Membro | Valor | Categoria |
|--------|-------|-----------|
| `PAP_RECUPERACAO` | 649 | PAP |
| `PAP_COLABORATIVO` | 650 | PAP |
| `PAEE_SRM` | 656 | PAEE |
| `PAEE_COLABORATIVO` | 657 | PAEE |
| `PAEE_ITINERANTE` | 658 | PAEE |

### Métodos

- `TipoProgramaEOL.categoria(codigo) → CategoriaPrograma` — resolve PAP/PAEE a partir do `cd_tipo_programa`. Retorna `PAP` como default para códigos desconhecidos.
- `TipoProgramaEOL.codigos() → tuple[int, ...]` — usado no `services.py` para montar os filtros `IN (...)` das SQLs da Fase 1, 3, 4 e 5.

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

- `ComponenteCurricularEOL.categoria(codigo) → CategoriaPrograma`
- `ComponenteCurricularEOL.vigente(codigo) → bool` — `True` para componentes ativos; `False` para legados (PAP antigos de 2014-2019)
- `ComponenteCurricularEOL.codigos() → tuple[int, ...]` — usado nos filtros `IN (...)` das SQLs das Fases 2, 4 e 5

> O flag `vigente` é persistido no modelo `ComponenteCurricularPrograma` e substitui a constante `IDS_COMPONENTES_CURRICULARES_PAP_NOVO` do Pedagogico-API legado.

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

Valores de `cd_situacao_aluno` / `st_matricula` do EOL (campo `codigo_situacao_matricula` em `MatriculaTurmaPrograma`).

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

> **Impacto no ETL:** o `MatriculaTurmaProgramaOut.from_in()` usa `SituacaoMatricula.get_descricao()` para derivar `descricao_situacao_matricula` em Python. Antes do refactor, essa tradução vinha de um bloco `CASE WHEN ... END` de 17 linhas dentro do `SQL_MATRICULA_TURMA_PROGRAMA`. Agora o SQL é mais simples e a regra vive em um único lugar.

---

## Por que enums (e não constantes soltas)

1. **Fonte única de verdade** — adicionar um novo tipo de programa ou componente é uma linha no enum; os filtros SQL (`TipoProgramaEOL.codigos()`, `ComponenteCurricularEOL.codigos()`) montam o `IN (...)` automaticamente.
2. **Simplifica o SQL** — o `CASE WHEN` de situação de matrícula saiu do SQL e virou Python puro.
3. **Reaproveitável na API** — quando o DRF expor endpoints de leitura, os enums já dão validação e serialização prontas.
4. **Testável isoladamente** — `tests/test_dtos.py` tem classes dedicadas (`TestTipoProgramaEOLEnum`, `TestComponenteCurricularEOLEnum`, `TestSituacaoTurmaEnum`, `TestSituacaoMatriculaEnum`) cobrindo cada `.categoria()`, `.vigente()`, `.get_descricao()`.
