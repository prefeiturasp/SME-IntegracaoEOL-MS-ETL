# Visão Geral do Domínio Professores

## Objetivo

Popular `professores_db` com dados necessários para o domínio de professores, evitando dependências de runtime entre bancos.

## Classe principal

A classe central é `EtlProfessoresService`, em `apps/professores/services.py`.

Ela expõe 26 métodos de carga específicos e um método `executar(fase_inicial=1)` que orquestra as fases.

## Total de modelos do app

O código atual define **26 modelos** em `apps/professores/models.py`.

## Fases implementadas

### Fase 1 — referências
- DRE
- TipoEscola
- ComponenteCurricular
- SerieEnsino
- TerritorioSaber
- TipoExperienciaPedagogica
- Grade
- Cargo
- FuncaoFuncionarioExterno

### Fase 2 — estruturas e pessoas
- UnidadeEducacional
- EscolaGrade
- TurmaEscola
- Professor
- Pessoa

### Fase 3 — vínculos
- SerieTurmaGrade
- TurmaEscolaGradePrograma
- CargoBaseServidor
- ContratoExterno
- TurmaGradeTerritorioExperiencia
- LotacaoServidor
- CargoSobrepostoServidor
- FuncaoAtividadeCargoServidor
- LaudoMedico

### Fase 4 — atribuições
- AtribuicaoAula
- AtribuicaoExterno

### Estrutura prevista no modelo, mas não integrada ao fluxo de escrita
- AgrupamentoAtribuicaoTerritorioSaber

## Fluxo

```{graphviz}
digraph G {
    rankdir=TB;
    node [shape=box, style="rounded"];

    F1 [label="Fase 1\nReferências"];
    F2 [label="Fase 2\nEstruturas"];
    F3 [label="Fase 3\nVínculos"];
    F4 [label="Fase 4\nAtribuições"];

    F1 -> F2 -> F3 -> F4;
}
```
