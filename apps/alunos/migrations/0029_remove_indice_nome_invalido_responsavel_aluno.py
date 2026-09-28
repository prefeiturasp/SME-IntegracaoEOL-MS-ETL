"""Remove do grafo de migrations o índice com nome inválido da 0027.

`idx_resp_aluno_vigente_prioridade` (33 caracteres) violava o limite de
30 caracteres do Django (E034) e já não existe fisicamente no banco --
foi removido por uma migration gerada automaticamente pelo pipeline de
deploy (nunca commitada neste repositório) assim que o `makemigrations`
detectou que o model não declarava esse índice. Usa DROP INDEX IF EXISTS,
então roda sem erro independente do estado físico atual. Formaliza no
histórico de migrations o que já é verdade no banco, para o
`makemigrations` parar de sugerir essa remoção a cada rodada.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("alunos", "0028_reaplica_indice_responsavel_aluno_vigente_por_aluno"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="responsavelaluno",
            name="idx_resp_aluno_vigente_prioridade",
        ),
    ]
