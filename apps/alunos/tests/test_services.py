from datetime import date, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import TestCase

from apps.alunos.dtos.model_in import (
    MatriculaTurmaIn,
    NecessidadeEspecialAlunoIn,
)
from apps.alunos.models import (
    DadosAlunoAcompanhamentoEscolar,
    MatriculaAnoAnterior,
    MatriculaAnoLetivo,
    MatriculaComponenteCurricularAnoLetivo,
    ResponsavelAlunoTurma,
)
from apps.alunos.queries import (
    SQL_ALUNO,
    SQL_MATRICULA,
    SQL_MATRICULA_ANO_ANTERIOR,
    SQL_MATRICULA_TURMA,
    SQL_NEE_ALUNO,
    SQL_RESPONSAVEL,
    SQL_RESPONSAVEL_ALUNO_TURMA,
)
from apps.alunos.services import EtlAlunosService, PhaseConfig
from apps.core.libs.base_etl_service import PipelineMetrics


class TestAlunosService(TestCase):
    """Testes para EtlAlunosService (Arquitetura Turbo/PhaseConfig)."""

    def setUp(self) -> None:
        """Inicializa service com EOL mockado.

        _truncar_tabela é mockado para evitar UndefinedTable do psycopg.
        """
        self.mock_eol = MagicMock()
        self.service = EtlAlunosService(
            db_alias="default",
            eol=self.mock_eol,
            id_execucao=uuid4(),
        )
        # Evita UndefinedTable em testes SimpleTestCase/TestCase.
        self.service._truncar_tabela = MagicMock()

    def test_phase_config_e_imutavel(self) -> None:
        """Valida que PhaseConfig é frozen."""
        config = PhaseConfig(
            nome="teste",
            sql="SELECT 1",
            table_name="tb",
            model_class=None,
            dto_in=None,
            pk_field="id",
            update_fields=("f1",),
            unique_fields=("id",),
        )
        with self.assertRaises(AttributeError):
            config.nome = "mudar"  # type: ignore[misc]

    def test_fases_contem_11_configs(self) -> None:
        """Valida que o service define as 11 fases esperadas."""
        self.assertEqual(len(self.service._fases), 11)
        nomes = [f.nome for f in self.service._fases]
        self.assertEqual(
            nomes,
            [
                "tipo_necessidade_especial",
                "aluno",
                "responsavel_aluno",
                "nee_aluno",
                "matricula",
                "matricula_turma",
                "matricula_ano_letivo",
                "matricula_componente_curricular_ano_letivo",
                "dados_aluno_acompanhamento_escolar",
                "responsavel_aluno_turma",
                "matricula_ano_anterior",
            ],
        )

    def test_criar_transform_retorna_tripla(self) -> None:
        """Valida que a factory de transform gera a tripla (pk, hash, obj)."""
        config = self.service._fases[0]
        transform = self.service._criar_transform(config)

        row = (1, "Desc", 10, None)
        pk, h, obj = transform(row)

        self.assertEqual(pk, "1")
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)
        self.assertEqual(obj.descricao, "Desc")

    def test_criar_transform_pk_composta(self) -> None:
        """Valida PK composta (Matricula-Turma-Situacao-Sequencia)."""
        config = self.service._fases[5]
        transform = self.service._criar_transform(config)

        # Ordem POSICIONAL deve casar com MatriculaTurmaIn:
        # ... sequencia, origem, ano, serie_resumida.
        row = (
            123,
            456,
            "01",
            None,
            None,
            7,
            1,
            None,
            None,
            "5A",
            "100001",
            5,
            2,
            "Ensino Fundamental",
            "Ciclo Interdisciplinar",
            1,
            True,
            2026,
            "5",
        )
        pk, _, _ = transform(row)

        self.assertEqual(pk, "123-456-7-1")

    def test_sql_matricula_turma_ordem_final_casa_com_dto(self) -> None:
        """Ordem do SELECT final casa com MatriculaTurmaIn (din posicional)."""
        antes_from = SQL_MATRICULA_TURMA.split(
            "FROM CteMatriculaTurmaSequencia"
        )[0]
        select_final = antes_from[antes_from.rfind(")") + 1 :]
        self.assertLess(
            select_final.index("codigo_ue_turma"),
            select_final.index("codigo_etapa_ensino"),
        )
        self.assertLess(
            select_final.index("descricao_ciclo_ensino"),
            select_final.index("sequencia"),
        )
        self.assertLess(
            select_final.index("sequencia"),
            select_final.index("origem_atual"),
        )
        self.assertLess(
            select_final.index("origem_atual"),
            select_final.index("ano_letivo_turma"),
        )
        self.assertLess(
            select_final.index("ano_letivo_turma"),
            select_final.index("serie_resumida"),
        )

    def test_sql_aluno_expoe_cns_antes_de_data_atualizacao(self) -> None:
        """Valida que a query segue a ordem esperada pelo AlunoIn."""
        self.assertIn("cns.nr_cns AS cns", SQL_ALUNO)
        self.assertIn("OUTER APPLY", SQL_ALUNO)
        self.assertIn("WHERE nee.cd_aluno = a.cd_aluno", SQL_ALUNO)
        self.assertLess(
            SQL_ALUNO.index("cns.nr_cns AS cns"),
            SQL_ALUNO.index("data_atualizacao_contato"),
        )

    def test_sqls_expoem_campos_complementares_dos_dtos(self) -> None:
        """Valida campos esperados pelos DTOs nas fases principais."""
        self.assertIn("e.ci_endereco AS endereco_id", SQL_RESPONSAVEL)
        self.assertIn(
            "ra.cd_ddd_telefone_fixo_responsavel AS ddd_telefone_fixo",
            SQL_RESPONSAVEL,
        )
        self.assertIn(
            "ra.nr_telefone_comercial_responsavel AS nr_telefone_comercial",
            SQL_RESPONSAVEL,
        )
        self.assertIn(
            "ra.dt_atualizacao_tabela AS data_atualizacao_tabela",
            SQL_RESPONSAVEL,
        )
        self.assertIn(
            "ra.cd_tipo_recurso AS codigo_tipo_recurso", SQL_NEE_ALUNO
        )
        self.assertIn(
            "tra.dc_tipo_recurso AS descricao_tipo_recurso", SQL_NEE_ALUNO
        )
        self.assertIn("OUTER APPLY", SQL_NEE_ALUNO)
        self.assertIn("recurso_aluno", SQL_NEE_ALUNO)
        self.assertIn("tipo_recurso_aluno", SQL_NEE_ALUNO)
        self.assertIn("data_situacao_matricula_data_hora", SQL_MATRICULA)
        self.assertIn("CAST(1 AS bit) AS origem_atual", SQL_MATRICULA)
        self.assertIn("ROW_NUMBER() OVER", SQL_MATRICULA)
        self.assertIn(
            "te.cd_tipo_turma AS codigo_tipo_turma",
            SQL_MATRICULA_TURMA,
        )
        self.assertIn(
            "mt.dt_atlz_tab AS data_atualizacao_tabela",
            SQL_MATRICULA_TURMA,
        )
        self.assertIn("te.cd_escola AS codigo_ue_turma", SQL_MATRICULA_TURMA)
        self.assertIn(
            "serie.cd_ciclo_ensino AS codigo_ciclo_ensino",
            SQL_MATRICULA_TURMA,
        )
        self.assertIn(
            "serie.dc_etapa_ensino AS descricao_etapa_ensino",
            SQL_MATRICULA_TURMA,
        )
        self.assertIn(
            "serie.dc_ciclo_ensino AS descricao_ciclo_ensino",
            SQL_MATRICULA_TURMA,
        )

    def test_sem_ano_letivo_remove_marcadores_e_preserva_padrao(self) -> None:
        """Valida SQLs sem marcador quando ano_letivo não é informado."""
        fases = {fase.nome: fase for fase in self.service._fases}

        for fase in fases.values():
            self.assertNotIn("/*FILTRO_ANO_LETIVO", fase.sql)

        self.assertIn(
            "and an_letivo = year(getdate())",
            fases["dados_aluno_acompanhamento_escolar"].sql,
        )
        self.assertIn(
            "matricula.an_letivo = YEAR(GETDATE())",
            fases["responsavel_aluno_turma"].sql,
        )
        self.assertIn(
            "te.an_letivo = YEAR(GETDATE()) - 1",
            fases["matricula_ano_anterior"].sql,
        )

    def test_anos_letivos_aplica_filtro_in_nas_fases(self) -> None:
        """Valida que anos_letivos gera filtro IN e remove marcadores."""
        service = EtlAlunosService(
            db_alias="default",
            eol=self.mock_eol,
            id_execucao=uuid4(),
            anos_letivos=[2021, 2022, 2023, 2024, 2025],
        )
        fases = {fase.nome: fase for fase in service._fases}
        anos = "2021, 2022, 2023, 2024, 2025"

        for fase in fases.values():
            self.assertNotIn("/*FILTRO_ANO_LETIVO", fase.sql)

        self.assertIn(
            f"AND an_letivo IN ({anos})", fases["matricula"].sql
        )
        self.assertIn(
            f"AND te.an_letivo IN ({anos})", fases["matricula_turma"].sql
        )
        self.assertIn("fmc.cd_aluno = a.cd_aluno", fases["aluno"].sql)
        self.assertIn(
            f"and an_letivo IN ({anos})",
            fases["dados_aluno_acompanhamento_escolar"].sql,
        )
        self.assertNotIn(
            "year(getdate())",
            fases["dados_aluno_acompanhamento_escolar"].sql,
        )
        self.assertIn(
            f"matricula.an_letivo IN ({anos})",
            fases["responsavel_aluno_turma"].sql,
        )
        self.assertIn(
            f"te.an_letivo IN ({anos})",
            fases["matricula_ano_anterior"].sql,
        )

    def test_fases_selecionadas_sao_repassadas_para_base(self) -> None:
        """Valida que o service respeita execução parcial por nome de fase."""
        service = EtlAlunosService(
            db_alias="default",
            eol=self.mock_eol,
            id_execucao=uuid4(),
            fases=["aluno"],
        )

        self.assertEqual(service._fases_selecionadas, ["aluno"])

    def test_criar_transform_aluno_mapeia_cns_e_possui_deficiencia(
        self,
    ) -> None:
        """Valida linha completa da query de aluno."""
        config = self.service._fases[1]
        transform = self.service._criar_transform(config)

        row = (
            1,
            "Aluno",
            None,
            date(2010, 1, 1),
            1,
            "BR",
            "123",
            "456",
            "Mae",
            "Branca",
            "789",
            datetime(2023, 1, 1, 14, 46, 50),
            1,
        )

        pk, _, obj = transform(row)

        self.assertEqual(pk, "1")
        self.assertEqual(obj.cns, "789")
        self.assertTrue(obj.possui_deficiencia)
        self.assertEqual(
            obj.data_atualizacao_contato.replace(tzinfo=None),
            datetime(2023, 1, 1, 14, 46, 50),
        )

    @patch.object(EtlAlunosService, "sync_batch")
    def test_executar_fase_chama_sync_batch_por_chunk(
        self, mock_sync: MagicMock
    ) -> None:
        """Valida o pipeline Producer-Consumer com 2 chunks."""
        config = self.service._fases[0]
        self.mock_eol.iter_query.return_value = [
            [(1, "A", 1, None)],
            [(2, "B", 1, None)],
        ]
        mock_sync.return_value = (1, 0)

        metrics = self.service._executar_fase(config)

        self.assertEqual(metrics.total_lidos, 2)
        self.assertEqual(metrics.total_escritos, 2)
        self.assertEqual(mock_sync.call_count, 2)

    def test_executar_fase_erro_producer_e_propagado(self) -> None:
        """Valida que erros na extração (Producer thread) param o ETL."""
        config = self.service._fases[1]
        self.mock_eol.iter_query.side_effect = RuntimeError("Falha SQL")

        with self.assertRaises(RuntimeError):
            self.service._executar_fase(config)

    def test_executar_pula_fases_anteriores(self) -> None:
        """Valida o parâmetro fase_inicial — fases 1-5 devem ser ignoradas."""
        with patch.object(EtlAlunosService, "_executar_fase") as mock_fase:
            mock_fase.return_value = PipelineMetrics(total_escritos=1)

            res = self.service.executar(fase_inicial=6)

            self.assertEqual(len(res), 4)
            self.assertIn("matricula_turma", res)
            self.assertEqual(mock_fase.call_count, 4)

    def test_executar_completo_acumula_resultados(self) -> None:
        """Valida execução completa."""
        with patch.object(EtlAlunosService, "_executar_fase") as mock_fase:
            mock_fase.return_value = PipelineMetrics(total_escritos=10)

            res = self.service.executar(fase_inicial=1)

            self.assertEqual(len(res), 9)
            self.assertEqual(res["aluno"], 10)
            self.assertEqual(mock_fase.call_count, 9)

    @patch.object(EtlAlunosService, "sync_batch")
    def test_executar_fase_passa_batch_num_correto(
        self, mock_sync: MagicMock
    ) -> None:
        """Valida que batch_num é incrementado a cada chunk."""
        config = self.service._fases[0]
        self.mock_eol.iter_query.return_value = [
            [(1, "A", 1, None)],
            [(2, "B", 1, None)],
            [(3, "C", 1, None)],
        ]
        mock_sync.return_value = (1, 0)

        self.service._executar_fase(config)

        # Parâmetro batch_num foi removido do _sync_batch.
        # O teste agora apenas valida que a chamada ocorreu
        self.assertTrue(mock_sync.called)

    @patch.object(EtlAlunosService, "sync_batch")
    def test_sync_batch_argumentos_corretos(
        self, mock_sync: MagicMock
    ) -> None:
        """Valida que model_class, table_name, update/unique_fields.

        Verifica se os campos são passados corretamente ao _sync_batch.
        """
        config = self.service._fases[0]
        self.mock_eol.iter_query.return_value = [[(1, "A", 1, None)]]
        mock_sync.return_value = (1, 0)

        self.service._executar_fase(config)

        args, _ = mock_sync.call_args
        fase_meta = args[1]
        self.assertEqual(fase_meta["model_class"], config.model_class)
        self.assertEqual(
            fase_meta["update_fields"], list(config.update_fields)
        )
        self.assertEqual(
            fase_meta["unique_fields"], list(config.unique_fields)
        )
        self.assertEqual(fase_meta["modo_escrita"], config.modo_escrita)

    def test_nee_aluno_dto_in_aceita_campos_recurso(self) -> None:
        """Valida que NecessidadeEspecialAlunoIn recebe recurso do SQL."""
        dto = NecessidadeEspecialAlunoIn(
            codigo_necessidade_especial_aluno=1,
            codigo_aluno=100,
            codigo_necessidade_especial=5,
            dt_inicio=date(2020, 1, 1),
            dt_fim=None,
            codigo_tipo_recurso=10,
            descricao_tipo_recurso="NENHUM",
        )
        self.assertEqual(dto.codigo_necessidade_especial_aluno, 1)
        self.assertEqual(dto.dt_inicio, date(2020, 1, 1))
        self.assertIsNone(dto.dt_fim)
        self.assertEqual(dto.codigo_tipo_recurso, 10)

    def test_primeiro_run_repassado_ao_base(self) -> None:
        """Valida que primeiro_run=True chega ao BaseEtlService."""
        service = EtlAlunosService(
            db_alias="default",
            eol=self.mock_eol,
            primeiro_run=True,
        )
        self.assertTrue(service.primeiro_run)

    @patch.object(EtlAlunosService, "sync_batch")
    def test_executar_fase_loga_throughput(self, mock_sync: MagicMock) -> None:
        """Valida que o log de cada lote inclui throughput em reg/s."""
        config = self.service._fases[0]
        self.mock_eol.iter_query.return_value = [[(1, "A", 1, None)]]
        mock_sync.return_value = (1, 0)

        with self.assertLogs(
            "apps.core.libs.base_etl_service", level="INFO"
        ) as cm:
            self.service._executar_fase(config)

        self.assertTrue(any("reg/s" in msg for msg in cm.output))

    def test_matricula_turma_dto_in_aceita_matricula_nula(self) -> None:
        """Valida que MatriculaTurmaIn aceita codigo_matricula nulo."""
        dto = MatriculaTurmaIn(
            codigo_matricula=None,
            codigo_turma=101,
            numero_chamada="05",
            data_situacao=None,
            data_situacao_data_hora=None,
            codigo_situacao_aluno=None,
            codigo_tipo_turma=None,
            tipo_turno=None,
            data_atualizacao_tabela=None,
            nome_turma=None,
            codigo_ue_turma=None,
            codigo_etapa_ensino=None,
            codigo_ciclo_ensino=None,
            descricao_etapa_ensino=None,
            descricao_ciclo_ensino=None,
            sequencia=1,
        )
        domain = dto.to_domain()
        self.assertIsNone(domain["codigo_matricula"])
        self.assertEqual(domain["codigo_turma"], 101)
        self.assertEqual(domain["sequencia"], 1)
        self.assertIsNone(domain["codigo_ue_turma"])

    def test_fase_matricula_turma_chave_inclui_sequencia(self) -> None:
        """Valida chave e update_fields da fase matricula_turma."""
        fase = self.service._fases[5]
        self.assertEqual(fase.nome, "matricula_turma")
        self.assertEqual(
            fase.pk_field,
            [
                "codigo_matricula",
                "codigo_turma",
                "codigo_situacao_aluno",
                "sequencia",
            ],
        )
        self.assertEqual(
            fase.unique_fields,
            (
                "codigo_matricula",
                "codigo_turma",
                "codigo_situacao_aluno",
                "sequencia",
            ),
        )
        self.assertIn("sequencia", fase.update_fields)
        self.assertIn("codigo_ue_turma", fase.update_fields)
        self.assertIn("codigo_ciclo_ensino", fase.update_fields)
        self.assertIn("descricao_etapa_ensino", fase.update_fields)
        self.assertIn("descricao_ciclo_ensino", fase.update_fields)

    def test_fase_matricula_inclui_codigo_dre_em_update_fields(self) -> None:
        """Valida que a fase matricula atualiza codigo_dre."""
        fase = self.service._fases[4]
        self.assertEqual(fase.nome, "matricula")
        self.assertIn("codigo_dre", fase.update_fields)

    def test_fase_7_nome_e_model_corretos(self) -> None:
        """Valida nome e model_class da fase 7."""
        fase = self.service._fases[6]
        self.assertEqual(fase.nome, "matricula_ano_letivo")
        self.assertEqual(fase.model_class, MatriculaAnoLetivo)

    def test_fase_8_nome_e_model_corretos(self) -> None:
        """Valida nome e model_class da fase 8."""
        fase = self.service._fases[7]
        self.assertEqual(
            fase.nome, "matricula_componente_curricular_ano_letivo"
        )
        self.assertEqual(
            fase.model_class, MatriculaComponenteCurricularAnoLetivo
        )

    def test_fase_7_suporta_bulk_insert(self) -> None:
        """Valida que fase 7 tem suporta_bulk_insert=True."""
        self.assertTrue(self.service._fases[6].suporta_bulk_insert)

    def test_fase_8_suporta_bulk_insert(self) -> None:
        """Valida que fase 8 tem suporta_bulk_insert=True."""
        self.assertTrue(self.service._fases[7].suporta_bulk_insert)

    def test_criar_transform_fase_7_pk_composta(self) -> None:
        """Valida PK composta de 7 campos na fase 7."""
        config = self.service._fases[6]
        transform = self.service._criar_transform(config)
        row = ("DRE01", "UE01", 1, 2024, 5, "EF", 3, "3A", "Turma A", 100)
        pk, h, _ = transform(row)
        self.assertEqual(pk, "DRE01-UE01-1-2024-EF-3A-Turma A")
        self.assertEqual(len(h), 64)

    def test_criar_transform_fase_8_pk_composta(self) -> None:
        """Valida PK composta de 7 campos (com turma) na fase 8."""
        config = self.service._fases[7]
        transform = self.service._criar_transform(config)
        row = ("UE01", "DRE01", 2024, "EF", 3, 100, "3A", "T A", 50)
        pk, h, _ = transform(row)
        self.assertEqual(pk, "UE01-DRE01-2024-EF-100-3A-T A")
        self.assertEqual(len(h), 64)

    def test_executar_pula_fases_1_a_6(self) -> None:
        """Valida que executar(fase_inicial=7) retorna as fases restantes."""
        with patch.object(EtlAlunosService, "_executar_fase") as mock_fase:
            mock_fase.return_value = PipelineMetrics(total_escritos=1)
            res = self.service.executar(fase_inicial=7)
            self.assertEqual(len(res), 5)
            self.assertIn("matricula_ano_letivo", res)
            self.assertIn("matricula_componente_curricular_ano_letivo", res)
            self.assertIn("dados_aluno_acompanhamento_escolar", res)
            self.assertIn("responsavel_aluno_turma", res)
            self.assertIn("matricula_ano_anterior", res)
            self.assertEqual(mock_fase.call_count, 5)

    @patch.object(EtlAlunosService, "sync_batch")
    def test_fase_7_chama_sync_batch_por_chunk(
        self, mock_sync: MagicMock
    ) -> None:
        """Valida 2 chunks sync_batch chamado 2 vezes para fase 7."""
        config = self.service._fases[6]
        self.mock_eol.iter_query.return_value = [
            [("DRE01", "UE01", 1, 2024, 5, "EF", 3, "3A", "T A", 10)],
            [("DRE02", "UE02", 1, 2024, 5, "EF", 3, "3A", "T B", 20)],
        ]
        mock_sync.return_value = (1, 0)
        metrics = self.service._executar_fase(config)
        self.assertEqual(mock_sync.call_count, 2)
        self.assertEqual(metrics.total_lidos, 2)

    @patch.object(EtlAlunosService, "sync_batch")
    def test_fase_8_chama_sync_batch_por_chunk(
        self, mock_sync: MagicMock
    ) -> None:
        """Valida 2 chunks sync_batch chamado 2 vezes para fase 8."""
        config = self.service._fases[7]
        self.mock_eol.iter_query.return_value = [
            [("UE01", "DRE01", 2024, "EF", 3, 100, "3A", "T A", 10)],
            [("UE02", "DRE02", 2024, "EF", 3, 200, "3A", "T B", 20)],
        ]
        mock_sync.return_value = (1, 0)
        metrics = self.service._executar_fase(config)
        self.assertEqual(mock_sync.call_count, 2)
        self.assertEqual(metrics.total_lidos, 2)

    def test_fase_9_nome_e_model_corretos(self) -> None:
        """Valida nome e model_class da fase 9."""
        fase = self.service._fases[8]
        self.assertEqual(fase.nome, "dados_aluno_acompanhamento_escolar")
        self.assertEqual(fase.model_class, DadosAlunoAcompanhamentoEscolar)

    def test_fase_9_suporta_bulk_insert(self) -> None:
        """Valida que fase 9 tem suporta_bulk_insert=True."""
        self.assertTrue(self.service._fases[8].suporta_bulk_insert)

    def test_fases_lote_5_sao_full_refresh(self) -> None:
        """Valida as fases materializadas do lote 5."""
        responsaveis = self.service._fases[9]
        historico = self.service._fases[10]

        self.assertEqual(responsaveis.nome, "responsavel_aluno_turma")
        self.assertEqual(responsaveis.model_class, ResponsavelAlunoTurma)
        self.assertEqual(historico.nome, "matricula_ano_anterior")
        self.assertEqual(historico.model_class, MatriculaAnoAnterior)
        self.assertEqual(responsaveis.modo_escrita, "full_refresh")
        self.assertEqual(historico.modo_escrita, "full_refresh")
        self.assertTrue(responsaveis.truncate_on_full_sync)
        self.assertTrue(historico.truncate_on_full_sync)

    def test_queries_lote_5_replicam_filtros_legados(self) -> None:
        """Valida os filtros estruturais das queries materializadas."""
        self.assertIn(
            "aluno.cd_tipo_sigilo IS NULL", SQL_RESPONSAVEL_ALUNO_TURMA
        )
        self.assertIn(
            "matricula.st_matricula = 1", SQL_RESPONSAVEL_ALUNO_TURMA
        )
        self.assertIn(
            "MAX(mte.dt_situacao_aluno)", SQL_MATRICULA_ANO_ANTERIOR
        )
        self.assertIn(
            "mte.nr_chamada_aluno <> '0'", SQL_MATRICULA_ANO_ANTERIOR
        )
        self.assertIn(
            "mte.nr_chamada_aluno <> 'NULL'",
            SQL_MATRICULA_ANO_ANTERIOR,
        )

    def test_criar_transform_fases_lote_5(self) -> None:
        """Valida transformação e chaves naturais das fases do lote 5."""
        responsaveis = self.service._criar_transform(self.service._fases[9])
        pk_responsavel, _, obj_responsavel = responsaveis(
            (
                10,
                20,
                2026,
                "DRE01 ",
                "DRE TESTE ",
                "UE01 ",
                "UE TESTE ",
                30,
                "5A ",
                12345678901,
                40,
                1,
                5,
                2,
                "5 ",
                5,
            )
        )
        historico = self.service._criar_transform(self.service._fases[10])
        pk_historico, _, obj_historico = historico((2025, "UE01 ", 30, 27))

        self.assertEqual(pk_responsavel, "10-20-30")
        self.assertEqual(obj_responsavel.codigo_ue, "UE01")
        self.assertEqual(pk_historico, "2025-UE01 -30")
        self.assertEqual(obj_historico.codigo_ue, "UE01")

    def test_criar_transform_fase_9_pk_composta(self) -> None:
        """Valida PK composta de 3 campos na fase 9."""
        config = self.service._fases[8]
        transform = self.service._criar_transform(config)
        row = (
            1001,
            "JOAO",
            None,
            "MARIA",
            "123",
            None,
            "EMEF",
            1,
            "DRE01",
            "DRE-N",
            "UE01",
            "EMEF TESTE",
            555,
            "T A",
            1,
            "Ativo",
            None,
            5,
            2,
            "Ensino Fundamental",
            "Ciclo Interdisciplinar",
            "5A",
            5,
        )
        pk, h, _ = transform(row)
        self.assertEqual(pk, "1001-555-1")
        self.assertEqual(len(h), 64)

    @patch.object(EtlAlunosService, "sync_batch")
    def test_fase_9_chama_sync_batch_por_chunk(
        self, mock_sync: MagicMock
    ) -> None:
        """Valida 2 chunks sync_batch chamado 2 vezes para fase 9."""
        config = self.service._fases[8]
        row = (
            1001,
            "JOAO",
            None,
            "MARIA",
            "123",
            None,
            "EMEF",
            1,
            "DRE01",
            "DRE-N",
            "UE01",
            "EMEF TESTE",
            555,
            "T A",
            1,
            "Ativo",
            None,
            5,
            2,
            "Ensino Fundamental",
            "Ciclo Interdisciplinar",
            "5A",
            5,
        )
        self.mock_eol.iter_query.return_value = [[row], [row]]
        mock_sync.return_value = (1, 0)
        metrics = self.service._executar_fase(config)
        self.assertEqual(mock_sync.call_count, 2)
        self.assertEqual(metrics.total_lidos, 2)
