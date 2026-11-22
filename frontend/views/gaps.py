"""Questions sans réponse : à compléter dans la base."""
from html import escape

import streamlit as st

import api_client as api
import ui

ui.setup(max_width=900)
ui.sidebar(active="gaps")

st.title("Questions sans réponse")
st.markdown(
    "<p class='muted' style='margin-top:-10px'>Les questions pour lesquelles l'assistant n'a trouvé aucun extrait assez "
    "pertinent. Complétez la base pour qu'il sache y répondre.</p>",
    unsafe_allow_html=True,
)


@st.dialog("Ajouter à la FAQ", width="medium")
def to_faq(gap: dict) -> None:
    question = st.text_input("Question", value=gap["question"])
    answer = st.text_area("Réponse", height=180)
    if st.button("Ajouter et marquer comme traitée", type="primary", disabled=not answer.strip()):
        api.add_faq(question, answer)
        api.set_gap_resolved(gap["id"], True)
        st.rerun()


todo = ui.guard(lambda: api.list_gaps(resolved=False))
done = ui.guard(lambda: api.list_gaps(resolved=True))
tab_todo, tab_done = st.tabs([f"À traiter ({len(todo)})", f"Traitées ({len(done)})"])


def gap_row(gap: dict, resolved: bool) -> None:
    with st.container(border=True):
        text, actions = st.columns([3, 2], vertical_alignment="center")
        meta = ui.fmt_date(gap["created_at"])
        if gap.get("best_score") is not None:
            meta += f" · meilleur score {gap['best_score']:.2f}".replace(".", ",")
        text.markdown(f"**{escape(gap['question'])}**<br><span class='muted'>{meta}</span>", unsafe_allow_html=True)
        with actions.container(horizontal=True, horizontal_alignment="right", gap="small"):
            if gap.get("conversation_id") and st.button("Conversation", key=f"conv_{gap['id']}", type="tertiary"):
                ui.go("views/chat.py", conversation_id=gap["conversation_id"])
            if resolved:
                if st.button("Rouvrir", key=f"open_{gap['id']}"):
                    api.set_gap_resolved(gap["id"], False)
                    st.rerun()
            else:
                if st.button("Marquer comme traitée", key=f"ok_{gap['id']}"):
                    api.set_gap_resolved(gap["id"], True)
                    st.rerun()
                if st.button("Ajouter à la FAQ", key=f"faq_{gap['id']}", type="primary"):
                    to_faq(gap)


with tab_todo:
    if not todo:
        st.markdown("<div class='card muted'>Rien à traiter : l'assistant a trouvé une réponse à toutes les questions.</div>", unsafe_allow_html=True)
    for gap in todo:
        gap_row(gap, resolved=False)
with tab_done:
    for gap in done:
        gap_row(gap, resolved=True)
