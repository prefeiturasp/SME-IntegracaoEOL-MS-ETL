"""Altera identidade da grade curricular para usar serie de ensino."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pedagogico", "0009_estado_atribuicao_componente"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="gradecomponentecurricular",
            name="uq_grade_componente_curricular",
        ),
        migrations.AddConstraint(
            model_name="gradecomponentecurricular",
            constraint=models.UniqueConstraint(
                fields=(
                    "codigo_componente_curricular",
                    "ano_letivo",
                    "modalidade",
                    "codigo_serie_ensino",
                ),
                name="uq_grade_componente_curricular",
                nulls_distinct=False,
            ),
        ),
    ]
