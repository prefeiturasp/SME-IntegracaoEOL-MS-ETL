"""Modelos abstratos compartilhados entre os domínios do projeto."""

from django.db import models


class ModeloBase(models.Model):
    """Modelo abstrato base para tabelas de domínio gerenciadas pelo ETL.

    Fornece o campo de auditoria `transferido_em`, presente em todas as tabelas
    de destino. Esse campo é ETL-controlado e atualizado em toda execução
    (INSERT e ON CONFLICT DO UPDATE), independente de o dado ter mudado.

    Permite cruzar com o SINC_REC_DB: registros com `transferido_em` anterior
    ao início da última execução ETL não foram alcançados na carga.
    """

    transferido_em = models.DateTimeField()

    class Meta:
        abstract = True
