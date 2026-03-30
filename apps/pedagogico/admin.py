"""Admin do app pedagogico."""

from django.contrib import admin

from .models import (
    DuracaoTipoTurno,
    EscolaGrade,
    Grade,
    GradeComponenteCurricular,
    SerieTurmaEscola,
    SerieTurmaGrade,
    TerritorioSaber,
    TipoExperienciaPedagogica,
    TurmaEscola,
    TurmaEscolaGradePrograma,
    TurmaGradeTerritorioExperiencia,
)

admin.site.register(TerritorioSaber)
admin.site.register(TipoExperienciaPedagogica)
admin.site.register(DuracaoTipoTurno)
admin.site.register(TurmaEscola)
admin.site.register(EscolaGrade)
admin.site.register(Grade)
admin.site.register(GradeComponenteCurricular)
admin.site.register(SerieTurmaEscola)
admin.site.register(SerieTurmaGrade)
admin.site.register(TurmaEscolaGradePrograma)
admin.site.register(TurmaGradeTerritorioExperiencia)
