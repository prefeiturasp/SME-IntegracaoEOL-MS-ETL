from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pedagogico", "0017_modelobase_tabelas_api_eol"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="agrupamentoatribuicaoterritoriosaber",
            name="uq_aats_agrupamento_exato",
        ),
    ]
