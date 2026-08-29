DC = docker compose -f docker-compose-dev.yml
RUN = $(DC) run --rm etl_auditoria python manage.py
RUN_SH = $(DC) run --rm etl_auditoria sh

.PHONY: help build up down logs shell setup-db migrate migrate-all createsuperuser \
        etl etl-institucional etl-alunos etl-pedagogico etl-professores etl-programas \
        agendar agendar-institucional agendar-programas disparar-anos disparar-anos-dry-run recovery \
        docs-html docs-pdf test lint check

help:
	@echo ""
	@echo "Uso: make <comando>"
	@echo ""
	@echo "Infraestrutura"
	@echo "  build                  Build da imagem etl_auditoria"
	@echo "  up                     Sobe ambiente dev em background"
	@echo "  down                   Derruba todos os containers"
	@echo "  logs                   Acompanha logs do etl_auditoria em tempo real"
	@echo "  shell                  Abre shell Django interativo"
	@echo ""
	@echo "Migrações"
	@echo "  setup-db               Cria bancos locais do ETL"
	@echo "  migrate                Aplica migrations (fake-initial)"
	@echo "  migrate-all            Gera e aplica migrations em todos os bancos"
	@echo "  createsuperuser        Cria superusuário Django"
	@echo ""
	@echo "ETL — execução direta (sem broker)"
	@echo "  etl-institucional      ETL institucional completo (DRE + TipoEscola + SubPrefeitura + UE)"
	@echo "  etl-institucional-ue   Somente fase 4: unidade_educacional"
	@echo "  etl-alunos             ETL do domínio alunos"
	@echo "  etl-pedagogico         ETL do domínio pedagógico"
	@echo "  etl-professores        ETL do domínio professores"
	@echo "  etl-programas          ETL do domínio programas"
	@echo "  etl                    Roda todos os domínios em sequência"
	@echo ""
	@echo "ETL — agendamento via Celery (requer worker e broker ativos)"
	@echo "  agendar                Enfileira domínio. Uso: make agendar DOMINIO=programas"
	@echo "  agendar-institucional  Enfileira ETL institucional na fila Celery"
	@echo "  agendar-programas      Enfileira ETL programas na fila Celery"
	@echo "  disparar-anos          Dispara cron manual por anos letivos"
	@echo "  disparar-anos-dry-run  Simula disparo por anos letivos"
	@echo "  recovery               Executa recovery de execuções interrompidas"
	@echo ""
	@echo "Documentação"
	@echo "  docs-html              Gera documentação HTML"
	@echo "  docs-pdf               Gera documentação PDF"
	@echo ""
	@echo "Qualidade"
	@echo "  check                  Roda django check"
	@echo "  test                   Roda testes com coverage (mínimo 80%)"
	@echo "  lint                   Roda pre-commit nos arquivos do projeto"
	@echo ""

# ------------------------------------------------------------
# Infraestrutura
# ------------------------------------------------------------

build:
	$(DC) build etl_auditoria

up:
	$(DC) up --build -d

down:
	$(DC) down

logs:
	$(DC) logs -f etl_auditoria

shell:
	$(DC) run --rm etl_auditoria python manage.py shell

# ------------------------------------------------------------
# Migrações
# ------------------------------------------------------------

setup-db:
	$(DC) up -d postgres
	$(DC) exec -T postgres sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' < scripts/criar_bancos.sql

migrate:
	$(RUN) migrate --noinput --fake-initial

migrate-all:
	$(RUN_SH) scripts/executar_migrations.sh

createsuperuser:
	$(RUN) createsuperuser

# ------------------------------------------------------------
# ETL — execução direta (sem broker)
# ------------------------------------------------------------

etl-institucional:
	$(RUN) etl_institucional

etl-institucional-ue:
	$(RUN) etl_institucional --fase 4

etl-alunos:
	$(RUN) etl_alunos

etl-pedagogico:
	$(RUN) etl_pedagogico

etl-professores:
	$(RUN) etl_professores

etl-programas:
	$(RUN) etl_programas

etl: etl-institucional etl-alunos etl-pedagogico etl-professores etl-programas

# ------------------------------------------------------------
# ETL — agendamento via Celery (requer worker e broker ativos)
# ------------------------------------------------------------

agendar:
	@test -n "$(DOMINIO)" || \
		(echo "Informe DOMINIO. Ex.: make agendar DOMINIO=programas" >&2; exit 1)
	$(RUN) agendar_dominio --dominio $(DOMINIO) --continuar

agendar-institucional:
	$(RUN) agendar_dominio --dominio institucional

agendar-programas:
	$(RUN) agendar_dominio --dominio programas --continuar

disparar-anos:
	bash scripts/disparar_etl_anos_letivos.sh

disparar-anos-dry-run:
	ETL_DRY_RUN=true bash scripts/disparar_etl_anos_letivos.sh

recovery:
	bash scripts/recuperar_etl.sh

# ------------------------------------------------------------
# Documentação
# ------------------------------------------------------------

docs-html:
	$(RUN_SH) -lc 'sphinx-build -b html docs docs/_build'

docs-pdf:
	$(RUN_SH) -lc 'sphinx-build -b latex docs docs/_build/latex && make -C docs/_build/latex'

# ------------------------------------------------------------
# Qualidade
# ------------------------------------------------------------

check:
	$(RUN) check

test:
	bash executar_testes_docker.sh

lint:
	$(DC) run --rm etl_auditoria bash executar_precommit.sh
