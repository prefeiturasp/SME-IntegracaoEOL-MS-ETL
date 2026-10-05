"""Testes do modelo EtlAuditoriaLinha."""

from django.test import TestCase

from apps.controle_auditoria.models import EtlAuditoriaLinha


class EtlAuditoriaLinhaTest(TestCase):
    """Testes de criação e atualização de EtlAuditoriaLinha."""

    def test_cria_e_recupera_hash(self) -> None:
        """Verifica que um registro é criado e seu hash pode ser recuperado."""
        EtlAuditoriaLinha.objects.create(
            id_destino="professor:0012345",
            hash_controle="a" * 64,
        )
        obj = EtlAuditoriaLinha.objects.get(id_destino="professor:0012345")
        self.assertEqual(obj.hash_controle, "a" * 64)

    def test_upsert_atualiza_hash(self) -> None:
        """Verifica que bulk_create com update_conflicts atualiza o hash existente."""
        EtlAuditoriaLinha.objects.create(
            id_destino="professor:0099999",
            hash_controle="hash_antigo" + "0" * 53,
        )
        EtlAuditoriaLinha.objects.bulk_create(
            [
                EtlAuditoriaLinha(
                    id_destino="professor:0099999",
                    hash_controle="b" * 64,
                )
            ],
            update_conflicts=True,
            unique_fields=["id_destino"],
            update_fields=["hash_controle"],
        )
        obj = EtlAuditoriaLinha.objects.get(id_destino="professor:0099999")
        self.assertEqual(obj.hash_controle, "b" * 64)

    def test_pk_e_id_destino(self) -> None:
        """Verifica que a chave primária é o próprio id_destino."""
        linha = EtlAuditoriaLinha.objects.create(
            id_destino="turma_escola:9988776",
            hash_controle="c" * 64,
        )
        self.assertEqual(linha.pk, "turma_escola:9988776")

    def test_atualizado_em_preenchido_automaticamente(self) -> None:
        """Verifica que o campo atualizado_em é preenchido automaticamente."""
        linha = EtlAuditoriaLinha.objects.create(
            id_destino="cargo:3239",
            hash_controle="d" * 64,
        )
        self.assertIsNotNone(linha.atualizado_em)
