# Mapeamento ETL (Origem -> Destino)

Documenta os grupos de dados carregados para o domínio de professores e suas
dependencias conceituais.

## Fase 1 — sem dependências internas

| Grupo | Destino | Estratégia | Origem |
|---|---|---|---|
| Professores | `professor` | incremental | servidores |
| Pessoas | `pessoa` | incremental | pessoas |

## Fase 2 — dependem da Fase 1

| Grupo | Destino | Estratégia | Origem |
|---|---|---|---|
| Cargos base | `cargo_base_servidor` | incremental | cargos dos servidores |
| Contratos externos | `contrato_externo` | incremental | contratos externos |

## Fase 3 — dependem da Fase 2

| Grupo | Destino | Estratégia | Origem |
|---|---|---|---|
| Lotacoes | `lotacao_servidor` | completa | lotacoes |
| Cargos sobrepostos | `cargo_sobreposto_servidor` | completa | cargos sobrepostos |
| Funcoes de atividade | `funcao_atividade_cargo_servidor` | completa | funcoes de atividade |
| Laudos | `laudo_medico` | completa | laudos |
| Atribuicoes de aula | `atribuicao_aula` | incremental | atribuicoes de aula |
| Atribuicoes externas | `atribuicao_externo` | incremental | atribuicoes externas |

## Fase 4 — dependem das Fases 1–3

| Grupo | Destino | Estratégia | Origem |
|---|---|---|---|
| Funcionarios por unidade | `funcionario_unidade_educacional` | incremental | vinculos de servidor com unidade |
| Turmas por abrangencia de unidade | `turma_atribuida_ue` | completa | turmas associadas ao vinculo de unidade |
| Componentes por abrangencia de unidade | `disciplina_turma_atribuida_ue` | completa | componentes disponiveis nas turmas abrangidas |

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
- Cargas incrementais atualizam registros identificaveis sem recompor todo o
  historico.
- Cargas completas recriam conjuntos consolidados quando o dado de origem nao
  oferece uma chave natural estavel para controle linha a linha.
