"""Point d'entrée Streamlit : configuration de la page et navigation.

Lancement depuis la racine du dépôt : streamlit run frontend/app.py
"""

import streamlit as st

st.set_page_config(page_title="Assistant RAG", page_icon="📚", layout="wide")

pages = [
    st.Page("views/chat.py", title="Nouvelle conversation", icon=":material/add:", default=True),
    st.Page("views/knowledge.py", title="Base de connaissances", icon=":material/library_books:"),
    st.Page("views/settings.py", title="Paramètres de l'IA", icon=":material/settings:"),
]

st.navigation(pages).run()
