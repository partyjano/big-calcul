import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

DEFAULT_PANEL_LENGTH = 2440  # en mm
DEFAULT_PANEL_WIDTH = 1220   # en mm
DEFAULT_METAL_LENGTH = 6000  # en mm

MATERIAL_DENSITIES = {
    "Bois": 600,    # kg/m³
    "Métal": 7850
}

st.set_page_config(page_title="Optimisation de découpe", layout="wide")

st.title("Optimisation de découpe de panneaux bois et métaux")

with st.sidebar:
    mat_principal = st.selectbox("Choisir le matériau principal", options=["Bois", "Métal"])

    if mat_principal == "Bois":
        panel_length = st.number_input("Longueur panneau (mm)", value=DEFAULT_PANEL_LENGTH, min_value=10)
        panel_width = st.number_input("Largeur panneau (mm)", value=DEFAULT_PANEL_WIDTH, min_value=10)
        panel_thickness = st.number_input("Épaisseur panneau (mm)", value=18.0, min_value=1.0)

    else:
        bar_length = st.number_input("Longueur barre métal (mm)", value=DEFAULT_METAL_LENGTH, min_value=10)
        ref_bar = st.text_input("Référence barre (ex: 40x40x2mm)", value="40x40x2mm")

    with st.expander("Options avancées"):
        kerf = st.number_input("Épaisseur de la lame (découpe) en mm", value=3.0, min_value=0.1, max_value=10.0, step=0.1)
        # Ici on pourrait ajouter d'autres options avancées 3D si besoin

    st.header("Ajouter une pièce")
    longueur = st.number_input("Longueur pièce (mm)", min_value=1, value=200)
    largeur = st.number_input("Largeur pièce (mm)", min_value=1, value=100)
    epaisseur = st.number_input("Épaisseur pièce (mm)", min_value=1.0, value=18.0)
    matiere = st.selectbox("Matériau pièce", options=list(MATERIAL_DENSITIES.keys()))
    quantite = st.number_input("Quantité", min_value=1, value=1, step=1)

    if "pieces" not in st.session_state:
        st.session_state.pieces = []

    if st.button("Ajouter la pièce"):
        for _ in range(quantite):
            st.session_state.pieces.append((longueur, largeur, epaisseur, matiere))

if not st.session_state.pieces:
    st.info("Ajoutez des pièces pour commencer.")
    st.stop()

# Conversion en mètre pour calculs de poids
def mm_to_m(x): return x / 1000

pieces = [(l, L, e, m) for l, L, e, m in st.session_state.pieces]

# Algorithme simplifié de placement (sans kerf ni nesting complexe ici)
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
    for l, L, _, _ in sorted(pieces, key=lambda x: max(x[0], x[1]), reverse=True):
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

# Ajout d'une clé 'couches' vide pour chaque panneau (exemple placeholder)
for panneau in panneaux:
    panneau['couches'] = [{'placements': [(x, y, l, L, rot, 0) for (x, y, l, L, rot) in panneau['placements']], 'hauteur_cumulee': 0}]

# Affichage graphique avec gestion sécurisée du slider
for p_idx, panneau in enumerate(panneaux):
    st.subheader(f"Panneau #{p_idx+1}")
    if len(panneau['couches']) == 0:
        st.warning("Aucune couche disponible pour ce panneau.")
        continue

    couche_idx = st.slider(
        f"Choisir la couche à afficher (panneau #{p_idx+1})",
        0, len(panneau['couches']) - 1, 0
    )
    couche = panneau['couches'][couche_idx]

    fig, ax = plt.subplots()
    ax.set_title(f"Panneau #{p_idx+1} - Couche {couche_idx+1} (Hauteur cumulée: {couche['hauteur_cumulee']} mm)")
    ax.set_xlim(0, panel_length)
    ax.set_ylim(0, panel_width if mat_principal=="Bois" else 50)
    ax.set_aspect('equal')
    ax.invert_yaxis()

    for i, (x, y, l, L, rot, z) in enumerate(couche['placements']):
        rect = patches.Rectangle((x, y), l, L, edgecolor='black', facecolor='lightblue')
        ax.add_patch(rect)
        ax.text(x + l/2, y + L/2, f"{i+1}", ha='center', va='center', fontsize=7)

    st.pyplot(fig)

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
    volume = mm_to_m(l) * mm_to_m(L) * mm_to_m(e)
    stats.setdefault(mat, 0)
    stats[mat] += volume

for mat, vol in stats.items():
    poids = vol * MATERIAL_DENSITIES.get(mat, 0)
    st.markdown(f"**{mat}** - Volume: {vol:.4f} m³ | Poids estimé: {poids:.1f} kg")
