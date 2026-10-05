-- Cria os bancos do ETL se nao existirem.
-- Executar no postgres do docker-compose:
--   docker exec -i sme_sgp_ms_etl_postgres psql -U postgres < scripts/criar_bancos.sql

-- Banco default/auditoria. Nao faz DROP para preservar historico de execucoes,
-- checkpoints e hashes.
SELECT 'CREATE DATABASE etl_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'etl_db')\gexec

-- Drop com force (desconecta sessões ativas) antes de recriar.
SELECT 'DROP DATABASE IF EXISTS institucional_db WITH (FORCE)'\gexec
SELECT 'DROP DATABASE IF EXISTS professores_db WITH (FORCE)'\gexec
SELECT 'DROP DATABASE IF EXISTS alunos_db WITH (FORCE)'\gexec
SELECT 'DROP DATABASE IF EXISTS pedagogico_db WITH (FORCE)'\gexec
SELECT 'DROP DATABASE IF EXISTS programas_db WITH (FORCE)'\gexec

SELECT 'CREATE DATABASE institucional_db'\gexec
SELECT 'CREATE DATABASE professores_db'\gexec
SELECT 'CREATE DATABASE alunos_db'\gexec
SELECT 'CREATE DATABASE pedagogico_db'\gexec
SELECT 'CREATE DATABASE programas_db'\gexec
