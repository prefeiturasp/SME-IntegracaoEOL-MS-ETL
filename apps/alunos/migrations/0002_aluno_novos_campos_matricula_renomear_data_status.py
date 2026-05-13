import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("alunos", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="aluno",
            name="data_atualizacao_contato",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="aluno",
            name="possui_deficiencia",
            field=models.BooleanField(default=False),
        ),
        migrations.RenameField(
            model_name="matricula",
            old_name="data_status",
            new_name="data_situacao_matricula",
        ),
    ]
