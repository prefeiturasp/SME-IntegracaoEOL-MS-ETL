# ruff: noqa: D100,D101,E501

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("alunos", "0004_matriculaturma_codigo_tipo_turma"),
    ]

    state_operations = [
        # Aluno.cns é novo; nome_mae e possui_deficiencia já estão no estado
        # via 0002_aluno_novos_campos_matricula_renomear_data_status da homolog.
        migrations.AddField(
            model_name="aluno",
            name="cns",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="responsavelaluno",
            name="endereco_id",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="responsavelaluno",
            name="numero_endereco",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="responsavelaluno",
            name="complemento",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="responsavelaluno",
            name="bairro",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="responsavelaluno",
            name="nome_municipio",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="responsavelaluno",
            name="sigla_uf",
            field=models.CharField(blank=True, max_length=2, null=True),
        ),
        migrations.AddField(
            model_name="responsavelaluno",
            name="tipo_logradouro",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="responsavelaluno",
            name="data_atualizacao_tabela",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="necessidadeespecialaluno",
            name="codigo_tipo_recurso",
            field=models.SmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="necessidadeespecialaluno",
            name="descricao_tipo_recurso",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="matricula",
            name="origem_atual",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="matriculaturma",
            name="codigo_situacao_aluno",
            field=models.SmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="matriculaturma",
            name="data_atualizacao_tabela",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE aluno ADD COLUMN IF NOT EXISTS nome_mae varchar(200);
                    ALTER TABLE aluno ADD COLUMN IF NOT EXISTS cns varchar(20);
                    ALTER TABLE aluno ADD COLUMN IF NOT EXISTS possui_deficiencia boolean DEFAULT false NOT NULL;
                    ALTER TABLE responsavel_aluno ADD COLUMN IF NOT EXISTS endereco_id bigint;
                    ALTER TABLE responsavel_aluno ADD COLUMN IF NOT EXISTS numero_endereco varchar(20);
                    ALTER TABLE responsavel_aluno ADD COLUMN IF NOT EXISTS complemento varchar(100);
                    ALTER TABLE responsavel_aluno ADD COLUMN IF NOT EXISTS bairro varchar(100);
                    ALTER TABLE responsavel_aluno ADD COLUMN IF NOT EXISTS nome_municipio varchar(100);
                    ALTER TABLE responsavel_aluno ADD COLUMN IF NOT EXISTS sigla_uf varchar(2);
                    ALTER TABLE responsavel_aluno ADD COLUMN IF NOT EXISTS tipo_logradouro varchar(50);
                    ALTER TABLE responsavel_aluno ADD COLUMN IF NOT EXISTS data_atualizacao_tabela timestamp with time zone;
                    ALTER TABLE necessidade_especial_aluno ADD COLUMN IF NOT EXISTS codigo_tipo_recurso smallint;
                    ALTER TABLE necessidade_especial_aluno ADD COLUMN IF NOT EXISTS descricao_tipo_recurso varchar(100);
                    ALTER TABLE matricula ADD COLUMN IF NOT EXISTS origem_atual boolean DEFAULT true NOT NULL;
                    ALTER TABLE matricula_turma ADD COLUMN IF NOT EXISTS codigo_situacao_aluno smallint;
                    ALTER TABLE matricula_turma ADD COLUMN IF NOT EXISTS data_atualizacao_tabela timestamp with time zone;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
            state_operations=state_operations,
        )
    ]
