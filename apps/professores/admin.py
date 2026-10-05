from django.contrib import admin

from .models import (
    AtribuicaoAula,
    AtribuicaoExterno,
    CargoBaseServidor,
    CargoSobrepostoServidor,
    ContratoExterno,
    FuncaoAtividadeCargoServidor,
    LaudoMedico,
    LotacaoServidor,
    Pessoa,
    Professor,
)

admin.site.register(Professor)
admin.site.register(CargoBaseServidor)
admin.site.register(LotacaoServidor)
admin.site.register(CargoSobrepostoServidor)
admin.site.register(FuncaoAtividadeCargoServidor)
admin.site.register(LaudoMedico)
admin.site.register(Pessoa)
admin.site.register(ContratoExterno)
admin.site.register(AtribuicaoAula)
admin.site.register(AtribuicaoExterno)
