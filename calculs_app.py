import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF

# === CONFIGURATION INITIALE ===
st.set_page_config(page_title="Optimisation Découpe", layout="wide")
st.image("logo.gif", width=150)

# === CONSTANTES ===
MATERIALS = {
    "Bois": {"longueur": 2440, "largeur": 1220, "densite": 600},
    "Métal": {"longueur": 6000, "largeur": None, "densite": 7850}
}

# === ALGORITHME MAXRECTS ===
class Rect:
    def __init__(self, x=0, y=0, width=0, height=0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    
    def __repr__(self):
        return f"Rect(x={self.x}, y={self.y}, w={self.width}, h={self.height})"

class MaxRectsBinPack:
    def __init__(self, width, height, allow_rotate=True):
        self.bin_width = width
        self.bin_height = height
        self.allow_rotate = allow_rotate
        self.used_rectangles = []
        self.free_rectangles = [Rect(0, 0, width, height)]

    def insert(self, width, height, method='best_short_side_fit'):
        newNode = None
        score1 = float('inf')  # Best score for the method
        score2 = float('inf')  # Secondary score for tiebreakers
        best_rect_index = -1

        for i, freeRect in enumerate(self.free_rectangles):
            # Try to place without rotation
            if freeRect.width >= width and freeRect.height >= height:
                score1_candidate, score2_candidate = self.score_rect(freeRect, width, height, method)
                if score1_candidate < score1 or (score1_candidate == score1 and score2_candidate < score2):
                    newNode = Rect(freeRect.x, freeRect.y, width, height)
                    score1 = score1_candidate
                    score2 = score2_candidate
                    best_rect_index = i

            # Try with rotation
            if self.allow_rotate and freeRect.width >= height and freeRect.height >= width:
                score1_candidate, score2_candidate = self.score_rect(freeRect, height, width, method)
                if score1_candidate < score1 or (score1_candidate == score1 and score2_candidate < score2):
                    newNode = Rect(freeRect.x, freeRect.y, height, width)
                    score1 = score1_candidate
                    score2 = score2_candidate
                    best_rect_index = i

        if newNode is None:
            return None  # Pas de place

        self.place_rect(newNode, best_rect_index)
        return newNode

    def place_rect(self, node, free_rect_index):
        # Place rectangle and split free space
        self.used_rectangles.append(node)
        free_rect = self.free_rectangles.pop(free_rect_index)

        # Split free rectangle into up to 2 new free rectangles
        if free_rect.width - node.width > 0:
            new_rect = Rect(free_rect.x + node.width, free_rect.y,
                            free_rect.width - node.width, node.height)
            self.free_rectangles.append(new_rect)
        if free_rect.height - node.height > 0:
            new_rect = Rect(free_rect.x, free_rect.y + node.height,
                            free_rect.width, free_rect.height - node.height)
            self.free_rectangles.append(new_rect)
        self.prune_free_list()

    def prune_free_list(self):
        # Remove any redundant free rectangles
        i = 0
        while i < len(self.free_rectangles):
            j = i + 1
            while j < len(self.free_rectangles):
                if self.is_contained_in(self.free_rectangles[i], self.free_rectangles[j]):
                    self.free_rectangles.pop(i)
                    i -= 1
                    break
                if self.is_contained_in(self.free_rectangles[j], self.free_rectangles[i]):
                    self.free_rectangles.pop(j)
                    j -= 1
                j += 1
            i += 1

    @staticmethod
    def is_contained_in(r1, r2):
        return r1.x >= r2.x and r1.y >= r2.y \
            and r1.x + r1.width <= r2.x + r2.width \
            and r1.y + r1.height <= r2.y + r2.height

    def score_rect(self, free_rect, width, height, method):
        leftover_h = abs(free_rect.width - width)
        leftover_v = abs(free_rect.height - height)
        leftover_area = free_rect.width * free_rect.height - width * height

        if method == 'best_short_side_fit':
            short_side = min(leftover_h, leftover_v)
            long_side = max(leftover_h, leftover_v)
            return short_side, long_side
        elif method == 'best_long_side_fit':
            short_side = min(leftover_h, leftover_v)
            long_side = max(leftover_h, leftover_v)
            return long_side, short_side
        elif method == 'best_area_fit':
            return leftover_area, min(leftover_h, leftover_v)
        elif method == 'bottom_left':
            return free_rect.y + height, free_rect.x
        elif method == 'contact_point':
            score = self.contact_point_score(free_rect.x, free_rect.y, width, height)
            return -score, 0
        else:
            # Par défaut best_short_side_fit
            short_side = min(leftover_h, leftover_v)
            long_side = max(leftover_h, leftover_v)
            return short_side, long_side

    def contact_point_score(self, x, y, width, height):
        score = 0
        if x == 0 or x + width == self.bin_width:
            score += height
        if y == 0 or y + height == self.bin_height:
            score += width

        for used in self.used_rectangles:
            if used.x == x + width or used.x + used.width == x:
                vert_overlap = min(used.y + used.height, y + height) - max(used.y, y)
                if vert_overlap > 0:
                    score += vert_overlap
            if used.y == y + height or used.y + used.height == y:
                horiz_overlap = min(used.x + used.width, x + width) - max(used.x, x)
                if horiz_overlap > 0:
                    score += horiz_overlap
        return score

# === FONCTIONS UTILITAIRES ===
def nom_panneau(mat, type_piece):
    if mat == "Bois":
        return "Panneaux Bois" if type_piece == "Panneau" else "Tasseaux Bois"
    else:
        return "Tôles Métal" if type_piece == "Panneau" else "Barres Métal"

def dessiner_optimisation(panneau, placements):
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_xlim(0, panneau["longueur"])
    largeur = panneau["largeur"] if panneau["largeur"] else 1000
    ax.set_ylim(0, largeur)
    ax.set_aspect('equal')
    ax.invert_yaxis()

    step = 500
    xticks = range(0, panneau["longueur"] + step, step)
    yticks = range(0, largeur + step, step)
    ax.set_xticks(xticks)
    ax.set_yticks(yticks)
    ax.tick_params(axis='both', labelsize=12)

    for i, (rect, piece) in enumerate(zip(placements, panneau["pieces"])):
        if rect is None:
            # Pièce non placée
            continue
        ax.add_patch(
            patches.Rectangle((rect.x, rect.y), rect.width, rect.height,
                              facecolor='lightgreen', edgecolor='black')
        )
        ax.text(rect.x + rect.width / 2, rect.y + rect.height / 2,
                f"{i+1}", ha='center', va='center', fontsize=10)

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

# === SIDEBAR ===
st.sidebar.header("Sélection panneau / barre")
cle_choix = st.sidebar.selectbox(
    "Panneau / Barre actif",
    options=list(st.session_state.panneaux.keys()),
    format_func=lambda x: st.session_state.panneaux[x]["nom"]
)
panneau = st.session_state.panneaux[cle_choix]

nouveau_nom = st.sidebar.text_input("Nom du panneau / barre", panneau["nom"])
if nouveau_nom.strip():
    panneau["nom"] = nouveau_nom.strip()

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

# === OPTIMISATION MAXRECTS ===
st.subheader("Disposition optimisée (MaxRects)")

# On trie pièces par aire décroissante (optimisation classique)
pieces_sorted = sorted(panneau["pieces"], key=lambda p: p["longueur"]*p["largeur"], reverse=True)
packer = MaxRectsBinPack(panneau["longueur"], panneau["largeur"] if panneau["largeur"] else 1000, allow_rotate=True)

placements = []
for piece in pieces_sorted:
    rect = packer.insert(piece["longueur"], piece["largeur"], method='best_short_side_fit')
    if rect is None:
        rect = packer.insert(piece["largeur"], piece["longueur"], method='best_short_side_fit')  # tentative rotation si pas déjà testée
    placements.append(rect)

# Aligner les placements avec l'ordre original (par indices)
# pieces_sorted => original order, donc on doit associer.
# Simplifions : affichons selon ordre trié (numérotation séquentielle)

fig = dessiner_optimisation(panneau, placements)
st.pyplot(fig)

# === STATISTIQUES ===
st.subheader("Statistiques")
total_volume = sum(p["longueur"] * p["largeur"] * p["epaisseur"] / 1e9 for p in panneau["pieces"])
total_poids = total_volume * MATERIALS[panneau["materiau"]]["densite"]
st.markdown(f"**Volume total :** {total_volume:.3f} m³")
st.markdown(f"**Poids estimé :** {total_poids:.2f} kg")

# === EXPORT PDF ===
def exporter_pdf(panneau):
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

if st.button("📄 Générer fiche PDF"):
    pdf_bytes = exporter_pdf(panneau)
    st.download_button(
        label="Télécharger PDF",
        data=pdf_bytes,
        file_name=f"{panneau['nom'].replace(' ', '_')}.pdf",
        mime="application/pdf"
    )
