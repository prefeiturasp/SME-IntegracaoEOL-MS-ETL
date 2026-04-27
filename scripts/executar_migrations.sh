#!/bin/sh
# Gera e aplica migrations para todos os bancos destino do ETL.
# Executar dentro do container: docker exec sme_sgp_ms_etl_web_debug sh scripts/executar_migrations.sh
# Ou localmente com o venv ativo.

set -e

echo "==> makemigrations para todos os apps de dominio"
python manage.py makemigrations institucional professores alunos pedagogico programas

echo "==> migrate banco default (controle_auditoria, auth, etc.)"
python manage.py migrate

echo "==> migrate institucional_db"
python manage.py migrate --database=institucional_db

echo "==> migrate professores_db"
python manage.py migrate --database=professores_db

echo "==> migrate alunos_db"
python manage.py migrate --database=alunos_db

echo "==> migrate pedagogico_db"
python manage.py migrate --database=pedagogico_db

echo "==> loaddata pedagogico_db"
python manage.py loaddata componente_curricular_pap regencia_componente_curricular --database=pedagogico_db

echo "==> migrate programas_db"
python manage.py migrate --database=programas_db

echo "==> Migrations concluidas."
