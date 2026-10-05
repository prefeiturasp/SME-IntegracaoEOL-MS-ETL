from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("professores", "0015_turma_atribuida_ue"),
    ]

    operations = [
        migrations.CreateModel(
            name="DisciplinaTurmaAtribuidaUe",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("codigo_escola", models.CharField(max_length=6)),
                ("codigo_turma", models.BigIntegerField()),
                ("ano_letivo", models.IntegerField()),
                ("usuario_rf", models.CharField(max_length=10)),
                ("codigo_componente_curricular", models.IntegerField()),
                (
                    "descricao_componente_curricular",
                    models.CharField(max_length=200),
                ),
                (
                    "codigo_componente_curricular_pai",
                    models.IntegerField(blank=True, null=True),
                ),
                ("regencia", models.BooleanField(default=False)),
                (
                    "codigo_componente_territorio_saber",
                    models.IntegerField(blank=True, null=True),
                ),
                ("territorio_saber", models.BooleanField(default=False)),
                (
                    "codigo_dre",
                    models.CharField(blank=True, max_length=6, null=True),
                ),
                (
                    "codigo_tipo_escola",
                    models.IntegerField(blank=True, null=True),
                ),
                (
                    "tipo_escola",
                    models.CharField(blank=True, max_length=12, null=True),
                ),
                ("cargo", models.IntegerField(blank=True, null=True)),
                (
                    "cargo_sobreposto",
                    models.IntegerField(blank=True, null=True),
                ),
            ],
            options={
                "verbose_name": "disciplina atribuída por vínculo com UE",
                "verbose_name_plural": (
                    "disciplinas atribuídas por vínculo com UE"
                ),
                "db_table": "disciplina_turma_atribuida_ue",
            },
        ),
        migrations.AddIndex(
            model_name="disciplinaturmaatribuidaue",
            index=models.Index(
                fields=["usuario_rf", "codigo_turma"],
                name="idx_dtau_rf_turma",
            ),
        ),
        migrations.AddIndex(
            model_name="disciplinaturmaatribuidaue",
            index=models.Index(
                fields=["codigo_turma", "codigo_componente_curricular"],
                name="idx_dtau_turma_comp",
            ),
        ),
        migrations.AddIndex(
            model_name="disciplinaturmaatribuidaue",
            index=models.Index(fields=["ano_letivo"], name="idx_dtau_ano"),
        ),
        migrations.AddConstraint(
            model_name="disciplinaturmaatribuidaue",
            constraint=models.UniqueConstraint(
                fields=(
                    "usuario_rf",
                    "codigo_turma",
                    "codigo_componente_curricular",
                    "cargo",
                    "cargo_sobreposto",
                ),
                name="uq_dtau_rf_turma_comp_cargo",
            ),
        ),
    ]
