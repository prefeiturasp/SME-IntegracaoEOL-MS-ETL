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

## Execução atual

A estrutura atual do projeto inclui:

- execução síncrona via `python manage.py etl_professores`
- execução indireta via `executar_dominio`
- task assíncrona `executar_dominio_task`
- agendamento com `agendar_dominio`