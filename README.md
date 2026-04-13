# SME-IntegracaoEOL-MS-ETL

Microsserviço ETL em Django com execução assíncrona via Celery, usando KeyDB
como broker.

## Versão de Python

- Python alvo do projeto: `3.12`

## Regra de Execução

- O ETL não executa sozinho na inicialização.
- Toda execução deve ser registrada na fila Celery/KeyDB (imediata ou agendada).
- O serviço `etl` atua como worker Celery.

## Compose

- `docker-compose.yml` (base):
  - `keydb`, `etl`, `web`
- `docker-compose-dev.yml` (desenvolvimento):
  - `postgres`, `keydb`, `etl`, `etl_auditoria`

## Subir Ambiente

Base:

```bash
docker compose up --build -d
docker compose exec web python manage.py migrate --noinput --fake-initial
```

Desenvolvimento:

```bash
docker compose -f docker-compose-dev.yml up --build -d
docker compose -f docker-compose-dev.yml exec etl_auditoria \
  python manage.py migrate --noinput --fake-initial
```

## Bancos de Dados (dev)

Após subir o ambiente de desenvolvimento, crie os bancos e aplique as migrations:

```bash
# Recriar containers com o .env atualizado
docker compose -f docker-compose-dev.yml up -d --force-recreate

# Criar os bancos (se ainda não existirem)
docker exec -i sme_sgp_ms_etl_postgres psql -U postgres < scripts/criar_bancos.sql

# Rodar migrations
docker exec sme_sgp_ms_etl_auditoria sh scripts/executar_migrations.sh
```

> Os URLs dos bancos no `.env` devem usar o nome do serviço Docker `postgres` (porta `5432`), não `localhost`.
> O mapeamento `5438:5432` no docker-compose é apenas para acesso externo do host.

## Admin

Base:

```bash
docker compose sme_sgp_ms_etl_auditoria python manage.py createsuperuser
```

Dev:

```bash
docker compose -f docker-compose-dev.yml exec etl_auditoria \
  python manage.py createsuperuser
```

- URL: `http://localhost:8000/admin`

## API e Swagger

- Swagger UI: `http://localhost:8000/api/v1/docs/`
- Schema: `http://localhost:8000/api/v1/schema/`

Autenticação via API key:

- Header: `X-API-Key`
- Valor: variável `API_KEY` no `.env`

Exemplo:

```bash
curl -H "X-API-Key: sua_chave" http://localhost:8000/api/v1/checkpoints/
```

## Enfileirar Execução

### Via API

Endpoint:

- `POST /api/v1/dominios/{dominio}/executar/`

Payload imediato:

```json
{
  "volume": 100,
  "offset": 0,
  "continuar": true
}
```

Payload agendado:

```json
{
  "volume": 100,
  "offset": 0,
  "continuar": true,
  "executar_em": "2026-03-10T23:00:00-03:00"
}
```

### Via command

Imediato:

```bash
docker compose exec web python manage.py agendar_dominio \
  --dominio institucional --volume 100 --continuar
```

Agendado:

```bash
docker compose exec web python manage.py agendar_dominio \
  --dominio institucional --volume 100 --continuar \
  --executar-em 2026-03-10T23:00:00-03:00
```

### Domínio Professores

O domínio `professores` usa o endpoint genérico de execução. O agendamento passa pela
fila Celery e executa o ETL completo do `professores_db`.

Cadeia de execução:

```
POST /api/v1/dominios/professores/executar/
  → executar_dominio_task (Celery)
  → management command: executar_dominio --dominio professores
  → management command: etl_professores
  → EtlProfessoresService.executar()
```

Execução imediata via API:

```bash
curl -X POST http://localhost:8068/api/v1/dominios/professores/executar/ \
  -H "X-API-Key: sua_chave" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Execução agendada via API:

```bash
curl -X POST http://localhost:8068/api/v1/dominios/professores/executar/ \
  -H "X-API-Key: sua_chave" \
  -H "Content-Type: application/json" \
  -d '{"executar_em": "2026-03-23T23:00:00-03:00"}'
```

Resposta:

```json
{ "task_id": "abc123-..." }
```

Execução direta via command (dev):

```bash
docker exec sme_sgp_ms_etl_auditoria python manage.py etl_professores
```

## Debug (dev)

```bash
docker compose -f docker-compose-dev.yml up --build -d etl_auditoria
```

- App: `http://localhost:8000`
- Debug attach: `localhost:5678`

## Documentação (Sphinx)

Gera a documentação HTML a partir dos arquivos em `docs/`:

```bash
docker compose -f docker-compose-dev.yml run --rm etl_auditoria \
  sphinx-build -b html docs docs/_build
```

Gera a documentação PDF a partir dos arquivos em `docs/`:

```bash
docker compose -f docker-compose-dev.yml run --rm etl_auditoria \
  sh -c "sphinx-build -b latex docs docs/_build/latex && make -C docs/_build/latex"
```

O resultado fica em `docs/_build/index.html` (acessível no host via volume).

## Testes

Executa testes no container via ambiente dev:

```bash
./executar_testes_docker.sh
```

O script executa cobertura com `coverage` e exige mínimo de `80%`.
