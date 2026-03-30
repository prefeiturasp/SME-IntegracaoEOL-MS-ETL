# Repositório de Auditoria

Classe: `RepositorioAuditoriaPostgres`

## Métodos implementados

- `iniciar_execucao(dominio)`
- `finalizar_execucao(id_execucao, situacao, mensagem_erro=None)`
- `registrar_tabela_lida(...)`
- `registrar_tabela_escrita(...)`
- `obter_checkpoint_dominio(dominio)`
- `atualizar_checkpoint_dominio(...)`

## Responsabilidades

- abrir e fechar execuções
- registrar métricas por tabela
- ler checkpoint
- fazer upsert transacional do checkpoint

## Papel no domínio professores

O comando `etl_professores` depende diretamente desse repositório para:
- gerar `id_execucao`
- registrar logs
- manter checkpoint consistente
