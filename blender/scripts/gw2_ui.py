# plantRTS — Éléments d'interface extraits des atlas de Garden Warfare 2 fournis dans
# blender/addon GW2/ (usage personnel uniquement, voir CLAUDE.md : ne pas diffuser).
# Les fichiers produits vont dans assets/gw2/ui/ (ignoré par Git) ; le HUD les utilise
# s'ils existent (HudSkin, SquadData.local_portrait_path), sinon des styles simples.
# Les atlas originaux ne sont pas modifiés.
#
# Exécution : blender -b --python blender/scripts/gw2_ui.py
#
# - Cadre des panneaux et des emplacements : barre sombre bordée de pierre de
#   HUDTextureMappingWin32 (texte clair lisible dessus), en 9 tranches.
# - Portraits des troupes : cases de 164 px de CharacterIconsWin32 (grille 12 × 11),
#   repérées à la main ; l'Imp, le Z-Mech, le Citron et le Zombie classique n'y ont pas de
#   portrait par défaut identifiable (vignette de repli du HUD).

import os
import bpy
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "blender", "addon GW2", "UI-20261009T102552Z-1-001", "UI")
OUT = os.path.join(ROOT, "assets", "gw2", "ui")

# Atlas, rectangle (x0, y0, x1, y1 en pixels, origine en haut à gauche), fichiers.
FRAMES = {
    "UI/HUDTextureMappingWin32.png": [((283, 808, 576, 861), ("panel_stone.png", "slot_stone.png"))],
}
ICON_ATLAS = "Texture Mappings/CharacterIconsWin32.png"
ICON_CELL = 164
ICON_INSET = 3
# id de troupe → (rangée, colonne) dans CharacterIconsWin32.
PORTRAITS = {
    "engineer": (4, 0), "kernel_corn": (7, 1), "peashooter": (7, 9), "sunflower": (10, 0),
    "cactus": (6, 4), "chomper": (8, 1), "rose": (9, 6), "torchwood": (8, 7),
    "foot_soldier": (9, 2), "scientist": (8, 2), "deadbeard": (2, 5), "all_star": (5, 3),
    "super_brainz": (9, 5), "action_hero_80s": (4, 8),
}


def load(rel):
    image = bpy.data.images.load(os.path.join(SRC, rel))
    w, h = image.size
    return np.array(image.pixels[:], np.float32).reshape(h, w, 4)[::-1]


def save(pixels, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    h, w = pixels.shape[:2]
    image = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    image.pixels = pixels[::-1].ravel()
    image.filepath_raw = path
    image.file_format = 'PNG'
    image.save()
    print("écrit", os.path.relpath(path, ROOT))


def main():
    for rel, crops in FRAMES.items():
        atlas = load(rel)
        for (x0, y0, x1, y1), names in crops:
            for name in names:
                save(atlas[y0:y1, x0:x1].copy(), os.path.join(OUT, name))
    icons = load(ICON_ATLAS)
    for unit_id, (row, col) in PORTRAITS.items():
        y0, x0 = row * ICON_CELL + ICON_INSET, col * ICON_CELL + ICON_INSET
        size = ICON_CELL - 2 * ICON_INSET
        save(icons[y0:y0 + size, x0:x0 + size].copy(), os.path.join(OUT, "portraits", unit_id + ".png"))


main()
