# Generated manually on 2026-04-08
# Adds structural fields required for ProfessorController queries:
#   - TurmaEscola.tipo_turma        (VerificaSeEhTurmaDeProgramaAsync)
#   - TurmaEscola.dt_inicio_turma   (BuscaTurmasAtribuidasProfessorAsync)
#   - Professor.cpf                 (BuscaProfessoresAsync — CPF column)
#   - CargoBaseServidor.situacao_funcional (VerificarValidadeProfessorAsync)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "professores",
            "0003_alter_atribuicaoaula_cargo_base_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="turmaescola",
            name="tipo_turma",
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text="cd_tipo_turma: 1=Série, 2=Ciclo, 3=Programa.",
            ),
        ),
        migrations.AddField(
            model_name="turmaescola",
            name="dt_inicio_turma",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="professor",
            name="cpf",
            field=models.CharField(
                blank=True,
                max_length=14,
                null=True,
                help_text=(
                    "cd_cpf_pessoa do servidor — retornado como CPF"
                    " em consultas de perfil."
                ),
            ),
        ),
        migrations.AddField(
            model_name="cargobaseservidor",
            name="situacao_funcional",
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text=(
                    "cd_situacao_funcional — usado em"
                    " VerificarValidadeProfessorAsync (filtro = 6)."
                ),
            ),
        ),
    ]
