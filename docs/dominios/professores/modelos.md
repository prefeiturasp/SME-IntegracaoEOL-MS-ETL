# Modelos do App `professores`

Modelos atuais de `apps/professores/models.py`.

> **Princípio:** apenas IDs são armazenados para referências a domínios externos.
> Descrições e nomes são resolvidos pelo Transition Gateway em tempo de resposta.

## Servidores Efetivos

### Professor

- **db_table:** `professor`
- **Fonte EOL:** `v_servidor_cotic`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_rf` | `CharField` | max_length=20; primary_key=True |
| `nome` | `CharField` | max_length=200 |
| `nome_social` | `CharField` | max_length=200; null=True |
| `cpf` | `CharField` | max_length=50; null=True (para compatibilidade com legado) |

---

### CargoBaseServidor

- **db_table:** `cargo_base_servidor`
- **Fonte EOL:** `v_cargo_base_cotic`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `professor` | `ForeignKey` | → Professor; db_column=`codigo_rf` |
| `codigo_cargo` | `IntegerField` | ID do cargo (domínio RH) |
| `descricao_cargo` | `CharField` | max_length=100; null=True |
| `situacao_funcional` | `IntegerField` | null=True |
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
| `codigo_unidade_educacao` | `CharField` | max_length=20 — ID da unidade educacional |
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
| `nome_pai` | `CharField` | max_length=200; null=True |
| `nome_mae` | `CharField` | max_length=200; null=True |
| `data_nascimento` | `DateField` | null=True |
| `rg` | `CharField` | max_length=30; null=True |
| `titulo_eleitoral` | `CharField` | max_length=30; null=True |
| `pis_pasep` | `CharField` | max_length=30; null=True |

---

### ContratoExterno

- **db_table:** `contrato_externo`
- **Fonte EOL:** `contrato_externo`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_contrato` | `BigIntegerField` | primary_key=True |
| `pessoa` | `ForeignKey` | → Pessoa |
| `codigo_tipo_funcao` | `IntegerField` | ID do tipo de função (domínio funcional) |
| `codigo_unidade_educacao` | `CharField` | max_length=20 — ID da unidade educacional |
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
| `codigo_turma_escola` | `BigIntegerField` | null=True — ID da turma escolar |
| `codigo_turma_escola_grade_programa` | `BigIntegerField` | null=True — ID da grade/programa da turma |
| `descricao_turma_escola` | `CharField` | max_length=200; null=True |
| `codigo_grade` | `IntegerField` | ID da grade (domínio pedagógico) |
| `codigo_componente_curricular` | `IntegerField` | ID do componente curricular |
| `descricao_componente_curricular` | `CharField` | max_length=200; null=True |
| `codigo_serie_grade` | `IntegerField` | null=True — ID de série-grade |
| `ano_escolar` | `CharField` | max_length=5; null=True |
| `ano_atribuicao` | `IntegerField` | |
| `codigo_etapa_ensino` | `IntegerField` | null=True |
| `dt_atribuicao_aula` | `DateField` | |
| `dt_disponibilizacao_aulas` | `DateField` | null=True |
| `dt_inicio_turma` | `DateField` | null=True — início da turma |
| `dt_fim_turma` | `DateField` | null=True — fim da turma |
| `codigo_motivo_disponibilizacao` | `IntegerField` | null=True |
| `dt_cancelamento` | `DateField` | null=True — IS NULL = ativa |
| `codigo_dre` | `CharField` | max_length=20; null=True — ID da DRE (domínio institucional) |
| `nome_dre` | `CharField` | max_length=200; null=True |
| `abreviacao_dre` | `CharField` | max_length=100; null=True |
| `nome_unidade_educacional` | `CharField` | max_length=200; null=True |
| `codigo_tipo_escola` | `IntegerField` | null=True |
| `codigo_tipo_turma` | `IntegerField` | null=True |
| `modalidade` | `CharField` | max_length=50; null=True — derivada (ver mapeamento) |
| `codigo_modalidade` | `IntegerField` | null=True — derivada (ver mapeamento) |
| `semestre` | `IntegerField` | null=True — derivada (ver mapeamento) |
| `duracao_turno` | `IntegerField` | null=True |
| `tipo_turno` | `IntegerField` | null=True |

Índices: `codigo_unidade_educacao`, `codigo_turma_escola`, `codigo_componente_curricular`, `ano_atribuicao`, `dt_cancelamento`.

> Dados de DRE/UE, modalidade, semestre e turno são **desnormalizados** na
> atribuição para que a abrangência de turmas do funcionário seja respondida sem
> recompor a hierarquia DRE → UE → turma no serviço de consumo. Regras de
> derivação em [Mapeamento ETL](mapeamento_etl.md).

---

### AtribuicaoExterno

- **db_table:** `atribuicao_externo`
- **Fonte EOL:** `atribuicao_externo`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `contrato_externo` | `ForeignKey` | → ContratoExterno |
| `codigo_unidade_educacao` | `CharField` | max_length=20 |
| `codigo_turma_escola` | `BigIntegerField` | null=True — ID da turma escolar |
| `descricao_turma_escola` | `CharField` | max_length=200; null=True |
| `codigo_grade` | `IntegerField` | ID da grade (domínio pedagógico) |
| `codigo_componente_curricular` | `IntegerField` | ID do componente curricular |
| `descricao_componente_curricular` | `CharField` | max_length=200; null=True |
| `codigo_serie_grade` | `IntegerField` | null=True — ID de série-grade |
| `codigo_turma_escola_grade_programa` | `BigIntegerField` | null=True — ID da grade/programa da turma |
| `ano_escolar` | `CharField` | max_length=5; null=True |
| `ano_atribuicao` | `IntegerField` | |
| `codigo_etapa_ensino` | `IntegerField` | null=True |
| `dt_atribuicao` | `DateField` | |
| `dt_disponibilizacao` | `DateField` | null=True |
| `dt_inicio_turma` | `DateField` | null=True |
| `codigo_motivo_disponibilizacao_externo` | `IntegerField` | null=True |
| `dt_cancelamento` | `DateField` | null=True — IS NULL = ativa |

Índices: `codigo_unidade_educacao`, `codigo_turma_escola`, `codigo_componente_curricular`, `ano_atribuicao`, `dt_cancelamento`.

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
| `data_inicio` | `DateTimeField` | default=1900-01-01 UTC |
| `data_fim` | `DateTimeField` | null=True |
| `codigo_cargo` | `IntegerField` | null=True |
| `cargo` | `CharField` | max_length=100; null=True |
| `codigo_tipo_funcao_atividade` | `IntegerField` | default=0 |
| `pessoa` | `ForeignKey` | -> Pessoa; null=True; db_constraint=False |
| `nome_ue` | `CharField` | max_length=200; null=True |
| `tipo_funcionario_externo` | `CharField` | max_length=100; null=True |
| `dc_funcao_externo` | `CharField` | max_length=100; null=True |
| `supervisor_dre` | `BooleanField` | default=False |
| `eh_professor` | `BooleanField` | default=False; interno |
| `esta_afastado` | `BooleanField` | default=False |
| `funcao_externo` | `IntegerField` | default=0 |
| `tipo_funcao_externo` | `IntegerField` | default=0 |

Indices: `codigo_ue`, `codigo_cargo`, `codigo_rf`, `(codigo_ue, codigo_cargo)`.
Restricao unica: `(codigo_rf, codigo_ue, codigo_cargo,
codigo_tipo_funcao_atividade, data_inicio, data_fim, funcao_externo,
tipo_funcao_externo)` para permitir múltiplos vínculos do mesmo servidor sem
sobrescrever registros no upsert.

Alimenta a consulta de funcionários por unidade educacional, filtrável por
cargo. É a única fonte dessa consulta — não recompõe vínculos em tempo de
resposta.

---

### FuncionarioSistemaPerfil

- **db_table:** `funcionario_sistema_perfil`
- **Fonte CoreSSO:** `SQL_FUNCIONARIO_SISTEMA_PERFIL`
- **Estrategia:** `upsert_incremental`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `login` | `CharField` | max_length=500 |
| `nome_servidor` | `CharField` | max_length=200; null=True |
| `cpf` | `CharField` | max_length=14; null=True |
| `email` | `CharField` | max_length=500; null=True |
| `uad_codigo` | `CharField` | max_length=20; null=True |
| `perfil` | `UUIDField` | grupo/perfil do sistema |
| `sis_id` | `IntegerField` | sistema de origem do perfil |

Indices: `login`, `sis_id`, `perfil`.
Restricao unica: `(login, perfil, sis_id)`.

A carga considera atualmente o SGP (`sis_id = 1000`) para manter
compatibilidade com a API legada. Quando a origem retorna a mesma combinacao
de `login`, `perfil` e `sis_id` com e sem UAD, a carga preserva a linha unica com `uad_codigo` preenchido.

---

### TurmaAtribuidaUe

Turmas sob abrangência de um servidor pelo **vínculo com a UE** (lotação/cargo),
não pelas aulas que leciona. Um gestor de UE (por exemplo, diretor ou CP) enxerga
todas as turmas da unidade onde está lotado, mesmo sem atribuição de aula.

Esse conjunto existe para preservar a visão de abrangência que nasce do vínculo
administrativo com a unidade, separada da visão de aulas atribuídas.

| Campo | Tipo | Detalhes |
|---|---|---|
| `usuario_rf` | `CharField` | RF do servidor — filtro principal |
| `cargo` / `cargo_sobreposto` | `IntegerField` | cargo do vínculo (null=True) |
| `codigo_escola` | `CharField` | UE da turma |
| `codigo_dre` | `CharField` | DRE da turma (null=True) |
| `codigo_turma` | `BigIntegerField` | turma |
| demais campos | | metadados da turma (modalidade, semestre, turno, tipo de escola, etc.) |

Os recortes por UE, DRE e cargo são aplicados pelos consumidores conforme o
perfil informado.

---

### DisciplinaTurmaAtribuidaUe

Componentes disponíveis em cada turma sob abrangência de UE do servidor —
responde "quais disciplinas o funcionário vê nesta turma". A tabela mantém
cardinalidade por `RF + turma + componente`, separada de `turma_atribuida_ue`
para não duplicar a abrangência de turmas.

| Campo | Tipo | Detalhes |
|---|---|---|
| `usuario_rf` | `CharField` | RF do servidor |
| `codigo_escola` | `CharField` | UE da turma |
| `codigo_turma` | `BigIntegerField` | turma |
| `ano_letivo` | `IntegerField` | ano letivo da turma |
| `codigo_componente_curricular` | `IntegerField` | componente |
| `descricao_componente_curricular` | `CharField` | nome do componente na origem |
| `codigo_componente_curricular_pai` | `IntegerField` | null=True |
| `regencia` | `BooleanField` | default=False |
| `codigo_componente_territorio_saber` | `IntegerField` | null=True |
| `territorio_saber` | `BooleanField` | default=False |
| `codigo_dre` | `CharField` | DRE da turma (null=True) |
| `codigo_tipo_escola` / `tipo_escola` | | tipo de escola da turma |
| `cargo` / `cargo_sobreposto` | `IntegerField` | cargo do vínculo (null=True) |

Esse conjunto atende consultas de disciplinas por abrangência de unidade. A
expansão de planejamento por regência permanece fora deste modelo.
