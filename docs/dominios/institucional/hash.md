# Hash por Linha

## Implementação real

O controle incremental é implementado em `_calcular_hash` e `_upsert_incremental`.

### `_calcular_hash`
- ordena os campos relevantes
- serializa como `chave=valor`
- calcula SHA-256 em hexadecimal

### `_upsert_incremental`
1. monta `id_destino = "{tabela}:{pk}"`
2. calcula hash dos `update_fields`
3. busca hashes existentes em lotes de 1000
4. filtra apenas registros novos ou alterados
5. faz upsert no `institucional_db`
6. atualiza `EtlAuditoriaLinha`

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

Exemplos de `id_destino`:
- `dre:0012345`
- `tipo_escola:123456`
- `unidade_educacional:9988776`

## Benefícios reais no código
- evita reescrita desnecessária
- permite token de progresso baseado apenas em linhas alteradas
- preserva rastreabilidade da última sincronização