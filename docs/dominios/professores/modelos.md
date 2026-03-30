# Modelos do App `professores`

A seguir, os modelos atuais de `apps/professores/models.py`.

## DRE

- **db_table:** `dre`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_dre` | `CharField` | max_length=20; primary_key=True |
| `nome` | `CharField` | max_length=200 |
| `sigla` | `CharField` | max_length=20; null=True; blank=True |

## TipoEscola

- **db_table:** `tipo_escola`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_tipo_escola` | `IntegerField` | primary_key=True |
| `descricao` | `CharField` | max_length=200 |
| `sigla` | `CharField` | max_length=20; null=True; blank=True |

## UnidadeEducacional

- **db_table:** `unidade_educacional`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_ue` | `CharField` | max_length=20; primary_key=True |
| `nome` | `CharField` | max_length=200 |
| `sigla` | `CharField` | max_length=50; null=True; blank=True |
| `dre` | `ForeignKey` | DRE; on_delete=models.CASCADE; related_name='unidades'; db_column='codigo_dre' |
| `nome_dre` | `CharField` | max_length=200 |
| `sigla_dre` | `CharField` | max_length=20; null=True; blank=True |
| `tipo_escola` | `ForeignKey` | TipoEscola; on_delete=models.SET_NULL; null=True; blank=True; related_name='unidades'; db_column='codigo_tipo_escola' |
| `sigla_tipo_escola` | `CharField` | max_length=20; null=True; blank=True |

## ComponenteCurricular

- **db_table:** `componente_curricular`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo` | `IntegerField` | primary_key=True |
| `descricao` | `CharField` | max_length=200 |
| `dt_cancelamento` | `DateField` | null=True; blank=True |

## SerieEnsino

- **db_table:** `serie_ensino`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_serie` | `IntegerField` | primary_key=True |
| `sigla_resumida` | `CharField` | max_length=20; null=True; blank=True; help_text='sg_resumida_serie — exibida como AnoTurma nas queries.' |

## TerritorioSaber

- **db_table:** `territorio_saber`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_territorio` | `IntegerField` | primary_key=True |
| `descricao` | `CharField` | max_length=200 |

## TipoExperienciaPedagogica

- **db_table:** `tipo_experiencia_pedagogica`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_experiencia` | `IntegerField` | primary_key=True |
| `descricao` | `CharField` | max_length=200 |

## Grade

- **db_table:** `grade`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_grade` | `IntegerField` | primary_key=True |
| `codigo_serie_ensino` | `IntegerField` | help_text='Ref. SerieEnsino.codigo_serie neste DB.' |
| `codigo_tipo_turno` | `IntegerField` | null=True; blank=True |

## EscolaGrade

- **db_table:** `escola_grade`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_escola_grade` | `IntegerField` | primary_key=True |
| `codigo_escola` | `CharField` | max_length=20; help_text='Ref. UnidadeEducacional.codigo_ue neste DB.' |
| `grade` | `ForeignKey` | Grade; on_delete=models.CASCADE; related_name='escola_grades'; db_column='codigo_grade' |

## TurmaEscola

- **db_table:** `turma_escola`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_turma` | `BigIntegerField` | primary_key=True |
| `codigo_escola` | `CharField` | max_length=20; help_text='Ref. UnidadeEducacional.codigo_ue neste DB.' |
| `ano_letivo` | `IntegerField` |  |
| `nome_turma` | `CharField` | max_length=200 |
| `codigo_tipo_turma` | `IntegerField` | help_text='1=Regular, 3=Programa.' |
| `codigo_duracao` | `IntegerField` | null=True; blank=True |
| `codigo_tipo_turno` | `IntegerField` | null=True; blank=True |
| `status` | `CharField` | max_length=1; help_text="'O'=Aberta, 'A'=Ativa, 'E'=Extinta, 'C'=Cancelada." |
| `dt_inicio_turma` | `DateField` | null=True; blank=True |
| `dt_fim_turma` | `DateField` | null=True; blank=True |
| `dt_fim` | `DateField` | null=True; blank=True |

## SerieTurmaGrade

- **db_table:** `serie_turma_grade`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_serie_grade` | `IntegerField` | primary_key=True |
| `turma` | `ForeignKey` | TurmaEscola; on_delete=models.CASCADE; related_name='serie_grades'; db_column='codigo_turma' |
| `codigo_escola` | `CharField` | max_length=20; help_text='Ref. UnidadeEducacional.codigo_ue neste DB.' |
| `escola_grade` | `ForeignKey` | EscolaGrade; on_delete=models.SET_NULL; null=True; blank=True; related_name='serie_turma_grades'; db_column='codigo_escola_grade' |
| `dt_fim` | `DateField` | null=True; blank=True |

## TurmaEscolaGradePrograma

- **db_table:** `turma_escola_grade_programa`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo` | `BigIntegerField` | primary_key=True |
| `turma` | `ForeignKey` | TurmaEscola; on_delete=models.CASCADE; related_name='grade_programas'; db_column='codigo_turma' |
| `escola_grade` | `ForeignKey` | EscolaGrade; on_delete=models.CASCADE; related_name='turma_programas'; db_column='codigo_escola_grade' |
| `dt_fim` | `DateField` | null=True; blank=True |

## TurmaGradeTerritorioExperiencia

- **db_table:** `turma_grade_territorio_experiencia`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `serie_grade` | `ForeignKey` | SerieTurmaGrade; on_delete=models.CASCADE; related_name='territorios_experiencias'; db_column='codigo_serie_grade' |
| `codigo_componente_curricular` | `IntegerField` | help_text='Ref. ComponenteCurricular.codigo neste DB.' |
| `territorio_saber` | `ForeignKey` | TerritorioSaber; on_delete=models.CASCADE; related_name='grade_territorios'; db_column='codigo_territorio' |
| `experiencia_pedagogica` | `ForeignKey` | TipoExperienciaPedagogica; on_delete=models.CASCADE; related_name='grade_experiencias'; db_column='codigo_experiencia' |
| `dt_inicio` | `DateField` | null=True; blank=True |

## AgrupamentoAtribuicaoTerritorioSaber

- **db_table:** `agrupamento_atribuicao_territorio_saber`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_agrupamento` | `BigIntegerField` | primary_key=True |
| `codigo_territorio_saber` | `IntegerField` | null=True; blank=True |
| `codigo_experiencia_pedagogica` | `IntegerField` | null=True; blank=True |
| `dt_inicio_atribuicao` | `DateField` | null=True; blank=True |
| `ano_atribuicao` | `IntegerField` | null=True; blank=True |
| `dt_fim_atribuicao` | `DateField` | null=True; blank=True |
| `dt_fim_turma` | `DateField` | null=True; blank=True |
| `rf_professor` | `CharField` | max_length=20; null=True; blank=True; help_text='Ref. Professor.codigo_rf neste DB.' |
| `codigo_turma` | `BigIntegerField` | null=True; blank=True; help_text='Ref. TurmaEscola.codigo_turma neste DB.' |
| `codigos_componentes_curriculares` | `TextField` | null=True; blank=True; help_text='Lista de códigos separados por vírgula.' |
| `ano_letivo` | `IntegerField` | null=True; blank=True |
| `codigo_motivo_disponibilizacao` | `IntegerField` | null=True; blank=True |
| `descricao_territorio_saber` | `CharField` | max_length=200; null=True; blank=True |
| `descricao_experiencia_pedagogica` | `CharField` | max_length=200; null=True; blank=True |
| `encerramento_atribuicao_agrupamento_atualizado` | `BooleanField` | null=True; blank=True |
| `criado_em` | `DateTimeField` | null=True; blank=True |
| `alterado_em` | `DateTimeField` | null=True; blank=True |

## Cargo

- **db_table:** `cargo`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_cargo` | `IntegerField` | primary_key=True |
| `descricao` | `CharField` | max_length=200 |

## Professor

- **db_table:** `professor`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_rf` | `CharField` | max_length=20; primary_key=True |
| `nome` | `CharField` | max_length=200 |
| `nome_social` | `CharField` | max_length=200; null=True; blank=True |

## CargoBaseServidor

- **db_table:** `cargo_base_servidor`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `professor` | `ForeignKey` | Professor; on_delete=models.CASCADE; related_name='cargos_base'; db_column='codigo_rf' |
| `cargo` | `ForeignKey` | Cargo; on_delete=models.CASCADE; related_name='servidores' |
| `dt_posse` | `DateField` | null=True; blank=True |
| `dt_fim_nomeacao` | `DateField` | null=True; blank=True |
| `dt_cancelamento` | `DateField` | null=True; blank=True |

## LotacaoServidor

- **db_table:** `lotacao_servidor`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `cargo_base` | `ForeignKey` | CargoBaseServidor; on_delete=models.CASCADE; related_name='lotacoes' |
| `codigo_unidade_educacao` | `CharField` | max_length=20; help_text='Ref. UnidadeEducacional.codigo_ue neste DB.' |
| `dt_inicio` | `DateField` | null=True; blank=True |
| `dt_fim` | `DateField` | null=True; blank=True |

## CargoSobrepostoServidor

- **db_table:** `cargo_sobreposto_servidor`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `cargo_base` | `ForeignKey` | CargoBaseServidor; on_delete=models.CASCADE; related_name='cargos_sobrepostos' |
| `cargo` | `ForeignKey` | Cargo; on_delete=models.CASCADE; related_name='sobreposicoes' |
| `codigo_unidade_local_servico` | `CharField` | max_length=20; help_text='UE onde o cargo sobreposto é exercido.' |
| `dt_fim_cargo_sobreposto` | `DateField` | null=True; blank=True |

## FuncaoAtividadeCargoServidor

- **db_table:** `funcao_atividade_cargo_servidor`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `cargo_base` | `ForeignKey` | CargoBaseServidor; on_delete=models.CASCADE; related_name='funcoes_atividade' |
| `codigo_unidade_local_servico` | `CharField` | max_length=20; help_text='UE onde a função é exercida.' |
| `dt_fim_funcao_atividade` | `DateField` | null=True; blank=True |

## LaudoMedico

- **db_table:** `laudo_medico`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `cargo_base` | `ForeignKey` | CargoBaseServidor; on_delete=models.CASCADE; related_name='laudos_medicos' |

## FuncaoFuncionarioExterno

- **db_table:** `funcao_funcionario_externo`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_tipo_funcao` | `IntegerField` | primary_key=True |
| `descricao` | `CharField` | max_length=200 |
| `dt_cancelamento` | `DateField` | null=True; blank=True |

## Pessoa

- **db_table:** `pessoa`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_pessoa` | `BigIntegerField` | primary_key=True |
| `cpf` | `CharField` | max_length=14; unique=True |
| `nome` | `CharField` | max_length=200 |
| `nome_social` | `CharField` | max_length=200; null=True; blank=True |

## ContratoExterno

- **db_table:** `contrato_externo`

| Campo | Tipo | Detalhes |
|---|---|---|
| `codigo_contrato` | `BigIntegerField` | primary_key=True |
| `pessoa` | `ForeignKey` | Pessoa; on_delete=models.CASCADE; related_name='contratos' |
| `tipo_funcao` | `ForeignKey` | FuncaoFuncionarioExterno; on_delete=models.CASCADE; related_name='contratos' |
| `codigo_unidade_educacao` | `CharField` | max_length=20; help_text='Ref. UnidadeEducacional.codigo_ue neste DB.' |
| `dt_cancelamento` | `DateField` | null=True; blank=True |
| `codigo_motivo_desligamento` | `IntegerField` | null=True; blank=True |

## AtribuicaoAula

- **db_table:** `atribuicao_aula`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `cargo_base` | `ForeignKey` | CargoBaseServidor; on_delete=models.CASCADE; related_name='atribuicoes' |
| `codigo_unidade_educacao` | `CharField` | max_length=20; help_text='Ref. UnidadeEducacional.codigo_ue neste DB.' |
| `codigo_turma_escola` | `BigIntegerField` | null=True; blank=True; help_text='Ref. TurmaEscola.codigo_turma neste DB.' |
| `codigo_turma_escola_grade_programa` | `BigIntegerField` | null=True; blank=True; help_text='Ref. TurmaEscolaGradePrograma.codigo neste DB.' |
| `codigo_grade` | `IntegerField` | help_text='Ref. Grade.codigo_grade neste DB.' |
| `codigo_componente_curricular` | `IntegerField` | help_text='Ref. ComponenteCurricular.codigo neste DB.' |
| `codigo_serie_grade` | `IntegerField` | help_text='Ref. SerieTurmaGrade.codigo_serie_grade neste DB.' |
| `ano_atribuicao` | `IntegerField` |  |
| `dt_atribuicao_aula` | `DateField` |  |
| `dt_disponibilizacao_aulas` | `DateField` | null=True; blank=True |
| `codigo_motivo_disponibilizacao` | `IntegerField` | null=True; blank=True |
| `dt_cancelamento` | `DateField` | null=True; blank=True |

## AtribuicaoExterno

- **db_table:** `atribuicao_externo`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | `BigAutoField` | primary_key=True |
| `contrato_externo` | `ForeignKey` | ContratoExterno; on_delete=models.CASCADE; related_name='atribuicoes' |
| `codigo_unidade_educacao` | `CharField` | max_length=20; help_text='Ref. UnidadeEducacional.codigo_ue neste DB.' |
| `codigo_grade` | `IntegerField` | help_text='Ref. Grade.codigo_grade neste DB.' |
| `codigo_componente_curricular` | `IntegerField` | help_text='Ref. ComponenteCurricular.codigo neste DB.' |
| `codigo_serie_grade` | `IntegerField` | help_text='Ref. SerieTurmaGrade.codigo_serie_grade neste DB.' |
| `codigo_turma_escola_grade_programa` | `BigIntegerField` | null=True; blank=True; help_text='Ref. TurmaEscolaGradePrograma.codigo neste DB.' |
| `ano_atribuicao` | `IntegerField` |  |
| `dt_atribuicao` | `DateField` |  |
| `dt_disponibilizacao` | `DateField` | null=True; blank=True |
| `codigo_motivo_disponibilizacao_externo` | `IntegerField` | null=True; blank=True |
| `dt_cancelamento` | `DateField` | null=True; blank=True |
