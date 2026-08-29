# SME-IntegracaoEOL-MS-ETL

Microsserviço ETL em Django para sincronizar dados do EOL em bancos de domínio,
com execução assíncrona via Celery e KeyDB.

## Requisitos

- Python `3.12`
- Docker e Docker Compose
- `.env` configurado com conexões dos bancos, KeyDB e `API_KEY`

## Como o ETL executa

- O ETL não executa sozinho ao subir a aplicação.
- Execuções operacionais devem ser enfileiradas no Celery/KeyDB, de forma
  imediata ou agendada.
- O serviço `etl_auditoria_worker` processa a fila.
- O serviço `etl_auditoria` expõe API, Swagger, admin e dashboards.

## Serviços Docker

`docker-compose.yml`:

- `keydb`
- `etl_auditoria_worker`
- `etl_auditoria`

`docker-compose-dev.yml`:

- `postgres`
- `keydb`
- `etl_auditoria_worker`
- `etl_auditoria`

## Subir ambiente dev

```bash
make up
```

Crie os bancos e aplique as migrations:

```bash
make setup-db
make migrate-all
```

No ambiente Docker dev, os hosts de banco no `.env` devem apontar para o
serviço `postgres` na porta `5432`. O mapeamento `5438:5432` serve apenas para
acesso externo a partir do host.

## URLs úteis

Dev:

- App/admin: `http://localhost:8068/admin`
- Swagger UI: `http://localhost:8068/api/v1/docs/`
- Schema OpenAPI: `http://localhost:8068/api/v1/schema/`
- Kanban ETL: `http://localhost:8068/dashboard/kanban/`
- Debug attach: `localhost:5668`

Base:

- App/admin: `http://localhost:8000/admin`
- Swagger UI: `http://localhost:8000/api/v1/docs/`
- Schema OpenAPI: `http://localhost:8000/api/v1/schema/`

## API

A API usa autenticação por API key:

- Header: `X-API-Key`
- Valor: variável `API_KEY` no `.env`

Exemplo:

```bash
curl -H "X-API-Key: sua_chave" \
  http://localhost:8068/api/v1/checkpoints/
```

## Enfileirar ETL

Endpoint genérico:

```text
POST /api/v1/dominios/{dominio}/executar/
```

Exemplo imediato:

```bash
curl -X POST http://localhost:8068/api/v1/dominios/programas/executar/ \
  -H "X-API-Key: sua_chave" \
  -H "Content-Type: application/json" \
  -d '{"anos_letivos": [2026], "continuar": true}'
```

Exemplo agendado:

```bash
curl -X POST http://localhost:8068/api/v1/dominios/programas/executar/ \
  -H "X-API-Key: sua_chave" \
  -H "Content-Type: application/json" \
  -d '{"anos_letivos": [2026], "continuar": true, "executar_em": "2026-03-10T23:00:00-03:00"}'
```

Parâmetros principais:

| Campo | Padrão | Uso |
|---|---:|---|
| `continuar` | `false` | Retoma pelo checkpoint do domínio quando `true` |
| `prioridade` | `5` | Prioridade da task: `0` mais urgente, `9` menos urgente |
| `fases` | `null` | Lista opcional de fases |
| `anos_letivos` | `null` | Lista opcional de anos letivos, para domínios/fases compatíveis |
| `executar_em` | `null` | Data/hora ISO 8601 para agendamento |

Também é possível enfileirar via management command:

```bash
make agendar DOMINIO=programas
```

## Cron por ano letivo

O script `scripts/disparar_etl_anos_letivos.sh` enfileira os domínios pela API
e calcula os anos letivos pela data de referência:

- diariamente: ano vigente;
- dia 8: ano vigente e ano anterior;
- dia 15: ano vigente e dois anos atrás;
- dia 22: ano vigente e três anos atrás;
- dia 29: ano vigente e quatro anos atrás.

Simulação:

```bash
ETL_DRY_RUN=true ETL_DATA_REFERENCIA=2026-08-15 \
  scripts/disparar_etl_anos_letivos.sh
```

Exemplo de cron com trava para evitar sobreposição:

```cron
0 2 * * * flock -n /tmp/sme-sgp-ms-etl.lock /app/scripts/disparar_etl_anos_letivos.sh >> /var/log/sme-sgp-ms-etl-cron.log 2>&1
```

Para anos anteriores ao quarto ano, configure uma janela periódica:

```bash
ETL_ANO_MINIMO_ANTERIORES=2020 ETL_INTERVALO_MESES_ANTERIORES=3 \
  scripts/disparar_etl_anos_letivos.sh
```

## Recovery

O script `scripts/recuperar_etl.sh` executa o fluxo de recuperação:

1. chama `POST /api/v1/execucoes/limpar-orfas/`;
2. marca como `interrompido` execuções sem task viva no Celery;
3. chama `POST /api/v1/execucoes/retomar/`;
4. retoma a última execução interrompida de cada domínio com `continuar=true`.

Exemplo de cron:

```cron
*/30 * * * * cd /app && ./scripts/recuperar_etl.sh >> /var/log/sme-sgp-ms-etl-recovery.log 2>&1
```

## Comandos úteis

```bash
make help
make up
make migrate
make etl-programas
make agendar-institucional
make test
make lint
```

Execução direta de domínio em dev:

```bash
make etl-programas
```

Criar superusuário:

```bash
make createsuperuser
```

## Documentação

Gerar HTML com Sphinx:

```bash
make docs-html
```

Gerar PDF:

```bash
make docs-pdf
```

Referências principais:

- [API de auditoria](docs/auditoria/api.md)
- [Tasks de auditoria](docs/auditoria/tasks.md)
- [Manutenção da auditoria](docs/auditoria/manutencao.md)
- [Compatibilidade do domínio professores](docs/dominios/professores/compatibilidade.md)

## Testes

```bash
./executar_testes_docker.sh
```

O script executa cobertura com `coverage` e exige mínimo de `80%`.
