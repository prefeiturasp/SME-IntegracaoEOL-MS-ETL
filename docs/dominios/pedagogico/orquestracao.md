# Orquestração do Domínio Pedagógico

## Caminhos de execução

### 1. Execução direta
```bash
python manage.py etl_pedagogico
```

### 2. Execução via domínio genérico
```bash
python manage.py executar_dominio --dominio pedagogico
```

### 3. Execução assíncrona (Celery)
- Task: `executar_dominio_task` em `apps/controle_auditoria/libs/tasks.py`
- Agendamento: `python manage.py agendar_dominio --dominio pedagogico`

## Fluxo atual

```{graphviz}
digraph G {
    rankdir=LR;
    node [shape=box, style="rounded"];

    A [label="agendar_dominio"];
    T [label="executar_dominio_task"];
    C [label="executar_dominio"];
    P [label="etl_pedagogico"];
    S [label="EtlPedagogicoService"];
    R [label="RepositorioAuditoriaPostgres"];

    A -> T -> C -> P -> S;
    P -> R;
}
```

## Observação

O projeto ainda contém infraestrutura Celery (`celery_app.py`, `tasks.py`, `agendar_dominio`). O domínio pedagógico segue o mesmo padrão dos demais domínios nesse aspecto.
