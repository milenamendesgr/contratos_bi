"""Persistencia SQLite dos comentarios versionados de contratos."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from config.settings import COMENTARIOS_DB_CONFIG


QUERY_DIR = Path(__file__).resolve().parents[1] / "queries"
SCHEMA_FILE = QUERY_DIR / "comentarios_schema.sql"
_INITIALIZED_DATABASES: set[Path] = set()
_INITIALIZATION_LOCK = threading.Lock()
try:
    APP_TIMEZONE = ZoneInfo("America/Sao_Paulo")
except ZoneInfoNotFoundError:
    APP_TIMEZONE = timezone(timedelta(hours=-3))


class CommentRepositoryError(RuntimeError):
    """Erro base das operacoes de persistencia de comentarios."""


class CommentNotFoundError(CommentRepositoryError):
    """O comentario solicitado nao existe ou ja foi excluido."""


class ConcurrentCommentUpdateError(CommentRepositoryError):
    """A versao informada deixou de ser a versao atual."""


def _database_path(database_path: str | Path | None = None) -> Path:
    """Resolve o caminho configurado e garante que seu diretorio exista."""
    path = Path(database_path or COMENTARIOS_DB_CONFIG["path"]).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _read_query(filename: str) -> str:
    """Le um comando SQL externo sem o terminador opcional."""
    return (QUERY_DIR / filename).read_text(encoding="utf-8").strip().rstrip(";")


def _now_iso() -> str:
    """Gera data auditavel no fuso corporativo e no formato ISO 8601."""
    return datetime.now(APP_TIMEZONE).isoformat(timespec="seconds")


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def _configure_connection(connection: sqlite3.Connection) -> None:
    """Aplica configuracoes de integridade e concorrencia em cada conexao."""
    busy_timeout_ms = int(COMENTARIOS_DB_CONFIG["busy_timeout_ms"])
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA busy_timeout = {busy_timeout_ms}")
    connection.execute("PRAGMA journal_mode = WAL")


def _ensure_measurement_columns(connection: sqlite3.Connection) -> None:
    """Migra bancos antigos sem apagar comentarios ligados a contratos."""
    columns = {
        str(row["name"]).lower()
        for row in connection.execute("PRAGMA table_info(contrato_comentario)").fetchall()
    }
    if "revisao_contrato" not in columns:
        connection.execute(
            "ALTER TABLE contrato_comentario ADD COLUMN revisao_contrato TEXT"
        )
    if "numero_medicao" not in columns:
        connection.execute(
            "ALTER TABLE contrato_comentario ADD COLUMN numero_medicao TEXT"
        )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_contrato_comentario_medicao
        ON contrato_comentario (
            filial,
            contrato,
            revisao_contrato,
            numero_medicao,
            versao_atual,
            excluido,
            data_criacao,
            id_comentario
        )
        """
    )


@contextmanager
def get_connection(
    database_path: str | Path | None = None,
) -> Iterator[sqlite3.Connection]:
    """Abre uma conexao curta e garante fechamento mesmo quando houver erro."""
    connection = sqlite3.connect(
        _database_path(database_path),
        timeout=int(COMENTARIOS_DB_CONFIG["busy_timeout_ms"]) / 1000,
    )
    try:
        _configure_connection(connection)
        yield connection
    finally:
        connection.close()


def initialize_comments_database(database_path: str | Path | None = None) -> Path:
    """Cria, de forma idempotente, a tabela e os indices de comentarios."""
    resolved_path = _database_path(database_path)
    if resolved_path in _INITIALIZED_DATABASES and resolved_path.exists():
        return resolved_path

    with _INITIALIZATION_LOCK:
        if resolved_path in _INITIALIZED_DATABASES and resolved_path.exists():
            return resolved_path

        schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
        with get_connection(resolved_path) as connection:
            try:
                connection.executescript(schema_sql)
                _ensure_measurement_columns(connection)
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        _INITIALIZED_DATABASES.add(resolved_path)

    return resolved_path


def list_comments(
    filial: str,
    contrato: str,
    contract_revision: str,
    measurement_number: str,
    *,
    include_deleted: bool = False,
    database_path: str | Path | None = None,
) -> list[dict]:
    """Lista as versoes atuais da medicao em ordem cronologica."""
    with get_connection(database_path) as connection:
        rows = connection.execute(
            _read_query("comentarios_listar.sql"),
            {
                "filial": str(filial).strip(),
                "contrato": str(contrato).strip(),
                "revisao_contrato": str(contract_revision or "").strip(),
                "numero_medicao": str(measurement_number).strip(),
                "incluir_excluidos": int(include_deleted),
            },
        ).fetchall()
    return [dict(row) for row in rows]


def get_comment_history(
    comment_id: int,
    *,
    database_path: str | Path | None = None,
) -> list[dict]:
    """Retorna todas as versoes de um comentario, da mais antiga para a atual."""
    with get_connection(database_path) as connection:
        rows = connection.execute(
            _read_query("comentarios_historico.sql"),
            {"id_comentario": int(comment_id)},
        ).fetchall()
    return [dict(row) for row in rows]


def add_comment(
    filial: str,
    contrato: str,
    contract_revision: str,
    measurement_number: str,
    comment: str,
    username: str,
    *,
    database_path: str | Path | None = None,
) -> dict:
    """Cria a primeira versao de um comentario em uma transacao curta."""
    params = {
        "versao": 1,
        "filial": str(filial).strip(),
        "contrato": str(contrato).strip(),
        "revisao_contrato": str(contract_revision or "").strip(),
        "numero_medicao": str(measurement_number).strip(),
        "comentario": str(comment).strip(),
        "usuario_criacao": str(username).strip(),
        "data_criacao": _now_iso(),
        "usuario_alteracao": None,
        "data_alteracao": None,
        "excluido": 0,
        "usuario_exclusao": None,
        "data_exclusao": None,
    }

    with get_connection(database_path) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            params["id_comentario"] = connection.execute(
                "SELECT COALESCE(MAX(id_comentario), 0) + 1 FROM contrato_comentario"
            ).fetchone()[0]
            cursor = connection.execute(_read_query("comentarios_inserir.sql"), params)
            row = connection.execute(
                "SELECT * FROM contrato_comentario WHERE id_registro = ?",
                (cursor.lastrowid,),
            ).fetchone()
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return _row_to_dict(row) or {}


def edit_comment(
    comment_id: int,
    expected_version: int,
    new_comment: str,
    username: str,
    *,
    database_path: str | Path | None = None,
) -> dict:
    """Insere uma nova versao sem sobrescrever o texto anterior."""
    with get_connection(database_path) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                _read_query("comentarios_obter_atual.sql"),
                {"id_comentario": int(comment_id)},
            ).fetchone()
            if current is None or int(current["excluido"]) == 1:
                raise CommentNotFoundError("Comentario inexistente ou excluido.")
            if int(current["versao"]) != int(expected_version):
                raise ConcurrentCommentUpdateError(
                    "O comentario foi alterado por outro usuario. Recarregue o historico."
                )

            updated = connection.execute(
                _read_query("comentarios_desativar_versao.sql"),
                {"id_comentario": int(comment_id), "versao": int(expected_version)},
            )
            if updated.rowcount != 1:
                raise ConcurrentCommentUpdateError(
                    "A versao atual mudou durante a edicao. Recarregue o historico."
                )

            params = {
                "id_comentario": int(comment_id),
                "versao": int(expected_version) + 1,
                "filial": current["filial"],
                "contrato": current["contrato"],
                "revisao_contrato": current["revisao_contrato"],
                "numero_medicao": current["numero_medicao"],
                "comentario": str(new_comment).strip(),
                "usuario_criacao": current["usuario_criacao"],
                "data_criacao": current["data_criacao"],
                "usuario_alteracao": str(username).strip(),
                "data_alteracao": _now_iso(),
                "excluido": 0,
                "usuario_exclusao": None,
                "data_exclusao": None,
            }
            cursor = connection.execute(_read_query("comentarios_inserir.sql"), params)
            row = connection.execute(
                "SELECT * FROM contrato_comentario WHERE id_registro = ?",
                (cursor.lastrowid,),
            ).fetchone()
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return _row_to_dict(row) or {}


def delete_comment(
    comment_id: int,
    expected_version: int,
    username: str,
    *,
    database_path: str | Path | None = None,
) -> dict:
    """Cria uma versao final excluida e preserva todas as versoes anteriores."""
    with get_connection(database_path) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                _read_query("comentarios_obter_atual.sql"),
                {"id_comentario": int(comment_id)},
            ).fetchone()
            if current is None or int(current["excluido"]) == 1:
                raise CommentNotFoundError("Comentario inexistente ou ja excluido.")
            if int(current["versao"]) != int(expected_version):
                raise ConcurrentCommentUpdateError(
                    "O comentario foi alterado por outro usuario. Recarregue o historico."
                )

            updated = connection.execute(
                _read_query("comentarios_desativar_versao.sql"),
                {"id_comentario": int(comment_id), "versao": int(expected_version)},
            )
            if updated.rowcount != 1:
                raise ConcurrentCommentUpdateError(
                    "A versao atual mudou durante a exclusao. Recarregue o historico."
                )

            deleted_at = _now_iso()
            params = {
                "id_comentario": int(comment_id),
                "versao": int(expected_version) + 1,
                "filial": current["filial"],
                "contrato": current["contrato"],
                "revisao_contrato": current["revisao_contrato"],
                "numero_medicao": current["numero_medicao"],
                "comentario": current["comentario"],
                "usuario_criacao": current["usuario_criacao"],
                "data_criacao": current["data_criacao"],
                "usuario_alteracao": current["usuario_alteracao"],
                "data_alteracao": current["data_alteracao"],
                "excluido": 1,
                "usuario_exclusao": str(username).strip(),
                "data_exclusao": deleted_at,
            }
            cursor = connection.execute(_read_query("comentarios_inserir.sql"), params)
            row = connection.execute(
                "SELECT * FROM contrato_comentario WHERE id_registro = ?",
                (cursor.lastrowid,),
            ).fetchone()
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return _row_to_dict(row) or {}
