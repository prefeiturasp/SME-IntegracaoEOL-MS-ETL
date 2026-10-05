from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pedagogico", "0013_turma_tipo_grade_programa"),
    ]

    operations = [
        migrations.AlterField(
            model_name="agrupamentoatribuicaoterritoriosaber",
            name="cod_agrupamento",
            field=models.BigIntegerField(),
        ),
        migrations.AddIndex(
            model_name="agrupamentoatribuicaoterritoriosaber",
            index=models.Index(
                fields=["cod_agrupamento"], name="idx_aats_cod_agrupamento"
            ),
        ),
        migrations.AddConstraint(
            model_name="agrupamentoatribuicaoterritoriosaber",
            constraint=models.UniqueConstraint(
                fields=(
                    "cod_turma",
                    "cod_territorio_saber",
                    "cod_experiencia_pedagogica",
                    "rf_professor",
                    "dt_inicio_atribuicao",
                    "cod_componentes_curriculares",
                ),
                name="uq_aats_agrupamento_exato",
                nulls_distinct=False,
            ),
        ),
        migrations.RemoveConstraint(
            model_name="componentecurricularagrupamento",
            name="uq_componente_agrupamento",
        ),
        migrations.AddConstraint(
            model_name="componentecurricularagrupamento",
            constraint=models.UniqueConstraint(
                fields=(
                    "componente_codigo",
                    "turma_codigo",
                    "codigo_agrupamento",
                    "rf_professor",
                ),
                name="uq_componente_agrupamento",
                nulls_distinct=False,
            ),
        ),
    ]
