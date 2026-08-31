# Orquestração do ETL — Domínio Programas

## Fluxo geral

```
API (POST /executar/)
    └── Task Celery (despachada via EtlProgramasOrquestrador)
            └── management command etl_programas
                    └── EtlProgramasService.executar()
                            ├── Fase 1: tipo_programa
                            ├── Fase 2: componente_curricular_programa
                            ├── Fase 3: turma_programa
                            ├── Fase 4: turma_programa_componente_curricular
                            ├── Fase 5: matricula_turma_programa
                            ├── Fase 6: matricula_turma_programa_historico
                            ├── Fase 7: aluno_pap_ano_letivo
                            └── Fase 8: aluno_pap_ano_letivo_historico
```

## EtlProgramasService

Classe: `apps.programas.services.EtlProgramasService` — herda de
`apps.core.libs.base_etl_service.BaseEtlService`.

### Construção e injeção de dependência

```python
EtlProgramasService(
    db_alias: str,
    id_execucao: UUID | None = None,
    repositorio_auditoria: Any | None = None,
    primeiro_run: bool = False,
    eol: EOLService | None = None,
)
```

A assinatura espelha `BaseEtlService` e adiciona `eol`. O service injeta um
`EOLService` real por padrão — testes passam um mock.

Exemplo:

```python
# Produção — via BaseEtlCommand._handle_sync
service = EtlProgramasService(
    db_alias="programas_db",
    id_execucao=id_execucao,
    repositorio_auditoria=repositorio,
    primeiro_run=False,
)

# Testes
service = EtlProgramasService(db_alias="programas_db", eol=EOLServiceMock())
```

### Fases (`_init_fases`)

Retorna uma lista de `PhaseConfig` ordenada — cada entrada declara:

- `nome`, `sql`, `table_name`, `source_table`
- `model_class`, `dto_in`
- `pk_field`, `unique_fields`, `update_fields`
- `modo_escrita="upsert"`

A execução por fase é tratada pelo `BaseEtlService.executar()` — ele
itera as `PhaseConfig`, lê chunks via `_iter_chunks(sql)` (que internamente chama
`self.eol.iter_query(sql)`), aplica `dto_in.to_domain()` e chama
`_upsert_incremental` com a configuração da fase.

### Chunks da origem

```python
def _iter_chunks(self, sql: str) -> Iterator[list[tuple]]:
    return self.eol.iter_query(sql)
```

A leitura é feita em lotes pelo `EOLService` (cursor pyodbc).

## EtlProgramasOrquestrador

Classe: `apps.programas.orquestrador.EtlProgramasOrquestrador` — herda de
`apps.core.libs.base_etl_orquestrador.GenericEtlOrquestrador`. É a forma assíncrona
do pipeline:

```python
class EtlProgramasOrquestrador(GenericEtlOrquestrador):
    def __init__(self, **kwargs):
        kwargs.setdefault("dominio", "programas")
        kwargs.setdefault("service_class", EtlProgramasService)
        super().__init__(**kwargs)
```

As tasks Celery genéricas reaproveitadas:

```python
processar_chunk_programas = processar_chunk
finalizar_fase_programas = finalizar_fase
```

São aliases de `apps.core.tasks.processar_chunk` e `apps.core.tasks.finalizar_fase`
— expostos com nome de domínio para facilitar o roteamento via filas Celery por
domínio.

## Controle incremental por hash

Cada fase usa `_upsert_incremental`, que:

1. Calcula SHA-256 dos campos de conteúdo (`update_fields` sem o timestamp).
2. Consulta `EtlAuditoriaLinha` (banco `default`) para obter hashes anteriores.
3. Filtra apenas registros novos ou alterados.
4. Executa `bulk_create(update_conflicts=True)` no `programas_db`.
5. Atualiza `EtlAuditoriaLinha` com os novos hashes.

Ver {doc}`hash` para detalhes.

## Registro de auditoria

O comando `etl_programas` (via `BaseEtlCommand`) registra:

- `EtlExecucao` — início, fim, status e total de linhas alteradas.
- `EtlExecucaoTabelaLeitura` — linhas lidas por tabela do EOL.
- `EtlExecucaoTabelaEscrita` — linhas escritas por tabela destino,
  com `modo_escrita` definido por `Command.get_modo_escrita()`.
- `EtlCheckpoint` — fase atual para suporte a retomada.

## Exemplo de execução via API

```bash
# Execução imediata
curl -X POST http://localhost:8068/api/v1/dominios/programas/executar/ \
  -H "X-API-Key: sua_chave" \
  -H "Content-Type: application/json" \
  -d '{}'

# Agendada
curl -X POST http://localhost:8068/api/v1/dominios/programas/executar/ \
  -H "X-API-Key: sua_chave" \
  -H "Content-Type: application/json" \
  -d '{"executar_em": "2026-06-09T02:00:00-03:00"}'
```

## Exemplo de execução direta (dev)

```bash
docker exec sme_sgp_ms_etl_web_debug python manage.py etl_programas
docker exec sme_sgp_ms_etl_web_debug python manage.py etl_programas --continuar
```
