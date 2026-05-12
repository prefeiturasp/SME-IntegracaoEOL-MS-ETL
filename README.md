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

## Verificação de Compatibilidade — Professores

Valida que o `professores_db` replica corretamente os dados do EOL para todas
as queries do `ProfessorController`, sem necessidade de INNER JOINs externos.

Cada verificador busca uma amostra de `--limite` linhas na origem (EolConnection/SQL Server),
consulta o equivalente no destino (professores_db/PostgreSQL) e compara os campos-chave.
Aprovação: ≥ 80% de correspondência por query.

### Pré-requisito

O `professores_db` deve ter dados. Use `--rodar-etl` para popular automaticamente
antes de verificar, ou execute o ETL separadamente:

```bash
docker exec sme_sgp_ms_etl_etl_auditoria python manage.py etl_professores
```

### Execução

Verificação simples (ETL já rodou):

```bash
docker exec sme_sgp_ms_etl_etl_auditoria \
  python manage.py compat_professores
```

Rodar ETL amostral (30 linhas) e verificar:

```bash
docker exec sme_sgp_ms_etl_etl_auditoria \
  python manage.py compat_professores --rodar-etl
```

Alterar tamanho da amostra:

```bash
docker exec sme_sgp_ms_etl_etl_auditoria \
  python manage.py compat_professores --rodar-etl --limite 50
```

Exibir exemplos de divergências nos verificadores reprovados:

```bash
docker exec sme_sgp_ms_etl_etl_auditoria \
  python manage.py compat_professores --detalhes
```

Salvar resultado completo em JSON:

```bash
docker exec sme_sgp_ms_etl_etl_auditoria \
  python manage.py compat_professores --saida resultado.json
```

Tudo junto:

```bash
docker exec sme_sgp_ms_etl_etl_auditoria \
  python manage.py compat_professores \
    --rodar-etl --limite 30 --detalhes --saida resultado.json
```

### Saída esperada

```
========================================================================
RELATÓRIO DE COMPATIBILIDADE — PROFESSORES_DB
========================================================================
[OK  ] FuncionarioRepository.BuscaFuncionarioPorRfAsync: 30/30 (100%) | destino=30
[OK  ] ProfessorRepository.VerificarValidadeProfessorAsync: 28/30 (93%) | destino=30
[IGNORADO] ProfessorRepository.BuscaProfessoresAsync_externo: sem dados na origem
...
========================================================================
Total: 12  OK: 10  FALHA: 0  IGNORADO: 2  ERRO: 0

✓ professores_db está COMPATÍVEL com EolConnection.
```

O comando retorna código de saída `0` se compatível ou `1` se algum verificador reprovar.

### Verificadores cobertos

| Verificador | Query do ProfessorController |
|---|---|
| `VerificadorCargoBaseAtivo` | `BuscaFuncionarioPorRfAsync` |
| `VerificadorValidadeProf` | `VerificarValidadeProfessorAsync` |
| `VerificadorAtribuicaoAula` | `BuscaProfessoresAsync` (servidor) |
| `VerificadorTitularServidor` | `BuscarProfessorTitularPorDisciplinaAsync` (servidor) |
| `VerificadorPerfilProfServidor` | `BuscarInformacoesPerfilProfAsync` (servidor) |
| `VerificadorAtribuicaoExterno` | `BuscaProfessoresAsync` (externo) |
| `VerificadorTitularExterno` | `BuscarProfessorTitularPorDisciplinaAsync` (externo) |
| `VerificadorPerfilProfExterno` | `BuscarInformacoesPerfilProf` (externo) |
| `VerificadorTurmaEscola` | `VerificaSeEhTurmaDeProgramaAsync` |
| `VerificadorTurmaEscolaGradePrograma` | `VerificaSeTemAtribuicaoNaTurmaDeProgramaNaDisciplina` |
| `VerificadorTerritorioReplicado` | `ObterComponentesCurricularesTerritorioAtribuidos` |
| `VerificadorTerritorioAtribuicao` | cadeia JOIN com `AtribuicaoAula` |

## Atalhos Make

Use `make help` para listar todos os comandos disponíveis. Os principais:

**Infraestrutura**

| Comando | Descrição |
|---|---|
| `make build` | Build da imagem `etl_auditoria` |
| `make up` | Sobe `postgres` e `keydb` em background |
| `make down` | Derruba todos os containers |
| `make logs` | Acompanha logs do `etl_auditoria` em tempo real |
| `make shell` | Abre shell Django interativo |

**Migrações**

| Comando | Descrição |
|---|---|
| `make migrate` | Aplica migrations com `--fake-initial` |

**ETL — execução direta (sem broker)**

| Comando | Descrição |
|---|---|
| `make etl-institucional` | ETL institucional completo (DRE + TipoEscola + SubPrefeitura + UE) |
| `make etl-institucional-ue` | Somente fase 4: `unidade_educacional` |
| `make etl-alunos` | ETL do domínio alunos |
| `make etl-pedagogico` | ETL do domínio pedagógico |
| `make etl-professores` | ETL do domínio professores |
| `make etl-programas` | ETL do domínio programas |
| `make etl` | Roda todos os domínios em sequência |

**ETL — agendamento via Celery (requer worker e broker ativos)**

| Comando | Descrição |
|---|---|
| `make agendar-institucional` | Enfileira ETL institucional na fila Celery |

**Qualidade**

| Comando | Descrição |
|---|---|
| `make test` | Roda testes com coverage (mínimo 80%) |
| `make lint` | Roda pre-commit nos arquivos do projeto |

## Testes

Executa testes no container via ambiente dev:

```bash
./executar_testes_docker.sh
```

O script executa cobertura com `coverage` e exige mínimo de `80%`.
