from django.contrib import admin

from .models import (
    AgrupamentoAtribuicaoTerritorioSaber,
    ComponenteCurricular,
    ComponenteCurricularAgrupamento,
    ComponenteCurricularPorTurma,
    ComponenteInicioTurma,
    GradeCurricularSerie,
)

admin.site.register(ComponenteCurricular)
admin.site.register(ComponenteCurricularPorTurma)
admin.site.register(ComponenteCurricularAgrupamento)
admin.site.register(ComponenteInicioTurma)
admin.site.register(GradeCurricularSerie)
admin.site.register(AgrupamentoAtribuicaoTerritorioSaber)
