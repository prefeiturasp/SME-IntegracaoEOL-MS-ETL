# Mapeamento do ETL Pedagógico

Resumo de origem e destino por fase. As fases com origem no EOL SQL Server usam `EOLService`; as fases com origem na API EOL PostgreSQL usam `API_EOL_DB`.

---

## Fase 1 — ComponenteCurricular

**Query:** `SQL_COMPONENTES_NAO_CANCELADOS` (sem parâmetro de ano)

| Campo EOL | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `cd_componente_curricular` | `codigo` | `int()` |
| `dc_componente_curricular` | `descricao` | `strip_str()` |
| CASE sobre `_IDS_REGENCIA` | `regencia` | `bool()` |
| — | `transferido_em` | `timezone.now()` |

---

## Fase 2 — ComponenteTurma

**Query:** `SQL_COMPONENTE_TURMA` (parâmetro `?` por ano letivo)

Estrutura turma × componente, sem professor e sem regra de planejamento.
Serve para dizer quais componentes existem em cada turma real do EOL. Para
componentes de Território do Saber, também materializa a descrição contextual
da turma, porque essa descrição vem da grade de território/experiência e não do
catálogo base `componente_curricular`.

| Campo Origem | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `cd_turma_escola` | `turma_codigo` | `str()` ou `None` |
| `cd_componente_curricular` | `componente_codigo` | `int()` |
| presença em `turma_grade_territorio_experiencia` | `codigo_componente_territorio_saber` | código do componente ou `None` |
| `território_saber.dc_territorio_saber` | `desc_territorio_saber` | texto contextual do território ou `None` |
| `tipo_experiencia_pedagogica.dc_experiencia_pedagogica` | `desc_experiencia_pedagogica` | texto contextual da experiência ou `None` |
| — | `transferido_em` | `timezone.now()` |

Quando `codigo_componente_territorio_saber` está preenchido, o MS Pedagógico
usa esses campos para compor a descrição exibida: `desc_territorio_saber -
desc_experiencia_pedagogica`. Se a experiência pedagógica estiver ausente,
usa apenas `desc_territorio_saber`.

---

## Fase 3 — AtribuicaoComponente

**Query:** `SQL_ATRIBUICAO_COMPONENTE` (parâmetro `?` por ano letivo)

Relação professor × turma × componente. A query une atribuições SME e externas,
ativas e históricas, excluindo motivo de disponibilização `26`.

Branches contemplados:

- SME ativo por série.
- SME ativo por programa explícito.
- SME ativo por programa via `escola_grade`.
- Externo ativo por série.
- Externo ativo por programa.
- SME liberado por disponibilização.
- Externo liberado por disponibilização.

Todos os branches consideram turmas com situação `O`, `A`, `C` ou `E`.
Registros externos são limitados aos tipos de escola `11`, `12`, `32` e `33`.
`professor = NULL` não é usado para representar ausência de professor; nesse
caso a linha não deve existir.

| Campo Origem | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `cd_turma_escola` | `turma_codigo` | `str()` ou `None` |
| `cd_componente_curricular` | `componente_codigo` | `int()` |
| RF ou CPF | `professor` | `str()` ou `None` |
| branch externo | `atribuicao_externa` | `bool()` |
| ano da atribuição | `ano_letivo` | `int()` |
| — | `transferido_em` | `timezone.now()` |

---

## Fase 4 — AtribuicaoTerritorioSaber

**Query:** `SQL_ATRIBUICOES_TERRITORIO_SABER` (parâmetro `?` por ano letivo)

Materializa a atribuição granular de Território do Saber. Cada linha representa um componente de território atribuído a um professor em uma turma, com território, experiência, datas e motivo de disponibilização.

| Campo Origem | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `cd_componente_curricular` | `componente_codigo` | `int()` |
| `cd_turma_escola` | `turma_codigo` | `str()` |
| RF ou CPF | `professor` | `str()` |
| `cd_territorio_saber` | `codigo_territorio_saber` | `int()` |
| `cd_experiencia_pedagogica` | `codigo_experiencia_pedagogica` | `int()` ou `None` |
| `dc_territorio_saber` | `desc_territorio_saber` | `strip_str()` |
| `dc_experiencia_pedagogica` | `desc_experiencia_pedagogica` | `strip_str()` |
| data de atribuição | `dt_atribuicao` | `make_aware()` |
| data de disponibilização | `dt_disponibilizacao` | `make_aware()` |
| motivo de disponibilização | `cd_motivo_disponibilizacao` | `int()` ou `None` |
| fim da turma | `dt_fim_turma` | `make_aware()` |
| branch externo | `atribuicao_externa` | `bool()` |
| `ano_letivo` | `ano_letivo` | direto |
| — | `transferido_em` | `timezone.now()` |

---

## Fase 5 — ComponenteCurricularApiEol

**Query:** `SQL_API_EOL_COMPONENTE_CURRICULAR`

Materializa em `componente_curricular_api_eol` o resultado do `LEFT JOIN`
entre `componentecurricular` e `componentecurricularpai` da API EOL. A carga
preserva componentes sem pai e todas as relações históricas existentes.

| Campo API EOL | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `ccp.id` | `id_relacao_origem` | `int_or_none()` |
| `cc.idcomponentecurricular` | `id_componente_curricular` | `int()` |
| `cc.ehregencia` | `eh_regencia` | `bool()` |
| `cc.ehterritorio` | `eh_territorio` | `bool()` |
| `cc.descricao` | `descricao` | `strip_str()` ou `None` |
| `ccp.idcomponentecurricularpai` | `id_componente_curricular_pai` | `int_or_none()` |
| `ccp.vigencia` | `vigencia` | `aware_or_none()` |

**Chave da linha:** `(id_relacao_origem, id_componente_curricular)`, com
`nulls_distinct=False` para identificar também componentes sem pai.

---

## Fases 6 a 9 — tabelas auxiliares da API EOL

Todas usam `full_refresh` e `truncate_on_full_sync=True`.

| Fase | Origem API EOL | Destino | Observação |
| :--- | :--- | :--- | :--- |
| 6 | `componentecurricularpai` | `componente_curricular_hierarquia` | Hierarquia pai/filho de componentes. |
| 7 | `componentecurricularpap` | `componente_curricular_pap` | Componentes PAP. |
| 8 | `regenciacomponentecurricular` | `componente_curricular_planejamento_regencia` | Planejamento de regência por componente, turno e ano. |
| 9 | `turma_tipo_itinerario` | `turma_itinerario_ensino_medio` | Itinerários do Ensino Médio. |

---

## Fase 10 — AgrupamentoAtribuicaoTerritorioSaber

**Query:** `SQL_API_EOL_AGRUPAMENTO_ATRIBUICAO_TERRITORIO_SABER`

Copia a tabela `agrupamentoatribuicaoterritoriosaber` da API EOL em modo `full_refresh`. O ETL não recalcula o `cod_agrupamento` nesse fluxo principal; ele preserva o identificador público recebido da origem. A query cria `id_linha_api_eol` com `ROW_NUMBER()` apenas como chave técnica para processar todas as linhas, inclusive quando o mesmo `cod_agrupamento` aparece em mais de um recorte físico.

| Campo Origem API EOL | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `codagrupamento` | `cod_agrupamento` | `int()` |
| `codterritoriosaber` | `cod_territorio_saber` | `int()` |
| `codexperienciapedagogica` | `cod_experiencia_pedagogica` | `int()` ou `None` |
| `dtinicioatribuicao` | `dt_inicio_atribuicao` | `make_aware()` |
| `anoatribuicao` | `ano_atribuicao` | `int()` |
| `dtfimatribuicao` | `dt_fim_atribuicao` | `make_aware()` |
| `dtfimturma` | `dt_fim_turma` | `make_aware()` |
| `rfprofessor` | `rf_professor` | `str()` |
| `codturma` | `cod_turma` | `str()` |
| `codcomponentescurriculares` | `cod_componentes_curriculares` | CSV recebido da origem |
| `anoletivo` | `ano_letivo` | `int()` |
| `codmotivodisponibilizacao` | `cod_motivo_disponibilizacao` | `int()` ou `None` |
| `descterritoriosaber` | `desc_territorio_saber` | `strip_str()` |
| `descexperienciapedagogica` | `desc_experiencia_pedagogica` | `strip_str()` |
| `encerramento_atribuicao_agrupamento_atualizado` | `encerramento_atribuicao_agrupamento_atualizado` | `bool()` ou `None` |
| — | `transferido_em` | `timezone.now()` |

**Observação:** `cod_agrupamento` deve ser tratado como ID de contrato, não como unique físico. A mesma numeração pode aparecer em mais de uma linha quando a origem registra outro professor ou histórico.

---

## Fase 11 — GradeComponenteCurricular

**Query:** `SQL_GRADE_COMPONENTE_CURRICULAR` (parâmetro `?` por ano letivo)

Catálogo de oferta curricular por série, ano letivo e modalidade. Considera
turmas abertas, aguardando abertura e continuadas (`O`, `A`, `C`), mas não
turmas extintas. Exige série válida (`sg_resumida_serie IS NOT NULL`) e inclui
ofertas de programas via `turma_escola_grade_programa`.

**Chave de upsert:** `(codigo_componente_curricular, ano_letivo, modalidade, codigo_serie_ensino)`.

`codigo_ano_turma` é atualizado como atributo de resposta, mas não compõe a
identidade do registro. No legado, esse valor pode variar para a mesma série de
ensino; por isso `codigo_serie_ensino` é a referência de identidade.

| Campo EOL | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `CodigoComponenteCurricular` | `codigo_componente_curricular` | `int()` |
| `DescricaoComponenteCurricular` | `descricao_componente_curricular` | `strip_str()` |
| `CodigoAnoTurma` | `codigo_ano_turma` | `str()` ou `None` |
| `DescricaoSerieEnsino` | `descricao_serie_ensino` | `strip_str()` ou `None` |
| `CodigoSerieEnsino` | `codigo_serie_ensino` | `int()` ou `None` |
| CASE na query EOL | `modalidade` | `int()` ou `None` |
| `AnoLetivo` | `ano_letivo` | `int()` |
| — | `transferido_em` | `timezone.now()` |

---

## Fase 12 — Turma

**Query:** `SQL_TURMAS` (parâmetro `?` por ano letivo)

Origem: `turma_escola` (NOLOCK) com joins em `escola`, `serie_turma_escola`, `serie_ensino` e `etapa_ensino`. Filtra `st_turma_escola IN ('O', 'A', 'E', 'C')`.

| Campo EOL | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `cd_turma_escola` | `codigo` | `int()` |
| `an_letivo` | `ano_letivo` | `int()` |
| CASE sobre `dc_turma_escola` (1º char numérico) | `ano` | `str()` ou `None` |
| `cd_tipo_turma` | `tipo_turma` | `int()` |
| `dc_turma_escola` | `nome_turma` | `strip_str()` |
| `cd_duracao` | `duracao_turno` | `int()` ou `None` |
| `cd_tipo_turno` | `tipo_turno` | `int()` ou `None` |
| `dt_inicio` | `data_inicio` | `make_aware()` ou `None` — **coluna EOL diferente de `dt_inicio_turma`**; é a que o legado usa em `dataInicioTurma` da abrangência (`QueriesAbrangencia.cs`) |
| `dt_inicio_turma` | `data_inicio_turma` | `make_aware()` ou `None` |
| `dt_fim` | `data_fim` | `make_aware()` ou `None` |
| CASE `st_turma_escola = 'E'` | `extinta` | `bool()` |
| `st_turma_escola` | `situacao` | `str()` ou `None` |
| `cd_escola` | `ue_codigo` | `str()` ou `None` |
| `dt_atualizacao_tabela` | `data_atualizacao` | `make_aware()` ou `None` |
| `dt_status_turma_escola` | `data_status_turma_escola` | `make_aware()` ou `None` |
| `dc_serie_ensino` | `serie_ensino` | `strip_str()` ou `None` |
| `cd_serie_ensino` | `codigo_serie_ensino` | `int()` ou `None` |
| CASE sobre `cd_etapa_ensino` | `modalidade` | `str()` (`'EJA'`, `'Fundamental'`, `'Médio'`, `'Infantil'`) ou `None` |
| CASE sobre `cd_etapa_ensino` + `tp_escola` | `codigo_modalidade` | `int()` (1=EI, 3=EJA, 4=CIEJA, 5=EF, 6=EM) |
| `cd_tipo_programa` | `codigo_tipo_programa` | `int()` ou `None` |
| CASE sobre `COALESCE(cd_etapa_ensino, etapa do programa)` + `tp_escola` | `codigo_modalidade_etapa` | `int()` — **bucket derivado** (1/3/4/5/6), NÃO o `cd_etapa_ensino` cru |
| `ee.cd_etapa_ensino` (cru) | `codigo_etapa_ensino` | `int_or_none()` — código de etapa do EOL (1–17), paridade com `EtapaEnsino` do legado |
| `se.cd_ciclo_ensino` | `codigo_ciclo_ensino` | `int_or_none()` — paridade com `CicloEnsino` do legado |
| CASE EJA pelo mês de `dt_inicio_turma` | `semestre` | `int()` (1 ou 2 para EJA; 0 demais) |
| `cd_etapa_ensino = 13` e `cd_modalidade_ensino = 2` | `ensino_especial` | `bool()` |
| — | `transferido_em` | `timezone.now()` |

---

## Fase 13 — TurmaAtribuidaDreUe

**Query:** `SQL_TURMAS_ATRIBUIDAS_DRE_UE` — montada em tempo de execução por
`EtlPedagogicoService._sql_turmas_atribuidas_dre_ue()` (sem parâmetro `?`, roda
1x por execução do ETL, não 1x por ano letivo).

**Origem (20/08/2026):** join ao vivo em `turma_escola`+`escola`+
`v_cadastro_unidade_educacao`+`unidade_administrativa` no EOL, reimplementando
`ObterEstruturaInstitucionalVigente` (`QueriesAbrangencia.cs` do legado) — **não**
mais a view `turmas_atribuidas_dre_ue`, que só cobria `tp_escola` em
`{1,3,4,13,16}` (bem mais estreito que o recorte real usado pelo legado).
Sempre ano corrente (`YEAR(GETDATE())` no SQL Server, igual ao legado) — por
isso a query não recebe `ano_letivo` como parâmetro.

O recorte de `tp_escola`/etapas por modalidade vem de `parametros` (Postgres
`api_eol_db`, mesma fonte que o legado chama de "ParametrosApiEol"), lido a
cada execução via `_parametros_abrangencia()` — chaves `tipo_escola_sgp`,
`tipo_escola_infantil_sgp`, `etapas_por_modalidade`. Os IDs de componente PAP
usados no filtro de turma tipo 3 são constante fixa
(`_IDS_COMPONENTES_PAP` em `queries.py`, espelha
`ComponentesCurricularesConstants.IDS_COMPONENTES_CURRICULARES_PAP` do legado).

A origem entrega a turma final, então a carga substitui o conteúdo do ano letivo
sem detecção de mudança por linha. Linhas sem escola ou turma são descartadas.

| Campo EOL | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `CodEscola` | `codigo_escola` | `strip_str()` |
| `CodTurma` | `codigo_turma` | `int()` |
| `AnoLetivo` | `ano_letivo` | `int()` |
| `Modalidade` | `modalidade` | `strip_or_none()` |
| `Semestre` | `semestre` | `int_or_none()` |
| `CodModalidade` | `codigo_modalidade` | `int_or_none()` |
| `CodDre` | `codigo_dre` | `strip_str()` |
| `Dre` / `DreAbrev` | `dre` / `dre_abreviacao` | `strip_or_none()` |
| `UE` / `UEAbrev` | `ue` / `ue_abreviacao` | `strip_or_none()` |
| `NomeTurma` | `nome_turma` | `strip_or_none()` |
| `Ano` | `ano` | `strip_or_none()` |
| `TipoUE` / `CodTipoUE` | `tipo_ue` / `codigo_tipo_ue` | `strip_or_none()` / `int_or_none()` |
| `CodTipoEscola` / `TipoEscola` | `codigo_tipo_escola` / `tipo_escola` | `int_or_none()` / `strip_or_none()` |
| `DuracaoTurno` / `TipoTurno` | `duracao_turno` / `tipo_turno` | `int_or_none()` |
| — | `transferido_em` | `timezone.now()` |

---

## Fase 14 — EtapaEnsino

**Query:** `SQL_ETAPA_ENSINO` (sem parâmetro de ano, `full_refresh` + `truncate_on_full_sync=True`)

Catálogo estático de etapas de ensino (`etapa_ensino` no EOL), sem filtro
`WHERE`. Alimenta o endpoint `modalidades_ensino` do domínio Pedagógico, que
devolve as descrições como lista de strings.

| Campo EOL | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `cd_etapa_ensino` | `codigo` | `int()` |
| `dc_etapa_ensino` | `descricao` | `strip_str()` (já com `LTRIM`/`RTRIM` na query) |
| — | `transferido_em` | `timezone.now()` |

---

## Fase 15 — CicloEnsino

**Query:** `SQL_CICLO_ENSINO` (sem parâmetro de ano, `full_refresh` + `truncate_on_full_sync=True`)

Catálogo completo de ciclos de ensino (`ciclo_ensino` no EOL), sem filtro
`WHERE`. Alimenta o endpoint de abrangência `ciclo-ensino` do domínio
Pedagógico.

| Campo EOL | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `cd_modalidade_ensino` | `codigo_modalidade_ensino` | `int()` |
| `cd_etapa_ensino` | `codigo_etapa_ensino` | `int()` |
| `cd_ciclo_ensino` | `codigo` | `int()` |
| `dc_ciclo_ensino` | `descricao` | `str_value_or_none()` |
| `dt_atualizacao_tabela` | `data_atualizacao` | `aware_or_none()` |
| — | `transferido_em` | `timezone.now()` |
