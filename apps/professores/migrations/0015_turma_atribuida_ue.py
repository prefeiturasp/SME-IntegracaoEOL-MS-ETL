from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("professores", "0014_atribuicaoaula_abreviacao_dre_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="TurmaAtribuidaUe",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("codigo_escola", models.CharField(max_length=6)),
                ("codigo_turma", models.BigIntegerField()),
                ("ano_letivo", models.IntegerField()),
                (
                    "modalidade",
                    models.CharField(blank=True, max_length=15, null=True),
                ),
                ("semestre", models.IntegerField(blank=True, null=True)),
                (
                    "codigo_modalidade",
                    models.IntegerField(blank=True, null=True),
                ),
                (
                    "codigo_dre",
                    models.CharField(blank=True, max_length=6, null=True),
                ),
                (
                    "dre",
                    models.CharField(blank=True, max_length=60, null=True),
                ),
                (
                    "dre_abreviacao",
                    models.CharField(blank=True, max_length=60, null=True),
                ),
                (
                    "ue",
                    models.CharField(blank=True, max_length=60, null=True),
                ),
                (
                    "ue_abreviacao",
                    models.CharField(blank=True, max_length=60, null=True),
                ),
                (
                    "nome_turma",
                    models.CharField(blank=True, max_length=15, null=True),
                ),
                (
                    "ano",
                    models.CharField(blank=True, max_length=18, null=True),
                ),
                (
                    "tipo_ue",
                    models.CharField(blank=True, max_length=25, null=True),
                ),
                ("codigo_tipo_ue", models.IntegerField(blank=True, null=True)),
                (
                    "codigo_tipo_escola",
                    models.IntegerField(blank=True, null=True),
                ),
                (
                    "tipo_escola",
                    models.CharField(blank=True, max_length=12, null=True),
                ),
                ("duracao_turno", models.IntegerField(blank=True, null=True)),
                ("tipo_turno", models.IntegerField(blank=True, null=True)),
                ("usuario_rf", models.CharField(max_length=10)),
                ("cargo", models.IntegerField(blank=True, null=True)),
                (
                    "cargo_sobreposto",
                    models.IntegerField(blank=True, null=True),
                ),
            ],
            options={
                "verbose_name": "turma atribuída por UE",
                "verbose_name_plural": "turmas atribuídas por UE",
                "db_table": "turma_atribuida_ue",
            },
        ),
        migrations.AddIndex(
            model_name="turmaatribuidaue",
            index=models.Index(
                fields=["usuario_rf"], name="idx_tau_usuario_rf"
            ),
        ),
        migrations.AddIndex(
            model_name="turmaatribuidaue",
            index=models.Index(
                fields=["codigo_escola"], name="idx_tau_cod_ue"
            ),
        ),
        migrations.AddIndex(
            model_name="turmaatribuidaue",
            index=models.Index(fields=["codigo_dre"], name="idx_tau_cod_dre"),
        ),
        migrations.AddIndex(
            model_name="turmaatribuidaue",
            index=models.Index(fields=["cargo"], name="idx_tau_cargo"),
        ),
        migrations.AddIndex(
            model_name="turmaatribuidaue",
            index=models.Index(
                fields=["cargo_sobreposto"], name="idx_tau_cargo_sobreposto"
            ),
        ),
    ]
