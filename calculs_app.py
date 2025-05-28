import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF

# === CONFIGURATION INITIALE ===
st.set_page_config(page_title="Optimisation Découpe Multi-Matériaux", layout="wide")

# === CONSTANTES ===
MATERIALS = {
    "Bois": {"longueur": 2440, "largeur": 1220, "densite": 600},
    "Métal": {"longueur": 6000, "largeur": 1250, "densite": 7850}
}

NAMES = {
    "panneau": {"Bois": "Panneau Bois", "Métal": "Tôle Métal"},
    "barre": {"Bois": "Tasseau Bois", "Métal": "Barre Métal"}
}

# === CLASSES ET ALGO MAXRECTS SIMPLIFIE ===
class Rect:
    def __init__(self, x, y, width, height):
        self.x, self.y = x, y
        self.width, self.height = width, height

class MaxRectsBinPack:
    def __init__(self, width, height):
        self.bin_width = width
        self.bin_height = height
        self.free_rects = [Rect(0, 0, width, height)]
        self.used_rects = []

    def insert(self, width, height):
        # Recherche première free rect compatible avec rotation
        for i, freerect in enumerate(self.free_rects):
            if width <= freerect.width and height <= freerect.height:
                rect = Rect(freerect.x, freerect.y, width, height)
                self.used_rects.append(rect)
                self.free_rects.pop(i)
                # TODO : diviser free_rects (simplifié ici)
                return rect, False
            if height <= freerect.width and width <= freerect.height:
                rect = Rect(freerect.x, freerect.y, height, width)
                self.used_rects.append(rect)
                self.free_rects.pop(i)
                return rect, True
        return None, False

# === INITIALISATION ÉTAT ===
for cat in ["panneau", "barre"]:
    for mat in MATERIALS.keys():
        key = f"{cat}_{mat}"
        if key not in st.session_state:
            st.session_state[key] = {
                "nom": NAMES[cat][mat],
                "longueur": MATERIALS[mat]["longueur"],
                "largeur": MATERIALS[mat]["largeur"] if cat == "panneau" else None,
                "pieces": []
            }

# === SIDEBAR ===
st.sidebar.header("Configuration")

cat_choice = st.sidebar.radio("Catégorie", ["Panneaux", "Barres"])

mat_choice = st.sidebar.selectbox("Matériau", list(MATERIALS.keys()))

cat_key = "panneau" if cat_choice == "Panneaux" else "barre"
state_key = f"{cat_key}_{mat_choice}"
item = st.session_state[state_key]

st.sidebar.markdown(f"### {item['nom']}")

# Dimensions panneau ou barre
long_p = st.sidebar.number_input(f"Longueur {cat_choice[:-1]} (mm)", min_value=1, value=item["longueur"])
if cat_key == "panneau":
    larg_p = st.sidebar.number_input(f"Largeur {cat_choice[:-1]} (mm)", min_value=1, value=item["largeur"] or 1000)
else:
    larg_p = None

item["longueur"] = long_p
item["largeur"] = larg_p

# Ajouter pièce
st.sidebar.markdown("### Ajouter une pièce")
long_piece = st.sidebar.number_input("Longueur pièce (mm)", min_value=1, value=200)
larg_piece = st.sidebar.number_input("Largeur pièce (mm)", min_value=1, value=100)
epaisseur_piece = st.sidebar.number_input("Épaisseur pièce (mm)", min_value=1, value=18)
quantite_piece = st.sidebar.number_input("Quantité", min_value=1, value=1)

profil = ""
if mat_choice == "Métal" and cat_key == "barre":
    profil = st.sidebar.text_input("Profil (ex: 40x40x2 mm)", "40x40x2")

if st.sidebar.button(f"Ajouter pièce {cat_choice[:-1]}"):
    for _ in range(quantite_piece):
        item["pieces"].append({
            "longueur": long_piece,
            "largeur": larg_piece,
            "epaisseur": epaisseur_piece,
            "profil": profil
        })

# === AFFICHAGE PRINCIPAL ===
st.title("Optimisation Multi-Panneaux et Barres")

# Onglets par catégorie et matériau
tabs = []
keys = []
for cat in ["panneau", "barre"]:
    for mat in MATERIALS.keys():
        tabs.append(NAMES[cat][mat])
        keys.append(f"{cat}_{mat}")

tab_objs = st.tabs(tabs)

def draw_plan(panneau, placements):
    fig, ax = plt.subplots(figsize=(8, 5))
    longueur = panneau["longueur"]
    largeur = panneau["largeur"] or 1000
    ax.set_xlim(0, longueur)
    ax.set_ylim(0, largeur)
    ax.set_aspect('equal')
    ax.invert_yaxis()

    ax.set_title(panneau["nom"], fontsize=14)
    ax.set_xticks(range(0, longueur + 1, 500))
    ax.set_yticks(range(0, largeur + 1, 500))
    ax.tick_params(axis='both', labelsize=12)
    ax.set_xlabel("mm", fontsize=12)
    ax.set_ylabel("mm", fontsize=12)

    for i, rect in enumerate(placements):
        x, y, w, h = rect["x"], rect["y"], rect["width"], rect["height"]
        ax.add_patch(patches.Rectangle((x, y), w, h, edgecolor='black', facecolor='lightblue'))
        ax.text(x + w / 2, y + h / 2, f"{i+1}", ha='center', va='center', fontsize=8)

    return fig

for i, tab in enumerate(tab_objs):
    with tab:
        panneau = st.session_state[keys[i]]
        st.header(panneau["nom"])

        if not panneau["pieces"]:
            st.info("Ajoutez des pièces via la barre latérale.")
            continue

        maxrects = MaxRectsBinPack(panneau["longueur"], panneau["largeur"] or 1000)
        placements = []
        erreurs = []

        for idx, piece in enumerate(panneau["pieces"]):
            rect, rotated = maxrects.insert(piece["longueur"], piece["largeur"])
            if rect is None:
                erreurs.append(f"Pièce {idx+1} ({piece['longueur']}x{piece['largeur']}) ne rentre pas.")
            else:
                placements.append({
                    "x": rect.x,
                    "y": rect.y,
                    "width": rect.width,
                    "height": rect.height,
                    "rotated": rotated
                })

        if erreurs:
            st.error("⚠️ Certaines pièces ne rentrent pas dans le panneau/tôle/barre:")
            for err in erreurs:
                st.write(f"- {err}")

        fig = draw_plan(panneau, placements)
        st.pyplot(fig)

        vol_total = sum(p["longueur"] * p["largeur"] * p["epaisseur"] / 1e9 for p in panneau["pieces"])
        poids_total = vol_total * MATERIALS[keys[i].split("_")[1]]["densite"]

        st.markdown(f"**Volume total pièces :** {vol_total:.3f} m³")
        st.markdown(f"**Poids estimé :** {poids_total:.2f} kg")

        # Export PDF
        if st.button(f"📄 Générer fiche PDF {panneau['nom']}"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=panneau["nom"], ln=1, align='C')
            for idx, piece in enumerate(panneau["pieces"]):
                pdf.cell(200, 10, txt=f"{idx+1}. {piece['longueur']} x {piece['largeur']} x {piece['epaisseur']} mm", ln=1)
            pdf_bytes = pdf.output(dest='S').encode("latin1")
            st.download_button(
                label=f"Télécharger PDF {panneau['nom']}",
                data=pdf_bytes,
                file_name=f"{panneau['nom'].replace(' ', '_')}.pdf",
                mime="application/pdf"
            )
