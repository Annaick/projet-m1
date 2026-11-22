"""Thème (CSS d'après docs/design/), barre latérale et petits composants partagés."""
from datetime import datetime
from html import escape

import streamlit as st

import api_client as api

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
.stApp *:not([data-testid="stIconMaterial"]):not(code):not(pre),
[data-testid="stPopoverBody"] *:not([data-testid="stIconMaterial"]) { font-family: Inter, system-ui, sans-serif; }
[data-testid="stIconMaterial"] { font-family: "Material Symbols Rounded" !important; }
.stApp { background: #F7F8FA; color: #1A1D23; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none; }
.block-container { padding-top: 2.2rem; padding-bottom: 6rem; }

/* Barre latérale */
section[data-testid="stSidebar"] { background: #EEF0F4; border-right: 1px solid #E1E4EA; }
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding-top: 0.5rem; }
section[data-testid="stSidebar"] .stButton button,
section[data-testid="stSidebar"] [data-testid="stPageLink"] a {
  justify-content: flex-start; text-align: left; width: 100%; min-height: 38px; padding: 0 10px;
  border-radius: 8px; border: none; background: transparent; color: #1A1D23; font-size: 14px; font-weight: 400;
}
section[data-testid="stSidebar"] .stButton button > div { justify-content: flex-start; width: 100%; gap: 10px; }
section[data-testid="stSidebar"] .stButton button p { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: left; }
section[data-testid="stSidebar"] .stButton button:hover,
section[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover { background: #E2E5EC; color: #1A1D23; }
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 2px; }
section[data-testid="stSidebar"] [class*="_active"] button { background: #E0E5F5; font-weight: 600; }
section[data-testid="stSidebar"] [data-testid="stPopover"] button { min-height: 38px; width: 34px; padding: 0; justify-content: center; }
.brand { display: flex; align-items: center; gap: 10px; padding: 4px 10px 16px; font-weight: 700; font-size: 16px; }
.brand-logo { width: 30px; height: 30px; border-radius: 8px; background: #3B5BDB; color: #fff; display: flex; align-items: center; justify-content: center; }
.side-label { padding: 18px 10px 10px; line-height: 1.2; font-size: 12px; font-weight: 600; color: #5A6170; }
.status { display: flex; align-items: center; gap: 8px; padding: 6px 10px; font-size: 12px; color: #5A6170; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }

/* Boutons */
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] { background: #3B5BDB; border-color: #3B5BDB; border-radius: 10px; font-weight: 600; }
.stButton button[kind="primary"]:hover { background: #2B46B0; border-color: #2B46B0; }
.stButton button[kind="secondary"] { border-radius: 10px; border-color: #D5D9E1; }

/* Chat */
.user-row { display: flex; justify-content: flex-end; margin: 18px 0 10px; }
.user-bubble { max-width: 80%; background: #E6E9F0; border-radius: 16px; padding: 10px 16px; font-size: 15px; line-height: 1.55; white-space: pre-wrap; }
.not-found { background: #FFF7EF; border: 1px solid #F3D2B3; color: #8A3B00; border-radius: 12px; padding: 12px 16px; font-size: 14px; margin: 4px 0; }
.meta { font-size: 12px; color: #5A6170; margin: 2px 0 6px; }
.cite { display: inline-flex; align-items: center; justify-content: center; min-width: 20px; height: 20px; padding: 0 6px;
  border-radius: 999px; background: #E0E5F5; color: #2B46B0; font-size: 12px; font-weight: 600; margin: 0 2px; }
[data-testid="stPopover"] button { border-radius: 999px; font-size: 13px; }
.extract { background: #F7F8FA; border-left: 3px solid #3B5BDB; padding: 10px 14px; border-radius: 6px; font-size: 14px; line-height: 1.55; white-space: pre-wrap; }

/* Cartes et pastilles */
.card { background: #fff; border: 1px solid #E1E4EA; border-radius: 12px; padding: 16px 18px; }
.card-title { font-weight: 600; font-size: 15px; }
.card-count { font-size: 26px; font-weight: 700; margin: 4px 0; }
.muted { color: #5A6170; font-size: 13px; }
.pill { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.pill-indexed { background: #E3F4EB; color: #1E7A4F; }
.pill-indexing, .pill-pending { background: #E0E5F5; color: #2B46B0; }
.pill-error { background: #FDECEA; color: #B42318; }
.pill-gap { background: #FDE9D7; color: #8A3B00; }
[data-testid="stHeading"] h1 { font-size: 28px !important; font-weight: 600 !important; letter-spacing: -0.01em; padding-bottom: 4px; }
[data-testid="stSidebarHeader"] { padding: 0.75rem 1rem 0; height: auto; min-height: 0; }
[data-testid="stForm"] { border: none; padding: 0; }
</style>
"""

STATUS_LABELS = {"indexed": "Indexée", "indexing": "Indexation…", "pending": "En attente", "error": "Erreur"}
TYPE_LABELS = {"file": "Fichier", "richtext": "Texte riche", "faq": "FAQ"}


def setup(max_width: int = 820) -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        f"<style>.block-container, [data-testid='stBottomBlockContainer'] {{ max-width: {max_width}px; }}</style>",
        unsafe_allow_html=True,
    )


def go(page: str, **state) -> None:
    for key, value in state.items():
        st.session_state[key] = value
    query = {"c": str(state["conversation_id"])} if state.get("conversation_id") else None
    st.switch_page(page, query_params=query)


def open_conversation(conversation_id: int | None) -> None:
    st.session_state["conversation_id"] = conversation_id


@st.dialog("Renommer la conversation")
def rename_dialog(conversation: dict) -> None:
    title = st.text_input("Titre", value=conversation["title"], max_chars=120)
    if st.button("Enregistrer", type="primary") and title.strip():
        api.rename_conversation(conversation["id"], title.strip())
        st.rerun()


def _nav_button(name, label, icon, page, state, active) -> None:
    with st.container(key=f"nav_{name}_{'active' if name == active else 'idle'}"):
        if st.button(label, icon=icon, key=f"nav_{name}", width="stretch", type="tertiary"):
            go(page, **state)


def sidebar(active: str | None = None) -> None:
    """Navigation complète, façon assistant IA (D-011)."""
    with st.sidebar:
        st.markdown(
            '<div class="brand"><div class="brand-logo">'
            '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">'
            '<path d="M4 19.5V5a2 2 0 0 1 2-2h14v16H6a2 2 0 0 0-2 2z"/><path d="M8 7h8M8 11h6"/></svg></div>'
            "Assistant RAG</div>",
            unsafe_allow_html=True,
        )
        try:
            open_gaps = len(api.list_gaps(resolved=False))
        except api.ApiError:
            open_gaps = 0
        nav_items = [
            ("chat", "Nouvelle conversation", ":material/add:", "views/chat.py", {"conversation_id": None}),
            ("search", "Rechercher", ":material/search:", "views/search.py", {}),
            ("knowledge", "Base de connaissances", ":material/menu_book:", "views/knowledge.py", {}),
            ("gaps", f"Questions sans réponse ({open_gaps})" if open_gaps else "Questions sans réponse",
             ":material/help:", "views/gaps.py", {}),
        ]
        for name, label, icon, page, state in nav_items:
            _nav_button(name, label, icon, page, state, active)

        st.markdown('<div class="side-label">Récentes</div>', unsafe_allow_html=True)
        try:
            conversations = api.list_conversations(limit=15)
        except api.ApiError:
            conversations = []
        if not conversations:
            st.markdown('<div class="muted" style="padding:0 10px">Aucune conversation</div>', unsafe_allow_html=True)
        current = st.session_state.get("conversation_id") if active == "conversation" else None
        for conv in conversations:
            left, right = st.columns([6, 1], gap=None, vertical_alignment="center")
            with left:
                state = "active" if conv["id"] == current else "idle"
                with st.container(key=f"recent_{conv['id']}_{state}"):
                    if st.button(conv["title"], key=f"conv_{conv['id']}", width="stretch", type="tertiary"):
                        go("views/chat.py", conversation_id=conv["id"])
            with right:
                with st.popover("", icon=":material/more_horiz:", type="tertiary"):
                    if st.button("Renommer", key=f"ren_{conv['id']}", icon=":material/edit:"):
                        rename_dialog(conv)
                    if st.button("Supprimer", key=f"del_{conv['id']}", icon=":material/delete:"):
                        api.delete_conversation(conv["id"])
                        if current == conv["id"]:
                            st.session_state["conversation_id"] = None
                        st.rerun()

        st.divider()
        _nav_button("settings", "Paramètres de l'IA", ":material/tune:", "views/settings.py", {}, active)
        health = api.get_health()
        st.markdown(status_html(health), unsafe_allow_html=True)


def status_html(health: dict | None) -> str:
    if health is None:
        color, text = "#B42318", "API injoignable"
    elif not health["ollama"]["ok"]:
        color, text = "#B42318", "Ollama non lancé"
    elif health["ollama"].get("missing"):
        color, text = "#B8860B", "Modèle manquant : " + ", ".join(health["ollama"]["missing"])
    else:
        try:
            model = api.get_settings()["llm_model"]
        except api.ApiError:
            model = ""
        color, text = "#1E8E5A", f"Ollama connecté · {model}"
    return f'<div class="status"><span class="dot" style="background:{color}"></span>{escape(text)}</div>'


def pill(status: str) -> str:
    return f'<span class="pill pill-{status}">{STATUS_LABELS.get(status, status)}</span>'


def fmt_date(iso: str) -> str:
    try:
        value = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return iso
    today = datetime.now().astimezone().date()
    if value.date() == today:
        return f"Aujourd'hui, {value:%H:%M}"
    return f"{value:%d/%m/%Y, %H:%M}"


def guard(fn):
    """Affiche une erreur propre si l'API ne répond pas."""
    try:
        return fn()
    except api.ApiError as exc:
        st.error(str(exc))
        st.stop()
