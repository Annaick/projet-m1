"""Accueil (nouvelle conversation) et conversation : réponse streamée, bulles de citation."""
import re
from html import escape

import streamlit as st

import api_client as api
import ui

# Questions proposées sur l'accueil (adaptées au corpus de démonstration)
SUGGESTIONS = [
    "Combien de jours de congés par an ?",
    "Comment déclarer une note de frais ?",
    "Qui contacter en cas de panne ?",
    "Quelles sont les règles du télétravail ?",
]

# La conversation ouverte est aussi dans l'URL (?c=12) : un rafraîchissement ne la perd pas
if "c" in st.query_params and "conversation_id" not in st.session_state:
    try:
        st.session_state["conversation_id"] = int(st.query_params["c"])
    except ValueError:
        pass
conversation_id = st.session_state.get("conversation_id")
if conversation_id:
    st.query_params["c"] = str(conversation_id)
else:
    st.query_params.pop("c", None)
ui.setup(max_width=800)
ui.sidebar(active="conversation" if conversation_id else "chat")


@st.cache_data(ttl=120, show_spinner=False)
def chunk(chunk_id: int) -> dict | None:
    return api.get_chunk(chunk_id)


def start(question: str) -> None:
    conversation = api.create_conversation()
    st.session_state["conversation_id"] = conversation["id"]
    st.session_state["pending_question"] = question
    st.rerun()


# --- Rendu des messages ----------------------------------------------------------------

def user_bubble(text: str) -> None:
    st.markdown(f'<div class="user-row"><div class="user-bubble">{escape(text)}</div></div>', unsafe_allow_html=True)


def with_citation_pills(text: str) -> str:
    text = text.replace("<", "&lt;")
    return re.sub(r"\[(\d+(?:\s*[,;]\s*\d+)*)\]", lambda m: "".join(
        f'<span class="cite">{n}</span>' for n in re.split(r"\s*[,;]\s*", m.group(1))), text)


def citations(items: list[dict], key: str) -> None:
    if not items:
        return
    with st.container(horizontal=True, gap="small"):
        for c in items:
            page = f" · p. {c['page']}" if c.get("page") else ""
            with st.popover(f"{c['rank']}  {c['title']}{page}", key=f"{key}_{c['rank']}"):
                data = chunk(c["chunk_id"])
                st.markdown(f"**{escape(c['title'])}**")
                type_label = ui.TYPE_LABELS.get(data["source"]["type"], "") if data and data.get("source") else ""
                st.caption(" · ".join(x for x in (type_label, f"page {c['page']}" if c.get("page") else "", f"pertinence {c['score']:.2f}".replace(".", ",")) if x))
                if data:
                    st.markdown(f'<div class="extract">{escape(data["text"])}</div>', unsafe_allow_html=True)
                else:
                    st.info("Cette source a été supprimée de la base.")


def assistant_message(message: dict) -> None:
    if not message["answered"]:
        st.markdown(
            f'<div class="not-found">{escape(message["content"])}</div>', unsafe_allow_html=True
        )
    else:
        st.markdown(with_citation_pills(message["content"]), unsafe_allow_html=True)
    citations(message.get("citations", []), key=f"m{message['id']}")
    meta = []
    if message.get("latency_ms") is not None:
        meta.append(f"{message['latency_ms'] / 1000:.1f} s".replace(".", ","))
    if message.get("model"):
        meta.append(message["model"])
    n = len(message.get("citations", []))
    meta.append(f"{n} source{'s' if n > 1 else ''}" if n else "aucune source citée")
    st.markdown(f'<div class="meta">{" · ".join(meta)}</div>', unsafe_allow_html=True)


def stream_answer(question: str) -> None:
    user_bubble(question)
    status = st.empty()
    status.markdown('<div class="meta">Recherche dans la base de connaissances…</div>', unsafe_allow_html=True)
    result: dict = {}

    def tokens():
        for event in api.ask(conversation_id, question):
            kind = event["type"]
            if kind == "sources":
                n = len(event["sources"])
                status.markdown(
                    f'<div class="meta">{n} extrait{"s" if n > 1 else ""} trouvé{"s" if n > 1 else ""}, rédaction de la réponse…</div>'
                    if n else '<div class="meta">Aucun extrait pertinent.</div>',
                    unsafe_allow_html=True,
                )
            elif kind == "token":
                yield event["text"]
            elif kind in ("done", "error"):
                result[kind] = event

    try:
        st.write_stream(tokens())
    except api.ApiError as exc:
        result["error"] = {"message": str(exc)}
    status.empty()
    if "error" in result:
        st.error(result["error"]["message"])
        return
    st.rerun()


# --- Accueil -------------------------------------------------------------------------

def home() -> None:
    st.markdown('<div style="height: 9vh"></div>', unsafe_allow_html=True)
    st.markdown(
        "<h1 style='text-align:center; font-size:34px; margin-bottom:8px'>Que voulez-vous savoir aujourd'hui ?</h1>",
        unsafe_allow_html=True,
    )
    with st.container():
        question = st.chat_input("Posez une question sur vos documents…", key="home_input")
    st.markdown(
        "<p class='muted' style='text-align:center'>Les réponses s'appuient uniquement sur votre base de connaissances et citent leurs sources.</p>",
        unsafe_allow_html=True,
    )
    with st.container(horizontal=True, horizontal_alignment="center", gap="small"):
        for i, suggestion in enumerate(SUGGESTIONS):
            if st.button(suggestion, key=f"sugg_{i}"):
                question = suggestion
    if question:
        start(question)

    summary = ui.guard(api.knowledge_summary)
    st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
    left, right = st.columns([3, 1], vertical_alignment="bottom")
    left.markdown("**Sources récentes**")
    if right.button("Tout voir", type="tertiary", key="see_all"):
        ui.go("views/knowledge.py")
    if not summary["recent"]:
        st.markdown(
            "<div class='card muted'>La base est vide. Ajoutez des documents dans <b>Base de connaissances</b> pour commencer.</div>",
            unsafe_allow_html=True,
        )
        return
    cols = st.columns(3)
    for col, source in zip(cols, summary["recent"][:3]):
        unit = "question" if source["type"] == "faq" else "fragment"
        count = f"{source['chunks']} {unit}{'s' if source['chunks'] > 1 else ''}"
        col.markdown(
            f"<div class='card'><div class='muted'>{ui.TYPE_LABELS[source['type']]}</div>"
            f"<div class='card-title' style='margin:4px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{escape(source['title'])}</div>"
            f"<div class='muted'>{count} · {ui.STATUS_LABELS[source['status']].lower()}</div></div>",
            unsafe_allow_html=True,
        )


# --- Conversation --------------------------------------------------------------------

def conversation() -> None:
    try:
        data = api.get_messages(conversation_id)
    except api.ApiError:
        st.session_state["conversation_id"] = None
        st.query_params.pop("c", None)
        st.rerun()
    st.markdown(f"<div style='font-weight:600; font-size:15px'>{escape(data['conversation']['title'])}</div>", unsafe_allow_html=True)
    for message in data["messages"]:
        if message["role"] == "user":
            user_bubble(message["content"])
        else:
            assistant_message(message)

    pending = st.session_state.pop("pending_question", None)
    typed = st.chat_input("Posez une question de suivi…", key="conv_input")
    question = pending or typed
    if question:
        stream_answer(question)


if conversation_id:
    conversation()
else:
    home()
