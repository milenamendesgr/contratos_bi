from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from utils.comentarios_service import (
    CommentConflictError,
    CommentValidationError,
    adicionar_comentario,
    editar_comentario,
    excluir_comentario,
    listar_comentarios,
    obter_historico_comentario,
)


class CommentsServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "comentarios_service_test.db"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_validates_required_fields(self) -> None:
        invalid_cases = [
            ("", "000001", "01", "MED001", "Texto"),
            ("0101", "", "01", "MED001", "Texto"),
            ("0101", "000001", "01", "", "Texto"),
            ("0101", "000001", "01", "MED001", "   "),
        ]

        for filial, contrato, revisao, medicao, comentario in invalid_cases:
            with self.subTest(
                filial=filial,
                contrato=contrato,
                comentario=comentario,
                medicao=medicao,
            ):
                with self.assertRaises(CommentValidationError):
                    adicionar_comentario(
                        filial,
                        contrato,
                        revisao,
                        medicao,
                        comentario,
                        database_path=self.database_path,
                    )

    def test_rejects_comment_above_limit(self) -> None:
        with self.assertRaises(CommentValidationError):
            adicionar_comentario(
                "0101",
                "000001",
                "01",
                "MED001",
                "x" * 4001,
                database_path=self.database_path,
            )

    def test_accepts_operation_without_user(self) -> None:
        created = adicionar_comentario(
            "0101",
            "000003",
            "01",
            "MED003",
            "Comentario sem usuario",
            database_path=self.database_path,
        )
        self.assertEqual(created["usuario_criacao"], "Nao identificado")

    def test_complete_service_flow(self) -> None:
        created = adicionar_comentario(
            " 0101 ",
            " 000001 ",
            " 01 ",
            " MED001 ",
            " Comentario original ",
            " usuario.um ",
            database_path=self.database_path,
        )
        self.assertEqual(created["comentario"], "Comentario original")
        self.assertEqual(created["filial"], "0101")

        edited = editar_comentario(
            created["id_comentario"],
            created["versao"],
            "Comentario editado",
            "usuario.dois",
            database_path=self.database_path,
        )
        self.assertEqual(edited["versao"], 2)

        listed = listar_comentarios(
            "0101",
            "000001",
            "01",
            "MED001",
            database_path=self.database_path,
        )
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["comentario"], "Comentario editado")

        history = obter_historico_comentario(
            created["id_comentario"],
            database_path=self.database_path,
        )
        self.assertEqual([row["versao"] for row in history], [1, 2])

        deleted = excluir_comentario(
            created["id_comentario"],
            edited["versao"],
            "usuario.tres",
            database_path=self.database_path,
        )
        self.assertEqual(deleted["excluido"], 1)
        self.assertEqual(
            listar_comentarios(
                "0101",
                "000001",
                "01",
                "MED001",
                database_path=self.database_path,
            ),
            [],
        )

    def test_translates_concurrent_update(self) -> None:
        created = adicionar_comentario(
            "0101",
            "000002",
            "01",
            "MED002",
            "Versao inicial",
            "usuario.um",
            database_path=self.database_path,
        )
        editar_comentario(
            created["id_comentario"],
            1,
            "Versao atual",
            "usuario.dois",
            database_path=self.database_path,
        )

        with self.assertRaises(CommentConflictError):
            editar_comentario(
                created["id_comentario"],
                1,
                "Versao atrasada",
                "usuario.tres",
                database_path=self.database_path,
            )


if __name__ == "__main__":
    unittest.main()
