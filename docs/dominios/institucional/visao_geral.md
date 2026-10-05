# Visão Geral do Domínio Institucional

## Objetivo

Popular `institucional_db` com os dados da estrutura administrativa da SME (DREs, Tipos de Escola, Subprefeituras e Unidades Educacionais), além da projeção de DREs elegíveis para abrangência.

## Origem dos Dados e Enriquecimento (SSO e EOL)

A estrutura fundamental (nomes, hierarquia, endereços) é extraída do banco **SE1426 (EOL)**. 
No entanto, o campo `codigo_ue_integracao` não existe no EOL. O detentor oficial dessa informação é o banco legado **CORE_SSO**.

Por este motivo, o sistema utiliza uma estratégia de cache:
- O **CORE_SSO** é consultado para obter o código de integração da Unidade Educacional.
- Este mapeamento é persistido no **KeyDB** para permitir o enriquecimento da `UnidadeEducacional` de forma performática e sem acoplar o tempo de resposta do EOL ao banco legado CORE_SSO.

## Classe principal

`EtlInstitucionalService` em `apps/institucional/services.py`.

Expõe um método `executar(fase_inicial=1)` que orquestra as 5 fases.

## Total de modelos do app

O código define **5 modelos principais** em `apps/institucional/models.py`:
1. `DRE`
2. `TipoEscola`
3. `SubPrefeitura`
4. `UnidadeEducacional`
5. `DREAbrangencia`

## Fases implementadas

### Fase 1 — DRE (Diretoria Regional de Educação)
- Extrai dados da DRE e seus tipos administrativos.
- **Enriquecimento Antecipado**: Durante esta fase, o sistema consulta o banco legado `CORE_SSO` para buscar os IDs de integração de todas as UEs daquela DRE e popula o cache particionado no KeyDB.

### Fase 2 — Tipo de Escola
- Extrai as parametrizações de tipos de unidades (EMEF, CEI, etc.).

### Fase 3 — Subprefeituras
- Extrai o mapeamento geográfico das subprefeituras vinculadas às unidades.

### Fase 4 — Unidade Educacional (UE)
- A fase mais densa, extrai dados de endereço, ocupação, vagas e telefones.
- **Cache Segmentado**: Utiliza as partições criadas na Fase 1 (`etl_institucional:dre:{codigo_dre}:...`) para obter o `codigo_ue_integracao` sem sobrecarregar o banco legado.

### Fase 5 — DRE de abrangência
- Materializa somente as DREs com tipos de escola e etapas de ensino aceitos
  pelo contrato legado.
- Usa substituição integral para remover DREs que deixarem de ser elegíveis.

## Fluxo

```{graphviz}
digraph G {
    rankdir=TB;
    node [shape=box, style="rounded"];

    F1 [label="Fase 1\nDRE / Cache SSO"];
    F2 [label="Fase 2\nTipo Escola"];
    F3 [label="Fase 3\nSubprefeitura"];
    F4 [label="Fase 4\nUnidade Educacional"];
    F5 [label="Fase 5\nDRE Abrangência"];

    F1 -> F2 -> F3 -> F4 -> F5;
}
```
