# Visão Geral do Domínio Professores

## Objetivo

Popular `professores_db` com dados do domínio de professores, mantendo o banco autossuficiente
e sem dependências de runtime com outros domínios.

## Princípio de separação de domínios

O domínio professores **não replica** tabelas de outros domínios (DRE, Escola, Componente, Cargo, etc.).
Referências externas são armazenadas somente como IDs (`IntegerField` / `CharField`).
Descrições e nomes são resolvidos em tempo de resposta pelo **Transition Gateway**.

> **Regra prática:** um campo `dc_` (descrição) só é persistido se aparecer em cláusula `WHERE`
> de alguma query deste domínio. Caso contrário, não é armazenado.

## Classe principal

`EtlProfessoresService` em `apps/professores/services.py`.

Expõe métodos `popular_*` por tabela e um método `executar(fase_inicial=1)` que orquestra as 4 fases.

## Total de modelos do app

O código atual define **16 modelos** em `apps/professores/models.py`.

## Fases implementadas

### Fase 1 — sem dependências internas
- `UnidadeEducacional` — IDs de DRE e tipo escola
- `TurmaEscola` — campos para filtros de atribuição
- `Professor` — servidores com cargo de professor
- `Pessoa` — pessoas físicas (externos ativos)

### Fase 2 — dependem da Fase 1
- `SerieTurmaGrade` — liga TurmaEscola a escola_grade (ID externo)
- `TurmaEscolaGradePrograma` — liga TurmaEscola a escola_grade para turmas Programa
- `CargoBaseServidor` — cargo base do Professor (código cargo como ID)
- `ContratoExterno` — contrato da Pessoa (tipo funcao como ID)

### Fase 3 — dependem da Fase 2
- `TurmaGradeTerritorioExperiencia` — IDs de componente, território e experiência
- `LotacaoServidor` — lotação do CargoBaseServidor
- `CargoSobrepostoServidor` — cargo sobreposto do CargoBaseServidor (código cargo como ID)
- `FuncaoAtividadeCargoServidor` — função de atividade do CargoBaseServidor
- `LaudoMedico` — laudo impedindo atribuição do CargoBaseServidor
- `AtribuicaoAula` — atribuição de aulas ao CargoBaseServidor
- `AtribuicaoExterno` — atribuição de aulas ao ContratoExterno

### Fase 4 — dependem das Fases 1–3
- `AgrupamentoAtribuicaoTerritorioSaber` — agrega atribuições por (turma, território, experiência, professor, data); apenas grupos com 2+ componentes; inclui SME (RF) e externos (CPF)

## Fluxo

```{graphviz}
digraph G {
    rankdir=TB;
    node [shape=box, style="rounded"];

    F1 [label="Fase 1\nUE / Turma / Professor / Pessoa"];
    F2 [label="Fase 2\nSerie / TEGP / CargoBase / Contrato"];
    F3 [label="Fase 3\nVinculos / Atribuicoes"];
    F4 [label="Fase 4\nAgrupamentoTerritorioSaber"];

    F1 -> F2 -> F3 -> F4;
}
```
