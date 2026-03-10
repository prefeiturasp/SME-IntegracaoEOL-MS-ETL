# SME-SGP-MS-ETL

Microsserviço ETL em Django com execução assíncrona via Celery, usando KeyDB
como broker.

## Regra de Execução

- O ETL não executa sozinho na inicialização.
- Toda execução deve ser registrada na fila Celery/KeyDB (imediata ou agendada).
- O serviço `etl` atua como worker Celery.

## Compose

- `docker-compose.yml` (base):
  - `keydb`, `etl`, `web`
- `docker-compose-dev.yml` (desenvolvimento):
  - `postgres`, `keydb`, `etl`, `web_debug`

## Subir Ambiente

Base:

```bash
docker compose up --build -d
docker compose exec web python manage.py migrate --noinput --fake-initial
```

Desenvolvimento:

```bash
docker compose -f docker-compose-dev.yml up --build -d
docker compose -f docker-compose-dev.yml exec web_debug \
  python manage.py migrate --noinput --fake-initial
```

## Admin

Base:

```bash
docker compose exec web python manage.py createsuperuser
```

Dev:

```bash
docker compose -f docker-compose-dev.yml exec web_debug \
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
  --dominio escola --volume 100 --continuar
```

Agendado:

```bash
docker compose exec web python manage.py agendar_dominio \
  --dominio escola --volume 100 --continuar \
  --executar-em 2026-03-10T23:00:00-03:00
```

## Debug (dev)

```bash
docker compose -f docker-compose-dev.yml up --build -d web_debug
```

- App: `http://localhost:8000`
- Debug attach: `localhost:5678`

## Testes

Executa testes no container via ambiente dev:

```bash
./executar_testes_docker.sh
```
