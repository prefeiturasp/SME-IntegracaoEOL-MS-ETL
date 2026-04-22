# Otimização: `_SQL_COMPONENTES_POR_TURMA_V1` → `SQL_COMPONENTES_POR_TURMA`

## Contexto

A query `_SQL_COMPONENTES_POR_TURMA_V1` (arquivo `apps/pedagogico/queries.py`) foi substituída por
`SQL_COMPONENTES_POR_TURMA`. Este documento registra a análise de equivalência semântica que embasou
essa decisão.

---

## Problema da versão original

`_SQL_COMPONENTES_POR_TURMA_V1` usava uma CTE única (`tmpComponentePrograma`) que fazia LEFT JOIN
simultâneo dos dois caminhos de obtenção de componentes — via **série** e via **programa** — sobre
a mesma linha de turma. Isso causava dois problemas:

1. **Produto cartesiano série × programa**: para uma turma com N componentes de série e M
   componentes de programa, a CTE gerava N × M linhas. O `SELECT DISTINCT *` externo deduplicava
   o resultado, mas a custo de processamento elevado.

2. **OR no JOIN com `atribuicao_aula`**: o JOIN de Branch 1 (SME) usava `OR` entre o caminho da
   série e o caminho do programa. O otimizador do SQL Server não consegue usar índice de forma
   eficiente em JOINs com `OR`, resultando em table/index scans.

```sql
-- Trecho problemático do OR na V1
ON ((tmp.CodigoGradeSerie = aa.cd_grade
      AND tmp.CodigoComponenteSerie = aa.cd_componente_curricular
      AND aa.cd_serie_grade = tmp.CodigoSerieGrade)
    OR (tmp.CodigoGradePrograma = aa.cd_grade
        AND tmp.CodigoComponentePrograma = aa.cd_componente_curricular
        AND (tmp.CodigoSerieGrade IS NULL
             OR tmp.CodigoSerieGrade = aa.cd_serie_grade)))
```

---

## Solução adotada

`SQL_COMPONENTES_POR_TURMA` separa os dois caminhos em CTEs distintas:

- **`cte_turmas`**: base comum com turmas ativas do ano (1 parâmetro `?`).
- **`cte_serie`**: componentes via grade curricular de série (inclui override de programa via `iif`
  quando a turma possui ambos).
- **`cte_programa`**: componentes via grade de programa, **restrito a turmas sem série**
  (`WHERE NOT EXISTS` em `serie_turma_escola`).

Com isso, cada branch do `UNION ALL` usa predicados de igualdade simples no JOIN, permitindo uso
pleno de índices.

---

## Análise de equivalência semântica

### Caso potencialmente divergente

A principal diferença estrutural estava no tratamento de turmas que possuem **série e programa
simultaneamente**:

| Comportamento | V1 | Nova versão |
|---|---|---|
| Turmas só série | OR braço 1: `(grade_série + comp_série)` | Branch 1: `(grade_série + comp_série)` ✓ |
| Turmas só programa | OR braço 2: `(grade_programa + comp_programa)` | Branch 3: `(grade_programa + comp_programa)` ✓ |
| Turmas série + programa | OR braço 1 **e** braço 2 cobertos | `cte_serie` usa `(grade_série + iif_comp)` e `cte_programa` exclui essas turmas |

Para turmas com série + programa, a nova versão usa `(grade_série + componente_priorizado_por_iif)`,
enquanto a V1 tentava `(grade_programa + comp_programa)` pelo segundo braço do OR. Essa combinação
híbrida poderia, em tese, deixar de encontrar atribuições registradas pela grade do programa.

### Validação no banco

A divergência só se materializaria se existissem turmas com registros simultâneos em
`serie_turma_escola` **e** `turma_escola_grade_programa`. A consulta abaixo foi executada contra o
banco de produção EOL:

```sql
SELECT COUNT(*)
FROM turma_escola te
WHERE EXISTS (
    SELECT 1 FROM serie_turma_escola ste
    WHERE ste.cd_turma_escola = te.cd_turma_escola
)
AND EXISTS (
    SELECT 1 FROM turma_escola_grade_programa tegp
    WHERE tegp.cd_turma_escola = te.cd_turma_escola
)
AND te.st_turma_escola IN ('O', 'A', 'C', 'E')
AND te.an_letivo = <ano>
```

**Resultado: 0 linhas.** Nenhuma turma ativa possui série e programa simultaneamente.

Portanto, `cte_programa` nunca excluirá uma turma que o caminho de programa da V1 teria coberto, e
as duas queries são **funcionalmente equivalentes** nos dados reais.

---

## Outras diferenças sem impacto funcional

| Aspecto | V1 | Nova versão | Impacto |
|---|---|---|---|
| Parâmetros `?` | 2 (ambos `ano_letivo`, mesmo valor) | 1 (`cte_turmas`) | Nenhum — serviço usa `str.replace` |
| `duracao_tipo_turno` hint | sem `(NOLOCK)` | com `(NOLOCK)` | Apenas leitura suja; coerente com restante da query |
| LEFT JOIN `tipo_programa` | presente, sem uso em SELECT/WHERE | removido | Nenhum |
| `SELECT DISTINCT *` externo | presente (deduplica produto cartesiano) | ausente | Sem necessidade — produto cartesiano eliminado |

---
