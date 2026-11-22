"""Accueil et conversation. À construire : historique, streaming, bulles de citation."""

import streamlit as st

from api_client import get_health

st.title("Que voulez-vous savoir aujourd'hui ?")

health = get_health()
if health is None:
    st.error("L'API ne répond pas. Lancez-la avec : `uvicorn app.main:app --reload --app-dir backend`")
elif not health["ollama"]["ok"]:
    st.warning("L'API répond, mais Ollama est injoignable. Vérifiez qu'Ollama est lancé.")
else:
    st.success(f"API et Ollama opérationnels. Modèles disponibles : {', '.join(health['ollama']['models']) or 'aucun'}")

st.chat_input("Posez une question sur vos documents…", disabled=True)
