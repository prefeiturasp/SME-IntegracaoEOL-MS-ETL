-- Cria os bancos destino do ETL se nao existirem.
-- Executar no postgres do docker-compose:
--   docker exec -i sme_sgp_ms_etl_postgres psql -U postgres < scripts/criar_bancos.sql

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
