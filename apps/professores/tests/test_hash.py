"""Testes de _calcular_hash e _upsert_incremental do serviço de professores."""

import hashlib
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.controle_auditoria.models import EtlAuditoriaLinha
from apps.professores.services import _calcular_hash, _upsert_incremental


class CalcularHashTest(TestCase):
    """Testes para a função _calcular_hash."""

    def test_hash_deterministico(self) -> None:
        """Verifica que o mesmo conjunto de campos sempre gera o mesmo hash."""
        campos = {"nome": "Ana", "codigo_rf": "012345"}
        h1 = _calcular_hash(campos)
        h2 = _calcular_hash(campos)
        self.assertEqual(h1, h2)

    def test_hash_e_sha256_hex(self) -> None:
        """O hash gerado é uma string hexadecimal SHA-256 de 64 caracteres."""
        campos = {"nome": "Ana"}
        resultado = _calcular_hash(campos)
        self.assertEqual(len(resultado), 64)
        # Verifica que é hexadecimal válido
        int(resultado, 16)

    def test_ordem_dos_campos_nao_altera_hash(self) -> None:
        """Verifica que a ordem dos campos não afeta o hash calculado."""
        h1 = _calcular_hash({"a": 1, "b": 2})
        h2 = _calcular_hash({"b": 2, "a": 1})
        self.assertEqual(h1, h2)

    def test_campos_diferentes_geram_hashes_diferentes(self) -> None:
        """Verifica que campos com valores diferentes geram hashes distintos."""
        h1 = _calcular_hash({"nome": "Ana"})
        h2 = _calcular_hash({"nome": "Bia"})
        self.assertNotEqual(h1, h2)

    def test_valor_none_e_aceito(self) -> None:
        """Verifica que campos com valor None não causam exceção."""
        # Não deve lançar exceção
        resultado = _calcular_hash({"nome": None, "codigo": 123})
        self.assertEqual(len(resultado), 64)

    def test_hash_correto_manualmente(self) -> None:
        """Verifica que o hash calculado corresponde ao SHA-256 esperado manualmente."""
        campos = {"z": "b", "a": "x"}
        conteudo = "a='x'|z='b'"
        esperado = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()
        self.assertEqual(_calcular_hash(campos), esperado)


class UpsertIncrementalTest(TestCase):
    """Testa _upsert_incremental com modelos reais no banco professores_db."""

    databases = ["default", "professores_db"]

    def _make_cargo(self, codigo: int, descricao: str) -> dict:  # type: ignore[type-arg]
        """Cria um dicionário representando um cargo com código e descrição."""
        return {"codigo_cargo": codigo, "descricao": descricao}

    def setUp(self) -> None:
        """Configuração base para os testes de upsert incremental."""

    @patch("apps.professores.services.Cargo")
    def test_lista_vazia_retorna_zero(self, _mock_cargo: MagicMock) -> None:
        """Verifica que _upsert_incremental retorna zero para lista vazia."""
        from apps.professores.models import Cargo

        result = _upsert_incremental(Cargo, "cargo", [], ["descricao"])
        self.assertEqual(result, 0)

    def test_registros_novos_sao_escritos(self) -> None:
        """Verifica que novos registros são escritos no banco."""
        from apps.professores.models import Cargo

        rows = [self._make_cargo(3239, "PEB I"), self._make_cargo(3247, "PEB II")]
        escritos = _upsert_incremental(Cargo, "cargo", rows, ["descricao"])
        self.assertEqual(escritos, 2)
        self.assertEqual(Cargo.objects.using("professores_db").count(), 2)

    def test_hashes_salvos_no_banco_de_auditoria(self) -> None:
        """Verifica que os hashes de auditoria são salvos após upsert."""
        from apps.professores.models import Cargo

        rows = [self._make_cargo(3239, "PEB I")]
        _upsert_incremental(Cargo, "cargo", rows, ["descricao"])
        self.assertTrue(
            EtlAuditoriaLinha.objects.filter(id_destino="cargo:3239").exists()
        )

    def test_registro_sem_mudanca_nao_e_reescrito(self) -> None:
        """Verifica que registros sem alteração não são reescritos."""
        from apps.professores.models import Cargo

        rows = [self._make_cargo(3239, "PEB I")]
        # Primeira carga
        _upsert_incremental(Cargo, "cargo", rows, ["descricao"])
        # Segunda carga com os mesmos dados
        escritos = _upsert_incremental(Cargo, "cargo", rows, ["descricao"])
        self.assertEqual(escritos, 0)

    def test_registro_alterado_e_reescrito(self) -> None:
        """Verifica que registros com dados alterados são reescritos."""
        from apps.professores.models import Cargo

        rows_v1 = [self._make_cargo(3239, "PEB I")]
        _upsert_incremental(Cargo, "cargo", rows_v1, ["descricao"])

        rows_v2 = [self._make_cargo(3239, "PEB I - Atualizado")]
        escritos = _upsert_incremental(Cargo, "cargo", rows_v2, ["descricao"])
        self.assertEqual(escritos, 1)

        cargo = Cargo.objects.using("professores_db").get(codigo_cargo=3239)
        self.assertEqual(cargo.descricao, "PEB I - Atualizado")

    def test_mix_novos_e_inalterados(self) -> None:
        """Verifica que apenas registros alterados são reescritos em uma carga mista."""
        from apps.professores.models import Cargo

        rows_v1 = [self._make_cargo(3239, "PEB I"), self._make_cargo(3247, "PEB II")]
        _upsert_incremental(Cargo, "cargo", rows_v1, ["descricao"])

        # Apenas o segundo muda
        rows_v2 = [
            self._make_cargo(3239, "PEB I"),
            self._make_cargo(3247, "PEB II Modificado"),
        ]
        escritos = _upsert_incremental(Cargo, "cargo", rows_v2, ["descricao"])
        self.assertEqual(escritos, 1)

    def test_hash_atualizado_apos_alteracao(self) -> None:
        """Verifica que o hash de auditoria é atualizado após alteração de registro."""
        from apps.professores.models import Cargo

        rows_v1 = [self._make_cargo(3239, "PEB I")]
        _upsert_incremental(Cargo, "cargo", rows_v1, ["descricao"])
        hash_v1 = EtlAuditoriaLinha.objects.get(id_destino="cargo:3239").hash_controle

        rows_v2 = [self._make_cargo(3239, "PEB I Novo")]
        _upsert_incremental(Cargo, "cargo", rows_v2, ["descricao"])
        hash_v2 = EtlAuditoriaLinha.objects.get(id_destino="cargo:3239").hash_controle

        self.assertNotEqual(hash_v1, hash_v2)
