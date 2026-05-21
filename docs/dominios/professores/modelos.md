# Modelos do App `professores`

Modelos atuais de `apps/professores/models.py`.

> **Princípio:** apenas IDs são armazenados para referências a domínios externos.
> Descrições e nomes são resolvidos pelo Transition Gateway em tempo de resposta.

---

## Tabelas de Suporte

### UnidadeEducacional

- **db_table:** `unidade_educacional`
- **Fonte EOL:** `v_cadastro_unidade_educacao`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_ue` | `CharField` | max_length=20; primary_key=True |
| `codigo_dre` | `CharField` | max_length=20; null=True — ID da DRE (domínio institucional) |
| `codigo_tipo_escola` | `IntegerField` | null=True — ID do tipo de escola |

Índices: `codigo_dre`, `codigo_tipo_escola`.

---

### TurmaEscola

- **db_table:** `turma_escola`
- **Fonte EOL:** `turma_escola`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_turma` | `BigIntegerField` | primary_key=True |
| `codigo_escola` | `CharField` | max_length=20 — ref. `UnidadeEducacional` |
| `ano_letivo` | `IntegerField` | |
| `status` | `CharField` | max_length=1 — `'O'`=Aberta, `'A'`=Ativa, `'E'`=Extinta, `'C'`=Cancelada |
| `dt_fim_turma` | `DateField` | null=True |
| `dt_fim` | `DateField` | null=True |

Índices: `codigo_escola`, `ano_letivo`, `status`, `(codigo_escola, ano_letivo)`.

---

### SerieTurmaGrade

- **db_table:** `serie_turma_grade`
- **Fonte EOL:** `serie_turma_grade`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_serie_grade` | `IntegerField` | primary_key=True |
| `codigo_turma` | `BigIntegerField` | ref. `TurmaEscola` neste DB |
| `codigo_escola` | `CharField` | max_length=20 — ref. `UnidadeEducacional` |
| `codigo_escola_grade` | `IntegerField` | ID da escola_grade (domínio pedagógico) |
| `dt_fim` | `DateField` | null=True — IS NULL = ativo |

Índices: `codigo_turma`, `dt_fim`, `codigo_escola`.

---

### TurmaEscolaGradePrograma

- **db_table:** `turma_escola_grade_programa`
- **Fonte EOL:** `turma_escola_grade_programa`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo` | `BigIntegerField` | primary_key=True |
| `codigo_turma` | `BigIntegerField` | ref. `TurmaEscola` neste DB |
| `codigo_escola_grade` | `IntegerField` | ID da escola_grade (domínio pedagógico) |
| `dt_fim` | `DateField` | null=True |

Índices: `codigo_turma`.

---

### TurmaGradeTerritorioExperiencia

- **db_table:** `turma_grade_territorio_experiencia`
- **Fonte EOL:** `turma_grade_territorio_experiencia`
- **Estratégia:** full_refresh (sem chave natural)

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `codigo_serie_grade` | `IntegerField` | ref. `SerieTurmaGrade` neste DB |
| `codigo_componente_curricular` | `IntegerField` | ID do componente (domínio curricular) |
| `codigo_territorio_saber` | `IntegerField` | ID do território do saber (domínio pedagógico) |
| `codigo_experiencia_pedagogica` | `IntegerField` | ID da experiência pedagógica (domínio pedagógico) |
| `dt_inicio` | `DateField` | null=True |

Índices: `codigo_serie_grade`, `codigo_componente_curricular`.

---

### AgrupamentoAtribuicaoTerritorioSaber

- **db_table:** `agrupamento_atribuicao_territorio_saber`
- **Fonte:** ApiEolConnection (integração pendente — não carregada pelo ETL atual)

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_agrupamento` | `BigIntegerField` | primary_key=True |
| `codigo_territorio_saber` | `IntegerField` | null=True — ID do território |
| `codigo_experiencia_pedagogica` | `IntegerField` | null=True — ID da experiência |
| `dt_inicio_atribuicao` | `DateField` | null=True |
| `ano_atribuicao` | `IntegerField` | null=True |
| `dt_fim_atribuicao` | `DateField` | null=True |
| `dt_fim_turma` | `DateField` | null=True |
| `rf_professor` | `CharField` | max_length=20; null=True — ref. `Professor.codigo_rf` |
| `codigo_turma` | `BigIntegerField` | null=True — ref. `TurmaEscola` |
| `codigos_componentes_curriculares` | `TextField` | null=True — IDs separados por vírgula |
| `ano_letivo` | `IntegerField` | null=True |
| `codigo_motivo_disponibilizacao` | `IntegerField` | null=True |
| `encerramento_atribuicao_agrupamento_atualizado` | `BooleanField` | null=True |
| `criado_em` | `DateTimeField` | null=True |
| `alterado_em` | `DateTimeField` | null=True |

Índices: `rf_professor`, `codigo_turma`, `ano_letivo`.

---

## Servidores Efetivos

### Professor

- **db_table:** `professor`
- **Fonte EOL:** `v_servidor_cotic`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_rf` | `CharField` | max_length=20; primary_key=True |
| `nome` | `CharField` | max_length=200 |
| `nome_social` | `CharField` | max_length=200; null=True |

---

### CargoBaseServidor

- **db_table:** `cargo_base_servidor`
- **Fonte EOL:** `v_cargo_base_cotic`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `professor` | `ForeignKey` | → Professor; db_column=`codigo_rf` |
| `codigo_cargo` | `IntegerField` | ID do cargo (domínio RH) |
| `dt_posse` | `DateField` | null=True |
| `dt_fim_nomeacao` | `DateField` | null=True — IS NULL = nomeação ativa |
| `dt_cancelamento` | `DateField` | null=True |

Índices: `professor`, `codigo_cargo`, `dt_fim_nomeacao`.

---

### LotacaoServidor

- **db_table:** `lotacao_servidor`
- **Fonte EOL:** `lotacao_servidor`
- **Estratégia:** full_refresh

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `cargo_base` | `ForeignKey` | → CargoBaseServidor |
| `codigo_unidade_educacao` | `CharField` | max_length=20 — ref. `UnidadeEducacional` |
| `dt_inicio` | `DateField` | null=True |
| `dt_fim` | `DateField` | null=True — IS NULL = ativo |

Índices: `codigo_unidade_educacao`, `dt_fim`.

---

### CargoSobrepostoServidor

- **db_table:** `cargo_sobreposto_servidor`
- **Fonte EOL:** `cargo_sobreposto_servidor`
- **Estratégia:** full_refresh

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `cargo_base` | `ForeignKey` | → CargoBaseServidor |
| `codigo_cargo` | `IntegerField` | ID do cargo sobreposto (domínio RH) |
| `codigo_unidade_local_servico` | `CharField` | max_length=20 — UE onde é exercido |
| `dt_fim_cargo_sobreposto` | `DateField` | null=True — IS NULL = impede atribuição |

Índices: `dt_fim_cargo_sobreposto`.

> Cargos sobrepostos que **não** impedem atribuição: `3379`, `3085`, `3360`.

---

### FuncaoAtividadeCargoServidor

- **db_table:** `funcao_atividade_cargo_servidor`
- **Fonte EOL:** `funcao_atividade_cargo_servidor`
- **Estratégia:** full_refresh

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `cargo_base` | `ForeignKey` | → CargoBaseServidor |
| `codigo_unidade_local_servico` | `CharField` | max_length=20 — UE onde a função é exercida |
| `dt_fim_funcao_atividade` | `DateField` | null=True — IS NULL = ativo |

---

### LaudoMedico

- **db_table:** `laudo_medico`
- **Fonte EOL:** `laudo_medico`
- **Estratégia:** full_refresh

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `cargo_base` | `ForeignKey` | → CargoBaseServidor |

> Existência de registro = servidor impedido de receber atribuição de aulas.

---

## Contratados Externos

### Pessoa

- **db_table:** `pessoa`
- **Fonte EOL:** `pessoa`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_pessoa` | `BigIntegerField` | primary_key=True |
| `cpf` | `CharField` | max_length=14; unique=True |
| `nome` | `CharField` | max_length=200 |
| `nome_social` | `CharField` | max_length=200; null=True |

---

### ContratoExterno

- **db_table:** `contrato_externo`
- **Fonte EOL:** `contrato_externo`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_contrato` | `BigIntegerField` | primary_key=True |
| `pessoa` | `ForeignKey` | → Pessoa |
| `codigo_tipo_funcao` | `IntegerField` | ID do tipo de função (domínio funcional) |
| `codigo_unidade_educacao` | `CharField` | max_length=20 — ref. `UnidadeEducacional` |
| `dt_cancelamento` | `DateField` | null=True — IS NULL = ativo |
| `codigo_motivo_desligamento` | `IntegerField` | null=True |

Índices: `codigo_unidade_educacao`, `dt_cancelamento`.

---

## Atribuições

### AtribuicaoAula

- **db_table:** `atribuicao_aula`
- **Fonte EOL:** `atribuicao_aula`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `cargo_base` | `ForeignKey` | → CargoBaseServidor |
| `codigo_unidade_educacao` | `CharField` | max_length=20 |
| `codigo_turma_escola` | `BigIntegerField` | null=True — ref. `TurmaEscola` |
| `codigo_turma_escola_grade_programa` | `BigIntegerField` | null=True — ref. `TurmaEscolaGradePrograma` |
| `codigo_grade` | `IntegerField` | ID da grade (domínio pedagógico) |
| `codigo_componente_curricular` | `IntegerField` | ID do componente curricular |
| `codigo_serie_grade` | `IntegerField` | ref. `SerieTurmaGrade` |
| `ano_atribuicao` | `IntegerField` | |
| `dt_atribuicao_aula` | `DateField` | |
| `dt_disponibilizacao_aulas` | `DateField` | null=True |
| `codigo_motivo_disponibilizacao` | `IntegerField` | null=True |
| `dt_cancelamento` | `DateField` | null=True — IS NULL = ativa |

Índices: `codigo_unidade_educacao`, `codigo_turma_escola`, `codigo_componente_curricular`, `ano_atribuicao`, `dt_cancelamento`.

---

### AtribuicaoExterno

- **db_table:** `atribuicao_externo`
- **Fonte EOL:** `atribuicao_externo`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `contrato_externo` | `ForeignKey` | → ContratoExterno |
| `codigo_unidade_educacao` | `CharField` | max_length=20 |
| `codigo_grade` | `IntegerField` | ID da grade (domínio pedagógico) |
| `codigo_componente_curricular` | `IntegerField` | ID do componente curricular |
| `codigo_serie_grade` | `IntegerField` | ref. `SerieTurmaGrade` |
| `codigo_turma_escola_grade_programa` | `BigIntegerField` | null=True — ref. `TurmaEscolaGradePrograma` |
| `ano_atribuicao` | `IntegerField` | |
| `dt_atribuicao` | `DateField` | |
| `dt_disponibilizacao` | `DateField` | null=True |
| `codigo_motivo_disponibilizacao_externo` | `IntegerField` | null=True |
| `dt_cancelamento` | `DateField` | null=True — IS NULL = ativa |

Índices: `codigo_unidade_educacao`, `codigo_componente_curricular`, `ano_atribuicao`, `dt_cancelamento`.

---

## Consulta Consolidada

### FuncionarioUnidadeEducacional

- **db_table:** `funcionario_unidade_educacional`
- **Fonte EOL:** `SQL_FUNCIONARIOS_UNIDADE_EDUCACIONAL`
- **Estrategia:** `upsert_incremental`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `nome` | `CharField` | max_length=200 |
| `nome_social` | `CharField` | max_length=200; null=True; nao exposto na API |
| `cpf` | `CharField` | max_length=14; null=True; nao exposto na API |
| `codigo_rf` | `CharField` | max_length=20; RF ou CPF para externo |
| `codigo_ue` | `CharField` | max_length=20; filtro principal da API |
| `data_inicio` | `DateTimeField` | null=True |
| `data_fim` | `DateTimeField` | null=True |
| `codigo_cargo` | `CharField` | max_length=20; null=True |
| `cargo` | `CharField` | max_length=100; null=True |
| `codigo_tipo_funcao_atividade` | `IntegerField` | default=0 |
| `eh_professor` | `BooleanField` | default=False; interno |
| `esta_afastado` | `BooleanField` | default=False |
| `funcao_externo` | `IntegerField` | default=0 |
| `tipo_funcao_externo` | `IntegerField` | default=0 |

Indices: `codigo_ue`, `codigo_cargo`, `codigo_rf`, `(codigo_ue, codigo_cargo)`.
Restricao unica: `(codigo_rf, codigo_ue)` para permitir o mesmo servidor em
mais de uma UE sem sobrescrever registros no upsert.

O endpoint `GET /api/v1/professores/escolas/{codigo_ue}/funcionarios/`
consulta apenas esta tabela no `professores_db`. O filtro `codigo_cargo` e
opcional por query string.
