from django.contrib import admin

from .models import (
    AgrupamentoAtribuicaoTerritorioSaber,
    ComponenteCurricularApi,
    ComponenteCurricularPai,
    ComponenteCurricularPap,
    Grupo,
    GrupoCargo,
    GrupoFuncaoAtividade,
    Parametro,
    RegenciaComponenteCurricular,
    TurmaTipoItinerario,
)

admin.site.register(Parametro)
admin.site.register(TurmaTipoItinerario)
admin.site.register(ComponenteCurricularApi)
admin.site.register(ComponenteCurricularPai)
admin.site.register(ComponenteCurricularPap)
admin.site.register(RegenciaComponenteCurricular)
admin.site.register(AgrupamentoAtribuicaoTerritorioSaber)
admin.site.register(Grupo)
admin.site.register(GrupoCargo)
admin.site.register(GrupoFuncaoAtividade)
