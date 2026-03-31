# Visão Geral da Arquitetura

## Bancos configurados

Pelo arquivo `config/settings.py`, o projeto define:

- `default`
- `institucional_db`
- `professores_db`
- `alunos_db`
- `pedagogico_db`
- `programas_db`

## Roteamento por app

O arquivo `config/db_router.py` roteia:

- `institucional` → `institucional_db`
- `professores` → `professores_db`
- `alunos` → `alunos_db`
- `pedagogico` → `pedagogico_db`
- `programas` → `programas_db`

Apps não mapeados explicitamente continuam em `default`.

---

## Fluxo lógico

```{graphviz}
digraph G {
    rankdir=LR;
    node [shape=box, style="rounded"];

    SRC [label="Origens"];
    ETL [label="Services + Commands"];
    ROUTER [label="DominioRouter"];
    PROF [label="professores_db"];
    AUD [label="default"];

    SRC -> ETL -> ROUTER;
    ROUTER -> PROF;
    ETL -> AUD;
}
```

---

## Princípio de separação de domínios

Cada domínio ETL é autossuficiente: **não replica tabelas de outros domínios**.
Referências externas (DRE, Cargo, ComponenteCurricular, etc.) são armazenadas apenas como IDs (`IntegerField` / `CharField`).

Descrições e nomes são resolvidos em tempo de resposta pelo **Transition Gateway** — serviço que enriquece as respostas consultando os domínios de origem.

> **Regra prática:** um campo descritivo (`dc_*`) só é persistido se aparecer em cláusula `WHERE` de alguma query do domínio. Caso contrário, não é armazenado.

---

## Execução atual

A estrutura atual do projeto inclui:

- execução síncrona via `python manage.py etl_professores`
- execução indireta via `executar_dominio`
- task assíncrona `executar_dominio_task`
- agendamento com `agendar_dominio`