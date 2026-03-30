# DER e Mapa de Dados

## Visão macro

O projeto organiza dados do domínio professores em um banco próprio e registra auditoria no banco padrão.

```{graphviz}
digraph G {
    rankdir=LR;
    node [shape=box, style="rounded"];

    EOL [label="Origem EOL"];
    SVC [label="EtlProfessoresService"];
    PROF [label="professores_db"];
    EXEC [label="etl_execucao"];
    CHK [label="etl_checkpoint_dominio"];
    HASH [label="etl_auditoria_linha"];

    EOL -> SVC -> PROF;
    SVC -> EXEC;
    SVC -> CHK;
    SVC -> HASH;
}
```

## Professores: grupos de tabelas

### Referências embarcadas
- DRE
- TipoEscola
- UnidadeEducacional
- ComponenteCurricular
- SerieEnsino
- TerritorioSaber
- TipoExperienciaPedagogica
- Grade
- EscolaGrade
- TurmaEscola
- SerieTurmaGrade
- TurmaEscolaGradePrograma
- TurmaGradeTerritorioExperiencia
- AgrupamentoAtribuicaoTerritorioSaber

### Núcleo professor
- Cargo
- Professor
- CargoBaseServidor
- LotacaoServidor
- CargoSobrepostoServidor
- FuncaoAtividadeCargoServidor
- LaudoMedico

### Núcleo externo
- FuncaoFuncionarioExterno
- Pessoa
- ContratoExterno
- AtribuicaoExterno

### Atribuições
- AtribuicaoAula

## Auditoria
- EtlExecucao
- EtlExecucaoTabelaLida
- EtlExecucaoTabelaEscrita
- EtlCheckpointDominio
- EtlAuditoriaLinha
