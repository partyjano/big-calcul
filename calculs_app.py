import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from io import BytesIO
from fpdf import FPDF

# === CONFIGURATION INITIALE ===
st.set_page_config(page_title="Optimisation Découpe", layout="wide")
st.image("logo.gif", width=150)

# === CONSTANTES ===
MATERIALS = {
    "Bois": {"longueur": 2440, "largeur": 1220, "densite": 600},
    "Métal": {"longueur": 6000, "largeur": None, "densite": 7850}
}

# === FONCTIONS ===
def nom_panneau(mat, type_piece):
    mat_clean = mat.capitalize()
    if mat == "Bois":
        return "Panneaux Bois" if type_piece == "Panneau" else "Tasseaux Bois"
    else:
        return "Tôles Métal" if type_piece == "Panneau" else "Barres Métal"

def format_dimension_label(val):
    # Label tous les 500mm avec taille 12
    return f"{int(val)} mm"

def dessiner_pieces_2d(panneau):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_xlim(0, panneau["longueur"])
    largeur = panneau["largeur"] if panneau["largeur"] else 1000  # Si None on fixe une largeur arbitraire
    ax.set_ylim(0, largeur)
    ax.set_aspect('equal')
    ax.invert_yaxis()

    # Ajout des graduations tous les 500mm en police 12
    step = 500
    xticks = range(0, panneau["longueur"]+step, step)
    yticks = range(0, largeur+step, step)
    ax.set_xticks(xticks)
    ax.set_yticks(yticks)
    ax.tick_params(axis='both', labelsize=12)

    # Placement simple en ligne (à remplacer par algo d'optimisation avancé)
    x, y = 0, 0
    max_height_line = 0
    for idx, piece in enumerate(panneau["pieces"]):
        l, L = piece["longueur"], piece["largeur"]
        # Rotation automatique si ça rentre mieux
        if l > L and l > panneau["longueur"] and L <= panneau["longueur"]:
            l, L = L, l  # Rotation simple

        if x + l > panneau["longueur"]:
            x = 0
            y += max_height_line
            max_height_line = 0
        if y + L > largeur:
            # Plus de place - ne pas afficher
            break
        ax.add_patch(patches.Rectangle((x, y), l, L, facecolor='lightblue', edgecolor='black'))
        ax.text(x + l / 2, y + L / 2, f"{idx+1}", ha='center', va='center', fontsize=10)
        x += l
        if L > max_height_line:
            max_height_line = L

    ax.set_xlabel("Longueur (mm)", fontsize=14)
    ax.set_ylabel("Largeur (mm)", fontsize=14)
    return fig

def export_pdf(panneau):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt=panneau["nom"], ln=1, align='C')

    pdf.set_font("Arial", size=12)
    for idx, piece in enumerate(panneau["pieces"]):
        line = f"{idx+1}. {piece['longueur']} x {piece['largeur']} x {piece['epaisseur']} mm"
        if "profil" in piece and piece["profil"]:
            line += f" (Profil: {piece['profil']})"
        pdf.cell(200, 10, txt=line, ln=1)
    return pdf.output(dest='S').encode("latin1")

# === INITIALISATION SESSION STATE ===
if "panneaux" not in st.session_state:
    st.session_state.panneaux = {}
    # Création de toutes les combinaisons (matériaux x types)
    for mat in MATERIALS.keys():
        for t in ["Panneau", "Barre"]:
            cle = f"{mat}_{t}"
            st.session_state.panneaux[cle] = {
                "nom": nom_panneau(mat, t),
                "materiau": mat,
                "type": t,
                "longueur": MATERIALS[mat]["longueur"],
                "largeur": MATERIALS[mat]["largeur"],
                "pieces": []
            }

# === SIDEBAR : CHOIX PANNEAU/BARRE ACTIF ===
st.sidebar.header("Sélection panneau / barre")
cle_choix = st.sidebar.selectbox(
    "Panneau / Barre actif",
    options=list(st.session_state.panneaux.keys()),
    format_func=lambda x: st.session_state.panneaux[x]["nom"]
)
panneau = st.session_state.panneaux[cle_choix]

# === MODIF NOM PANNEAU ===
nouveau_nom = st.sidebar.text_input("Nom du panneau / barre", panneau["nom"])
if nouveau_nom.strip():
    panneau["nom"] = nouveau_nom.strip()

# === AJOUT DE PIÈCE ===
st.sidebar.markdown("---")
st.sidebar.subheader(f"Ajouter une pièce à {panneau['nom']}")

longueur_defaut = 6000 if panneau["type"] == "Barre" else 200
largeur_defaut = 100 if panneau["type"] == "Barre" else 1000
epaisseur_defaut = 18

longueur_piece = st.sidebar.number_input("Longueur (mm)", min_value=1, value=longueur_defaut)
largeur_piece = st.sidebar.number_input("Largeur (mm)", min_value=1, value=largeur_defaut)
epaisseur_piece = st.sidebar.number_input("Épaisseur (mm)", min_value=1, value=epaisseur_defaut)
quantite_piece = st.sidebar.number_input("Quantité", min_value=1, value=1, step=1)

profil_piece = ""
if panneau["materiau"] == "Métal" and panneau["type"] == "Barre":
    profil_piece = st.sidebar.text_input("Profil (ex: 40x40x2 mm)", "40x40x2")

if st.sidebar.button("Ajouter la pièce"):
    for _ in range(quantite_piece):
        piece = {
            "longueur": longueur_piece,
            "largeur": largeur_piece,
            "epaisseur": epaisseur_piece,
            "profil": profil_piece
        }
        panneau["pieces"].append(piece)
    st.sidebar.success(f"{quantite_piece} pièce(s) ajoutée(s) à {panneau['nom']}")

# === AFFICHAGE PRINCIPAL ===
st.title(panneau["nom"])

if not panneau["pieces"]:
    st.info("Ajoutez des pièces pour ce panneau/barre dans le menu latéral.")
    st.stop()

# === LISTE DES PIÈCES ===
st.subheader("Liste des pièces")
for idx, piece in enumerate(panneau["pieces"]):
    desc = f"{idx+1}. {piece['longueur']} x {piece['largeur']} x {piece['epaisseur']} mm"
    if "profil" in piece and piece["profil"]:
        desc += f" (Profil: {piece['profil']})"
    st.markdown(desc)

# === VISUALISATION 2D ===
st.subheader("Visualisation 2D")
fig = dessiner_pieces_2d(panneau)
st.pyplot(fig)

# === STATISTIQUES ===
st.subheader("Statistiques")
total_volume = sum(p["longueur"] * p["largeur"] * p["epaisseur"] / 1e9 for p in panneau["pieces"])
total_poids = total_volume * MATERIALS[panneau["materiau"]]["densite"]
st.markdown(f"**Volume total :** {total_volume:.3f} m³")
st.markdown(f"**Poids estimé :** {total_poids:.2f} kg")

# === EXPORT PDF ===
if st.button("📄 Générer fiche PDF"):
    pdf_bytes = export_pdf(panneau)
    st.download_button(
        label="Télécharger PDF",
        data=pdf_bytes,
        file_name=f"{panneau['nom'].replace(' ', '_')}.pdf",
        mime="application/pdf"
    )
