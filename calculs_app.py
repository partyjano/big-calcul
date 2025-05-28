import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from io import BytesIO
from fpdf import FPDF
from PIL import Image

# === CONFIGURATION INITIALE ===
st.set_page_config(page_title="Optimisation Découpe", layout="wide")

# === LOGO ===
st.image("logo.gif", width=150)

# === CONSTANTES ===
MATERIALS = {
    "Bois": {"longueur": 2440, "largeur": 1220, "densite": 600},
    "Métal": {"longueur": 6000, "largeur": 1250, "densite": 7850}  # largeur fixée à 1250 par défaut pour métal
}

# === CLASSES & ALGORITHME MAXRECTS SIMPLIFIE (exemple, à intégrer complet selon besoins) ===
class Rect:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

class MaxRectsBinPack:
    def __init__(self, width, height):
        self.bin_width = width
        self.bin_height = height
        self.free_rects = [Rect(0, 0, width, height)]
        self.used_rects = []

    def insert(self, width, height):
        # Simplification: place first fit without rotation (pour exemple)
        for i, freerect in enumerate(self.free_rects):
            if width <= freerect.width and height <= freerect.height:
                rect = Rect(freerect.x, freerect.y, width, height)
                self.used_rects.append(rect)
                # Mise à jour free rects: simplifié ici, à améliorer selon vrai algorithme
                # Suppression free rect et découpage
                self.free_rects.pop(i)
                # Ajouter des nouveaux free rects après découpe (non implémenté ici)
                return rect, False
            if height <= freerect.width and width <= freerect.height:
                rect = Rect(freerect.x, freerect.y, height, width)
                self.used_rects.append(rect)
                self.free_rects.pop(i)
                return rect, True  # rotation
        return None, False

# === INITIALISATION ÉTAT ===
if "panneaux" not in st.session_state:
    st.session_state.panneaux = {
        mat: {
            "nom": f"Panneau {mat.capitalize()}",
            "longueur": MATERIALS[mat]["longueur"],
            "largeur": MATERIALS[mat]["largeur"],
            "pieces": []
        }
        for mat in MATERIALS.keys()
    }

# === SIDEBAR POUR AJOUT & PARAMÈTRES ===
st.sidebar.header("Ajouter une pièce")
mat_choice = st.sidebar.selectbox("Matériau panneau", list(MATERIALS.keys()))

panneau = st.session_state.panneaux[mat_choice]

long_p = st.sidebar.number_input("Longueur panneau (mm)", min_value=1, value=panneau["longueur"])
larg_p = st.sidebar.number_input("Largeur panneau (mm)", min_value=1, value=panneau["largeur"] or 1000)

panneau["longueur"] = long_p
panneau["largeur"] = larg_p

long_piece = st.sidebar.number_input("Longueur pièce (mm)", min_value=1, value=200)
larg_piece = st.sidebar.number_input("Largeur pièce (mm)", min_value=1, value=100)
epaisseur_piece = st.sidebar.number_input("Épaisseur pièce (mm)", min_value=1, value=18)
quantite_piece = st.sidebar.number_input("Quantité", min_value=1, value=1)

profil = ""
if mat_choice == "Métal":
    profil = st.sidebar.text_input("Profil (ex: 40x40x2 mm)", "40x40x2")

if st.sidebar.button("Ajouter la pièce"):
    for _ in range(quantite_piece):
        panneau["pieces"].append({
            "longueur": long_piece,
            "largeur": larg_piece,
            "epaisseur": epaisseur_piece,
            "profil": profil
        })

# === AFFICHAGE PRINCIPAL ===
st.title("Optimisation Multi-Panneaux")

tabs = st.tabs(list(st.session_state.panneaux.keys()))

def dessiner_plan(panneau, placement):
    fig, ax = plt.subplots(figsize=(8, 5))
    longueur = panneau["longueur"]
    largeur = panneau["largeur"] or 1000
    ax.set_xlim(0, longueur)
    ax.set_ylim(0, largeur)
    ax.set_aspect('equal')
    ax.invert_yaxis()

    ax.set_title(f"Disposition {panneau['nom']}", fontsize=14)

    # Graduations tous les 500 mm, police 12
    ax.set_xticks(range(0, longueur + 1, 500))
    ax.set_yticks(range(0, largeur + 1, 500))
    ax.tick_params(axis='both', labelsize=12)

    ax.set_xlabel("mm", fontsize=12)
    ax.set_ylabel("mm", fontsize=12)

    for i, rect in enumerate(placement):
        x, y, w, h = rect["x"], rect["y"], rect["width"], rect["height"]
        ax.add_patch(patches.Rectangle((x, y), w, h, edgecolor='black', facecolor='lightblue'))
        ax.text(x + w / 2, y + h / 2, f"{i+1}", ha='center', va='center', fontsize=8)

    return fig

for idx, mat in enumerate(st.session_state.panneaux.keys()):
    with tabs[idx]:
        panneau = st.session_state.panneaux[mat]
        st.header(panneau["nom"])

        if not panneau["pieces"]:
            st.info("Ajoutez des pièces via la barre latérale.")
            continue

        maxrects = MaxRectsBinPack(panneau["longueur"], panneau["largeur"] or 1000)
        placements = []
        erreurs = []

        for i, piece in enumerate(panneau["pieces"]):
            rect, rotated = maxrects.insert(piece["longueur"], piece["largeur"])
            if rect is None:
                erreurs.append(f"Pièce {i+1} ({piece['longueur']}x{piece['largeur']}) ne rentre pas.")
            else:
                placements.append({
                    "x": rect.x,
                    "y": rect.y,
                    "width": rect.width,
                    "height": rect.height,
                    "rotated": rotated
                })

        if erreurs:
            st.error("⚠️ Certaines pièces ne rentrent pas dans le panneau:")
            for err in erreurs:
                st.write(f"- {err}")

        fig = dessiner_plan(panneau, placements)
        st.pyplot(fig)

        # Statistiques
        vol_total = sum(p["longueur"] * p["largeur"] * p["epaisseur"] / 1e9 for p in panneau["pieces"])
        poids_total = vol_total * MATERIALS[mat]["densite"]
        st.markdown(f"**Volume total pièces :** {vol_total:.3f} m³")
        st.markdown(f"**Poids estimé :** {poids_total:.2f} kg")

# === EXPORT PDF ===
def export_pdf(panneau):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=panneau["nom"], ln=1, align='C')

    for idx, piece in enumerate(panneau["pieces"]):
        pdf.cell(200, 10, txt=f"{idx+1}. {piece['longueur']} x {piece['largeur']} x {piece['epaisseur']} mm", ln=1)

    return pdf.output(dest='S').encode("latin1")

for mat in st.session_state.panneaux.keys():
    if st.button(f"📄 Générer fiche PDF {mat}"):
        pdf_bytes = export_pdf(st.session_state.panneaux[mat])
        st.download_button(
            label=f"Télécharger PDF {mat}",
            data=pdf_bytes,
            file_name=f"{st.session_state.panneaux[mat]['nom'].replace(' ', '_')}.pdf",
            mime="application/pdf"
        )

