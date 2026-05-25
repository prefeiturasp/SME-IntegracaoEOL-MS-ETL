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
| `TipoPrograma` | `tipo_programa` | Seed/configuração (upsert) |
| `ComponenteCurricularPrograma` | `componente_curricular_programa` | Seed/configuração (upsert) |
| `TurmaPrograma` | `turma_programa` | ETL incremental (upsert) |
| `TurmaProgramaComponenteCurricular` | `turma_programa_componente_curricular` | ETL incremental (upsert) |
| `MatriculaTurmaPrograma` | `matricula_turma_programa` | ETL incremental (upsert) |
| `MatriculaTurmaProgramaHistorico` | `matricula_turma_programa_historico` | ETL incremental (upsert) |
| `AlunoPapAnoLetivo` | `aluno_pap_ano_letivo` | ETL incremental (upsert, pré-agregado live) |
| `AlunoPapAnoLetivoHistorico` | `aluno_pap_ano_letivo_historico` | ETL incremental (upsert, pré-agregado histórico) |

> `MatriculaTurmaPrograma` e `MatriculaTurmaProgramaHistorico` compartilham a classe
> abstrata `MatriculaTurmaProgramaBase` em `apps/programas/models.py`.

## Categorias

O campo `categoria` (`"PAP"`, `"PAEE"` ou `"OUTROS"`) aparece em quatro modelos
(`TipoPrograma`, `ComponenteCurricularPrograma`, `TurmaPrograma`,
`MatriculaTurmaPrograma` / `MatriculaTurmaProgramaHistorico`) e é desnormalizado
para permitir filtros diretos sem JOIN.

A derivação de categoria difere por modelo:

- **`TipoPrograma`**: via `TipoProgramaEOL.categoria_por_sigla(sigla, descricao)`
  (varre as strings em busca de `"PAEE"`/`"SRM"` ou `"PAP"`).
- **`ComponenteCurricularPrograma`** e matrículas: via
  `ComponenteCurricularEOL.categoria(cd_componente_curricular)`.
- **`TurmaPrograma`**: resolvida diretamente na SQL (`CASE WHEN`) cruzando os
  componentes curriculares vinculados à turma (PAEE se existir o componente
  `PAEE_SALA_RECURSOS_MULTIFUNCIONAIS`; senão PAP se houver algum componente
  PAP conhecido; caso contrário `OUTROS`).

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
| `apps/programas/models.py` | 8 modelos persistidos no `programas_db` (5 concretos + 1 abstrato base + 2 pré-agregados) |
| `apps/programas/enums.py` | Enums centralizando constantes do EOL — `CategoriaPrograma`, `TipoProgramaEOL`, `ComponenteCurricularEOL`, `SituacaoTurma`, `SituacaoMatricula`. Ver {doc}`enums` |
| `apps/programas/dtos/model_in.py` | Dataclasses (`@dataclass(slots=True)`) que mapeiam posicionalmente as tuplas brutas do cursor e expõem `to_domain()` — centraliza strip, conversão de tipos e derivação de categoria/descricao via enums |
| `apps/programas/services.py` | `EtlProgramasService` — herda de `BaseEtlService` e define 8 fases via `PhaseConfig` com `modo_escrita="upsert"` |
| `apps/programas/orquestrador.py` | `EtlProgramasOrquestrador` — herda de `GenericEtlOrquestrador` (Celery, async) |
| `apps/programas/management/commands/etl_programas.py` | Comando Django herdando de `BaseEtlCommand` (síncrono ou Celery) |
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
| `alunos-pap/{anoLetivo}` | `AlunoPapAnoLetivo` / `AlunoPapAnoLetivoHistorico` |
| `pap/ano-letivo/{anoLetivo}` | `AlunoPapAnoLetivo` / `AlunoPapAnoLetivoHistorico` |
| `{codigoAluno}/turmas-programa/{anoLetivo}/componentes-curriculares` | `TurmaProgramaComponenteCurricular` |
