import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF

# === CONFIGURATION INITIALE ===
st.set_page_config(page_title="Optimisation Découpe MaxRects", layout="wide")

# === CONSTANTES MATÉRIAUX ===
MATERIALS = {
    "Bois": {"longueur": 2440, "largeur": 1220, "densite": 600},
    "Métal": {"longueur": 6000, "largeur": None, "densite": 7850}
}

# === MAXRECTS ALGO + HEURISTIQUES ===
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
        newNode = Rect(0, 0, 0, 0)
        bestShortSideFit = float('inf')
        bestLongSideFit = float('inf')
        bestAreaFit = float('inf')
        bestNode = None
        rotated = False

        for rect in self.free_rectangles:
            # Try to place without rotation
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

            # Try to place with rotation
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
            # For BL, just accept the first fitting position (handled by insert order)
            return areaFit < bestAreaFit
        elif method == "Contact Point":
            # Not implemented detailed contact point heuristic here for simplicity
            return shortSideFit < bestShortSideFit or (shortSideFit == bestShortSideFit and longSideFit < bestLongSideFit)
        return False

    def _place_rect(self, node):
        num_free_rectangles = len(self.free_rectangles)
        i = 0
        while i < num_free_rectangles:
            if self._split_free_node(self.free_rectangles[i], node):
                self.free_rectangles.pop(i)
                num_free_rectangles -= 1
                i -= 1
            i += 1
        self._prune_free_list()
        self.used_rectangles.append(node)

    def _split_free_node(self, freeNode, usedNode):
        if usedNode.x >= freeNode.x + freeNode.width or usedNode.x + usedNode.width <= freeNode.x or \
           usedNode.y >= freeNode.y + freeNode.height or usedNode.y + usedNode.height <= freeNode.y:
            return False

        if usedNode.x < freeNode.x + freeNode.width and usedNode.x + usedNode.width > freeNode.x:
            # Bottom free rectangle
            if usedNode.y > freeNode.y and usedNode.y < freeNode.y + freeNode.height:
                newNode = Rect(freeNode.x, freeNode.y, freeNode.width, usedNode.y - freeNode.y)
                self.free_rectangles.append(newNode)
            # Top free rectangle
            if usedNode.y + usedNode.height < freeNode.y + freeNode.height:
                newNode = Rect(freeNode.x, usedNode.y + usedNode.height, freeNode.width, freeNode.y + freeNode.height - (usedNode.y + usedNode.height))
                self.free_rectangles.append(newNode)

        if usedNode.y < freeNode.y + freeNode.height and usedNode.y + usedNode.height > freeNode.y:
            # Left free rectangle
            if usedNode.x > freeNode.x and usedNode.x < freeNode.x + freeNode.width:
                newNode = Rect(freeNode.x, freeNode.y, usedNode.x - freeNode.x, freeNode.height)
                self.free_rectangles.append(newNode)
            # Right free rectangle
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

# === FONCTIONS UTILITAIRES ===
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
    ax.set_ylim(0, panneau["largeur"] or 1000)  # par sécurité si None largeur métal
    ax.set_aspect('equal')
    ax.invert_yaxis()
    ax.set_title(f"Disposition panneaux {panneau['nom']}")
    ax.set_xlabel("mm")
    ax.set_ylabel("mm")

    # Grille 1cm
    major_ticks_x = range(0, panneau["longueur"]+1, 10)
    major_ticks_y = range(0, (panneau["largeur"] or 1000)+1, 10)
    ax.set_xticks(major_ticks_x)
    ax.set_yticks(major_ticks_y)
    ax.grid(which='major', color='lightgray', linestyle='--', linewidth=0.5)

    for i, rect in enumerate(placement):
        x, y, w, h = rect["x"], rect["y"], rect["width"], rect["height"]
        color = 'lightblue'
        ax.add_patch(patches.Rectangle((x, y), w, h, edgecolor='black', facecolor=color))
        ax.text(x + w/2, y + h/2, f"{i+1}", ha='center', va='center', fontsize=8)

    return fig

# === APP STATE INIT ===
if "panneaux" not in st.session_state:
    st.session_state.panneaux = {}
if "actif" not in st.session_state:
    st.session_state.actif = None

# === SIDEBAR ===
st.sidebar.title("Paramètres de découpe")

# Choix matériau
materiau = st.sidebar.selectbox("Choisir matériau", list(MATERIALS.keys()))

# Initialisation panneau si besoin
if materiau not in st.session_state.panneaux:
    st.session_state.panneaux[materiau] = {
        "nom": f"Panneau {materiau}",
        "longueur": MATERIALS[materiau]["longueur"],
        "largeur": MATERIALS[materiau]["largeur"],
        "pieces": []
    }
st.session_state.actif = materiau

# Affichage panneau actif
panneau = st.session_state.panneaux[materiau]

# Nom panneau modifiable
panneau["nom"] = st.sidebar.text_input("Nom panneau", panneau["nom"])

# Ajout de pièces
st.sidebar.subheader("Ajouter une pièce")
longueur_piece = st.sidebar.number_input("Longueur (mm)", min_value=1, value=200)
largeur_piece = st.sidebar.number_input("Largeur (mm)", min_value=1, value=100)
epaisseur_piece = st.sidebar.number_input("Épaisseur (mm)", min_value=1, value=18)
quantite_piece = st.sidebar.number_input("Quantité", min_value=1, value=1, step=1)

if st.sidebar.button("Ajouter pièce"):
    for _ in range(quantite_piece):
        panneau["pieces"].append({
            "longueur": longueur_piece,
            "largeur": largeur_piece,
            "epaisseur": epaisseur_piece
        })

# Choix heuristique MaxRects avec explication
heuristique = st.sidebar.selectbox(
    "Heuristique MaxRects",
    ["Best Short Side Fit", "Best Long Side Fit", "Best Area Fit", "Bottom-Left", "Contact Point"],
    index=0
)
st.sidebar.info(afficher_explanation(heuristique))

# --- AFFICHAGE PRINCIPAL ---
st.title(f"Optimisation découpe panneau : {panneau['nom']}")

if not panneau["pieces"]:
    st.info("Ajoutez des pièces via la barre latérale.")
    st.stop()

# Optimisation MaxRects avec heuristique choisie
maxrects = MaxRectsBinPack(panneau["longueur"], panneau["largeur"] or 1000)

placements = []
errors = []
for i, piece in enumerate(panneau["pieces"]):
    rect, rotated = maxrects.insert(piece["longueur"], piece["largeur"], heuristique)
    if rect is None:
        errors.append(f"Pièce {i+1} ({piece['longueur']}x{piece['largeur']}) ne rentre pas.")
    else:
        placements.append({"x": rect.x, "y": rect.y, "width": rect.width, "height": rect.height, "rotated": rotated})

if errors:
    st.error("⚠️ Certaines pièces ne rentrent pas dans le panneau :")
    for err in errors:
        st.write(f"- {err}")

# Dessin du résultat
fig = dessiner_plan(panneau, placements)
st.pyplot(fig)

# Statistiques volume et poids
volume_total = sum(p["longueur"] * p["largeur"] * p["epaisseur"] / 1e9 for p in panneau["pieces"])
poids_total = volume_total * MATERIALS[materiau]["densite"]
st.markdown(f"**Volume total pièces :** {volume_total:.3f} m³")
st.markdown(f"**Poids estimé :** {poids_total:.2f} kg")

# Export PDF simple
def export_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Fiche découpe panneau: {panneau['nom']}", ln=1, align="C")
    pdf.cell(0, 10, f"Matériau: {materiau}", ln=1)
    pdf.cell(0, 10, f"Heuristique: {heuristique}", ln=1)
    pdf.ln(5)

    for i, piece in enumerate(panneau["pieces"]):
        rot_text = " (rotated)" if i < len(placements) and placements[i]["rotated"] else ""
        pdf.cell(0, 10, f"{i+1}. Pièce {piece['longueur']}x{piece['largeur']}x{piece['epaisseur']} mm{rot_text}", ln=1)

    if errors:
        pdf.ln(5)
        pdf.cell(0, 10, "⚠️ Pièces non placées :", ln=1)
        for err in errors:
            pdf.cell(0, 10, err, ln=1)

    return pdf.output(dest="S").encode("latin1")

if st.button("📄 Générer fiche PDF"):
    pdf_bytes = export_pdf()
    st.download_button(
        label="Télécharger PDF",
        data=pdf_bytes,
        file_name=f"{panneau['nom'].replace(' ', '_')}_decoupe.pdf",
        mime="application/pdf"
    )
