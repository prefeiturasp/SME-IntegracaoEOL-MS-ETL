# SME-IntegracaoEOL-MS-ETL

Documentação técnica completa baseada na **estrutura atual do código**, com foco em **domínio professores** e **controle/auditoria**.

---

## Escopo desta documentação

Esta documentação foi produzida a partir da leitura dos arquivos atuais do projeto, incluindo:

- `apps/professores/models.py`
- `apps/professores/services.py`
- `apps/professores/management/commands/etl_professores.py`
- `apps/controle_auditoria/models.py`
- `apps/controle_auditoria/libs/repositorio_auditoria.py`
- `apps/controle_auditoria/libs/tasks.py`
- `apps/controle_auditoria/api/*`
- `config/db_router.py`
- `config/settings.py`

---

## Arquitetura geral

```{graphviz}
digraph G {
    rankdir=LR;
    node [shape=box, style="rounded"];

    EOL [label="EOL SQL Server"];
    APIEOL [label="API EOL PostgreSQL"];
    ETL [label="SME-IntegracaoEOL-MS-ETL"];
    PROF [label="professores_db"];
    AUD [label="default / auditoria_db"];

    EOL -> ETL;
    APIEOL -> ETL;
    ETL -> PROF;
    ETL -> AUD;
}
```

---

## O que o projeto implementa hoje

- múltiplos bancos por domínio via `DominioRouter`
- domínio `professores` em banco dedicado `professores_db`
- controle de execução em `default`
- checkpoint por domínio
- hash por linha para incremental
- execução via comando Django
- orquestração assíncrona via Celery task e comando de agendamento

---

## Navegação

```{toctree}
:maxdepth: 2

arquitetura/visao_geral
arquitetura/der
dominios/professores/index
dominios/institucional/index
auditoria/index
```
