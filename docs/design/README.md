# Design de l'interface (validé le 22/11/2026)

Maquettes HTML statiques : ouvrir [`index.html`](index.html) dans un navigateur, puis naviguer avec la barre latérale.
Elles servent de référence pour l'implémentation Streamlit (`frontend/`).

| Écran | Fichier |
|---|---|
| Accueil (nouvelle conversation) | [`index.html`](index.html) |
| Conversation (citations, extrait source, « pas dans la base ») | [`conversation.html`](conversation.html) |
| Base de connaissances | [`base-de-connaissances.html`](base-de-connaissances.html) |
| Paramètres de l'IA | [`parametres.html`](parametres.html) |
| Questions sans réponse | [`questions-sans-reponse.html`](questions-sans-reponse.html) |

## Principes

- Disposition inspirée des assistants IA du marché : **toute la navigation dans la barre latérale**, zone centrale épurée
  (colonne de 720 px max pour le chat).
- Les réponses citent leurs sources par des bulles numérotées ; un clic affiche l'extrait et le document.
- Quand rien n'est assez pertinent, l'assistant le dit (encadré orange) et la question part dans « Questions sans réponse ».
- Les contenus affichés (congés, VPN, notes de frais…) sont des exemples.

## Couleurs

| Rôle | Valeur |
|---|---|
| Fond de page | `#F7F8FA` |
| Fond barre latérale | `#EEF0F4` (bordure `#E1E4EA`) |
| Surface (cartes, champs) | `#FFFFFF` (bordure `#E1E4EA` / champs `#D5D9E1`) |
| Texte principal | `#1A1D23` |
| Texte secondaire | `#5A6170` (`#3F4654` pour les libellés) |
| Accent (boutons, liens, citations) | `#3B5BDB` (survol `#2B46B0`) |
| Accent clair (élément actif, bulle citation) | `#E0E5F5` |
| Bulle utilisateur | `#E6E9F0` |
| Succès / indexée | `#1E7A4F` |
| En cours | `#2B46B0` |
| Erreur | `#B42318` |
| Avertissement « pas dans la base » | fond `#FFF7EF`, bordure `#F3D2B3`, texte `#8A3B00` |

## Typographie et formes

- Police **Inter** (Google Fonts), 400 / 500 / 600 / 700.
- Titres de page 26 px (accueil 34 px), texte du chat 15 px, texte courant 14 px, légendes 12–13 px.
- Rayons : 8 px (éléments de navigation), 10 px (boutons), 12 px (cartes), 16 px (zone de saisie), 999 px (pastilles).
- Icônes : traits fins (style Lucide), 18 px.

## Notes pour Streamlit

- La barre latérale native (`st.sidebar`) accueille la navigation et la liste des conversations.
- Le look (couleurs, rayons, police) passe par un bloc CSS injecté une fois (`st.markdown(..., unsafe_allow_html=True)`)
  et par `.streamlit/config.toml` (`primaryColor = "#3B5BDB"`, `backgroundColor = "#F7F8FA"`, `font`).
- Bulles de citation : `st.popover` ou petits boutons ; l'extrait s'affiche dans le popover.
- Accueil centré : `st.chat_input` placé dans le corps de page (et non en bas) sur l'écran d'accueil.

Source éditable des maquettes : artefact Design de l'équipe (lien dans le journal de projet).
