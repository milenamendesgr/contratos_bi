"""Regressoes de isolamento e transporte; nenhuma API real e chamada."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

import requests

from utils import contratos_repository as repository


class SecurityTests(unittest.TestCase):
    def test_demo_ignora_configuracao_privada(self):
        code = '''
import sys
class BlockPrivate:
    def find_spec(self, fullname, *args):
        if fullname == "config.local_settings":
            raise AssertionError("Importacao privada")
sys.meta_path.insert(0, BlockPrivate())
from config.settings import DEMO_MODE, COMENTARIOS_DB_CONFIG
assert DEMO_MODE
assert COMENTARIOS_DB_CONFIG["path"].name == "demo_comentarios.db"
from utils.contratos_repository import get_base_contratos, run_sql
assert len(get_base_contratos()) == 48
try:
    run_sql("SELECT 1")
except RuntimeError:
    pass
else:
    raise AssertionError("SQL externo permitido")
'''
        env = dict(os.environ, CONTRATOS_DATA_MODE="demo",
                   CONTRATOS_API_URL="https://example.invalid/sql",
                   CONTRATOS_SQLITE_PATH="banco_privado_nao_abrir.db")
        result = subprocess.run([sys.executable, "-c", code], env=env,
                                cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_configuracoes_inseguras_nao_fazem_requisicao(self):
        for url, verify in [("http://example.invalid", True),
                            ("https://user:secret@example.invalid", True),
                            ("https://example.invalid?token=secret", True),
                            ("https://example.invalid", False)]:
            with self.subTest(url=url), patch.object(repository, "DEMO_MODE", False), \
                    patch.object(repository, "API_CONFIG", {"url": url, "verify": verify}), \
                    patch("requests.sessions.Session.request") as request:
                self.assertTrue(repository.run_sql("SELECT 1").empty)
                request.assert_not_called()

    def test_transporte_e_erros_sem_dados_sensiveis(self):
        config = {"url": "https://example.invalid/sql", "verify": True,
                  "user": "usuario", "password": "segredo"}
        response = Mock(status_code=302, text="dados privados")
        with patch.object(repository, "DEMO_MODE", False), \
                patch.object(repository, "API_CONFIG", config), \
                patch("requests.Session") as session_type:
            session = session_type.return_value.__enter__.return_value
            session.get.return_value = response
            self.assertTrue(repository.run_sql("SELECT 1").empty)
            self.assertFalse(session.trust_env)
            self.assertFalse(session.get.call_args.kwargs["allow_redirects"])
            self.assertTrue(session.get.call_args.kwargs["verify"])
            self.assertNotIn("dados privados", repository.LAST_ERROR)
            session.get.side_effect = requests.ConnectionError("segredo")
            self.assertTrue(repository.run_sql("SELECT 1").empty)
            self.assertNotIn("segredo", repository.LAST_ERROR)
            session.get.side_effect = None
            response.status_code = 200
            response.headers = {"content-type": "application/json; charset=utf-8"}
            response.content = b'[{"CONTRATO": "TESTE"}]'
            self.assertEqual(repository.run_sql("SELECT 1").iloc[0]["CONTRATO"], "TESTE")
