# Manutenção da tabela de auditoria de linhas

`etl_auditoria_linha` guarda um hash por linha de destino, no formato
`{tabela}:{pk}`. Ela **não é um log**: é um cache de estado atual, com uma
entrada por linha existente no destino.

Duas consequências práticas:

- Não há registros "antigos" a expirar. O tamanho natural da tabela é o
  total de linhas de destino somadas — ela cresce junto com o dado, não
  sozinha. **Não existe rotina periódica de limpeza a ser feita.**
- Apagar uma entrada é sempre seguro. A execução seguinte vê a linha como
  alterada e regrava o mesmo conteúdo. Nunca há perda de dado, apenas o
  custo de uma regravação.

## Não use retenção por data

`atualizado_em` só é tocado quando o hash muda:

```sql
ON CONFLICT (id_destino) DO UPDATE SET ... atualizado_em = NOW()
WHERE etl_auditoria_linha.hash_controle <> EXCLUDED.hash_controle
```

Ou seja, a coluna registra a **última mudança**, não o último acesso. Uma
linha estável há dois anos carrega a data mais antiga da tabela — e é
justamente a que mais compensa manter em cache. Uma política do tipo
"apagar o que não é tocado há N meses" removeria primeiro as entradas mais
valiosas e provocaria a maior regravação possível.

## Recolher o espaço em produção

O `VACUUM` de rotina marca espaço como reutilizável, mas não devolve ao
sistema de arquivos. Depois de qualquer remoção em massa, ou quando a
proporção de tuplas mortas subir, use `pg_repack` — ele reorganiza a
tabela online, sem o `ACCESS EXCLUSIVE` que o `VACUUM FULL` exige:

```bash
pg_repack --no-superuser-check -d etl_db -t etl_auditoria_linha
```

`VACUUM FULL` só em janela de indisponibilidade: ele bloqueia leitura e
escrita na tabela durante toda a operação.

Para inspecionar antes de decidir:

```sql
SELECT n_live_tup, n_dead_tup,
       round(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 1) AS pct_morto,
       last_autovacuum
  FROM pg_stat_user_tables
 WHERE relname = 'etl_auditoria_linha';

SELECT pg_size_pretty(pg_relation_size('etl_auditoria_linha'))      AS heap,
       pg_size_pretty(pg_indexes_size('etl_auditoria_linha'))       AS indices,
       pg_size_pretty(pg_total_relation_size('etl_auditoria_linha')) AS total;
```

Medição local, 1,87 milhão de linhas: 724 MB antes, 537 MB depois — 26% só
de inchaço acumulado, sem apagar uma linha sequer.

## O índice `_like` é padrão do Django, e fica

Metade do espaço de índices da tabela é o
`etl_auditoria_linha_id_destino_596d0bd2_like`, criado automaticamente
pelo Django: todo campo `varchar` ou `text` com `unique` ou `db_index`
ganha um segundo índice com `varchar_pattern_ops`, porque fora do locale
`C` o índice comum não atende consultas por prefixo (`LIKE 'algo%'`).
Como `primary_key=True` implica `unique`, `id_destino` entra na regra.

Ele custa cerca de 126 MB, o mesmo tamanho da chave primária, e hoje
nenhuma consulta o utiliza — a contagem por tabela do kanban, único ponto
que consultava por prefixo, passou a usar `GROUP BY`. Ainda assim ele é
mantido de propósito: é o comportamento padrão do framework, e removê-lo
exigiria uma migration com `RunSQL` que teria de ser repetida a cada
`AlterField` em `id_destino`, já que o Django recria o índice nesses casos.

Se um dia o tamanho pesar mais que a aderência ao padrão, a alternativa
melhor que dropar é trocar o tipo de `id_destino` por `bytea` (um digest
da chave, em vez do texto). O Django não cria índice `_like` para tipo
binário, então o índice deixa de existir por consequência, e a chave em si
encolhe de 46 bytes para 16.

## Verificar se há entradas órfãs

Entradas cuja tabela de destino não existe mais (fase renomeada, fase que
passou a `full_refresh`) nunca são lidas nem atualizadas. Para encontrá-las,
compare os prefixos gravados com os `table_name` das fases `upsert` atuais:

```sql
SELECT split_part(id_destino, ':', 1) AS tabela, count(*)
  FROM etl_auditoria_linha
 GROUP BY 1
 ORDER BY 2 DESC;
```

Todo prefixo fora da lista de fases atuais pode ser removido com `DELETE`,
seguido de `pg_repack`. Se todos os prefixos corresponderem a fases ativas,
não há nada a limpar.

## Quando a chave carrega estado mutável

Se a chave primária de uma fase inclui um campo que muda ao longo do tempo,
cada mudança gera uma chave nova: a antiga deixa de ser emitida pela origem
e vira uma entrada morta permanente, tanto na auditoria quanto no destino.
Isso é acúmulo real, e limpeza periódica só trata o sintoma — a correção é
tirar o campo mutável da chave.

Para detectar, conte versões por chave estável no banco de destino:

```sql
SELECT n_versoes, count(*) FROM (
  SELECT codigo_matricula, codigo_turma, count(*) AS n_versoes
    FROM matricula_turma GROUP BY 1, 2
) t GROUP BY 1 ORDER BY 1 DESC;
```

Tudo em `n_versoes = 1` indica chaves estáveis. Uma cauda com 2, 3 ou mais
versões indica que a chave está absorvendo transições de estado.
