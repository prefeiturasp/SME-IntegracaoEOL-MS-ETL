"""Adiciona DRE ao funcionário por unidade educacional."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Inclui DRE nos vínculos consolidados por unidade."""

    dependencies = [
        ("professores", "0021_lotacao_servidor_codigo_dre"),
    ]

    operations = [
        migrations.AddField(
            model_name="funcionariounidadeeducacional",
            name="codigo_dre",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddIndex(
            model_name="funcionariounidadeeducacional",
            index=models.Index(
                fields=["codigo_dre"],
                name="idx_funcionario_dre",
            ),
        ),
        migrations.AddIndex(
            model_name="funcionariounidadeeducacional",
            index=models.Index(
                fields=["codigo_dre", "codigo_cargo"],
                name="idx_funcionario_dre_cargo",
            ),
        ),
    ]
