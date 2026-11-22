"""Point d'entrée Streamlit : configuration de la page et navigation.

Lancement depuis la racine du dépôt : streamlit run frontend/app.py
La navigation est dessinée par ui.sidebar() ; le menu automatique de Streamlit est masqué.
"""
import streamlit as st

st.set_page_config(page_title="Assistant RAG", page_icon=":material/menu_book:", layout="wide")

pages = [
    st.Page("views/chat.py", title="Assistant RAG", default=True),
    st.Page("views/search.py", title="Rechercher"),
    st.Page("views/knowledge.py", title="Base de connaissances"),
    st.Page("views/gaps.py", title="Questions sans réponse"),
    st.Page("views/settings.py", title="Paramètres de l'IA"),
]

st.navigation(pages, position="hidden").run()
