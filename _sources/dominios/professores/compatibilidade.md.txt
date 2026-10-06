# Verificação de Compatibilidade — Professores

Valida se o `professores_db` replica corretamente os dados do EOL para as
queries do `ProfessorController`, sem necessidade de `JOINs` externos.

Cada verificador busca uma amostra de `--limite` linhas na origem
(`EolConnection`/SQL Server), consulta o equivalente no destino
(`professores_db`/PostgreSQL) e compara os campos-chave.

Aprovação: pelo menos 80% de correspondência por query.

## Pré-requisito

O `professores_db` deve ter dados. Use `--rodar-etl` para popular
automaticamente antes de verificar, ou execute o ETL separadamente:

```bash
docker exec sme_sgp_ms_etl_auditoria python manage.py etl_professores
```

## Execução

Verificação simples, quando o ETL já rodou:

```bash
docker exec sme_sgp_ms_etl_auditoria \
  python manage.py compat_professores
```

Rodar ETL amostral e verificar:

```bash
docker exec sme_sgp_ms_etl_auditoria \
  python manage.py compat_professores --rodar-etl
```

Alterar tamanho da amostra:

```bash
docker exec sme_sgp_ms_etl_auditoria \
  python manage.py compat_professores --rodar-etl --limite 50
```

Exibir exemplos de divergências nos verificadores reprovados:

```bash
docker exec sme_sgp_ms_etl_auditoria \
  python manage.py compat_professores --detalhes
```

Salvar resultado completo em JSON:

```bash
docker exec sme_sgp_ms_etl_auditoria \
  python manage.py compat_professores --saida resultado.json
```

Tudo junto:

```bash
docker exec sme_sgp_ms_etl_auditoria \
  python manage.py compat_professores \
    --rodar-etl --limite 30 --detalhes --saida resultado.json
```

## Saída esperada

```text
========================================================================
RELATÓRIO DE COMPATIBILIDADE — PROFESSORES_DB
========================================================================
[OK  ] FuncionarioRepository.BuscaFuncionarioPorRfAsync: 30/30 (100%) | destino=30
[OK  ] ProfessorRepository.VerificarValidadeProfessorAsync: 28/30 (93%) | destino=30
[IGNORADO] ProfessorRepository.BuscaProfessoresAsync_externo: sem dados na origem
...
========================================================================
Total: 12  OK: 10  FALHA: 0  IGNORADO: 2  ERRO: 0

professores_db está COMPATÍVEL com EolConnection.
```

O comando retorna código de saída `0` se estiver compatível ou `1` se algum
verificador reprovar.

## Verificadores cobertos

| Verificador | Query do ProfessorController |
|---|---|
| `VerificadorCargoBaseAtivo` | `BuscaFuncionarioPorRfAsync` |
| `VerificadorValidadeProf` | `VerificarValidadeProfessorAsync` |
| `VerificadorAtribuicaoAula` | `BuscaProfessoresAsync` (servidor) |
| `VerificadorTitularServidor` | `BuscarProfessorTitularPorDisciplinaAsync` (servidor) |
| `VerificadorPerfilProfServidor` | `BuscarInformacoesPerfilProfAsync` (servidor) |
| `VerificadorAtribuicaoExterno` | `BuscaProfessoresAsync` (externo) |
| `VerificadorTitularExterno` | `BuscarProfessorTitularPorDisciplinaAsync` (externo) |
| `VerificadorPerfilProfExterno` | `BuscarInformacoesPerfilProf` (externo) |
| `VerificadorTurmaEscola` | `VerificaSeEhTurmaDeProgramaAsync` |
| `VerificadorTurmaEscolaGradePrograma` | `VerificaSeTemAtribuicaoNaTurmaDeProgramaNaDisciplina` |
| `VerificadorTerritorioReplicado` | `ObterComponentesCurricularesTerritorioAtribuidos` |
| `VerificadorTerritorioAtribuicao` | cadeia JOIN com `AtribuicaoAula` |
