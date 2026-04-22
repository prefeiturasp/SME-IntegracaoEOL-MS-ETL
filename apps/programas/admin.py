from django.contrib import admin

from .models import (
    ComponenteCurricularPrograma,
    MatriculaTurmaPrograma,
    TipoPrograma,
    TurmaPrograma,
    TurmaProgramaComponenteCurricular,
)

admin.site.register(TipoPrograma)
admin.site.register(ComponenteCurricularPrograma)
admin.site.register(TurmaPrograma)
admin.site.register(TurmaProgramaComponenteCurricular)
admin.site.register(MatriculaTurmaPrograma)
