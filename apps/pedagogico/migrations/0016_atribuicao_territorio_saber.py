from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pedagogico", "0015_componenteturma_descricoes_territorio"),
    ]

    operations = [
        migrations.CreateModel(
            name="AtribuicaoTerritorioSaber",
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
                    "transferido_em",
                    models.DateTimeField(),
                ),
                ("turma_codigo", models.CharField(max_length=20)),
                ("componente_codigo", models.IntegerField()),
                (
                    "professor",
                    models.CharField(blank=True, max_length=20, null=True),
                ),
                ("codigo_territorio_saber", models.IntegerField()),
                (
                    "codigo_experiencia_pedagogica",
                    models.IntegerField(blank=True, null=True),
                ),
                (
                    "desc_territorio_saber",
                    models.CharField(blank=True, max_length=200, null=True),
                ),
                (
                    "desc_experiencia_pedagogica",
                    models.CharField(blank=True, max_length=200, null=True),
                ),
                ("atribuicao_externa", models.BooleanField(default=False)),
                ("ano_letivo", models.IntegerField()),
                (
                    "dt_atribuicao",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "dt_disponibilizacao",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "cd_motivo_disponibilizacao",
                    models.IntegerField(blank=True, null=True),
                ),
                (
                    "dt_fim_turma",
                    models.DateTimeField(blank=True, null=True),
                ),
            ],
            options={
                "verbose_name": "atribuição território saber",
                "verbose_name_plural": "atribuições território saber",
                "db_table": "atribuicao_territorio_saber",
                "indexes": [
                    models.Index(
                        fields=["turma_codigo"], name="idx_ats_turma"
                    ),
                    models.Index(
                        fields=["professor"], name="idx_ats_professor"
                    ),
                    models.Index(
                        fields=["ano_letivo"], name="idx_ats_ano_letivo"
                    ),
                    models.Index(
                        fields=["turma_codigo", "componente_codigo"],
                        name="idx_ats_turma_comp",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=(
                            "turma_codigo",
                            "componente_codigo",
                            "professor",
                            "codigo_territorio_saber",
                            "codigo_experiencia_pedagogica",
                            "dt_atribuicao",
                            "dt_disponibilizacao",
                        ),
                        name="uq_atribuicao_territorio_saber",
                        nulls_distinct=False,
                    ),
                ],
            },
        ),
    ]
