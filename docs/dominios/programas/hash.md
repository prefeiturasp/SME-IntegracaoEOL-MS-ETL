# Hash por Linha

## Implementação real

O controle incremental é implementado em `_calcular_hash` e `_upsert_incremental`.

### `_calcular_hash`
- lê os campos relevantes da instância Django
- serializa como JSON com chaves ordenadas (`json.dumps(..., sort_keys=True, default=str)`)
- calcula SHA-256 em hexadecimal

### `_upsert_incremental`
1. deduplica os objetos por chave natural (`unique_fields`), mantendo o último em caso de duplicata da origem
2. monta `id_destino = "{tabela}:{v1}:{v2}..."` (concatena todos os valores da chave)
3. calcula hash SHA-256 dos `update_fields`, **excluindo** o `timestamp_field` (para que o timestamp não force reescrita)
4. consulta `EtlAuditoriaLinha` **em uma única query** (`filter(id_destino__in=ids_destino)`)
5. filtra apenas registros novos ou com hash diferente
6. atualiza `timestamp_field` dos registros alterados
7. faz `bulk_create(update_conflicts=True)` no `programas_db` com `batch_size=500`
8. grava os novos hashes de volta em `EtlAuditoriaLinha` (também com `batch_size=500`)

## Fluxo

```{graphviz}
digraph G {
    rankdir=LR;
    node [shape=box, style="rounded"];

    SRC [label="Origem"];
    HASH [label="Gerar hash"];
    LOOKUP [label="Consultar EtlAuditoriaLinha"];
    FILTER [label="Filtrar mudanças"];
    UPSERT [label="Upsert destino"];
    AUD [label="Atualizar auditoria"];

    SRC -> HASH -> LOOKUP -> FILTER -> UPSERT -> AUD;
}
```

## Formato do identificador

O `id_destino` concatena o nome da tabela com os valores da chave natural (`unique_fields`) separados por `:`. Para chaves compostas, todos os valores entram.

Exemplos reais para o domínio `programas`:

| Tabela | `unique_fields` | Exemplo de `id_destino` |
|--------|-----------------|-------------------------|
| `tipo_programa` | `[codigo_tipo_programa]` | `tipo_programa:649` |
| `componente_curricular_programa` | `[codigo_componente_curricular]` | `componente_curricular_programa:1322` |
| `turma_programa` | `[codigo_turma]` | `turma_programa:2528310` |
| `turma_programa_componente_curricular` | `[codigo_turma, codigo_componente_curricular]` | `turma_programa_componente_curricular:2528310:1322` |
| `matricula_turma_programa` | `[codigo_turma, codigo_aluno, codigo_componente_curricular]` | `matricula_turma_programa:2528310:8374625:1322` |

## Benefícios reais no código
- evita reescrita desnecessária
- permite token de progresso baseado apenas em linhas alteradas
- preserva rastreabilidade da última sincronização