from django.contrib import admin

from .models import (
    Aluno,
    HistoricoMatricula,
    HistoricoMatriculaTurmaEscola,
    Matricula,
    MatriculaTurmaEscola,
    NecessidadeEspecialAluno,
    ResponsavelAluno,
)

admin.site.register(Aluno)
admin.site.register(Matricula)
admin.site.register(MatriculaTurmaEscola)
admin.site.register(HistoricoMatricula)
admin.site.register(HistoricoMatriculaTurmaEscola)
admin.site.register(ResponsavelAluno)
admin.site.register(NecessidadeEspecialAluno)
