from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from utils.comentarios_repository import (
    ConcurrentCommentUpdateError,
    add_comment,
    delete_comment,
    edit_comment,
    get_comment_history,
    initialize_comments_database,
    list_comments,
)


class CommentsRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "comentarios_test.db"
        initialize_comments_database(self.database_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_complete_versioned_lifecycle(self) -> None:
        created = add_comment(
            "0101",
            "000001",
            "01",
            "MED001",
            "Comentario original",
            "usuario.criacao",
            database_path=self.database_path,
        )

        self.assertEqual(created["versao"], 1)
        self.assertEqual(created["versao_atual"], 1)
        self.assertEqual(created["excluido"], 0)

        edited = edit_comment(
            created["id_comentario"],
            created["versao"],
            "Comentario editado",
            "usuario.edicao",
            database_path=self.database_path,
        )

        self.assertEqual(edited["versao"], 2)
        self.assertEqual(edited["comentario"], "Comentario editado")
        self.assertEqual(edited["usuario_criacao"], "usuario.criacao")
        self.assertEqual(edited["usuario_alteracao"], "usuario.edicao")

        active = list_comments(
            "0101", "000001", "01", "MED001", database_path=self.database_path
        )
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["versao"], 2)

        history = get_comment_history(
            created["id_comentario"],
            database_path=self.database_path,
        )
        self.assertEqual([row["versao"] for row in history], [1, 2])
        self.assertEqual(history[0]["comentario"], "Comentario original")

        deleted = delete_comment(
            created["id_comentario"],
            edited["versao"],
            "usuario.exclusao",
            database_path=self.database_path,
        )

        self.assertEqual(deleted["versao"], 3)
        self.assertEqual(deleted["excluido"], 1)
        self.assertEqual(deleted["usuario_exclusao"], "usuario.exclusao")
        self.assertEqual(
            list_comments(
                "0101", "000001", "01", "MED001", database_path=self.database_path
            ),
            [],
        )
        self.assertEqual(
            len(
                list_comments(
                    "0101",
                    "000001",
                    "01",
                    "MED001",
                    include_deleted=True,
                    database_path=self.database_path,
                )
            ),
            1,
        )

    def test_rejects_stale_version(self) -> None:
        created = add_comment(
            "0101",
            "000002",
            "01",
            "MED002",
            "Primeira versao",
            "usuario.um",
            database_path=self.database_path,
        )
        edit_comment(
            created["id_comentario"],
            1,
            "Segunda versao",
            "usuario.dois",
            database_path=self.database_path,
        )

        with self.assertRaises(ConcurrentCommentUpdateError):
            edit_comment(
                created["id_comentario"],
                1,
                "Edicao baseada em versao antiga",
                "usuario.tres",
                database_path=self.database_path,
            )

    def test_isolates_comments_between_measurements(self) -> None:
        add_comment(
            "0101",
            "000010",
            "01",
            "MED001",
            "Comentario da primeira medicao",
            "usuario",
            database_path=self.database_path,
        )
        add_comment(
            "0101",
            "000010",
            "01",
            "MED002",
            "Comentario da segunda medicao",
            "usuario",
            database_path=self.database_path,
        )

        first = list_comments(
            "0101", "000010", "01", "MED001", database_path=self.database_path
        )
        second = list_comments(
            "0101", "000010", "01", "MED002", database_path=self.database_path
        )

        self.assertEqual([row["comentario"] for row in first], ["Comentario da primeira medicao"])
        self.assertEqual([row["comentario"] for row in second], ["Comentario da segunda medicao"])


if __name__ == "__main__":
    unittest.main()
