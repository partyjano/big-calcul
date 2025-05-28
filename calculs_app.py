import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from io import BytesIO
from fpdf import FPDF
from PIL import Image
import copy

# === CONFIGURATION INITIALE ===
st.set_page_config(page_title="Optimisation Découpe", layout="wide")

# === LOGO ===
st.image("logo.gif", width=150)

# === CONSTANTES ===
MATERIALS = {
    "Bois": {"longueur": 2440, "largeur": 1220, "densite": 600},
    "Métal": {"longueur": 6000, "largeur": 100, "densite": 7850}  # largeur fictive
}

# --- Fonction panneau initial ---
def panneau_initial(materiau):
    dim = MATERIALS[materiau]
    return {
        "nom": f"Panneau {materiau} 1",
        "longueur": dim["longueur"],
        "largeur": dim["largeur"],
        "epaisseur": 18 if materiau == "Bois" else 5,
        "pieces": []
    }

# === INITIALISATION ===
if "panneaux" not in st.session_state:
    st.session_state.panneaux = {}
if "actif" not in st.session_state:
    st.session_state.actif = None
if "confirm_restore" not in st.session_state:
    st.session_state.confirm_restore = False

# === MENU LATÉRAL ===
st.sidebar.header("Paramètres globaux")
materiau = st.sidebar.selectbox("Matériau principal", list(MATERIALS.keys()))

# Initialiser un panneau si nécessaire
if materiau not in st.session_state.panneaux:
    st.session_state.panneaux[materiau] = [panneau_initial(materiau)]
    st.session_state.actif = (materiau, 0)

# --- Bouton restaurer avec confirmation ---
if not st.session_state.confirm_restore:
    if st.sidebar.button("🔄 Restaurer données"):
        st.session_state.confirm_restore = True
else:
    st.sidebar.warning("⚠️ Êtes-vous sûr de vouloir restaurer ? Cela supprimera les modifications actuelles.")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Oui, restaurer"):
            st.session_state.panneaux[materiau] = [panneau_initial(materiau)]
            st.session_state.actif = (materiau, 0)
            st.session_state.confirm_restore = False
            st.experimental_rerun()
    with col2:
        if st.button("Annuler"):
            st.session_state.confirm_restore = False

# === ONGLET PAR MATÉRIAU ===
tabs = st.tabs(list(st.session_state.panneaux.keys()))

for i, mat in enumerate(st.session_state.panneaux):
    with tabs[i]:
        st.header(f"Panneaux pour {mat}")
        index_actif = st.session_state.actif[1] if st.session_state.actif[0] == mat else 0
        noms = [p["nom"] for p in st.session_state.panneaux[mat]]
        panneau_idx = st.selectbox("Choisir un panneau", range(len(noms)), format_func=lambda x: noms[x], index=index_actif)
        panneau = st.session_state.panneaux[mat][panneau_idx]
        st.session_state.actif = (mat, panneau_idx)

        # === NOM DU PANNEAU ===
        panneau["nom"] = st.text_input("Nom du panneau", panneau["nom"])

        # === Dimensions du panneau/barre de base modifiables ===
        st.subheader("Dimensions du panneau/barre de base")
        base_long = st.number_input(f"Longueur base (mm) [{mat}]", min_value=1, value=panneau["longueur"], key=f"base_long_{mat}_{panneau_idx}")
        base_larg = st.number_input(f"Largeur base (mm) [{mat}]", min_value=1, value=panneau["largeur"], key=f"base_larg_{mat}_{panneau_idx}")
        base_epais = st.number_input(f"Épaisseur base (mm) [{mat}]", min_value=1, value=panneau.get("epaisseur", 18), key=f"base_epais_{mat}_{panneau_idx}")

        panneau["longueur"] = base_long
        panneau["largeur"] = base_larg
        panneau["epaisseur"] = base_epais

        # === AJOUT D'UNE PIÈCE ===
        st.subheader("Ajouter une pièce")
        col1, col2, col3 = st.columns(3)
        with col1:
            longueur = st.number_input("Longueur (mm)", min_value=1, value=200)
        with col2:
            largeur = st.number_input("Largeur (mm)", min_value=1, value=100)
        with col3:
            epaisseur = st.number_input("Épaisseur (mm)", min_value=1, value=18)
        quantite = st.number_input("Quantité", min_value=1, value=1, step=1)

        profil_default = f"{longueur}x{largeur}x{epaisseur} mm"
        profil = ""
        if mat == "Métal":
            profil = st.text_input("Profil (L x l x e mm)", profil_default)

        if st.button("Ajouter la pièce", key=f"add_piece_{mat}_{panneau_idx}"):
            for _ in range(quantite):
                panneau["pieces"].append({
                    "longueur": longueur,
                    "largeur": largeur,
                    "epaisseur": epaisseur,
                    "profil": profil
                })

        # === AFFICHAGE DES PIÈCES ===
        st.subheader("Liste des pièces")
        for idx, piece in enumerate(panneau["pieces"]):
            st.markdown(f"{idx+1}. {piece['longueur']} x {piece['largeur']} x {piece['epaisseur']} mm | Profil : {piece.get('profil', '')}")

        # === VISUALISATION ===
        st.subheader("Disposition simulée")
        fig, ax = plt.subplots()
        ax.set_xlim(0, panneau["longueur"])
        ax.set_ylim(0, panneau["largeur"] or 200)
        ax.set_aspect('equal')
        ax.invert_yaxis()
        ax.set_xticks(range(0, int(panneau["longueur"])+1, 10))
        ax.set_yticks(range(0, int(panneau["largeur"])+1, 10))
        ax.grid(True, which='both', color='lightgray', linestyle='--', linewidth=0.5)

        x, y = 0, 0
        for idx, piece in enumerate(panneau["pieces"]):
            l, L = piece["longueur"], piece["largeur"]
            if x + l > panneau["longueur"]:
                x = 0
                y += L
            if y + L > panneau["largeur"]:
                continue
            ax.add_patch(patches.Rectangle((x, y), l, L, facecolor='lightblue', edgecolor='black'))
            ax.text(x + l / 2, y + L / 2, f"{idx+1}", ha='center', va='center')
            x += l

        st.pyplot(fig)

        # === STATISTIQUES ===
        st.subheader("Statistiques")
        total_volume = sum(p["longueur"] * p["largeur"] * p["epaisseur"] / 1e9 for p in panneau["pieces"])
        total_poids = total_volume * MATERIALS[mat]["densite"]
        st.markdown(f"**Volume total :** {total_volume:.3f} m³")
        st.markdown(f"**Poids estimé :** {total_poids:.2f} kg")

        # === EXPORT PDF ===
        def export_pdf():
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=panneau["nom"], ln=1, align='C')

            for idx, piece in enumerate(panneau["pieces"]):
                pdf.cell(200, 10, txt=f"{idx+1}. {piece['longueur']} x {piece['largeur']} x {piece['epaisseur']} mm", ln=1)

            return pdf.output(dest='S').encode("latin1")

        if st.button("📄 Générer fiche PDF", key=f"pdf_{mat}_{panneau_idx}"):
            pdf_bytes = export_pdf()
            st.download_button(
                label="Télécharger PDF",
                data=pdf_bytes,
                file_name=f"{panneau['nom'].replace(' ', '_')}.pdf",
                mime="application/pdf"
            )

        # === DUPLIQUER PANNEAU ===
        if st.button("➕ Dupliquer ce panneau", key=f"dupliquer_{mat}_{panneau_idx}"):
            nouveau = copy.deepcopy(panneau)
            nouveau["nom"] = panneau["nom"] + " (copie)"
            st.session_state.panneaux[mat].append(nouveau)

        # === PARAMÈTRES AVANCÉS ===
        with st.expander("⚙️ Options avancées"):
            if st.checkbox("Activer la découpe optimisée (nesting)", key=f"optimize_{mat}_{panneau_idx}"):
                st.warning("L'algorithme d'optimisation sera intégré ici.")
            if st.checkbox("Activer la vue 3D", key=f"3d_{mat}_{panneau_idx}"):
                st.info("Vue 3D non implémentée dans cette version.")
