"""Admin do app professores."""

from django.contrib import admin

from .models import (
    AtribuicaoAula,
    AtribuicaoExterno,
    Cargo,
    CargoBaseServidor,
    CargoSobrepostoServidor,
    ContratoExterno,
    FuncaoAtividadeCargoServidor,
    FuncaoFuncionarioExterno,
    LaudoMedico,
    LotacaoServidor,
    Pessoa,
    Professor,
)

admin.site.register(Professor)
admin.site.register(Cargo)
admin.site.register(CargoBaseServidor)
admin.site.register(LotacaoServidor)
admin.site.register(CargoSobrepostoServidor)
admin.site.register(FuncaoAtividadeCargoServidor)
admin.site.register(LaudoMedico)
admin.site.register(Pessoa)
admin.site.register(FuncaoFuncionarioExterno)
admin.site.register(ContratoExterno)
admin.site.register(AtribuicaoAula)
admin.site.register(AtribuicaoExterno)
