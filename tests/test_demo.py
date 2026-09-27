"""Integridade e isolamento da demonstração pública."""
import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd

from config.settings import COMENTARIOS_DB_CONFIG, DEMO_MODE
from utils.demo_data import gerar_bases_demo
from utils import contratos_repository as repository


class DemoTests(unittest.TestCase):
    def test_relacionamentos_e_totais(self):
        bases = gerar_bases_demo(date(2026, 9, 27))
        contratos = bases["contratos"].set_index(["FILIAL", "CONTRATO"])
        self.assertEqual(len(contratos), 48)
        self.assertTrue(contratos.index.is_unique)
        for nome in ["medicoes", "adiantamentos", "fluxo", "itens"]:
            chaves = pd.MultiIndex.from_frame(bases[nome][["FILIAL", "CONTRATO"]])
            self.assertTrue(chaves.isin(contratos.index).all(), nome)
        medido = bases["medicoes"].groupby(["FILIAL", "CONTRATO"]).VALOR_TOTAL_MEDICAO.sum()
        esperado = contratos.VALOR_ATUAL - contratos.SALDO_CONTRATO
        pd.testing.assert_series_equal(medido.reindex(contratos.index, fill_value=0), esperado, check_names=False)
        chaves = ["FILIAL", "CONTRATO", "REVISAO_CONTRATO", "NUMERO_MEDICAO"]
        detalhe = bases["medicoes_itens"].groupby(chaves).VALOR_TOTAL_ITEM.sum()
        cabecalho = bases["medicoes"].set_index(chaves).VALOR_TOTAL_MEDICAO.sort_index()
        pd.testing.assert_series_equal(detalhe, cabecalho, check_names=False)
        pd.testing.assert_frame_equal(bases["contratos"], gerar_bases_demo(date(2026, 9, 27))["contratos"])

    def test_repositorios_sem_rede(self):
        self.assertTrue(DEMO_MODE)
        self.assertEqual(COMENTARIOS_DB_CONFIG["path"].name, "demo_comentarios.db")
        with patch("requests.sessions.Session.request", side_effect=AssertionError("Acesso externo")):
            for nome in ["base_contratos", "execucao_contratual", "financeiro", "fluxo_financeiro",
                         "adiantamentos", "fornecedores", "medicoes", "medicoes_itens_detalhe",
                         "validacoes_base_contratos"]:
                func = getattr(repository, "get_" + nome)
                func.clear()
                self.assertFalse(func().empty, nome)
            with self.assertRaises(RuntimeError):
                repository.run_sql("SELECT 1")

    def test_telas(self):
        from streamlit.testing.v1 import AppTest
        with patch("requests.sessions.Session.request", side_effect=AssertionError("Acesso externo")):
            for arquivo in ["main.py", "app.py"]:
                app = AppTest.from_file(arquivo, default_timeout=30).run()
                self.assertEqual(len(app.exception), 0)
                opcoes = list(app.sidebar.radio[0].options)
                for opcao in opcoes:
                    app.sidebar.radio[0].set_value(opcao).run()
                    self.assertEqual(len(app.exception), 0, (arquivo, opcao, list(app.exception)))


if __name__ == "__main__":
    unittest.main()
