"""Base de connaissances : fichiers, texte riche, FAQ (inspirée de GoHighLevel)."""
from html import escape

import streamlit as st

import api_client as api
import ui

ui.setup(max_width=1000)
ui.sidebar(active="knowledge")


# --- Dialogues d'ajout / de consultation ------------------------------------------------

@st.dialog("Ajouter des fichiers", width="medium")
def add_files() -> None:
    files = st.file_uploader(
        "PDF, TXT, MD ou DOCX (20 Mo max par fichier)", type=["pdf", "txt", "md", "docx"], accept_multiple_files=True
    )
    if st.button("Ajouter", type="primary", disabled=not files):
        try:
            api.upload_files([(f.name, f.getvalue(), f.type or "application/octet-stream") for f in files])
        except api.ApiError as exc:
            st.error(str(exc))
            return
        st.rerun()


@st.dialog("Ajouter un texte", width="large")
def add_richtext(source: dict | None = None) -> None:
    title = st.text_input("Titre", value=source["title"] if source else "")
    content = st.text_area(
        "Contenu (Markdown accepté : titres #, listes -, **gras**)",
        value=source["content"] if source else "",
        height=320,
    )
    if st.button("Enregistrer", type="primary", disabled=not (title.strip() and content.strip())):
        try:
            if source:
                api.update_source(source["id"], {"title": title, "content": content})
            else:
                api.add_richtext(title, content)
        except api.ApiError as exc:
            st.error(str(exc))
            return
        st.rerun()


@st.dialog("Ajouter une question / réponse", width="medium")
def add_faq(source: dict | None = None) -> None:
    question = st.text_input("Question", value=source["question"] if source else "")
    answer = st.text_area("Réponse", value=source["answer"] if source else "", height=180)
    if st.button("Enregistrer", type="primary", disabled=not (question.strip() and answer.strip())):
        try:
            if source:
                api.update_source(source["id"], {"question": question, "answer": answer})
            else:
                api.add_faq(question, answer)
        except api.ApiError as exc:
            st.error(str(exc))
            return
        st.rerun()


@st.dialog("Contenu indexé", width="large")
def show_chunks(source: dict) -> None:
    st.markdown(f"**{escape(source['title'])}** · {ui.TYPE_LABELS[source['type']]}")
    chunks = api.source_chunks(source["id"])
    if not chunks:
        st.info("Aucun fragment indexé.")
    for c in chunks:
        page = f" · page {c['page']}" if c["page"] else ""
        st.caption(f"Fragment {c['position'] + 1}{page}")
        st.markdown(f'<div class="extract">{escape(c["text"])}</div>', unsafe_allow_html=True)


# --- Page ---------------------------------------------------------------------------------

head, action = st.columns([4, 1], vertical_alignment="bottom")
head.title("Base de connaissances")
head.markdown(
    "<p class='muted' style='margin-top:-10px'>Les documents que l'assistant utilise pour répondre. "
    "Tout ajout est découpé, vectorisé et indexé automatiquement.</p>",
    unsafe_allow_html=True,
)
with action.popover("Ajouter", icon=":material/add:", type="primary", width="stretch"):
    if st.button("Fichiers", icon=":material/upload_file:", width="stretch"):
        add_files()
    if st.button("Texte riche", icon=":material/article:", width="stretch"):
        add_richtext()
    if st.button("Question / réponse", icon=":material/quiz:", width="stretch"):
        add_faq()

summary = ui.guard(api.knowledge_summary)
cards = [
    ("file", "Fichiers", "PDF, TXT, MD, DOCX", add_files),
    ("richtext", "Texte riche", "Textes saisis dans l'application", add_richtext),
    ("faq", "FAQ", "Paires question / réponse", add_faq),
]
for col, (type_, label, hint, opener) in zip(st.columns(3), cards):
    with col.container(border=True):
        top, plus = st.columns([4, 1], vertical_alignment="center")
        top.markdown(f"<div class='card-title'>{label}</div><div class='muted'>{hint}</div>", unsafe_allow_html=True)
        if plus.button("", icon=":material/add:", key=f"plus_{type_}", help=f"Ajouter : {label.lower()}"):
            opener()
        st.markdown(f"<div class='card-count'>{summary['by_type'][type_]}</div>", unsafe_allow_html=True)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
filter_col, search_col = st.columns([3, 2], vertical_alignment="center")
choice = filter_col.segmented_control(
    "Type", ["Tout", "Fichiers", "Texte riche", "FAQ"], default="Tout", label_visibility="collapsed"
)
query = search_col.text_input("Filtrer", placeholder="Filtrer les sources", label_visibility="collapsed")
type_filter = {"Fichiers": "file", "Texte riche": "richtext", "FAQ": "faq"}.get(choice or "Tout")


@st.fragment(run_every=None)
def source_table() -> None:
    sources = ui.guard(lambda: api.list_sources(type_filter, query.strip() or None))
    busy = any(s["status"] in ("pending", "indexing") for s in sources)
    st.markdown(
        f"<div class='muted' style='margin:6px 0'>{len(sources)} source{'s' if len(sources) > 1 else ''}"
        f"{' · indexation en cours, actualisation automatique' if busy else ''}</div>",
        unsafe_allow_html=True,
    )
    if not sources:
        st.markdown("<div class='card muted'>Aucune source pour l'instant.</div>", unsafe_allow_html=True)
    for s in sources:
        with st.container(border=True):
            name, type_col, frag, state, date, menu = st.columns([4, 1.4, 1, 1.6, 1.8, 0.6], vertical_alignment="center")
            name.markdown(f"**{escape(s['title'])}**")
            type_col.markdown(f"<span class='muted'>{ui.TYPE_LABELS[s['type']]}</span>", unsafe_allow_html=True)
            frag.markdown(f"<span class='muted'>{s['chunks'] or '—'}</span>", unsafe_allow_html=True)
            state.markdown(ui.pill(s["status"]), unsafe_allow_html=True)
            date.markdown(f"<span class='muted'>{ui.fmt_date(s['created_at'])}</span>", unsafe_allow_html=True)
            with menu.popover("", icon=":material/more_vert:", type="tertiary"):
                if st.button("Voir le contenu indexé", key=f"see_{s['id']}", icon=":material/visibility:"):
                    show_chunks(s)
                if s["type"] != "file" and st.button("Modifier", key=f"edit_{s['id']}", icon=":material/edit:"):
                    full = api.get_source(s["id"])
                    (add_faq if s["type"] == "faq" else add_richtext)(full)
                if st.button("Réindexer", key=f"re_{s['id']}", icon=":material/refresh:"):
                    api.reindex_source(s["id"])
                    st.rerun()
                if st.button("Supprimer", key=f"rm_{s['id']}", icon=":material/delete:"):
                    api.delete_source(s["id"])
                    st.rerun()
            if s["status"] == "error" and s["error"]:
                st.markdown(f"<div style='color:#B42318;font-size:13px'>{escape(s['error'])}</div>", unsafe_allow_html=True)
    if busy:
        import time

        time.sleep(2)
        st.rerun(scope="fragment")


source_table()
