# Glossário do Domínio Pedagógico

Dicionário de termos, campos, regras de negócio e conceitos do legado EOL usados no ETL pedagógico. Serve de referência para quem está entrando no domínio ou precisando entender o que um campo ou tabela significa na prática.

---

## Conceitos de Negócio

---

### Componente Curricular

O que é ensinado numa turma. Equivale ao que no dia a dia chamamos de "disciplina" — Língua Portuguesa, Matemática, Ciências, Arte, etc.

No EOL, cada componente tem um `cd_componente_curricular` (inteiro). O nome fica em `dc_componente_curricular`.

**No ETL:**
- A tabela `componente_curricular` é o catálogo base. Todos os outros modelos referenciam o código daqui.
- Um componente pode ser de **regência**. Essa flag fica no catálogo `componente_curricular`.
- Um componente pode fazer parte de **território do saber** em determinada turma; nesse caso, a informação aparece em `componente_turma.codigo_componente_territorio_saber`.
- A relação pai/filho de componentes não é calculada no ETL principal. Ela fica na tabela local `componente_curricular_hierarquia`, usada pelo microsserviço de consumo quando necessário.

---

### Regência

Modalidade de ensino em que **um único professor é responsável por todas ou várias disciplinas** da turma — diferente do modelo em que cada disciplina tem um professor diferente.

Típica do **Ensino Fundamental I** (1º ao 5º ano), onde o professor regente leciona Língua Portuguesa, Matemática, Ciências, História e Geografia para a mesma turma.

**No ETL:**
- A flag `regencia` em `componente_curricular` indica que o componente é de regência.
- Determinada via lista hardcoded `_IDS_REGENCIA` em `queries.py` — 19 IDs fixos que representam os componentes de regência reconhecidos pelo sistema.
- Não é derivada de nenhuma tabela dinâmica: se o `cd_componente_curricular` está na lista, `regencia = True`.

**Atenção:** `regencia = True` não significa que o professor precisa planejar esse componente para uma turma específica. Para isso existe a configuração de planejamento de regência, mantida fora do ETL principal.

---

### Planejamento de Regência

Refinamento de `regencia`: indica se o componente de regência **entra efetivamente no planejamento de aulas** do professor para aquela combinação de **turno + ano escolar**.

**Por que existe essa distinção?**
Nem todo componente de regência se aplica a todas as séries e turnos. Por exemplo, um componente pode ser de regência apenas para turmas do 1º e 2º ano no turno da manhã. Para turmas do 5º ano ou de outro turno, o mesmo componente até existe, mas não entra no planejamento de regência.

**No desenho atual:**
- O ETL não grava `planejamento_regencia` em `ComponenteTurma`.
- A configuração fica na tabela local `componente_curricular_planejamento_regencia`.
- A aplicação da regra é responsabilidade do microsserviço de consumo, que cruza componente, turno e ano escolar quando precisa montar a resposta de planejamento.

---

### Território do Saber

Componentes curriculares especiais do programa **Mais Educação** / educação integral, como Dança, Teatro, Música, Esportes, etc. Esses componentes não seguem a grade curricular padrão — são associados a **territórios** (áreas temáticas) e **experiências pedagógicas**.

**Valor sentinela — código 1 (`TERRITORIO_SABER_NAO_UTILIZADO`):**
O código `cd_territorio_saber = 1` é um valor especial que significa "território não utilizado" — não representa um território real. O C# filtra explicitamente `CodigoTerritorioSaber != 1` antes de agrupar (`CargaDBAgrupamentosTerritorioSaberPorTurmaUseCase.cs:43`) e no service (`ComponenteCurricularService.cs:318`). **Registros com território 1 devem ser ignorados no agrupamento.**

> **Divergência atual:** o ETL Python (`SQL_ATRIBUICOES_TERRITORIO_SABER` e `_agrupar`) não aplica esse filtro. Qualquer registro com `cd_territorio_saber = 1` na base EOL entrará no agrupamento indevidamente.

**No EOL:**
- A presença na tabela `turma_grade_territorio_experiencia` indica que o componente é de território.
- Cada componente de território pertence a um `cd_territorio_saber` e pode ter um `cd_experiencia_pedagogica` associado.

**No ETL:**
- `ComponenteTurma` não guarda uma flag booleana `territorio_saber`.
- `SQL_COMPONENTE_TURMA` faz `LEFT JOIN` com `turma_grade_territorio_experiencia`.
- Quando o componente pertence a território, `codigo_componente_territorio_saber` recebe o próprio código do componente; caso contrário, fica `NULL`.

---

### Agrupamento de Território do Saber

Quando um professor é atribuído a **mais de um componente de território** na mesma turma (ex: Dança + Teatro + Música, todos com o mesmo território e experiência), esses componentes formam um **agrupamento**.

O agrupamento representa o conjunto como uma unidade: o professor planeja para o grupo todo, não componente a componente.

**No ETL:**
- Tabela `agrupamento_atribuicao_territorio_saber`: o agrupamento como um todo — quem é o professor, qual a turma, qual território, período de atribuição, e a lista de componentes como CSV em `cod_componentes_curriculares`.
- Tabela `componente_curricular_agrupamento`: uma linha por componente dentro do agrupamento (split do CSV acima). Alimenta `codigosTerritoriosAgrupamento` nos endpoints.
- **Regra:** somente grupos com 2 ou mais componentes distintos geram agrupamento. Atribuição isolada de um único componente de território não é agrupada.

**Chave de agrupamento:** a combinação `(turma, território, experiência pedagógica, professor, data de atribuição, data de disponibilização)` define um grupo. Atribuições com datas de disponibilização em dias diferentes formam grupos distintos.

**`cod_agrupamento`:** ID gerado por hash MD5 determinístico da chave natural + lista ordenada de componentes. Sempre `>= 800.000` para não colidir com IDs reais de componentes do EOL (constante `COMPONENTE_AGRUPAMENTO_TERRITORIO_SABER_ID_INICIAL` do legado C#).

---

### Atribuição de Aula

Registro no EOL que indica que um professor foi designado para lecionar um componente específico numa turma/série/grade num determinado ano letivo.

Existem dois tipos:
- **SME** (`atribuicao_aula`): professor identificado por RF (Registro Funcional) via `v_servidor_cotic`.
- **Externo** (`atribuicao_externo`): professor de escola conveniada/parceira, identificado por CPF via `contrato_externo` + `pessoa`.

**Campos importantes:**
- `dt_atribuicao_aula` / `dt_atribuicao`: quando a atribuição começou.
- `dt_disponibilizacao_aulas` / `dt_disponibilizacao`: quando a atribuição foi encerrada/disponibilizada. `NULL` = atribuição ativa.
- `cd_motivo_disponibilizacao`: por que foi encerrada. O código `26` = erro de cadastro (descartado). O código `34` = fim de ano letivo (tratado diferente — ainda aparece como válida em certas consultas).
- `dt_cancelamento`: quando foi cancelada. Se preenchida, o registro é ignorado.

---

### Disponibilização

Encerramento formal de uma atribuição. Quando `dt_disponibilizacao_aulas` está preenchida, significa que o professor **saiu** daquela turma/componente.

O motivo importa:
- `cd_motivo_disponibilizacao = 26` (erro de cadastro): atribuição inválida — excluída das consultas.
- `cd_motivo_disponibilizacao = 34` (fim de ano letivo): atribuição válida, encerrada naturalmente — incluída em alguns contextos.
- `NULL` ou outros: atribuição ativa ou encerrada por outros motivos.

No campo `fim_atribuicao` dos modelos, o valor é o `MAX(dt_disponibilizacao)` do grupo — a data mais recente de disponibilização dentre os registros do agrupamento.

---

### Turno

Período do dia em que a turma funciona (manhã, tarde, noite, integral).

No EOL, não é um campo texto — é representado por `qt_hora_duracao` da tabela `duracao_tipo_turno`, que armazena a **quantidade de horas do turno** (ex: 4h = tarde, 5h = manhã, etc.). Esse valor inteiro é o que o sistema usa como identificador de turno.

O JOIN para obter o turno é sempre: `turma_escola.cd_tipo_turno + turma_escola.cd_duracao → duracao_tipo_turno.qt_hora_duracao`.

---

### Ano Turma / Ano Escolar (`sg_resumida_serie`)

Série/ano escolar da turma — ex: "1", "2", "3", "4", "5" para o Ensino Fundamental I.

No EOL, vem da tabela `serie_ensino` como `sg_resumida_serie` (sigla resumida). Pode ter valores como "EI" (Educação Infantil), "1" a "9" (EF), "1EM" (Ensino Médio), etc.

No ETL, é sempre tratado como **string** — nunca convertido para inteiro, pois pode conter letras.

Nos endpoints do SGP, o parâmetro `anoTurma` usa esses valores como filtro.

---

### Grade Curricular

Estrutura que define quais componentes curriculares são obrigatórios para uma combinação de série + escola. No EOL: tabela `grade` + `grade_componente_curricular`.

Cada escola pode ter uma grade diferente (escola particular conveniada pode ter componentes distintos da rede municipal). Por isso o JOIN passa por `escola_grade` antes de chegar na `grade`.

Existe também a **grade de programa** (`turma_escola_grade_programa`), para turmas especiais que não seguem a grade da série — ex: turmas de aceleração, programas específicos. Nesse caso, o componente do programa tem prioridade sobre o da série (lógica do `IIF` nas queries).

---

### Etapa de Ensino

Subdivisão formal do sistema educacional, definida pelo MEC. Exemplos: Anos Iniciais do EF, Anos Finais do EF, Ensino Médio, EJA Fundamental.

No EOL: tabela `etapa_ensino`, campo `cd_etapa_ensino`. Cada `serie_ensino` pertence a uma etapa.

O caminho de origem é: `turma_escola → serie_turma_grade → grade → serie_ensino → etapa_ensino`. Desde a migration `0011`, o ETL **materializa o código cru de etapa na turma** como `codigo_etapa_ensino` (1–17), para paridade com o `EtapaEnsino` do legado. Não confundir com `codigo_modalidade_etapa`, que é *bucket* derivado (ver [Modalidade de Ensino](#modalidade-de-ensino)).

---

### Ciclo de Ensino

Agrupamento pedagógico de séries dentro de uma etapa (ex.: Ciclo de Alfabetização, Ciclo Interdisciplinar, Autoral).

No EOL: campo `cd_ciclo_ensino` na tabela `serie_ensino` (descrição em `dc_ciclo_ensino`, tabela `ciclo_ensino`). Desde a migration `0011`, o ETL materializa o código cru na turma como `codigo_ciclo_ensino` (via `se.cd_ciclo_ensino` na `SQL_TURMAS`), para paridade com o `CicloEnsino` do legado. A **descrição** (`dc_ciclo_ensino`) ainda não é materializada.

---

### Série de Ensino

O ano/série escolar dentro de uma etapa. Ex: 1º ano, 2º ano, 3º ano do EF.

No EOL: tabela `serie_ensino`. Campos relevantes:
- `sg_resumida_serie`: sigla curta usada como filtro nos endpoints — ex: `"1"`, `"2"`, `"1EM"`, `"EI"`.
- `sg_serie_ensino`: nome completo da série.
- `cd_serie_ensino`: chave numérica.

**Hierarquia completa no EOL:**

```
Modalidade (derivada)
  └── Etapa de Ensino (etapa_ensino)
        └── Série (serie_ensino)
              └── Grade (grade)           ← quais componentes são obrigatórios
                    └── Componentes (grade_componente_curricular)
              └── Turma (turma_escola)    ← vínculo via serie_turma_escola → serie_turma_grade
```

---

### Modalidade de Ensino

Categoria que agrupa etapas de ensino para fins de filtragem nos endpoints. Não existe como campo direto na turma — é **derivada** da etapa de ensino via `CASE` nas queries.

| Código | Modalidade | Etapas / Tipo de Escola |
|---|---|---|
| 1 | EI (Educação Infantil) | `cd_etapa_ensino IN (1, 10)` |
| 3 | EJA | `cd_etapa_ensino IN (2, 3, 7, 11)` |
| 4 | CIEJA | `tp_escola = 13` |
| 5 | EF (Ensino Fundamental) | `cd_etapa_ensino IN (4, 5, 12, 13)` |
| 6 | EM (Ensino Médio) | `cd_etapa_ensino IN (6, 7, 8, 9, 14, 17)` |

O CIEJA é identificado pelo `tp_escola` da escola (não pela etapa) porque suas turmas podem ter etapas variadas — o que define o CIEJA é o tipo da escola.

---

### PAP (Programa de Apoio e Acompanhamento à Aprendizagem)

Programa de reforço escolar da rede municipal destinado a alunos com dificuldades de aprendizagem. As turmas PAP têm componentes curriculares próprios — distintos dos componentes regulares — que são usados para planejamento e registro de frequência.

**No ETL:**
- A tabela local `componentecurricularpap` lista os IDs de componentes que pertencem ao PAP.
- Os IDs atualmente cadastrados são: `1033, 1051, 1052, 1053, 1054, 1322, 1770, 1804, 1805`.
- Essa lista é usada pelo endpoint `GET /turmas/{codigoTurma}/validar/pap` para verificar se uma turma possui componente PAP.
- No ETL, serve para identificar e tratar esses componentes de forma diferenciada quando necessário.

**Fonte dos dados:** tabela local Postgres `componentecurricularpap`, populada pelos scripts de migração `V18`, `V193` e `V194`.

---

### Tipo de Escola

Campo `tp_escola` da tabela `escola`. Indica o tipo de vínculo/administração da escola.

Tipos relevantes no ETL:

| Código | Descrição |
|---|---|
| 11 | CEI_INDIR (Centro de Educação Infantil Indireto) |
| 12 | CRP_CONV (Conveniado) |
| 13 | CIEJA |
| 32 | EMEFPFOM |
| 33 | EMEIPFOM |

Os tipos 11, 12, 32 e 33 são os que admitem **professor externo** (identificado por CPF). Os demais aceitam apenas professor SME (RF).

---

### Professor SME vs. Professor Externo

- **SME:** servidor da rede municipal, identificado por **RF (Registro Funcional)**. Atribuição em `atribuicao_aula`, professor em `v_servidor_cotic.cd_registro_funcional`.
- **Externo:** professor de escola parceira/conveniada, identificado por **CPF**. Atribuição em `atribuicao_externo`, professor em `pessoa.cd_cpf_pessoa` via `contrato_externo`.

O campo `atribuicao_externa` (0 ou 1) distingue os dois nos resultados das queries UNION ALL.

No modelo, o campo `professor` armazena RF ou CPF — é uma string opaca, o tipo depende do contexto.

---

### DRE (Diretoria Regional de Educação)

Instância administrativa intermediária entre a SME e as escolas. Cada escola pertence a uma DRE.

No EOL, o JOIN para chegar na DRE passa por:
`escola → v_cadastro_unidade_educacao → unidade_administrativa` com filtro `tp_unidade_administrativa = 24` (constante `_TIPO_UNIDADE_ADMINISTRATIVA_DRE`).

---

### Ano Letivo

O ano civil em que a turma/atribuição ocorre. Campo `an_letivo` em `turma_escola`.

O ETL itera sobre todos os anos letivos distintos encontrados em `turma_escola` (query `SQL_ANOS_LETIVOS`) e processa cada fase por ano. A fase de agrupamentos de território é a exceção — processa todos os anos de uma vez.

---

### Status da Turma (`st_turma_escola`)

Campo que indica o estado atual da turma:

| Valor | Significado |
|---|---|
| `O` | Ativa (em operação) |
| `A` | Aberta |
| `C` | Concluída |
| `E` | Encerrada |

A maioria das queries filtra `IN ('O', 'A', 'C', 'E')` — todas as turmas não canceladas. Algumas excluem `'E'` dependendo do contexto.

---

### Experiência Pedagógica

Subcategoria dentro de um território do saber. Por exemplo, dentro do território "Arte", a experiência pedagógica pode ser "Dança", "Teatro" ou "Artes Visuais".

No EOL: tabela `tipo_experiencia_pedagogica`, campo `cd_experiencia_pedagogica`.

Compõe a chave de agrupamento junto com `cd_territorio_saber`.

---

## Campos Técnicos

---

### `transferido_em`

Timestamp de quando o registro foi escrito pelo ETL. Equivale ao `timezone.now()` no início da execução. Não é um dado do EOL — é metadado de auditoria do ETL.

---

### `cod_componentes_curriculares` (CSV)

Campo de `AgrupamentoAtribuicaoTerritorioSaber` que armazena os IDs dos componentes do agrupamento separados por vírgula — ex: `"508,511,1064"`. Sempre ordenados crescentemente para garantir determinismo no hash.

O ETL faz o split desse CSV e popula `componente_curricular_agrupamento` com uma linha por componente.

---

### `codigo_componente_territorio_saber`

Em `ComponenteTurma`, esse campo recebe o próprio código do componente quando ele existe em `turma_grade_territorio_experiencia`. É uma redundância intencional para indexação cruzada nos endpoints — permite identificar componentes de território sem JOIN adicional.

---

### `codigo_componente_curricular_pai`

Alguns componentes são variações de um componente "pai" — ex: componentes filhos de Arte (513, 534, 535...) têm o componente 512 como pai.

**No C# legado:** a relação pai-filho é consultada dinamicamente na tabela `componentecurricularpai` da `ApiEolConnection` (Postgres), via LEFT JOIN com ordenação por `Id DESC`. A lógica distingue `CodigoComponentePai` de `CodigoComponentePaiVigencia` — o par mais recente por ordem de inserção é o vigente.

**No ETL Python:** essa regra não é mais aplicada em `ComponenteTurma`. A relação fica em `componente_curricular_hierarquia`, tabela local de apoio, e deve ser consultada pelo microsserviço de consumo quando precisar resolver pai/filho.

---

### `cod_agrupamento`

ID único de um agrupamento de território. Gerado por hash MD5 determinístico sobre a chave natural `(turma, território, experiência, professor, data_atribuicao, componentes_ordenados)`.

Sempre `>= 800.000` (piso definido pela constante `COMPONENTE_AGRUPAMENTO_TERRITORIO_SABER_ID_INICIAL` do legado C#, para não colidir com IDs de componentes curriculares reais do EOL, que ficam abaixo desse valor).

---

### `turno_turma`

Inteiro que representa as horas de duração do turno (`qt_hora_duracao` de `duracao_tipo_turno`). Não é um nome de turno — é um número de horas. O SGP interpreta esse número para derivar o período do dia.

---

### `ano_turma`

String que representa a série/ano escolar da turma (`sg_resumida_serie` de `serie_ensino`). Valores típicos: `"1"`, `"2"`, `"3"`, `"4"`, `"5"` para EF1. Pode conter letras: `"EI"`, `"1EM"`, etc. Nunca converter para inteiro.

---

### `motivo_disponibilizacao`

Código que explica por que uma atribuição foi encerrada:

| Código | Significado | Comportamento no ETL |
|---|---|---|
| `26` | Erro de cadastro | **Excluído** de todas as queries |
| `34` | Fim de ano letivo | Incluído (atribuição válida encerrada naturalmente) |
| `NULL` | Atribuição ainda ativa | Incluído |
| Outros | Outros motivos de encerramento | Incluído |

---

## Tabelas EOL Relevantes

| Tabela EOL | O que representa |
|---|---|
| `turma_escola` | Turmas (ano letivo, escola, turno, status) |
| `escola` | Escolas (código, tipo) |
| `componente_curricular` | Catálogo de componentes (código, descrição, cancelamento) |
| `grade` | Grade curricular (conjunto de componentes por série) |
| `grade_componente_curricular` | Componentes que fazem parte de uma grade |
| `serie_ensino` | Séries/anos escolares com sigla resumida |
| `serie_turma_escola` | Vínculo entre turma e série |
| `serie_turma_grade` | Vínculo entre turma/série e grade |
| `escola_grade` | Grade de uma escola específica |
| `duracao_tipo_turno` | Horas de duração por tipo/turno |
| `atribuicao_aula` | Atribuições SME (professor RF) |
| `atribuicao_externo` | Atribuições de professores externos (CPF) |
| `turma_grade_territorio_experiencia` | Componentes de território por série/grade |
| `territorio_saber` | Territórios do saber (nome, código) |
| `tipo_experiencia_pedagogica` | Experiências pedagógicas dentro de território |
| `v_servidor_cotic` | View de servidores SME (RF) |
| `v_cargo_base_cotic` | View de cargos de servidores |
| `contrato_externo` | Contratos de professores externos |
| `pessoa` | Pessoas físicas (CPF) |
| `v_cadastro_unidade_educacao` | View de unidades educacionais |
| `unidade_administrativa` | DREs e outras unidades administrativas |
| `etapa_ensino` | Etapas de ensino (EI, EF, EM, EJA...) |
| `turma_escola_grade_programa` | Grade de programa para turmas especiais |

**Tabelas locais (Postgres da API Pedagógico):**

| Tabela | O que representa |
|---|---|
| `componente_curricular_planejamento_regencia` | Configuração global de quais componentes entram no planejamento de regência por turno e ano escolar. Triplas `(id_componente_curricular, turno, ano)` — quando `turno` e `ano` são `null`, o componente é genérico para qualquer turma. |
| `componente_curricular_hierarquia` | Relação entre componente filho e componente pai, com vigência. |
| `componentecurricularpap` | Lista de IDs de componentes curriculares pertencentes ao PAP. Usada para identificar turmas e componentes do programa. |

---

## Relação entre os Modelos do ETL e Tabelas Locais

```
ComponenteCurricular          ← catálogo base (fase 1)
        │
        ├── ComponenteTurma                      ← vínculo turma × componente (fase 2)
        │       campo: codigo_componente_territorio_saber
        │
        ├── AtribuicaoComponente                 ← professor × turma × componente (fase 3)
        │
        ├── ComponenteCurricularAgrupamento       ← detalhe do agrupamento, 1 linha por componente (fase 4)
        │       └── referencia AgrupamentoAtribuicaoTerritorioSaber
        │
        ├── AgrupamentoAtribuicaoTerritorioSaber  ← agrupamento de território como unidade (fase 4)
        │
        └── GradeComponenteCurricular             ← oferta de componentes por ano/modalidade (fase 5)

Tabelas locais de apoio (fora do pipeline principal):
        ├── ComponenteCurricularPlanejamentoRegencia ← configuração de planejamento de regência
        ├── ComponenteCurricularHierarquia        ← relação componente pai/filho
        └── ComponenteCurricularPAP               ← lista local de componentes PAP
```
