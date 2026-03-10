## Visão Geral

**SME-SGP-MS-ETL** — Microsserviço de integração e sincronização de dados provenientes do ambiente legado EOL (Escola Online) para bancos PostgreSQL e cache KeyDB.

Requer Python >= 3.12.

## Comandos de Desenvolvimento

### Configuração do Ambiente

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements/local.txt
pip install -e .
pre-commit install
```

### Qualidade de Código

```bash
black .                        # formata o código (79 caracteres por linha)
isort .                        # ordena os imports
ruff check .                   # lint
mypy .                         # checagem de tipos (modo strict)
pre-commit run --all-files     # executa todas as verificações de uma vez
```

### Execução

```bash
python src/sme_pedagogico_etl/main.py
```

### Worker Celery

```bash
celery -A sme_pedagogico_etl.config.celery_app:celery_app worker --loglevel=info
```

## Arquitetura

Microsserviço ETL batch e assíncrono. Não expõe APIs públicas. Opera exclusivamente em leitura sobre as réplicas do EOL.

**Fluxo principal:**
1. `ETLJobController` — ponto único de entrada do processo batch
2. `LeitorEOLService` — leitura incremental do banco legado EOL (SQL Server, somente leitura)
3. `ETLTaskPublisher` — publica tarefas no broker KeyDB desacoplando leitura de escrita
4. `Celery Worker` — processa tarefas de forma distribuída e paralela
5. `UpsertTables` / `DataRepository` — persistência idempotente nas bases PostgreSQL destino
6. `SincRecordService` — auditoria e rastreabilidade da execução

**Bancos de dados:**
- Origem: **EOL/SE1426** (SQL Server, réplica somente leitura — Cimarron)
- Broker/Cache: **KeyDB** (compatível com Redis, DB 0 = broker, DB 1 = resultados)
- Destino: múltiplos bancos **PostgreSQL** por domínio (`ALUNO_DB`, `PROFESSORES_DB`, `INSTITUCIONAL_DB`, `PEDAGOGICO_DB`, `PROGRAMAS_DB`, `SINC_REC_DB`)

**Modelos de dados:**
- `Model_IN` — estrutura dos dados conforme o legado EOL
- `Model_OUT` — dados transformados alinhados ao domínio do Novo Web Pedagógico

As variáveis de ambiente estão definidas em `.env.example` — copie para `.env` antes de executar.

### Estrutura do Código-Fonte

```
src/sme_pedagogico_etl/
├── config/
│   ├── settings.py       # configurações centralizadas (env vars)
│   └── celery_app.py     # instância e configuração do Celery
├── worker/
│   ├── publisher.py      # ETLTaskPublisher — publica tarefas no KeyDB
│   └── tasks.py          # tarefas Celery (processar_registro)
└── main.py               # ponto de entrada da aplicação
```

## Padrões de Código

- Comprimento de linha: **79 caracteres** (Black + isort + Ruff)
- Docstrings: **estilo Google** (imposto pelas regras `D` do Ruff)
- Type hints: **obrigatórios em todo o código** (MyPy modo strict)
- Pre-commit hooks aplicam Black, isort, Ruff e MyPy antes de cada commit
