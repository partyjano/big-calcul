import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- CONSTANTES ---
MATERIAL_DENSITIES = {
    "Bois": 600,      # kg/m3
    "Métal": 7850     # kg/m3
}

# --- FONCTIONS UTILITAIRES ---

def parse_metal_section(section_str):
    try:
        parts = section_str.lower().replace('mm','').split('x')
        if len(parts) != 3:
            raise ValueError
        w, h, e = map(float, parts)
        return w, h, e
    except:
        st.error("Format section métal incorrect, utiliser LxHxépaisseur en mm, ex: 40x40x2")
        return None

def convert_mm_to_m(value_mm):
    return value_mm / 1000

def volume_m3(l_mm, L_mm, e_mm):
    return convert_mm_to_m(l_mm) * convert_mm_to_m(L_mm) * convert_mm_to_m(e_mm)

# --- PLACEMENT 3D ---

def try_place_piece(espace, l, L):
    best = None
    for i, (x, y, w, h) in enumerate(espace):
        for rl, rL, rot in [(l, L, False), (L, l, True)]:
            if rl <= w and rL <= h:
                reste = (w - rl) * h + (h - rL) * w
                if best is None or reste < best[0]:
                    best = (reste, i, x, y, rl, rL, rot)
    return best

def place_pieces_3d(pieces, panel_length, panel_width, panel_thickness):
    panneaux = []
    for l, L, e, mat in sorted(pieces, key=lambda x: max(x[0], x[1]), reverse=True):
        placed = False
        for panneau in panneaux:
            for couche in panneau['couches']:
                if couche['hauteur_cumulee'] + e <= panel_thickness:
                    idx = try_place_piece(couche['espace'], l, L)
                    if idx:
                        _, i, x, y, rl, rL, rot = idx
                        del couche['espace'][i]
                        couche['placements'].append((x, y, rl, rL, rot, couche['hauteur_cumulee']))
                        couche['espace'].append((x + rl, y, panel_length - (x + rl), rL))
                        couche['espace'].append((x, y + rL, rl, panel_width - (y + rL)))
                        placed = True
                        break
            if placed:
                break
        if not placed:
            if not panneaux or (sum(c['hauteur_cumulee'] + c['max_epaisseur'] for c in panneaux[-1]['couches']) + e > panel_thickness):
                panneau = {'couches': []}
                panneaux.append(panneau)
            else:
                panneau = panneaux[-1]

            hauteur_cumulee = 0
            for c in panneau['couches']:
                hauteur_cumulee += c['max_epaisseur']

            nouvelle_couche = {
                'hauteur_cumulee': hauteur_cumulee,
                'max_epaisseur': e,
                'espace': [(0, 0, panel_length, panel_width)],
                'placements': []
            }
            idx = try_place_piece(nouvelle_couche['espace'], l, L)
            if idx:
                _, i, x, y, rl, rL, rot = idx
                del nouvelle_couche['espace'][i]
                nouvelle_couche['placements'].append((x, y, rl, rL, rot, hauteur_cumulee))
                nouvelle_couche['espace'].append((x + rl, y, panel_length - (x + rl), rL))
                nouvelle_couche['espace'].append((x, y + rL, rl, panel_width - (y + rL)))
                panneau['couches'].append(nouvelle_couche)
                placed = True

            if not placed:
                st.error("Pièce trop grande pour panneau/barre")

    return panneaux

# --- UI ---

st.set_page_config(page_title="Optimisation 3D de découpe", layout="wide")
st.title("Optimisation 3D de découpe bois et métal")

with st.sidebar:
    mat_principal = st.selectbox("Matériau principal", options=["Bois", "Métal"])

    if mat_principal == "Bois":
        default_length = 2440
        default_width = 1220
        default_thickness = 18
    else:
        default_length = 6000
        default_width = 50  # largeur fixe pour barre métal
        default_thickness = 2

    panel_length = st.number_input("Longueur panneau/barre (mm)", value=default_length, min_value=1)
    panel_width = st.number_input("Largeur panneau (mm)", value=default_width, min_value=1, disabled=(mat_principal=="Métal"))

    with st.expander("Options avancées (épaisseur & empilement)"):
        panel_thickness = st.number_input("Épaisseur totale panneau/barre (mm)", value=default_thickness, min_value=1)

st.header("Ajouter une pièce à découper")
pieces = st.session_state.get("pieces", [])

longueur_piece = st.number_input("Longueur pièce (mm)", min_value=1, value=200)
largeur_piece = st.number_input("Largeur pièce (mm)", min_value=1, value=100)
epaisseur_piece = st.number_input("Épaisseur pièce (mm)", min_value=1, value=18)
matiere_piece = st.selectbox("Matériau pièce", options=["Bois", "Métal"])

if matiere_piece == "Métal":
    section = st.text_input("Section métal (LxHxépaisseur mm, ex: 40x40x2)", value="40x40x2")
    sec = parse_metal_section(section)
    if sec:
        largeur_piece, hauteur_piece, epaisseur_piece = sec

quantite_piece = st.number_input("Quantité", min_value=1, value=1)

if st.button("Ajouter la pièce"):
    for _ in range(quantite_piece):
        pieces.append((longueur_piece, largeur_piece, epaisseur_piece, matiere_piece))
    st.session_state.pieces = pieces

if not pieces:
    st.info("Ajoutez des pièces pour commencer.")
    st.stop()

# Utiliser épaisseur panneau sélectionnée (sinon default)
try:
    panel_thickness
except NameError:
    panel_thickness = default_thickness

panneaux = place_pieces_3d(pieces, panel_length, panel_width if mat_principal=="Bois" else 50, panel_thickness)

st.header("Visualisation des couches")
for p_idx, panneau in enumerate(panneaux):
    st.subheader(f"Panneau #{p_idx+1}")
    couche_idx = st.slider(f"Choisir la couche à afficher (panneau #{p_idx+1})", 0, len(panneau['couches'])-1, 0)
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

st.header("Statistiques")

total_piece_volume = sum(volume_m3(l, L, e) for l, L, e, _ in pieces)
total_panel_volume = 0
for panneau in panneaux:
    if mat_principal=="Bois":
        vol = convert_mm_to_m(panel_length) * convert_mm_to_m(panel_width) * convert_mm_to_m(panel_thickness)
    else:
        vol = convert_mm_to_m(panel_length) * convert_mm_to_m(panel_thickness) * convert_mm_to_m(50)
    total_panel_volume += vol

perte_vol = total_panel_volume - total_piece_volume
perte_pct = 100 * perte_vol / total_panel_volume if total_panel_volume > 0 else 0

st.markdown(f"**Volume total pièces:** {total_piece_volume:.4f} m³")
st.markdown(f"**Volume total panneaux/barres:** {total_panel_volume:.4f} m³")
st.markdown(f"**Perte en volume:** {perte_vol:.4f} m³ ({perte_pct:.2f}%)")

stats = {}
for l, L, e, mat in pieces:
    vol = volume_m3(l, L, e)
    stats.setdefault(mat, 0)
    stats[mat] += vol

for mat, vol in stats.items():
    poids = vol * MATERIAL_DENSITIES.get(mat, 0)
    st.markdown(f"**{mat}** - Volume: {vol:.4f} m³ | Poids estimé: {poids:.1f} kg")
