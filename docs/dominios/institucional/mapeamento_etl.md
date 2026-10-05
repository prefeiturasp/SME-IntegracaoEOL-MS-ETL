# Mapeamento do ETL Institucional

Detalhamento de origem e destino dos campos entre EOL/SSO e banco Institucional.

## Fase 1

| Campo EOL | Campo Destino | Descrição |
| :--- | :--- | :--- |
| `ua.cd_unidade_administrativa` | `codigo_dre` | ID único da DRE (ex: 108900). |
| `vcue.nm_unidade_educacao` | `nome` | Nome oficial da DRE. |
| `vcue.nm_exibicao_unidade` | `sigla` | Sigla da DRE (ex: BT). |
| `ua.tp_unidade_administrativa` | `tipo_unidade_adm` | Código do tipo administrativo (SME/DRE). |
| `tua.dc_tipo_unidade_administrativa` | `descricao_unidade_adm` | Texto do tipo administrativo. |

## Fase 2 — sem dependência

| Campo EOL | Campo Destino | Descrição |
| :--- | :--- | :--- |
| `tp_escola` | `codigo_tipo_escola` | ID numérico do tipo. |
| `sg_tp_escola` | `sigla` | Abreviação (ex: EMEF). |
| `dc_tipo_escola` | `descricao` | Nome completo. |

## Fase 3 — sem dependência

| Campo EOL | Campo Destino | Descrição |
| :--- | :--- | :--- |
| `cd_sub_prefeitura` | `codigo_sub_prefeitura` | ID único. |
| `sg_sub_prefeitura` | `sigla` | Abreviação geográfica. |
| `dc_sub_prefeitura` | `nome` | Nome oficial. |

## Fase 4 — depende das Fase 1, 2 e 3

| Campo Origem | Campo Destino | Descrição |
| :--- | :--- | :--- |
| `vuedg.cd_unidade_educacao` | `codigo_ue` | ID único da unidade (ex: 001089). |
| `vuedg.nm_unidade_educacao` | `nome` | Nome da escola. |
| `tpl.dc_tp_logradouro` + `logradouro` | `logradouro` | Endereço completo. |
| `escola.an_construcao` | `ano_construcao` | Ano de fundação da predial. |
| **CACHE: CORE_SSO** | `codigo_ue_integracao` | UUID legado do SSO. |
| `vuedg.tp_escola` | `tipo_escola_id` | FK externa para TipoEscola. |
| `vcue.cd_unidade_administrativa_referencia` | `dre_id` | FK externa para DRE. |

## Fase 5 — DREs de abrangência

| Campo EOL | Campo Destino | Descrição |
| :--- | :--- | :--- |
| `dre.cd_unidade_educacao` | `codigo_dre` | Código da DRE elegível. |
| `dre.nm_unidade_educacao` | `nome` | Nome oficial da DRE. |
| `dre.nm_exibicao_unidade` | `abreviacao` | Abreviação da DRE. |
| `ROW_NUMBER()` | `ordem` | Sequência materializada da consulta de origem. |

A elegibilidade reproduz os vínculos e filtros da consulta legada por tipo
de escola e etapa de ensino.
