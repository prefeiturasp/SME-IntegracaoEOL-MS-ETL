# DER e Mapa de Dados

## Visão macro

O projeto organiza dados do domínio professores em um banco próprio e registra auditoria no banco padrão.
Cada domínio é **autossuficiente**: referências a entidades externas (DRE, Escola, Componente, Cargo, etc.)
são armazenadas **somente como IDs**. Nomes e descrições são resolvidos em tempo de resposta pelo
**Transition Gateway**.

```{graphviz}
digraph G {
    rankdir=LR;
    node [shape=box, style="rounded"];

    EOL    [label="EOL (SQL Server)"];
    APIEOL [label="API EOL (PostgreSQL)"];
    SVC    [label="EtlProfessoresService"];
    PROF   [label="professores_db"];
    EXEC   [label="etl_execucao"];
    CHK    [label="etl_checkpoint_dominio"];
    HASH   [label="etl_auditoria_linha"];
    TGW    [label="Transition Gateway\n(resolução de IDs)"];

    EOL    -> SVC -> PROF;
    APIEOL -> PROF [label="futuro" style=dashed];
    SVC    -> EXEC;
    SVC    -> CHK;
    SVC    -> HASH;
    PROF   -> TGW  [style=dashed label="resposta API"];
}
```

---

## Professores: grupos de tabelas

### Suporte (estruturais — necessárias para filtros e junções)

Armazenam apenas os IDs mínimos para que as queries de professor funcionem.
Nenhum campo de descrição (`dc_`, `nm_`) é persistido — apenas IDs usados em cláusulas `WHERE`.

| Tabela | Chave | IDs externos armazenados |
|---|---|---|
| `UnidadeEducacional` | `codigo_ue` (PK) | `codigo_dre`, `codigo_tipo_escola` |
| `TurmaEscola` | `codigo_turma` (PK) | `codigo_escola` |
| `SerieTurmaGrade` | `codigo_serie_grade` (PK) | `codigo_turma`, `codigo_escola`, `codigo_escola_grade` |
| `TurmaEscolaGradePrograma` | `codigo` (PK) | `codigo_turma`, `codigo_escola_grade` |
| `TurmaGradeTerritorioExperiencia` | auto (PK) | `codigo_serie_grade`, `codigo_componente_curricular`, `codigo_territorio_saber`, `codigo_experiencia_pedagogica` |

### Programas (pendente — ref. ApiEolConnection)

| Tabela | Fonte | Nota |
|---|---|---|
| `AgrupamentoAtribuicaoTerritorioSaber` | ApiEolConnection | Integração prevista, não carregada pelo ETL atual |

### Núcleo servidor efetivo

| Tabela | Chave | FK interna |
|---|---|---|
| `Professor` | `codigo_rf` (PK) | — |
| `CargoBaseServidor` | auto (PK) | `professor` → Professor |
| `LotacaoServidor` | auto (PK) | `cargo_base` → CargoBaseServidor |
| `CargoSobrepostoServidor` | auto (PK) | `cargo_base` → CargoBaseServidor |
| `FuncaoAtividadeCargoServidor` | auto (PK) | `cargo_base` → CargoBaseServidor |
| `LaudoMedico` | auto (PK) | `cargo_base` → CargoBaseServidor |

### Núcleo externo

| Tabela | Chave | FK interna |
|---|---|---|
| `Pessoa` | `codigo_pessoa` (PK) | — |
| `ContratoExterno` | `codigo_contrato` (PK) | `pessoa` → Pessoa |

### Atribuições

| Tabela | Chave | FK interna |
|---|---|---|
| `AtribuicaoAula` | auto (PK) | `cargo_base` → CargoBaseServidor |
| `AtribuicaoExterno` | auto (PK) | `contrato_externo` → ContratoExterno |

---

## Auditoria (banco `default`)

| Tabela | Propósito |
|---|---|
| `EtlExecucao` | Registro de cada execução (status, timestamps, erro) |
| `EtlExecucaoTabelaLida` | Log de leituras por tabela origem |
| `EtlExecucaoTabelaEscrita` | Log de escritas por tabela destino |
| `EtlCheckpointDominio` | Fase e token de progresso por domínio |
| `EtlAuditoriaLinha` | Hash SHA-256 por linha para detecção incremental de mudanças |

---

## Princípio: separação de domínios

> **Regra:** guarda-se apenas o ID quando há par `id + descrição`.
> A descrição só é persistida se aparecer em cláusula `WHERE` de alguma query deste domínio.
> Caso contrário, será resolvida pelo **Transition Gateway** em tempo de resposta.

Domínios externos **não replicados** no `professores_db`:

| Domínio externo | Como é referenciado aqui |
|---|---|
| DRE | `UnidadeEducacional.codigo_dre` |
| TipoEscola | `UnidadeEducacional.codigo_tipo_escola` |
| EscolaGrade / Grade | `SerieTurmaGrade.codigo_escola_grade` |
| ComponenteCurricular | `TurmaGradeTerritorioExperiencia.codigo_componente_curricular` |
| TerritorioSaber | `TurmaGradeTerritorioExperiencia.codigo_territorio_saber` |
| TipoExperienciaPedagogica | `TurmaGradeTerritorioExperiencia.codigo_experiencia_pedagogica` |
| Cargo | `CargoBaseServidor.codigo_cargo`, `CargoSobrepostoServidor.codigo_cargo` |
| FuncaoFuncionarioExterno | `ContratoExterno.codigo_tipo_funcao` |
