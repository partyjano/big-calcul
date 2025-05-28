import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from io import BytesIO
from fpdf import FPDF
from PIL import Image
from rectpack import newPacker, PackingMode, MaxRectsBssf, MaxRectsBlsf, MaxRectsBaf

# === CONFIGURATION INITIALE ===
st.set_page_config(page_title="Optimisation Découpe", layout="wide")

# === LOGO ===
st.image("logo.gif", width=150)

# === CONSTANTES ===
MATERIALS = {
    "Bois": {"longueur": 2440, "largeur": 1220, "densite": 600},
    "Métal": {"longueur": 6000, "largeur": 100, "densite": 7850}
}

# === INITIALISATION ===
if "panneaux" not in st.session_state:
    st.session_state.panneaux = {}
if "actif" not in st.session_state:
    st.session_state.actif = None

# === MENU MATÉRIAU ===
st.sidebar.header("Paramètres globaux")
materiau = st.sidebar.selectbox("Matériau principal", list(MATERIALS.keys()))

if materiau not in st.session_state.panneaux:
    st.session_state.panneaux[materiau] = {
        "pieces": [],
        "nom": f"Panneau {materiau}",
        "longueur": MATERIALS[materiau]["longueur"],
        "largeur": MATERIALS[materiau]["largeur"]
    }
    st.session_state.actif = materiau

# === CHOIX PANNEAU ACTIF ===
st.sidebar.markdown("---")
st.sidebar.subheader("Changer de panneau")
choix = st.sidebar.selectbox("Panneau actif", list(st.session_state.panneaux.keys()), index=list(st.session_state.panneaux.keys()).index(st.session_state.actif))
st.session_state.actif = choix

panneau = st.session_state.panneaux[choix]

# === NOM DU PANNEAU ===
panneau["nom"] = st.sidebar.text_input("Nom du panneau", panneau["nom"])

# === AJOUT D'UNE PIÈCE ===
st.sidebar.markdown("---")
st.sidebar.subheader("Ajouter une pièce")
longueur = st.sidebar.number_input("Longueur (mm)", min_value=1, value=200)
largeur = st.sidebar.number_input("Largeur (mm)", min_value=1, value=100)
epaisseur = st.sidebar.number_input("Épaisseur (mm)", min_value=1, value=18)
quantite = st.sidebar.number_input("Quantité", min_value=1, value=1, step=1)

profil = st.sidebar.text_input("Profil (ex: 40x40x2 mm)", f"{longueur}x{largeur}x{epaisseur}")

if st.sidebar.button("Ajouter la pièce"):
    for _ in range(quantite):
        panneau["pieces"].append({
            "longueur": longueur,
            "largeur": largeur,
            "epaisseur": epaisseur,
            "profil": profil
        })

# === AFFICHAGE PRINCIPAL ===
st.title(panneau["nom"])

if not panneau["pieces"]:
    st.info("Ajoutez des pièces pour ce panneau dans le menu latéral.")
    st.stop()

# === AFFICHAGE DES PIÈCES ===
st.subheader("Liste des pièces")
for idx, piece in enumerate(panneau["pieces"]):
    st.markdown(f"{idx+1}. {piece['longueur']}x{piece['largeur']}x{piece['epaisseur']} mm")

# === OPTIMISATION MAXRECTS (AMÉLIORÉE) ===
def optimiser_maxrects(panneau):
    algos = [MaxRectsBssf, MaxRectsBlsf, MaxRectsBaf]
    best_result = None
    best_fill = 0

    for algo in algos:
        packer = newPacker(rotation=True, pack_algo=algo, bin_algo=PackingMode.Offline)
        for idx, p in enumerate(panneau["pieces"]):
            packer.add_rect(p["longueur"], p["largeur"], idx)
        packer.add_bin(panneau["longueur"], panneau["largeur"], count=10)
        packer.pack()

        used_area = sum(w * h for x, y, w, h, _, _ in packer.rect_list())
        total_area = panneau["longueur"] * panneau["largeur"]
        fill_ratio = used_area / total_area

        if fill_ratio > best_fill:
            best_fill = fill_ratio
            best_result = list(packer.rect_list())

    placements = [None] * len(panneau["pieces"])
    for x, y, w, h, _, rid in best_result:
        placements[rid] = (x, y, w, h)
    return placements

# === VISUALISATION OPTIMISÉE ===
st.subheader("Disposition optimisée (MaxRects)")
positions = optimiser_maxrects(panneau)

fig, ax = plt.subplots()
ax.set_xlim(0, panneau["longueur"])
ax.set_ylim(0, panneau["largeur"])
ax.set_aspect('equal')
ax.invert_yaxis()

for idx, pos in enumerate(positions):
    if pos is None:
        continue
    x, y, w, h = pos
    ax.add_patch(patches.Rectangle((x, y), w, h, facecolor='lightgreen', edgecolor='black'))
    ax.text(x + w / 2, y + h / 2, f"{idx+1}", ha='center', va='center')

st.pyplot(fig)

# === STATISTIQUES ===
st.subheader("Statistiques")
total_volume = sum(p["longueur"] * p["largeur"] * p["epaisseur"] / 1e9 for p in panneau["pieces"])
total_poids = total_volume * MATERIALS[materiau]["densite"]
total_surface = panneau["longueur"] * panneau["largeur"]
used_surface = sum(p["longueur"] * p["largeur"] for p in panneau["pieces"])
rendement = (used_surface / total_surface) * 100

st.markdown(f"**Volume total :** {total_volume:.3f} m³")
st.markdown(f"**Poids estimé :** {total_poids:.2f} kg")
st.markdown(f"**Taux d'occupation :** {rendement:.2f} %")

# === EXPORT PDF ===
def export_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=panneau["nom"], ln=1, align='C')

    for idx, piece in enumerate(panneau["pieces"]):
        pdf.cell(200, 10, txt=f"{idx+1}. {piece['longueur']} x {piece['largeur']} x {piece['epaisseur']} mm", ln=1)

    return pdf.output(dest='S').encode("latin1")

if st.button("📄 Générer fiche PDF"):
    pdf_bytes = export_pdf()
    st.download_button(
        label="Télécharger PDF",
        data=pdf_bytes,
        file_name=f"{panneau['nom'].replace(' ', '_')}.pdf",
        mime="application/pdf"
    )
