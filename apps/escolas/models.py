"""Modelos do app escolas."""

from django.db import models


class ConsultaEscolasLog(models.Model):
    """Historico de consultas de escolas por offset."""

    id = models.BigAutoField(primary_key=True)
    offset_inicial = models.IntegerField()
    limite = models.IntegerField()
    total_retorno = models.IntegerField()
    executado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "escolas_consulta_log"
        verbose_name = "consulta de escolas"
        verbose_name_plural = "consultas de escolas"

    def __str__(self) -> str:
        return f"offset={self.offset_inicial} limite={self.limite}"
