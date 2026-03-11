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
        """Configuração de metadados do modelo."""

        db_table = "escolas_consulta_log"
        verbose_name = "consulta de escolas"
        verbose_name_plural = "consultas de escolas"

    def __str__(self) -> str:
        """Representação do modelo como string."""
        return f"offset={self.offset_inicial} limite={self.limite}"
