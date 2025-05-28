import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF

# === CONFIG INIT ===
st.set_page_config(page_title="Optimisation Multi-Panneaux MaxRects", layout="wide")

# === CONSTANTES MATÉRIAUX ===
MATERIALS = {
    "Bois": {"longueur": 2440, "largeur": 1220, "densite": 600},
    "Métal": {"longueur": 6000, "largeur": None, "densite": 7850}
}

# === MAXRECTS ALGO (comme avant) ===
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
        self.used_rectangles = []
        self.free_rectangles = [Rect(0, 0, width, height)]

    def insert(self, width, height, method):
        score1 = float('inf')
        score2 = float('inf')
        bestShortSideFit = float('inf')
        bestLongSideFit = float('inf')
        bestAreaFit = float('inf')
        bestNode = None
        rotated = False

        for rect in self.free_rectangles:
            if rect.width >= width and rect.height >= height:
                leftover_h = abs(rect.height - height)
                leftover_w = abs(rect.width - width)
                shortSideFit = min(leftover_h, leftover_w)
                longSideFit = max(leftover_h, leftover_w)
                areaFit = rect.width * rect.height - width * height
                if self._check_score(method, shortSideFit, longSideFit, areaFit, bestShortSideFit, bestLongSideFit, bestAreaFit):
                    bestNode = Rect(rect.x, rect.y, width, height)
                    bestShortSideFit = shortSideFit
                    bestLongSideFit = longSideFit
                    bestAreaFit = areaFit
                    rotated = False

            if rect.width >= height and rect.height >= width:
                leftover_h = abs(rect.height - width)
                leftover_w = abs(rect.width - height)
                shortSideFit = min(leftover_h, leftover_w)
                longSideFit = max(leftover_h, leftover_w)
                areaFit = rect.width * rect.height - height * width
                if self._check_score(method, shortSideFit, longSideFit, areaFit, bestShortSideFit, bestLongSideFit, bestAreaFit):
                    bestNode = Rect(rect.x, rect.y, height, width)
                    bestShortSideFit = shortSideFit
                    bestLongSideFit = longSideFit
                    bestAreaFit = areaFit
                    rotated = True

        if bestNode is None:
            return None, False

        self._place_rect(bestNode)
        return bestNode, rotated

    def _check_score(self, method, shortSideFit, longSideFit, areaFit, bestShortSideFit, bestLongSideFit, bestAreaFit):
        if method == "Best Short Side Fit":
            return shortSideFit < bestShortSideFit or (shortSideFit == bestShortSideFit and longSideFit < bestLongSideFit)
        elif method == "Best Long Side Fit":
            return longSideFit < bestLongSideFit or (longSideFit == bestLongSideFit and shortSideFit < bestShortSideFit)
        elif method == "Best Area Fit":
            return areaFit < bestAreaFit or (areaFit == bestAreaFit and shortSideFit < bestShortSideFit)
        elif method == "Bottom-Left":
            return areaFit < bestAreaFit
        elif method == "Contact Point":
            return shortSideFit < bestShortSideFit or (shortSideFit == bestShortSideFit and longSideFit < bestLongSideFit)
        return False

    def _place_rect(self, node):
        i = 0
        while i < len(self.free_rectangles):
            if self._split_free_node(self.free_rectangles[i], node):
                self.free_rectangles.pop(i)
                i -= 1
            i += 1
        self._prune_free_list()
        self.used_rectangles.append(node)

    def _split_free_node(self, freeNode, usedNode):
        if usedNode.x >= freeNode.x + freeNode.width or usedNode.x + usedNode.width <= freeNode.x or \
           usedNode.y >= freeNode.y + freeNode.height or usedNode.y + usedNode.height <= freeNode.y:
            return False

        if usedNode.x < freeNode.x + freeNode.width and usedNode.x + usedNode.width > freeNode.x:
            if usedNode.y > freeNode.y and usedNode.y < freeNode.y + freeNode.height:
                newNode = Rect(freeNode.x, freeNode.y, freeNode.width, usedNode.y - freeNode.y)
                self.free_rectangles.append(newNode)
            if usedNode.y + usedNode.height < freeNode.y + freeNode.height:
                newNode = Rect(freeNode.x, usedNode.y + usedNode.height, freeNode.width, freeNode.y + freeNode.height - (usedNode.y + usedNode.height))
                self.free_rectangles.append(newNode)

        if usedNode.y < freeNode.y + freeNode.height and usedNode.y + usedNode.height > freeNode.y:
            if usedNode.x > freeNode.x and usedNode.x < freeNode.x + freeNode.width:
                newNode = Rect(freeNode.x, freeNode.y, usedNode.x - freeNode.x, freeNode.height)
                self.free_rectangles.append(newNode)
            if usedNode.x + usedNode.width < freeNode.x + freeNode.width:
                newNode = Rect(usedNode.x + usedNode.width, freeNode.y, freeNode.x + freeNode.width - (usedNode.x + usedNode.width), freeNode.height)
                self.free_rectangles.append(newNode)

        return True

    def _prune_free_list(self):
        i = 0
        while i < len(self.free_rectangles):
            j = i + 1
            while j < len(self.free_rectangles):
                if self._is_contained_in(self.free_rectangles[i], self.free_rectangles[j]):
                    self.free_rectangles.pop(i)
                    i -= 1
                    break
                if self._is_contained_in(self.free_rectangles[j], self.free_rectangles[i]):
                    self.free_rectangles.pop(j)
                    j -= 1
                j += 1
            i += 1

    def _is_contained_in(self, a, b):
        return a.x >= b.x and a.y >= b.y and a.x + a.width <= b.x + b.width and a.y + a.height <= b.y + b.height


# === UTILITAIRES ===
def afficher_explanation(heuristique):
    explanations = {
        "Best Short Side Fit": "Minimise la différence sur le plus petit côté entre pièce et espace restant.",
        "Best Long Side Fit": "Minimise la plus grande différence entre les côtés.",
        "Best Area Fit": "Minimise la surface libre restante après placement.",
        "Bottom-Left": "Place la pièce au plus bas à gauche possible.",
        "Contact Point": "Favorise le placement avec le maximum de contact avec les autres pièces."
    }
    return explanations.get(heuristique, "")

def dessiner_plan(panneau, placement):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_xlim(0, panneau["longueur"])
    ax.set_ylim(0, panneau["largeur"] or 1000)
    ax.set_aspect('equal')
    ax.invert_yaxis()
    ax.set_title(f"Disposition panneau {panneau['nom']}")
    ax.set_xlabel("mm")
    ax.set_ylabel("mm")

    for i, rect in enumerate(placement):
        x, y, w, h = rect["x"], rect["y"], rect["width"], rect["height"]
        color = 'lightblue'
        ax.add_patch(patches.Rectangle((x, y), w, h, edgecolor='black', facecolor=color))
        ax.text(x + w/2, y + h/2, f"{i+1}", ha='center', va='center', fontsize=8)

    return fig

# === STATE INIT ===
if "panneaux" not in st.session_state:
    st.session_state.panneaux = {
        mat: {
            "nom": f"Panneau {mat}",
            "longueur": MATERIALS[mat]["longueur"],
            "largeur": MATERIALS[mat]["largeur"],
            "pieces": []
        }
        for mat in MATERIALS.keys()
    }

# === SIDEBAR ===
st.sidebar.title("Ajouter une pièce à un matériau")

# Choix matériau pour nouvelle pièce
mat_piece = st.sidebar.selectbox("Matériau pièce", list(MATERIALS.keys()))

# Saisie pièce
longueur_piece = st.sidebar.number_input("Longueur (mm)", min_value=1, value=200, key="long_piece")
largeur_piece = st.sidebar.number_input("Largeur (mm)", min_value=1, value=100, key="larg_piece")
epaisseur_piece = st.sidebar.number_input("Épaisseur (mm)", min_value=1, value=18, key="epaisseur_piece")
quantite_piece = st.sidebar.number_input("Quantité", min_value=1, value=1, step=1)

if st.sidebar.button("Ajouter la/les pièces"):
    for _ in range(quantite_piece):
        st.session_state.panneaux[mat_piece]["pieces"].append({
            "longueur": longueur_piece,
            "largeur": largeur_piece,
            "epaisseur": epaisseur_piece
        })

# Choix heuristique
heuristique = st.sidebar.selectbox(
    "Heuristique MaxRects",
    ["Best Short Side Fit", "Best Long Side Fit", "Best Area Fit", "Bottom-Left", "Contact Point"],
    index=0
)
st.sidebar.info(afficher_explanation(heuristique))

# === AFFICHAGE PRINCIPAL AVEC ONGLETS ===
st.title("Optimisation Multi-Panneaux MaxRects")

tab_names = list(st.session_state.panneaux.keys())
tabs = st.tabs(tab_names)

# Pour chaque panneau/matériau, on calcule et affiche la découpe
for idx, mat in enumerate(tab_names):
    panneau = st.session_state.panneaux[mat]
    with tabs[idx]:
        st.header(f"{panneau['nom']} ({mat})")

        if not panneau["pieces"]:
            st.info("Ajoutez des pièces pour ce panneau via la barre latérale.")
            continue

        maxrects = MaxRectsBinPack(panneau["longueur"], panneau["largeur"] or 1000)
        placements = []
        errors = []

        for i, piece in enumerate(panneau["pieces"]):
            rect, rotated = maxrects.insert(piece["longueur"], piece["largeur"], heuristique)
            if rect is None:
                errors.append(f"Pièce {i+1} ({piece['longueur']}x{piece['largeur']}) ne rentre pas dans le panneau.")
            else:
                placements.append({"x": rect.x, "y": rect.y, "width": rect.width, "height": rect.height, "rotated": rotated})

        if errors:
            st.error("⚠️ Certaines pièces ne rentrent pas :")
            for err in errors:
                st.write(f"- {err}")

        fig = dessiner_plan(panneau, placements)
        st.pyplot(fig)

        # Statistiques
        volume_total = sum(p["longueur"] * p["largeur"] * p["epaisseur"] / 1e9 for p in panneau["pieces"])
        poids_total = volume_total * MATERIALS[mat]["densite"]
        st.markdown(f"**Volume total pièces :** {volume_total:.3f} m³")
        st.markdown(f"**Poids estimé :** {poids_total:.2f} kg")

# === EXPORT PDF GLOBAL ===
def export_pdf_global():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 10, "Rapport d'optimisation Multi-Panneaux", ln=1, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Heuristique utilisée : {heuristique}", ln=1)
    pdf.ln(5)

    for mat in tab_names:
        panneau = st.session_state.panneaux[mat]
        pdf.cell(0, 10, f"Panneau: {panneau['nom']} (Matériau: {mat})", ln=1)
        if not panneau["pieces"]:
            pdf.cell(0, 10, "Aucune pièce à découper.", ln=1)
            pdf.ln(3)
            continue

        maxrects = MaxRectsBinPack(panneau["longueur"], panneau["largeur"] or 1000)
        placements = []
        errors = []

        for i, piece in enumerate(panneau["pieces"]):
            rect, rotated = maxrects.insert(piece["longueur"], piece["largeur"], heuristique)
            if rect is None:
                errors.append(f"Pièce {i+1} ({piece['longueur']}x{piece['largeur']}) ne rentre pas.")
            else:
                placements.append({"x": rect.x, "y": rect.y, "width": rect.width, "height": rect.height, "rotated": rotated})

        for i, piece in enumerate(panneau["pieces"]):
            rot_text = ""
            if i < len(placements) and placements[i]["rotated"]:
                rot_text = " (rotated)"
            pdf.cell(0, 10, f"{i+1}. Pièce {piece['longueur']}x{piece['largeur']}x{piece['epaisseur']} mm{rot_text}", ln=1)

        if errors:
            pdf.ln(3)
            pdf.cell(0, 10, "⚠️ Pièces non placées :", ln=1)
            for err in errors:
                pdf.cell(0, 10, err, ln=1)
        pdf.ln(5)

    return pdf.output(dest="S").encode("latin1")

if st.button("📄 Générer rapport PDF global"):
    pdf_bytes = export_pdf_global()
    st.download_button(
        label="Télécharger rapport PDF",
        data=pdf_bytes,
        file_name="rapport_optimisation_multi_panneaux.pdf",
        mime="application/pdf"
    )

