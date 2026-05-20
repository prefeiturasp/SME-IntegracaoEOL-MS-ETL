from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("programas", "0005_alter_matriculaturmaprogramahistorico_categoria"),
    ]

    operations = [
        migrations.CreateModel(
            name="AlunoPapAnoLetivo",
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
                (
                    "codigo_aluno",
                    models.BigIntegerField(
                        help_text=(
                            "EOL cd_aluno — FK lógica para aluno "
                            "(PEDAGOGICO_DB)."
                        ),
                    ),
                ),
                (
                    "codigo_turma",
                    models.BigIntegerField(
                        help_text="FK lógica → turma_programa.codigo_turma.",
                    ),
                ),
                (
                    "codigo_componente_curricular",
                    models.BigIntegerField(
                        help_text=(
                            "FK lógica → componente_curricular_programa"
                            ".codigo_componente_curricular."
                        ),
                    ),
                ),
                (
                    "ano_letivo",
                    models.SmallIntegerField(
                        help_text=(
                            "EOL turma_escola.an_letivo — chave do filtro "
                            "do endpoint."
                        ),
                    ),
                ),
                (
                    "codigo_ue",
                    models.CharField(
                        max_length=20,
                        help_text="EOL escola.cd_escola — desnormalizado.",
                    ),
                ),
                (
                    "codigo_dre",
                    models.CharField(
                        max_length=20,
                        help_text=(
                            "EOL unidade_administrativa.cd_unidade_"
                            "administrativa — desnormalizado."
                        ),
                    ),
                ),
            ],
            options={
                "verbose_name": "aluno PAP por ano letivo",
                "verbose_name_plural": "alunos PAP por ano letivo",
                "db_table": "aluno_pap_ano_letivo",
                "app_label": "programas",
            },
        ),
        migrations.CreateModel(
            name="AlunoPapAnoLetivoHistorico",
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
                (
                    "codigo_aluno",
                    models.BigIntegerField(
                        help_text=(
                            "EOL cd_aluno — FK lógica para aluno "
                            "(PEDAGOGICO_DB)."
                        ),
                    ),
                ),
                (
                    "codigo_turma",
                    models.BigIntegerField(
                        help_text="FK lógica → turma_programa.codigo_turma.",
                    ),
                ),
                (
                    "codigo_componente_curricular",
                    models.BigIntegerField(
                        help_text=(
                            "FK lógica → componente_curricular_programa"
                            ".codigo_componente_curricular."
                        ),
                    ),
                ),
                (
                    "ano_letivo",
                    models.SmallIntegerField(
                        help_text=(
                            "EOL turma_escola.an_letivo — chave do filtro "
                            "do endpoint."
                        ),
                    ),
                ),
                (
                    "codigo_ue",
                    models.CharField(
                        max_length=20,
                        help_text="EOL escola.cd_escola — desnormalizado.",
                    ),
                ),
                (
                    "codigo_dre",
                    models.CharField(
                        max_length=20,
                        help_text=(
                            "EOL unidade_administrativa.cd_unidade_"
                            "administrativa — desnormalizado."
                        ),
                    ),
                ),
            ],
            options={
                "verbose_name": "aluno PAP por ano letivo (histórico)",
                "verbose_name_plural": (
                    "alunos PAP por ano letivo (histórico)"
                ),
                "db_table": "aluno_pap_ano_letivo_historico",
                "app_label": "programas",
            },
        ),
        migrations.AddConstraint(
            model_name="alunopapanoletivo",
            constraint=models.UniqueConstraint(
                fields=[
                    "ano_letivo",
                    "codigo_turma",
                    "codigo_aluno",
                    "codigo_componente_curricular",
                ],
                name="uq_aluno_pap_ano_turma_aluno_cc",
            ),
        ),
        migrations.AddIndex(
            model_name="alunopapanoletivo",
            index=models.Index(
                fields=["ano_letivo"], name="idx_aluno_pap_ano"
            ),
        ),
        migrations.AddConstraint(
            model_name="alunopapanoletivohistorico",
            constraint=models.UniqueConstraint(
                fields=[
                    "ano_letivo",
                    "codigo_turma",
                    "codigo_aluno",
                    "codigo_componente_curricular",
                ],
                name="uq_aluno_pap_hist_ano_turma_aluno_cc",
            ),
        ),
        migrations.AddIndex(
            model_name="alunopapanoletivohistorico",
            index=models.Index(
                fields=["ano_letivo"], name="idx_aluno_pap_hist_ano"
            ),
        ),
    ]
