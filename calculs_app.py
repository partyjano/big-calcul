import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

DEFAULT_PANEL_LENGTH = 2.44
DEFAULT_PANEL_WIDTH = 1.22

MATERIAL_DENSITIES = {
    "Bois": 600,
    "Métal": 7850
}

st.set_page_config(page_title="Optimisation de découpe", layout="wide")

st.title("Optimisation de découpe de panneaux bois et métaux")

with st.sidebar:
    st.header("Paramètres du panneau")
    panel_length = st.number_input("Longueur panneau (m)", value=DEFAULT_PANEL_LENGTH, min_value=0.1)
    panel_width = st.number_input("Largeur panneau (m)", value=DEFAULT_PANEL_WIDTH, min_value=0.1)

    st.header("Ajouter une pièce")
    longueur = st.number_input("Longueur (m)", min_value=0.01, value=0.2)
    largeur = st.number_input("Largeur (m)", min_value=0.01, value=0.1)
    epaisseur = st.number_input("Épaisseur (mm)", min_value=1.0, value=18.0)
    matiere = st.selectbox("Matériau", options=list(MATERIAL_DENSITIES.keys()))
    quantite = st.number_input("Quantité", min_value=1, value=1, step=1)

    if "pieces" not in st.session_state:
        st.session_state.pieces = []

    if st.button("Ajouter la pièce"):
        for _ in range(quantite):
            st.session_state.pieces.append((longueur, largeur, epaisseur, matiere))

if not st.session_state.pieces:
    st.info("Ajoutez des pièces pour commencer.")
    st.stop()

pieces = [(l, L) for l, L, _, _ in st.session_state.pieces]

# Placement des pièces
def try_place_piece(espace, l, L):
    best = None
    for i, (x, y, w, h) in enumerate(espace):
        for rl, rL, rot in [(l, L, False), (L, l, True)]:
            if rl <= w and rL <= h:
                reste = (w - rl) * h + (h - rL) * w
                if best is None or reste < best[0]:
                    best = (reste, i, x, y, rl, rL, rot)
    return best

def place_pieces(pieces):
    panneaux = []
    for l, L in sorted(pieces, key=lambda x: max(x), reverse=True):
        placed = False
        for panneau in panneaux:
            idx = try_place_piece(panneau['espace'], l, L)
            if idx:
                _, i, x, y, rl, rL, rot = idx
                del panneau['espace'][i]
                panneau['placements'].append((x, y, rl, rL, rot))
                panneau['espace'].append((x + rl, y, panel_length - (x + rl), rL))
                panneau['espace'].append((x, y + rL, rl, panel_width - (y + rL)))
                placed = True
                break
        if not placed:
            new = {
                'espace': [(0, 0, panel_length, panel_width)],
                'placements': []
            }
            idx = try_place_piece(new['espace'], l, L)
            if idx:
                _, i, x, y, rl, rL, rot = idx
                new['placements'].append((x, y, rl, rL, rot))
                new['espace'] = [
                    (x + rl, y, panel_length - (x + rl), rL),
                    (x, y + rL, rl, panel_width - (y + rL))
                ]
                panneaux.append(new)
    return panneaux

panneaux = place_pieces(pieces)

# Affichage graphique
cols = st.columns(len(panneaux))
for idx, (panneau, col) in enumerate(zip(panneaux, cols)):
    fig, ax = plt.subplots()
    ax.set_title(f"Panneau #{idx+1}")
    ax.set_xlim(0, panel_length)
    ax.set_ylim(0, panel_width)
    ax.set_aspect('equal')
    ax.invert_yaxis()
    for i, (x, y, l, L, rot) in enumerate(panneau['placements']):
        rect = patches.Rectangle((x, y), l, L, edgecolor='black', facecolor='lightblue')
        ax.add_patch(rect)
        ax.text(x + l/2, y + L/2, f"{i+1}", ha='center', va='center', fontsize=7)
    col.pyplot(fig)

# Statistiques
st.subheader("Statistiques")
total_piece_area = sum(l * L for l, L, _, _ in st.session_state.pieces)
total_panel_area = len(panneaux) * panel_length * panel_width
perte = total_panel_area - total_piece_area
perte_pct = 100 * perte / total_panel_area if total_panel_area else 0
st.markdown(f"**Utilisation :** {100 - perte_pct:.2f}%")
st.markdown(f"**Perte :** {perte_pct:.2f}%")

# Poids et volume par matériau
stats = {}
for l, L, e, mat in st.session_state.pieces:
    volume = l * L * (e / 1000)
    stats.setdefault(mat, 0)
    stats[mat] += volume

for mat, vol in stats.items():
    poids = vol * MATERIAL_DENSITIES.get(mat, 0)
    st.markdown(f"**{mat}** - Volume: {vol:.3f} m³ | Poids estimé: {poids:.1f} kg")
