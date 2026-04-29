from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("programas", "0002_turmaprograma_codigo_tipo_programa_nullable"),
    ]

    operations = [
        migrations.CreateModel(
            name="MatriculaTurmaProgramaHistorico",
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
                            "(PEDAGOGICO_DB — banco diferente)."
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
                    "nome_componente_curricular",
                    models.CharField(
                        max_length=200,
                        help_text=(
                            "EOL dc_componente_curricular — desnormalizado para evitar JOIN."
                        ),
                    ),
                ),
                (
                    "codigo_situacao_matricula",
                    models.SmallIntegerField(
                        help_text="EOL st_matricula.",
                    ),
                ),
                (
                    "descricao_situacao_matricula",
                    models.CharField(
                        max_length=50,
                        help_text=(
                            "Ex: 'Ativo', 'Concluído' — desnormalizado para evitar "
                            "mapeamento em código."
                        ),
                    ),
                ),
                (
                    "data_matricula",
                    models.DateField(
                        null=True,
                        blank=True,
                        help_text="EOL dt_status_matricula — nullable no histórico.",
                    ),
                ),
                (
                    "data_situacao",
                    models.DateField(
                        null=True,
                        blank=True,
                        help_text="EOL dt_situacao_aluno.",
                    ),
                ),
                (
                    "ano_letivo",
                    models.SmallIntegerField(
                        help_text=(
                            "Desnormalizado da turma — necessário para filtros diretos por ano."
                        ),
                    ),
                ),
                (
                    "codigo_ue",
                    models.CharField(
                        max_length=20,
                        help_text="Desnormalizado da turma — exigido por AlunoTurmaPapDto.",
                    ),
                ),
                (
                    "codigo_dre",
                    models.CharField(
                        max_length=20,
                        help_text="Desnormalizado da turma — exigido por AlunoTurmaPapDto.",
                    ),
                ),
                (
                    "categoria",
                    models.CharField(
                        max_length=10,
                        help_text=(
                            "'PAP' ou 'PAEE' — desnormalizado da turma para filtros diretos."
                        ),
                    ),
                ),
                (
                    "criado_em",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "atualizado_em",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="Última atualização pelo ETL — usado no incremental.",
                    ),
                ),
            ],
            options={
                "verbose_name": "matrícula histórica em turma de programa",
                "verbose_name_plural": "matrículas históricas em turmas de programa",
                "db_table": "matricula_turma_programa_historico",
                "app_label": "programas",
            },
        ),
        migrations.AddConstraint(
            model_name="matriculaturmaprogramahistorico",
            constraint=models.UniqueConstraint(
                fields=["codigo_turma", "codigo_aluno", "codigo_componente_curricular"],
                name="uq_hist_matricula_turma_aluno_componente",
            ),
        ),
        migrations.AddIndex(
            model_name="matriculaturmaprogramahistorico",
            index=models.Index(
                fields=["codigo_aluno"],
                name="idx_hist_matricula_aluno",
            ),
        ),
        migrations.AddIndex(
            model_name="matriculaturmaprogramahistorico",
            index=models.Index(
                fields=["ano_letivo"],
                name="idx_hist_matricula_ano",
            ),
        ),
        migrations.AddIndex(
            model_name="matriculaturmaprogramahistorico",
            index=models.Index(
                fields=["codigo_ue"],
                name="idx_hist_matricula_ue",
            ),
        ),
        migrations.AddIndex(
            model_name="matriculaturmaprogramahistorico",
            index=models.Index(
                fields=["categoria"],
                name="idx_hist_matricula_categoria",
            ),
        ),
    ]
