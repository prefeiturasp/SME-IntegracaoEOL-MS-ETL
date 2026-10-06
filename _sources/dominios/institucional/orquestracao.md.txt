# Orquestração Atual do Projeto

## Situação atual do código

O projeto possui **dois caminhos de execução**:

### 1. Execução síncrona
- `python manage.py etl_institucional`

### 2. Execução indireta / assíncrona
- `python manage.py executar_dominio --dominio institucional`
- task Celery `executar_dominio_task`
- `python manage.py agendar_dominio --dominio institucional`

## Fluxo atual

```{graphviz}
digraph G {
    rankdir=LR;
    node [shape=box, style="rounded"];

    A [label="agendar_dominio"];
    T [label="executar_dominio_task"];
    C [label="executar_dominio"];
    P [label="etl_institucional"];
    S [label="EtlInstitucionalService"];
    R [label="RepositorioAuditoriaPostgres"];

    A -> T -> C -> P -> S;
    P -> R;
}
```

## Observação importante

A documentação anterior havia removido Celery Beat por decisão de arquitetura desejada. Porém, **o código atual ainda contém infraestrutura Celery**, incluindo:

- `apps/controle_auditoria/libs/celery_app.py`
- `apps/controle_auditoria/libs/tasks.py`
- `agendar_dominio`
