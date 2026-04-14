# Visão Geral — Domínio Programas

O domínio **Programas** consolida os dados dos programas de apoio da rede municipal —
**PAP** (Programa de Apoio Pedagógico) e **PAEE** (Programa de Atendimento Educacional
Especializado / SRM) — extraídos do EOL (SQL Server) e persistidos no banco
`programas_db` (PostgreSQL).

## Banco de dados

| Parâmetro | Valor |
|-----------|-------|
| Alias Django | `programas_db` |
| Variável de ambiente | `URL_BANCO_PROGRAMAS` |
| App label | `programas` |
| Router | `DominioRouter` em `config/db_router.py` |

## Modelos

| Modelo | Tabela | Tipo de carga |
|--------|--------|---------------|
| `TipoPrograma` | `tipo_programa` | Seed (estático) |
| `ComponenteCurricularPrograma` | `componente_curricular_programa` | Seed (estático) |
| `TurmaPrograma` | `turma_programa` | ETL incremental |
| `TurmaProgramaComponenteCurricular` | `turma_programa_componente_curricular` | ETL incremental |
| `MatriculaTurmaPrograma` | `matricula_turma_programa` | ETL incremental |

## Categorias

O campo `categoria` (`"PAP"` ou `"PAEE"`) aparece em três modelos
(`TipoPrograma`, `TurmaPrograma`, `MatriculaTurmaPrograma`) e é desnormalizado para
permitir filtros diretos sem JOIN.

## Referências cruzadas

Nenhum modelo usa `ForeignKey` física. Todas as referências a outros bancos
são FK lógicas, com integridade garantida pela ordem de carga do ETL.

| Campo | Destino lógico | Banco |
|-------|---------------|-------|
| `codigo_turma` | `turma_programa.codigo_turma` | mesmo banco |
| `codigo_componente_curricular` | `componente_curricular_programa` | mesmo banco |
| `codigo_aluno` | `aluno.codigo_aluno` | `PEDAGOGICO_DB` |
| `codigo_ue` / `codigo_dre` | escola / unidade administrativa | `PEDAGOGICO_DB` |

## Componentes do domínio

| Módulo | Responsabilidade |
|--------|------------------|
| `apps/programas/models.py` | 5 modelos persistidos no `programas_db` |
| `apps/programas/enums.py` | Enums centralizando constantes do EOL (PAP/PAEE, situação de turma, situação de matrícula). Ver {doc}`enums` |
| `apps/programas/dtos/model_in.py` | Dataclasses que mapeiam posicionalmente as tuplas brutas do cursor pyodbc |
| `apps/programas/dtos/model_out.py` | Proxy models com `from_in()` — centraliza strip, conversão e derivação de categoria/descricao via enums |
| `apps/programas/services.py` | `EtlProgramasService` — 5 fases com `_upsert_incremental` por hash SHA-256 |
| `apps/programas/management/commands/etl_programas.py` | Comando Django herdando de `BaseEtlCommand` |
| `apps/programas/api/views.py` | `HealthProgramasView` — health check do banco `programas_db` |
| `apps/programas/api/urls.py` | Rota `GET /api/v1/programas/health/` |

## Health check

```bash
curl http://localhost:8068/api/v1/programas/health/
```

- `200 OK` com `{"status": "healthy"}` — quando `URL_BANCO_PROGRAMAS` está setada e o banco responde
- `503 Service Unavailable` com `{"status": "unhealthy"}` — sem a variável ou com erro de conexão

## Endpoints cobertos

| Endpoint (Pedagogico-API) | Modelo(s) principal(is) |
|---------------------------|------------------------|
| `turmas-pap/{anoLetivo}/ues/{codigoEscola}` | `TurmaPrograma` |
| `srm-paee/aluno/{codigoAluno}` | `MatriculaTurmaPrograma` |
| `paee/turma-srm-e-regular/aluno/{cod}` | `MatriculaTurmaPrograma` |
| `alunos-pap/{anoLetivo}` | `MatriculaTurmaPrograma` |
| `pap/ano-letivo/{anoLetivo}` | `MatriculaTurmaPrograma` |
| `{codigoAluno}/turmas-programa/{anoLetivo}/componentes-curriculares` | `TurmaProgramaComponenteCurricular` |
