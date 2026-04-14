from django.contrib import admin

from .models import (
    AgrupamentoAtribuicaoTerritorioSaber,
    ComponenteCurricular,
    ComponenteCurricularAgrupamento,
    ComponenteCurricularPorAnoLetivo,
    ComponenteCurricularPorTurma,
    ComponenteCurricularRegencia,
    DadosAulaTurma,
)

admin.site.register(ComponenteCurricular)
admin.site.register(ComponenteCurricularPorTurma)
admin.site.register(ComponenteCurricularAgrupamento)
admin.site.register(ComponenteCurricularRegencia)
admin.site.register(DadosAulaTurma)
admin.site.register(ComponenteCurricularPorAnoLetivo)
admin.site.register(AgrupamentoAtribuicaoTerritorioSaber)
