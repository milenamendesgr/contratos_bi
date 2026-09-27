"""Componente Streamlit para comentarios versionados de medicoes."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

import streamlit as st

from utils.comentarios_service import (
    CommentsServiceError,
    adicionar_comentario,
    editar_comentario,
    excluir_comentario,
    listar_comentarios,
    obter_historico_comentario,
)
def _state_prefix(
    filial: Any,
    contrato: Any,
    revisao_contrato: Any,
    numero_medicao: Any,
) -> str:
    scope = "|".join(
        [
            str(filial).strip(),
            str(contrato).strip(),
            str(revisao_contrato or "").strip(),
            str(numero_medicao).strip(),
        ]
    ).encode("utf-8")
    return f"comentarios_{hashlib.sha256(scope).hexdigest()[:12]}"


def _format_datetime(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "Nao informado"
    try:
        parsed = datetime.fromisoformat(text)
        return parsed.strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return text


def _rerun() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def _clear_action_state(prefix: str) -> None:
    st.session_state.pop(f"{prefix}_editing_id", None)
    st.session_state.pop(f"{prefix}_deleting_id", None)
    st.session_state.pop(f"{prefix}_history_id", None)


def _set_flash(prefix: str, message: str) -> None:
    st.session_state[f"{prefix}_flash"] = message


def _render_flash(prefix: str) -> None:
    message = st.session_state.pop(f"{prefix}_flash", None)
    if message:
        st.success(message)


def _schedule_edit_key_cleanup(prefix: str, edit_key: str) -> None:
    st.session_state[f"{prefix}_cleanup_edit_key"] = edit_key


def _run_pending_cleanup(prefix: str) -> None:
    edit_key = st.session_state.pop(f"{prefix}_cleanup_edit_key", None)
    if edit_key:
        st.session_state.pop(edit_key, None)


def _render_history(comment_id: int) -> None:
    try:
        history = obter_historico_comentario(comment_id)
    except CommentsServiceError as exc:
        st.error(str(exc))
        return

    if not history:
        st.info("Nenhuma versao encontrada para este comentario.")
        return

    st.markdown("#### Historico de versoes")
    for version in history:
        status = "Excluido" if int(version.get("excluido", 0)) == 1 else "Ativo"
        st.markdown(f"**Versao {version['versao']} — {status}**")
        st.write(version.get("comentario", ""))
        st.caption(
            f"Criado em {_format_datetime(version.get('data_criacao'))}"
        )
        if version.get("data_alteracao"):
            st.caption(
                f"Editado em {_format_datetime(version.get('data_alteracao'))}"
            )
        if int(version.get("excluido", 0)) == 1:
            st.caption(
                f"Excluido em {_format_datetime(version.get('data_exclusao'))}"
            )
        st.divider()


def _render_edit_form(comment: dict, prefix: str) -> None:
    comment_id = int(comment["id_comentario"])
    edit_key = f"{prefix}_edit_text_{comment_id}"
    if edit_key not in st.session_state:
        st.session_state[edit_key] = comment.get("comentario", "")

    with st.form(f"{prefix}_edit_form_{comment_id}"):
        edited_text = st.text_area(
            "Editar comentario",
            key=edit_key,
            height=140,
            max_chars=4000,
        )
        save_column, cancel_column = st.columns(2)
        save = save_column.form_submit_button("Salvar alteracao", type="primary")
        cancel = cancel_column.form_submit_button("Cancelar")

    if save:
        try:
            editar_comentario(
                comment_id,
                comment["versao"],
                edited_text,
            )
        except CommentsServiceError as exc:
            st.error(str(exc))
        else:
            _schedule_edit_key_cleanup(prefix, edit_key)
            _clear_action_state(prefix)
            _set_flash(prefix, "Comentario alterado com sucesso.")
            _rerun()

    if cancel:
        _schedule_edit_key_cleanup(prefix, edit_key)
        _clear_action_state(prefix)
        _rerun()


def _render_delete_confirmation(comment: dict, prefix: str) -> None:
    comment_id = int(comment["id_comentario"])
    st.warning("Confirma a exclusao deste comentario? O historico sera preservado.")
    confirm_column, cancel_column = st.columns(2)
    if confirm_column.button(
        "Confirmar exclusao",
        type="primary",
        key=f"{prefix}_confirm_delete_{comment_id}",
    ):
        try:
            excluir_comentario(comment_id, comment["versao"])
        except CommentsServiceError as exc:
            st.error(str(exc))
        else:
            _clear_action_state(prefix)
            _set_flash(prefix, "Comentario excluido com sucesso.")
            _rerun()

    if cancel_column.button("Cancelar", key=f"{prefix}_cancel_delete_{comment_id}"):
        _clear_action_state(prefix)
        _rerun()


def _render_comment(comment: dict, prefix: str) -> None:
    comment_id = int(comment["id_comentario"])
    editing_id = st.session_state.get(f"{prefix}_editing_id")
    deleting_id = st.session_state.get(f"{prefix}_deleting_id")
    history_id = st.session_state.get(f"{prefix}_history_id")

    with st.container():
        st.write(comment.get("comentario", ""))
        st.caption(
            f"Incluido em {_format_datetime(comment.get('data_criacao'))}"
        )
        if comment.get("data_alteracao"):
            st.caption(
                f"Ultima alteracao em {_format_datetime(comment.get('data_alteracao'))} "
                f"— versao {comment.get('versao', '')}"
            )

        edit_column, delete_column, history_column = st.columns(3)
        if edit_column.button("Editar", key=f"{prefix}_edit_{comment_id}"):
            _clear_action_state(prefix)
            st.session_state[f"{prefix}_editing_id"] = comment_id
            _rerun()
        if delete_column.button("Excluir", key=f"{prefix}_delete_{comment_id}"):
            _clear_action_state(prefix)
            st.session_state[f"{prefix}_deleting_id"] = comment_id
            _rerun()
        if history_column.button("Historico", key=f"{prefix}_history_{comment_id}"):
            if history_id == comment_id:
                st.session_state.pop(f"{prefix}_history_id", None)
            else:
                _clear_action_state(prefix)
                st.session_state[f"{prefix}_history_id"] = comment_id
            _rerun()

        if editing_id == comment_id:
            _render_edit_form(comment, prefix)
        if deleting_id == comment_id:
            _render_delete_confirmation(comment, prefix)
        if history_id == comment_id:
            _render_history(comment_id)


def render_comentarios(
    filial: Any,
    contrato: Any,
    revisao_contrato: Any,
    numero_medicao: Any,
) -> None:
    """Renderiza inclusao, manutencao e historico da medicao selecionada."""
    prefix = _state_prefix(filial, contrato, revisao_contrato, numero_medicao)
    _run_pending_cleanup(prefix)

    st.markdown("### Comentarios da medicao")
    _render_flash(prefix)

    new_comment_key = f"{prefix}_new_comment"
    with st.form(f"{prefix}_new_form", clear_on_submit=True):
        new_comment = st.text_area(
            "Novo comentario",
            key=new_comment_key,
            height=140,
            max_chars=4000,
            placeholder="Registre uma observacao sobre a medicao.",
        )
        submitted = st.form_submit_button("Salvar", type="primary")

    if submitted:
        try:
            adicionar_comentario(
                filial,
                contrato,
                revisao_contrato,
                numero_medicao,
                new_comment,
            )
        except CommentsServiceError as exc:
            st.error(str(exc))
        else:
            _clear_action_state(prefix)
            _set_flash(prefix, "Comentario adicionado com sucesso.")
            _rerun()

    st.markdown("### Comentarios registrados")
    try:
        comments = listar_comentarios(
            filial,
            contrato,
            revisao_contrato,
            numero_medicao,
        )
    except CommentsServiceError as exc:
        st.error(str(exc))
        return

    if not comments:
        st.info("Nenhum comentario registrado para esta medicao.")
        return

    for comment in comments:
        _render_comment(comment, prefix)
