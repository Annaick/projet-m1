"""Paramètres de l'IA : personnalité, modèle, recherche dans la base."""
import streamlit as st

import api_client as api
import ui

ui.setup(max_width=860)
ui.sidebar(active="settings")

TONES = ["professionnel", "neutre", "chaleureux", "concis"]

st.title("Paramètres de l'IA")
st.markdown(
    "<p class='muted' style='margin-top:-10px'>Comment l'assistant se comporte, quel modèle il utilise et comment il cherche dans la base.</p>",
    unsafe_allow_html=True,
)

current = ui.guard(api.get_settings)
health = api.get_health() or {}
installed = [m for m in health.get("ollama", {}).get("models", []) if "embed" not in m]
models = sorted(set(installed) | {current["llm_model"]})

if st.session_state.pop("settings_saved", False):
    st.success("Paramètres enregistrés.")

with st.form("settings"):
    with st.container(border=True):
        st.markdown("**Personnalité**")
        tone = st.segmented_control(
            "Ton", TONES, default=current["tone"] if current["tone"] in TONES else None, format_func=str.capitalize
        )
        directives = st.text_area(
            "Directives générales", value=current["directives"], height=120, help="Règles ajoutées à chaque réponse. Une par ligne."
        )
        system_prompt = st.text_area(
            "Prompt système",
            value=current["system_prompt"],
            height=160,
            help="Les extraits numérotés et la question sont ajoutés automatiquement après ce texte.",
        )
    with st.container(border=True):
        st.markdown("**Modèle**")
        llm_model = st.selectbox("Modèle de langage", models, index=models.index(current["llm_model"]), help="Modèles installés dans Ollama.")
        temperature = st.slider(
            "Température", 0.0, 1.0, float(current["temperature"]), 0.05,
            help="Bas = réponses fidèles et stables. Haut = plus créatif, plus de risque d'invention.",
        )
    with st.container(border=True):
        st.markdown("**Recherche dans la base**")
        top_k = st.slider("Nombre d'extraits utilisés (top-k)", 1, 10, int(current["top_k"]), help="Extraits les plus proches transmis au modèle.")
        threshold = st.slider(
            "Seuil de pertinence", 0.0, 1.0, float(current["score_threshold"]), 0.01,
            help="Sous ce score, l'extrait est ignoré. Si aucun ne passe, l'assistant répond qu'il ne sait pas.",
        )
    left, right = st.columns([1, 1])
    reset = left.form_submit_button("Rétablir le prompt par défaut")
    save = right.form_submit_button("Enregistrer", type="primary", width="stretch")

if save or reset:
    body = {
        "system_prompt": api.default_prompt() if reset else system_prompt,
        "tone": tone or "",
        "directives": directives,
        "llm_model": llm_model,
        "temperature": temperature,
        "top_k": top_k,
        "score_threshold": threshold,
    }
    try:
        api.put_settings(body)
    except api.ApiError as exc:
        st.error(str(exc))
    else:
        st.session_state["settings_saved"] = True
        st.rerun()
