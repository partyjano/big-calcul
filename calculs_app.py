import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from io import BytesIO
from fpdf import FPDF
import base64

# === CONFIGURATION ===
DEFAULTS = {
    "Bois": {"longueur": 2440, "largeur": 1220},
    "Métal": {"longueur": 6000, "largeur": 0}
}
MATERIAL_DENSITIES = {"Bois": 600, "Métal": 7850}  # en kg/m³

st.set_page_config(page_title="Optimisation découpe", layout="wide")

# === LOGO ===
st.image("https://raw.githubusercontent.com/ton-repo/logo/main/logo.gif", width=150)

st.title("Optimisation de découpe multi-matériaux")

# === Initialisation session state ===
if "panneaux" not in st.session_state:
    st.session_state.panneaux = {}
    st.session_state.panneau_actif = None

# === Sélection ou création panneau ===
st.sidebar.header("🔧 Gestion des panneaux")
nom_panneau = st.sidebar.text_input("Nom du panneau", value="Panneau 1")
if st.sidebar.button("Créer/Activer"):
    if nom_panneau not in st.session_state.panneaux:
        st.session_state.panneaux[nom_panneau] = {
            "mat": "Bois",
            "longueur": DEFAULTS["Bois"]["longueur"],
            "largeur": DEFAULTS["Bois"]["largeur"],
            "pieces": [],
            "ep_lame": 3
        }
    st.session_state.panneau_actif = nom_panneau

# Liste panneaux
for nom in st.session_state.panneaux:
    if st.sidebar.button(f"🧱 {nom}"):
        st.session_state.panneau_actif = nom

if st.session_state.panneau_actif is None:
    st.warning("Créez un panneau pour commencer.")
    st.stop()

panneau = st.session_state.panneaux[st.session_state.panneau_actif]
st.sidebar.markdown(f"**Actif:** `{st.session_state.panneau_actif}`")

# === Paramètres panneau ===
st.sidebar.divider()
st.sidebar.subheader("Paramètres panneau")
mat = st.sidebar.selectbox("Matériau", ["Bois", "Métal"], index=["Bois", "Métal"].index(panneau["mat"]))
longueur = st.sidebar.number_input("Longueur (mm)", value=panneau["longueur"], step=10)
largeur = st.sidebar.number_input("Largeur (mm)", value=panneau["largeur"], step=10, disabled=(mat == "Métal"))
ep_lame = st.sidebar.number_input("Épaisseur de lame (mm)", value=panneau["ep_lame"], step=1)
panneau.update({"mat": mat, "longueur": longueur, "largeur": largeur, "ep_lame": ep_lame})

# === Ajout pièce ===
st.sidebar.divider()
st.sidebar.subheader("Ajouter une pièce")
l = st.sidebar.number_input("Longueur pièce (mm)", min_value=10)
L = st.sidebar.number_input("Largeur pièce (mm)", min_value=0, value=100 if mat == "Bois" else 0, disabled=(mat == "Métal"))
ep = st.sidebar.number_input("Épaisseur (mm)", min_value=1.0, value=18.0)
profil = st.sidebar.text_input("Profil métal (ex: 40x40x2)", disabled=(mat != "Métal"))
qte = st.sidebar.number_input("Quantité", value=1, min_value=1, step=1)

if st.sidebar.button("Ajouter pièce"):
    for _ in range(qte):
        panneau["pieces"].append((l, L, ep, profil))

if not panneau["pieces"]:
    st.info("Ajoutez des pièces pour voir la découpe.")
    st.stop()

# === Découpe ===

# Découpe métal (1D)
def decoupe_barres(pieces, longueur_barre, ep_lame):
    barres = []
    for l, *_ in sorted(pieces, reverse=True):
        place = False
        for barre in barres:
            if sum(barre) + l + ep_lame <= longueur_barre:
                barre.append(l + ep_lame)
                place = True
                break
        if not place:
            barres.append([l + ep_lame])
    return barres

# Découpe bois (2D)
def try_place(espace, l, L):
    for i, (x, y, w, h) in enumerate(espace):
        if l <= w and L <= h:
            return i, x, y
    return None

def place_2D(pieces, W, H, ep_lame):
    panneaux = []
    for l, L, *_ in sorted(pieces, key=lambda x: max(x[0], x[1]), reverse=True):
        placed = False
        for panneau in panneaux:
            espace = panneau["espace"]
            idx = try_place(espace, l, L)
            if idx:
                i, x, y = idx
                panneau["placements"].append((x, y, l, L))
                del espace[i]
                espace.append((x + l + ep_lame, y, W - (x + l + ep_lame), L))
                espace.append((x, y + L + ep_lame, l, H - (y + L + ep_lame)))
                placed = True
                break
        if not placed:
            new = {"espace": [(0, 0, W, H)], "placements": []}
            idx = try_place(new["espace"], l, L)
            if idx:
                i, x, y = idx
                new["placements"].append((x, y, l, L))
                new["espace"] = [
                    (x + l + ep_lame, y, W - (x + l + ep_lame), L),
                    (x, y + L + ep_lame, l, H - (y + L + ep_lame))
                ]
                panneaux.append(new)
    return panneaux

# === Affichage graphique ===
st.subheader("Aperçu découpes")
if panneau["mat"] == "Bois":
    results = place_2D([(l, L, ep, p) for l, L, ep, p in panneau["pieces"]], panneau["longueur"], panneau["largeur"], panneau["ep_lame"])
    for idx, pan in enumerate(results):
        fig, ax = plt.subplots()
        ax.set_xlim(0, panneau["longueur"])
        ax.set_ylim(0, panneau["largeur"])
        ax.set_aspect('equal')
        ax.invert_yaxis()
        ax.set_title(f"Panneau #{idx+1}")
        for i, (x, y, l, L) in enumerate(pan["placements"]):
            rect = patches.Rectangle((x, y), l, L, edgecolor='black', facecolor='skyblue')
            ax.add_patch(rect)
            ax.text(x + l/2, y + L/2, f"{i+1}", ha='center', va='center', fontsize=8)
        st.pyplot(fig)
else:
    barres = decoupe_barres([(l, 0, ep, p) for l, _, ep, p in panneau["pieces"]], panneau["longueur"], panneau["ep_lame"])
    for i, barre in enumerate(barres):
        fig, ax = plt.subplots(figsize=(8, 1))
        pos = 0
        for j, l in enumerate(barre):
            ax.add_patch(patches.Rectangle((pos, 0), l - panneau["ep_lame"], 10, edgecolor='black', facecolor='lightcoral'))
            ax.text(pos + (l - panneau["ep_lame"]) / 2, 5, f"{j+1}", ha='center', va='center')
            pos += l
        ax.set_xlim(0, panneau["longueur"])
        ax.axis('off')
        st.pyplot(fig)

# === Statistiques ===
st.subheader("Statistiques")
total_volume = 0
for l, L, e, _ in panneau["pieces"]:
    v = l * (L if panneau["mat"] == "Bois" else 1) * e / 1_000_000  # mm³ → m³
    total_volume += v
poids = total_volume * MATERIAL_DENSITIES[panneau["mat"]]
st.markdown(f"**Volume total :** {total_volume:.3f} m³")
st.markdown(f"**Poids estimé :** {poids:.1f} kg")
