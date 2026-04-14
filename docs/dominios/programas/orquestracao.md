# Orquestração do ETL — Domínio Programas

## Fluxo geral

```
API (POST /executar/)
    └── Task Celery
            └── management command etl_programas
                    └── EtlProgramasService.executar()
                            ├── Fase 1: popular_tipos_programa()
                            ├── Fase 2: popular_componentes_curriculares()
                            ├── Fase 3: popular_turmas_programa()
                            ├── Fase 4: popular_turmas_programa_componentes()
                            └── Fase 5: popular_matriculas_turma_programa()
```

## EtlProgramasService

Classe: `apps.programas.services.EtlProgramasService`

### Método `executar(fase_inicial=1)`

Executa as fases em sequência a partir de `fase_inicial`. Retorna um dicionário
`{tabela: total_alterado}` com o número de linhas escritas em cada fase.

```python
resultados = service.executar(fase_inicial=1)
# → {"tipo_programa": 5, "componente_curricular_programa": 10,
#    "turma_programa": 320, "turma_programa_componente_curricular": 640,
#    "matricula_turma_programa": 1800}
```

O atributo `ultima_fase_concluida` é atualizado ao final de cada fase — usado pelo
comando para registrar o checkpoint de retomada.

### Assinatura e injeção de dependência

A assinatura do `__init__` espelha `BaseEtlService` para compatibilizar com
`BaseEtlCommand._handle_sync`, mas o service é síncrono próprio (não herda).

```python
EtlProgramasService(
    db_alias: str = "programas_db",
    id_execucao: UUID | None = None,
    repositorio_auditoria: Any | None = None,
    primeiro_run: bool = False,
    eol: EOLService | None = None,
)
```

Exemplos:

```python
# Produção — via BaseEtlCommand._handle_sync
service = EtlProgramasService(
    db_alias="programas_db",
    id_execucao=id_execucao,
    repositorio_auditoria=repositorio,
    primeiro_run=False,
)

# Testes
service = EtlProgramasService(eol=EOLServiceMock())
```

Atributos expostos para o contrato com `BaseEtlCommand`:

- `ultima_fase_concluida: int` — atualizado ao fim de cada fase
- `ultimo_token: str | None` — inicializado em `None`
- `_fases: list[_FaseInfo]` — 5 posições com `.table_name` para o finalizador da auditoria

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
  com `modo_escrita="upsert"` para todas as tabelas do domínio (todas estão em
  `_TABELAS_UPSERT` no `etl_programas.py`).
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
  -d '{"executar_em": "2026-04-09T02:00:00-03:00"}'
```

## Exemplo de execução direta (dev)

```bash
docker exec sme_sgp_ms_etl_web_debug python manage.py etl_programas --volume 500
docker exec sme_sgp_ms_etl_web_debug python manage.py etl_programas --volume 500 --continuar
```
