"""Admin do app alunos."""

from django.contrib import admin

from .models import (
    Aluno,
    Matricula,
    MatriculaTurma,
    NecessidadeEspecialAluno,
    ResponsavelAluno,
)

admin.site.register(Aluno)
admin.site.register(Matricula)
admin.site.register(MatriculaTurma)
admin.site.register(ResponsavelAluno)
admin.site.register(NecessidadeEspecialAluno)
