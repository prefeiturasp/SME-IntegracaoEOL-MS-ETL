DC = docker compose -f docker-compose-dev.yml
RUN = $(DC) run --rm etl_auditoria python manage.py

.PHONY: help build up down logs shell migrate \
        etl etl-institucional etl-alunos etl-pedagogico etl-professores etl-programas \
        agendar-institucional \
        test lint

help:
	@echo ""
	@echo "Uso: make <comando>"
	@echo ""
	@echo "Infraestrutura"
	@echo "  build                  Build da imagem etl_auditoria"
	@echo "  up                     Sobe postgres e keydb em background"
	@echo "  down                   Derruba todos os containers"
	@echo "  logs                   Acompanha logs do etl_auditoria em tempo real"
	@echo "  shell                  Abre shell Django interativo"
	@echo ""
	@echo "Migrações"
	@echo "  migrate                Aplica migrations (fake-initial)"
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
	@echo "  agendar-institucional  Enfileira ETL institucional na fila Celery"
	@echo ""
	@echo "Qualidade"
	@echo "  test                   Roda testes com coverage (mínimo 80%)"
	@echo "  lint                   Roda pre-commit nos arquivos do projeto"
	@echo ""

# ------------------------------------------------------------
# Infraestrutura
# ------------------------------------------------------------

build:
	$(DC) build etl_auditoria

up:
	$(DC) up -d postgres keydb

down:
	$(DC) down

logs:
	$(DC) logs -f etl_auditoria

shell:
	$(DC) run --rm etl_auditoria python manage.py shell

# ------------------------------------------------------------
# Migrações
# ------------------------------------------------------------

migrate:
	$(RUN) migrate --noinput --fake-initial

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

agendar-institucional:
	$(RUN) agendar_dominio --dominio institucional

# ------------------------------------------------------------
# Qualidade
# ------------------------------------------------------------

test:
	bash executar_testes_docker.sh

lint:
	$(DC) run --rm etl_auditoria bash executar_precommit.sh
