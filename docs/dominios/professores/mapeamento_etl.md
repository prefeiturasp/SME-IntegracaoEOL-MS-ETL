# Mapeamento ETL (Origem → Destino)

Documenta o fluxo real implementado nos métodos `popular_*` do serviço.

## Fase 1 — sem dependências internas

| Método | Tabela destino | Estratégia | SQL / Fonte |
|---|---|---|---|
| `popular_professores` | `professor` | `upsert_incremental` | `v_servidor_cotic` |
| `popular_pessoas` | `pessoa` | `upsert_incremental` | `pessoa` |

## Fase 2 — dependem da Fase 1

| Método | Tabela destino | Estratégia | SQL / Fonte |
|---|---|---|---|
| `popular_cargos_base` | `cargo_base_servidor` | `upsert_incremental` | `v_cargo_base_cotic` |
| `popular_contratos_externos` | `contrato_externo` | `upsert_incremental` | `contrato_externo` |

## Fase 3 — dependem da Fase 2

| Método | Tabela destino | Estratégia | SQL / Fonte |
|---|---|---|---|
| `popular_lotacoes` | `lotacao_servidor` | `full_refresh` | `lotacao_servidor` |
| `popular_cargos_sobrepostos` | `cargo_sobreposto_servidor` | `full_refresh` | `cargo_sobreposto_servidor` |
| `popular_funcoes_atividade` | `funcao_atividade_cargo_servidor` | `full_refresh` | `funcao_atividade_cargo_servidor` |
| `popular_laudos` | `laudo_medico` | `full_refresh` | `laudo_medico` |
| `popular_atribuicoes_aula` | `atribuicao_aula` | `upsert_incremental` | `atribuicao_aula` |
| `popular_atribuicoes_externo` | `atribuicao_externo` | `upsert_incremental` | `atribuicao_externo` |

## Fase 4 — dependem das Fases 1–3

| Método | Tabela destino | Estratégia | SQL / Fonte |
|---|---|---|---|
| `popular_funcionarios` | `funcionario_unidade_educacional` | `upsert_incremental` | `SQL_FUNCIONARIOS_UNIDADE_EDUCACIONAL` |

## Dados desnormalizados na atribuição de aula

Cada atribuição carrega, junto de si, os dados de DRE, UE, tipo de turma,
modalidade, semestre e turno. Isso evita recompor a hierarquia DRE → UE → turma
ao responder a abrangência de turmas do funcionário. DRE e UE vêm do cadastro de
unidades do EOL — a DRE é a unidade administrativa de referência da UE.

Modalidade, código de modalidade e semestre são **derivados** da etapa de ensino
e do tipo de turma da turma atribuída:

| Campo | Regra de domínio |
| :--- | :--- |
| `modalidade` / `codigo_modalidade` | classifica a turma em Fundamental, Médio ou EJA a partir da etapa de ensino e do tipo de turma |
| `semestre` | turmas de EJA recebem 1º ou 2º semestre conforme o mês de início; as demais não têm semestre |

## Filtro incremental por ano letivo

A carga das atribuições (SME e externas) pode ser restrita a um ano letivo em
diante, em vez de recarregar todo o histórico. Sem o filtro, a carga é completa.
Ver [Comando](comando.md).

## Observações

- Domínios externos (DRE, TipoEscola, ComponenteCurricular, Cargo, etc.) **não são carregados**
  como tabelas próprias; apenas seus IDs são armazenados nos campos `codigo_*` dos modelos acima.
  **Exceção:** a atribuição de aula desnormaliza nome/abreviação de DRE e nome da UE
  (ver seção acima), para servir a abrangência de turmas sem recompor a hierarquia.
- `_TABELAS_UPSERT` no comando `etl_professores` define quais tabelas registram
  `modo_escrita="upsert"` em `EtlExecucaoTabelaEscrita`.
- As 4 tabelas `full_refresh` não possuem chave natural para hash por linha —
  o controle de mudanças é feito via recarga completa em transação.
