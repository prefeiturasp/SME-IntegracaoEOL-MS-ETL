# Generated manually for the additive read models of Alunos lote 5.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("alunos", "0022_matricula_data_situacao_matricula_historica"),
    ]

    operations = [
        migrations.CreateModel(
            name="MatriculaAnoAnterior",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("ano_letivo", models.SmallIntegerField()),
                ("codigo_ue", models.CharField(max_length=20)),
                ("codigo_turma", models.BigIntegerField()),
                ("quantidade", models.IntegerField()),
            ],
            options={
                "db_table": "matricula_ano_anterior",
                "indexes": [
                    models.Index(
                        fields=["ano_letivo", "codigo_ue"],
                        name="idx_matr_ant_ano_ue",
                    )
                ],
                "unique_together": {
                    ("ano_letivo", "codigo_ue", "codigo_turma")
                },
            },
        ),
        migrations.CreateModel(
            name="ResponsavelAlunoTurma",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("codigo_responsavel", models.BigIntegerField()),
                ("codigo_matricula", models.BigIntegerField()),
                ("ano_letivo", models.SmallIntegerField()),
                ("codigo_dre", models.CharField(max_length=20)),
                (
                    "dre",
                    models.CharField(blank=True, max_length=300, null=True),
                ),
                ("codigo_ue", models.CharField(max_length=20)),
                (
                    "ue",
                    models.CharField(blank=True, max_length=300, null=True),
                ),
                ("codigo_turma", models.BigIntegerField()),
                (
                    "turma",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("cpf_responsavel", models.BigIntegerField()),
                ("codigo_aluno", models.BigIntegerField()),
                ("codigo_tipo_escola", models.SmallIntegerField()),
                ("codigo_etapa_ensino", models.SmallIntegerField()),
                ("codigo_ciclo_ensino", models.SmallIntegerField()),
                (
                    "serie_resumida",
                    models.CharField(blank=True, max_length=20, null=True),
                ),
                ("codigo_modalidade_turma", models.SmallIntegerField()),
            ],
            options={
                "db_table": "responsavel_aluno_turma",
                "indexes": [
                    models.Index(
                        fields=["ano_letivo", "codigo_dre", "codigo_ue"],
                        name="idx_resp_turma_ano_dre_ue",
                    ),
                    models.Index(
                        fields=["ano_letivo", "codigo_ue"],
                        name="idx_resp_turma_ano_ue",
                    ),
                ],
                "unique_together": {
                    (
                        "codigo_responsavel",
                        "codigo_matricula",
                        "codigo_turma",
                    )
                },
            },
        ),
    ]
