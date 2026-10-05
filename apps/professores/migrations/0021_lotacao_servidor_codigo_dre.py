"""Adiciona DRE à lotação do servidor."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Inclui DRE nas lotações do servidor."""

    dependencies = [
        ("professores", "0019_funcionario_cargo"),
    ]

    operations = [
        migrations.AddField(
            model_name="lotacaoservidor",
            name="codigo_dre",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddIndex(
            model_name="lotacaoservidor",
            index=models.Index(fields=["codigo_dre"], name="idx_ls_dre"),
        ),
    ]
