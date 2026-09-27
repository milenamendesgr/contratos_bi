"""Validacoes e casos de uso dos comentarios de contratos."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from utils.comentarios_repository import (
    CommentNotFoundError,
    ConcurrentCommentUpdateError,
    add_comment,
    delete_comment,
    edit_comment,
    get_comment_history,
    initialize_comments_database,
    list_comments,
)


MAX_FILIAL_LENGTH = 10
MAX_CONTRATO_LENGTH = 30
MAX_REVISAO_LENGTH = 30
MAX_MEDICAO_LENGTH = 30
MAX_COMMENT_LENGTH = 4000
MAX_USERNAME_LENGTH = 100
DEFAULT_USERNAME = "Nao identificado"


class CommentsServiceError(RuntimeError):
    """Erro funcional base apresentado pela camada de comentarios."""


class CommentValidationError(CommentsServiceError):
    """Os dados enviados nao atendem aos requisitos da funcionalidade."""


class CommentConflictError(CommentsServiceError):
    """O comentario mudou depois de ser carregado pelo usuario."""


class CommentUnavailableError(CommentsServiceError):
    """O comentario nao existe ou nao esta mais disponivel."""


class CommentStorageError(CommentsServiceError):
    """A persistencia SQLite falhou sem expor detalhes internos na interface."""


def _required_text(value: Any, field: str, max_length: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise CommentValidationError(f"{field} deve ser informado.")
    if len(text) > max_length:
        raise CommentValidationError(
            f"{field} deve possuir no maximo {max_length} caracteres."
        )
    return text


def _positive_integer(value: Any, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise CommentValidationError(f"{field} invalido.") from exc
    if number < 1:
        raise CommentValidationError(f"{field} deve ser maior que zero.")
    return number


def _prepare_measurement(
    filial: Any,
    contrato: Any,
    revisao_contrato: Any,
    numero_medicao: Any,
) -> tuple[str, str, str, str]:
    revision = str(revisao_contrato or "").strip()
    if len(revision) > MAX_REVISAO_LENGTH:
        raise CommentValidationError(
            f"Revisao do contrato deve possuir no maximo {MAX_REVISAO_LENGTH} caracteres."
        )
    return (
        _required_text(filial, "Filial", MAX_FILIAL_LENGTH),
        _required_text(contrato, "Contrato", MAX_CONTRATO_LENGTH),
        revision,
        _required_text(numero_medicao, "Numero da medicao", MAX_MEDICAO_LENGTH),
    )


def _prepare_username(username: Any) -> str:
    text = str(username or "").strip()
    if not text:
        return DEFAULT_USERNAME
    if len(text) > MAX_USERNAME_LENGTH:
        raise CommentValidationError(
            f"Usuario deve possuir no maximo {MAX_USERNAME_LENGTH} caracteres."
        )
    return text


def _prepare_comment(comment: Any) -> str:
    return _required_text(comment, "Comentario", MAX_COMMENT_LENGTH)


def _initialize(database_path: str | Path | None) -> None:
    try:
        initialize_comments_database(database_path)
    except (OSError, sqlite3.Error) as exc:
        raise CommentStorageError(
            "Nao foi possivel inicializar o banco de comentarios."
        ) from exc


def _translate_repository_error(action: str, operation) -> Any:
    try:
        return operation()
    except ConcurrentCommentUpdateError as exc:
        raise CommentConflictError(
            "Este comentario foi alterado por outro usuario. Atualize a tela e tente novamente."
        ) from exc
    except CommentNotFoundError as exc:
        raise CommentUnavailableError(
            "O comentario nao existe ou ja foi excluido."
        ) from exc
    except (OSError, sqlite3.Error) as exc:
        raise CommentStorageError(
            f"Nao foi possivel {action} o comentario."
        ) from exc


def listar_comentarios(
    filial: Any,
    contrato: Any,
    revisao_contrato: Any,
    numero_medicao: Any,
    *,
    incluir_excluidos: bool = False,
    database_path: str | Path | None = None,
) -> list[dict]:
    """Lista as versoes atuais vinculadas a uma medicao."""
    measurement_key = _prepare_measurement(
        filial, contrato, revisao_contrato, numero_medicao
    )
    _initialize(database_path)
    return _translate_repository_error(
        "consultar",
        lambda: list_comments(
            *measurement_key,
            include_deleted=bool(incluir_excluidos),
            database_path=database_path,
        ),
    )


def obter_historico_comentario(
    id_comentario: Any,
    *,
    database_path: str | Path | None = None,
) -> list[dict]:
    """Lista todas as versoes de um comentario logico."""
    comment_id = _positive_integer(id_comentario, "Identificador do comentario")
    _initialize(database_path)
    return _translate_repository_error(
        "consultar o historico de",
        lambda: get_comment_history(comment_id, database_path=database_path),
    )


def adicionar_comentario(
    filial: Any,
    contrato: Any,
    revisao_contrato: Any,
    numero_medicao: Any,
    comentario: Any,
    usuario: Any = None,
    *,
    database_path: str | Path | None = None,
) -> dict:
    """Valida e cria a primeira versao de um comentario."""
    measurement_key = _prepare_measurement(
        filial, contrato, revisao_contrato, numero_medicao
    )
    comment_value = _prepare_comment(comentario)
    username = _prepare_username(usuario)
    _initialize(database_path)
    return _translate_repository_error(
        "adicionar",
        lambda: add_comment(
            *measurement_key,
            comment_value,
            username,
            database_path=database_path,
        ),
    )


def editar_comentario(
    id_comentario: Any,
    versao_esperada: Any,
    novo_comentario: Any,
    usuario: Any = None,
    *,
    database_path: str | Path | None = None,
) -> dict:
    """Valida e cria uma nova versao editada do comentario."""
    comment_id = _positive_integer(id_comentario, "Identificador do comentario")
    expected_version = _positive_integer(versao_esperada, "Versao esperada")
    comment_value = _prepare_comment(novo_comentario)
    username = _prepare_username(usuario)
    _initialize(database_path)
    return _translate_repository_error(
        "editar",
        lambda: edit_comment(
            comment_id,
            expected_version,
            comment_value,
            username,
            database_path=database_path,
        ),
    )


def excluir_comentario(
    id_comentario: Any,
    versao_esperada: Any,
    usuario: Any = None,
    *,
    database_path: str | Path | None = None,
) -> dict:
    """Valida e registra uma nova versao logicamente excluida."""
    comment_id = _positive_integer(id_comentario, "Identificador do comentario")
    expected_version = _positive_integer(versao_esperada, "Versao esperada")
    username = _prepare_username(usuario)
    _initialize(database_path)
    return _translate_repository_error(
        "excluir",
        lambda: delete_comment(
            comment_id,
            expected_version,
            username,
            database_path=database_path,
        ),
    )
