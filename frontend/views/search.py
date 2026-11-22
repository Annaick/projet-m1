"""Recherche dans les conversations (titre et contenu des messages)."""
import streamlit as st

import api_client as api
import ui

ui.setup(max_width=800)
ui.sidebar(active="search")

st.title("Rechercher")
query = st.text_input("Rechercher", placeholder="Mot-clé dans un titre ou un message…", label_visibility="collapsed")
results = ui.guard(lambda: api.list_conversations(q=query.strip() or None, limit=100))

if query and not results:
    st.markdown("<p class='muted'>Aucune conversation ne correspond.</p>", unsafe_allow_html=True)
for conv in results:
    left, right = st.columns([5, 2], vertical_alignment="center")
    if left.button(conv["title"], key=f"s_{conv['id']}", type="tertiary"):
        ui.go("views/chat.py", conversation_id=conv["id"])
    right.markdown(f"<div class='muted' style='text-align:right'>{ui.fmt_date(conv['updated_at'])}</div>", unsafe_allow_html=True)
