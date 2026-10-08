# plantRTS — Kit d'environnement : petit décor (lot 7), côté jardins et côté cimetière.
# blender -b --python blender/scripts/environment/props.py -- [ids…] [--render]
#
# Accessoires sans rôle de couvert majeur. Couleurs vives tirées de l'atlas de
# peintures (Env_Paint:<couleur>) : lisibles mais en petites surfaces, pour ne pas
# concurrencer les unités. Avant vers -Y.

import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from env_lib import *  # noqa: F401,F403
import bmesh
from mathutils import Vector, Matrix, Quaternion


def _rig(model):
    rig = Rig(model, start(model))
    return rig, rig.part("Prop", (0, 0, 0))


def _done(rig, footprint=(2.0, 2.0), budget="small", smooth=45.0):
    finish(rig, smooth_angle=smooth)
    return {"category": "props", "budget": budget, "footprint": footprint}


def P(rig, color):
    return rig.m("Env_Paint:" + color)


# ---------------------------------------------------------------- Côté jardins

def mailbox():
    """Boîte aux lettres américaine sur poteau, drapeau rouge levé."""
    rig, bm = _rig("mailbox")
    METAL, WOOD, RED = rig.m("Env_Metal"), rig.m("Env_Trim:wood"), P(rig, "red")
    box(bm, (0, 0, 0.55), (0.1, 0.1, 1.1), WOOD)
    box(bm, (0, 0, 1.12), (0.22, 0.5, 0.06), WOOD)
    box(bm, (0, 0, 1.24), (0.22, 0.48, 0.18), METAL)
    cyl(bm, (0, -0.24, 1.33), (0, 0.24, 1.33), 0.11, 0.11, METAL, seg=10)
    box(bm, (0.12, 0.05, 1.42), (0.02, 0.04, 0.28), RED)
    box(bm, (0.12, 0.11, 1.53), (0.02, 0.14, 0.08), RED)
    return _done(rig)


def street_lamp():
    """Réverbère en fonte : socle, fût cannelé, crosse, lanterne à verre chaud. 4,4 m."""
    rig, bm = _rig("street_lamp")
    IRON, GLASS = rig.m("Env_Iron"), P(rig, "yellow")
    lathe(bm, [(0.26, 0.0), (0.26, 0.15), (0.16, 0.3), (0.09, 0.5), (0.07, 3.6), (0.09, 3.7), (0.0, 3.75)], 8,
          Matrix.Identity(4), IRON, ridge=0.08)
    tube_path(bm, [(0, 0, 3.6), (0.05, 0, 4.05), (0.35, 0, 4.25), (0.65, 0, 4.15)], [0.05, 0.045, 0.04, 0.04], 5, IRON)
    lantern = Matrix.Translation((0.65, 0, 3.6))
    lathe(bm, [(0.0, 0.0), (0.1, 0.02), (0.16, 0.12), (0.18, 0.42), (0.0, 0.42)], 6, lantern, GLASS)
    lathe(bm, [(0.2, 0.42), (0.24, 0.48), (0.08, 0.6), (0.0, 0.62)], 6, lantern, IRON)
    return _done(rig, budget="medium")


def fire_hydrant():
    """Bouche d'incendie rouge à chapeau, bouchons latéraux."""
    rig, bm = _rig("fire_hydrant")
    RED, METAL = P(rig, "red"), rig.m("Env_Metal")
    lathe(bm, [(0.2, 0.0), (0.2, 0.06), (0.14, 0.1), (0.14, 0.55), (0.17, 0.58), (0.15, 0.68), (0.08, 0.76),
               (0.03, 0.82), (0.0, 0.82)], 8, Matrix.Identity(4), RED)
    for a in (0, 180):
        d = Quaternion((0, 0, 1), math.radians(a)) @ Vector((1, 0, 0))
        cyl(bm, d * 0.12 + Vector((0, 0, 0.42)), d * 0.24 + Vector((0, 0, 0.42)), 0.06, 0.06, METAL, seg=6)
    cyl(bm, (0, -0.12, 0.35), (0, -0.25, 0.35), 0.08, 0.08, METAL, seg=6)
    return _done(rig)


def garden_gnome():
    """Nain de jardin : bonnet rouge pointu, barbe blanche, veste bleue, bottes noires."""
    rig, bm = _rig("garden_gnome")
    RED, BLUE, WHITE, SKIN = P(rig, "red"), P(rig, "blue"), P(rig, "white"), P(rig, "orange")
    lathe(bm, [(0.0, 0.0), (0.16, 0.0), (0.17, 0.12), (0.15, 0.3), (0.1, 0.38), (0.0, 0.4)], 8, Matrix.Identity(4), BLUE)
    ellipsoid(bm, (0, -0.02, 0.45), (0.11, 0.1, 0.1), SKIN, u=8, v=5)
    ellipsoid(bm, (0, -0.08, 0.37), (0.1, 0.06, 0.1), WHITE, u=8, v=5)
    ellipsoid(bm, (0, -0.11, 0.45), (0.035, 0.03, 0.03), SKIN, u=6, v=4)
    lathe(bm, [(0.0, 0.5), (0.12, 0.5), (0.0, 0.78)], 8, Matrix.Translation((0, 0.02, 0)), RED)
    for s in (-1, 1):
        ellipsoid(bm, (s * 0.07, -0.08, 0.04), (0.05, 0.08, 0.04), P(rig, "black"), u=6, v=4)
    return _done(rig)


def lawn_flamingo():
    """Flamant rose de pelouse en plastique, sur deux pattes de fil de fer."""
    rig, bm = _rig("lawn_flamingo")
    PINK, BLACK, METAL = P(rig, "pink"), P(rig, "black"), rig.m("Env_Metal")
    ellipsoid(bm, (0, 0.05, 0.6), (0.11, 0.24, 0.12), PINK, u=10, v=6,
              rot=Quaternion((1, 0, 0), math.radians(-15)))
    tube_path(bm, [(0, -0.12, 0.66), (0, -0.2, 0.82), (0, -0.12, 0.95), (0, -0.16, 1.02)], [0.04, 0.035, 0.035, 0.04],
              5, PINK)
    ellipsoid(bm, (0, -0.19, 1.04), (0.045, 0.07, 0.045), PINK, u=6, v=4)
    cyl(bm, (0, -0.25, 1.04), (0, -0.32, 0.98), 0.02, 0.008, BLACK, seg=4)
    for s in (-1, 1):
        cyl(bm, (s * 0.04, 0.05, 0.5), (s * 0.04, 0.05, 0.0), 0.008, 0.008, METAL, seg=4)
    return _done(rig)


def lawn_mower():
    """Tondeuse à gazon rouge : carter, moteur, roues, guidon et bac de ramassage."""
    rig, bm = _rig("lawn_mower")
    RED, BLACK, METAL, RUBBER = P(rig, "red"), P(rig, "black"), rig.m("Env_Metal"), rig.m("Env_Rubber")
    box(bm, (0, 0, 0.2), (0.55, 0.6, 0.16), RED, bevel=0.06)
    lathe(bm, [(0.16, 0.28), (0.15, 0.42), (0.1, 0.48), (0.0, 0.5)], 8, Matrix.Translation((0, -0.05, 0)), BLACK)
    for x in (-0.3, 0.3):
        for y in (-0.25, 0.25):
            cyl(bm, (x, y, 0.1), (x + math.copysign(0.05, x), y, 0.1), 0.1, 0.1, RUBBER, seg=8)
    for s in (-1, 1):
        cyl(bm, (s * 0.22, 0.3, 0.25), (s * 0.22, 0.85, 0.95), 0.018, 0.018, METAL, seg=4)
    cyl(bm, (-0.22, 0.85, 0.95), (0.22, 0.85, 0.95), 0.025, 0.025, BLACK, seg=5)
    box(bm, (0, 0.5, 0.3), (0.45, 0.35, 0.3), BLACK, bevel=0.05)
    return _done(rig, budget="medium")


def traffic_cone():
    """Plot de chantier orange à bandes blanches, base carrée."""
    rig, bm = _rig("traffic_cone")
    ORANGE, WHITE = P(rig, "orange"), P(rig, "white")
    box(bm, (0, 0, 0.02), (0.42, 0.42, 0.04), ORANGE)
    lathe(bm, [(0.16, 0.04), (0.14, 0.24), (0.113, 0.24), (0.1, 0.38), (0.083, 0.38), (0.045, 0.7), (0.0, 0.72)], 10,
          Matrix.Identity(4), [ORANGE, ORANGE, WHITE, ORANGE, WHITE, ORANGE])
    return _done(rig)


def bucket():
    """Seau en métal galvanisé à anse, posé de travers."""
    rig, bm = _rig("bucket")
    METAL, BLUE = rig.m("Env_Metal"), P(rig, "blue")
    lathe(bm, [(0.0, 0.0), (0.14, 0.0), (0.18, 0.32), (0.16, 0.32), (0.12, 0.03), (0.0, 0.03)], 10,
          Matrix.Identity(4), METAL)
    lathe(bm, [(0.179, 0.08), (0.183, 0.11), (0.18, 0.14)], 10, Matrix.Identity(4), BLUE)
    arc = [(0.18 * math.cos(math.radians(a)), 0.0, 0.32 + 0.16 * math.sin(math.radians(a))) for a in range(0, 181, 30)]
    tube_path(bm, arc, [0.008] * len(arc), 4, METAL)
    return _done(rig)


def road_sign():
    """Panneau STOP octogonal sur poteau métallique."""
    rig, bm = _rig("road_sign")
    METAL, RED, WHITE = rig.m("Env_Metal"), P(rig, "red"), P(rig, "white")
    cyl(bm, (0, 0.05, 0.0), (0, 0.05, 2.1), 0.04, 0.04, METAL, seg=6)
    oct_pts = [(0.36 * math.cos(math.radians(22.5 + 45 * k)), 2.2 + 0.36 * math.sin(math.radians(22.5 + 45 * k)))
               for k in range(8)]
    prism(bm, oct_pts, 0.03, Matrix.Identity(4), RED)
    border = [(0.33 * math.cos(math.radians(22.5 + 45 * k)), 2.2 + 0.33 * math.sin(math.radians(22.5 + 45 * k)))
              for k in range(8)]
    prism(bm, border, 0.005, Matrix.Translation((0, -0.018, 0)), WHITE)
    prism(bm, [(x * 0.9, 2.2 + (z - 2.2) * 0.9) for x, z in border], 0.005, Matrix.Translation((0, -0.022, 0)), RED)
    text_mesh(bm, "STOP", Matrix.Translation((0, -0.03, 2.2)), 0.2, 0.01, WHITE)
    return _done(rig, budget="medium")


def garden_bench():
    """Banc de jardin : lattes de bois, piètement et accoudoirs en fonte."""
    rig, bm = _rig("garden_bench")
    WOOD, IRON = rig.m("Env_Trim:wood"), rig.m("Env_Iron")
    for k in range(4):                                       # assise
        box(bm, (0, -0.2 + k * 0.13, 0.45), (1.7, 0.1, 0.04), WOOD)
    for k in range(3):                                       # dossier incliné
        slab(bm, (0, 0.27 + k * 0.03, 0.62 + k * 0.15), (1.7, 0.04, 0.11), WOOD, pitch=-12)
    for x in (-0.75, 0.75):
        box(bm, (x, -0.2, 0.22), (0.05, 0.05, 0.44), IRON)
        box(bm, (x, 0.27, 0.45), (0.05, 0.05, 0.9), IRON, rot=Quaternion((1, 0, 0), math.radians(-12)))
        box(bm, (x, 0.0, 0.43), (0.06, 0.56, 0.04), IRON)
        tube_path(bm, [(x, -0.24, 0.45), (x, -0.2, 0.68), (x, 0.0, 0.7), (x, 0.25, 0.68)], [0.025] * 4, 4, IRON)
    return _done(rig, budget="medium")


def picnic_table():
    """Table de pique-nique en bois, bancs solidaires, pieds en X ; nappe à carreaux."""
    rig, bm = _rig("picnic_table")
    WOOD, RED, WHITE = rig.m("Env_Trim:wood"), P(rig, "red"), P(rig, "white")
    for k in range(5):                                       # plateau
        box(bm, (0, -0.32 + k * 0.16, 0.75), (1.8, 0.14, 0.05), WOOD)
    for s in (-1, 1):                                        # bancs
        for k in range(2):
            box(bm, (0, s * (0.62 + k * 0.13), 0.45), (1.8, 0.12, 0.05), WOOD)
    for x in (-0.65, 0.65):
        for s in (-1, 1):
            a, b = Vector((x, s * 0.75, 0.0)), Vector((x, -s * 0.1, 0.73))
            box(bm, (a + b) / 2, (0.08, 0.08, (b - a).length), WOOD, rot=align_z(b - a))
        box(bm, (x, 0, 0.42), (0.08, 1.6, 0.06), WOOD)
    for i in range(4):                                       # nappe à carreaux
        for j in range(3):
            box(bm, (-0.45 + i * 0.3, -0.3 + j * 0.3, 0.78), (0.3, 0.3, 0.01), RED if (i + j) % 2 else WHITE)
    return _done(rig, budget="medium")


def bbq_grill():
    """Barbecue boule noir : cuve, couvercle entrouvert, trois pieds, roues, grille."""
    rig, bm = _rig("bbq_grill")
    BLACK, METAL, RUBBER = P(rig, "black"), rig.m("Env_Metal"), rig.m("Env_Rubber")
    bowl = Matrix.Translation((0, 0, 0.62))
    lathe(bm, [(0.0, -0.3), (0.2, -0.27), (0.3, -0.12), (0.32, 0.0), (0.0, 0.0)], 10, bowl, BLACK)
    lid = Matrix.Translation((0, 0.3, 0.64)) @ Matrix.Rotation(math.radians(-55), 4, 'X') @ Matrix.Translation((0, -0.3, 0))
    lathe(bm, [(0.32, 0.0), (0.3, 0.1), (0.2, 0.24), (0.0, 0.27)], 10, lid, BLACK)
    box(bm, (0, 0, 0.6), (0.56, 0.56, 0.01), METAL)
    for k in range(3):
        a = math.radians(90 + 120 * k)
        d = Vector((math.cos(a), math.sin(a), 0))
        cyl(bm, d * 0.18 + Vector((0, 0, 0.4)), d * 0.32 + Vector((0, 0, 0.0)), 0.02, 0.02, METAL, seg=4)
    for s in (-1, 1):
        cyl(bm, (s * 0.3 - 0.03, 0.15, 0.06), (s * 0.3 + 0.03, 0.15, 0.06), 0.07, 0.07, RUBBER, seg=8)
    return _done(rig, budget="medium")


def bird_bath():
    """Bain d'oiseaux en pierre : pied tourné, vasque d'eau, petit oiseau bleu."""
    rig, bm = _rig("bird_bath")
    STONE, WATER, BLUE, YELLOW = rig.m("Env_Rock"), rig.m("Env_Water"), P(rig, "blue"), P(rig, "yellow")
    lathe(bm, [(0.25, 0.0), (0.25, 0.08), (0.12, 0.15), (0.08, 0.3), (0.1, 0.55), (0.07, 0.75), (0.12, 0.85),
               (0.45, 0.92), (0.48, 1.0), (0.42, 1.0), (0.0, 0.95)], 12, Matrix.Identity(4), STONE)
    lathe(bm, [(0.0, 0.97), (0.42, 0.97)], 12, Matrix.Identity(4), WATER)
    ellipsoid(bm, (0.38, 0.1, 1.08), (0.05, 0.08, 0.05), BLUE, u=6, v=4)
    ellipsoid(bm, (0.38, 0.03, 1.12), (0.035, 0.035, 0.035), BLUE, u=6, v=4)
    cyl(bm, (0.38, 0.0, 1.12), (0.38, -0.04, 1.11), 0.012, 0.0, YELLOW, seg=4)
    return _done(rig, budget="medium")


def doghouse():
    """Niche en planches, toit de tuiles rouges, entrée en arche, gamelle et os."""
    rig, bm = _rig("doghouse")
    PLANK, ROOF, DARK, RED = rig.m("Env_WoodPlanks"), rig.m("Env_RoofTiles"), P(rig, "black"), P(rig, "red")
    hx, hy, h = 0.5, 0.6, 0.75
    box(bm, (0, 0, h / 2), (2 * hx, 2 * hy, h), PLANK)
    for y in (-hy, hy):
        prism(bm, [(-hx, h), (hx, h), (0, h + 0.45)], 0.04, Matrix.Translation((0, y, 0)), PLANK)
    for s in (-1, 1):
        slab(bm, (s * 0.3, 0, h + 0.24), (0.68, 2 * hy + 0.2, 0.05), ROOF, roll=s * 42)
    arch = [(-0.22, 0.0), (0.22, 0.0)] + [(0.22 * math.cos(math.radians(a)), 0.38 + 0.22 * math.sin(math.radians(a)))
                                          for a in range(0, 181, 30)]
    prism(bm, arch, 0.02, Matrix.Translation((0, -hy - 0.01, 0)), DARK)
    lathe(bm, [(0.0, 0.0), (0.12, 0.0), (0.14, 0.07), (0.11, 0.07), (0.0, 0.05)], 8,
          Matrix.Translation((0.45, -0.85, 0)), RED)
    return _done(rig, budget="medium")


def swing_set():
    """Portique de balançoire : cadre bleu en A, deux balançoires à chaînes. 4 × 2 m."""
    rig, bm = _rig("swing_set")
    BLUE, METAL, YELLOW, RED = P(rig, "blue"), rig.m("Env_Metal"), P(rig, "yellow"), P(rig, "red")
    top = 2.2
    cyl(bm, (-1.7, 0, top), (1.7, 0, top), 0.06, 0.06, BLUE, seg=6)
    for x in (-1.6, 1.6):
        for s in (-1, 1):
            cyl(bm, (x, 0, top), (x + math.copysign(0.15, x), s * 0.75, 0.0), 0.05, 0.05, BLUE, seg=6)
    for x, mi in ((-0.6, YELLOW), (0.6, RED)):
        for s in (-1, 1):
            cyl(bm, (x + s * 0.22, 0, top), (x + s * 0.22, 0, 0.5), 0.01, 0.01, METAL, seg=4)
        box(bm, (x, 0, 0.48), (0.5, 0.22, 0.04), mi, bevel=0.015)
    return _done(rig, (4.0, 2.0), budget="medium")


def pool():
    """Piscine enterrée : margelle en béton, eau, échelle chromée, bouée rose. 6 × 4 m."""
    rig, bm = _rig("pool")
    CONC, WATER, METAL, PINK = rig.m("Env_Concrete"), rig.m("Env_Water"), rig.m("Env_Metal"), P(rig, "pink")
    hx, hy, rim = 2.7, 1.7, 0.3
    for x0, y0, x1, y1 in ((-hx - rim, -hy - rim, hx + rim, -hy), (-hx - rim, hy, hx + rim, hy + rim),
                           (-hx - rim, -hy, -hx, hy), (hx, -hy, hx + rim, hy)):
        extrude_xy(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 0.0, 0.12, CONC)
    extrude_xy(bm, [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)], 0.0, 0.04, WATER)
    for s in (-1, 1):
        tube_path(bm, [(1.6 + s * 0.22, -hy - 0.15, 0.12), (1.6 + s * 0.22, -hy - 0.12, 0.65),
                       (1.6 + s * 0.22, -hy + 0.1, 0.7), (1.6 + s * 0.22, -hy + 0.2, 0.05)], [0.025] * 4, 5, METAL)
    lathe(bm, [(0.18, 0.05), (0.3, 0.0), (0.42, 0.05), (0.3, 0.12)], 12, Matrix.Translation((-1.0, 0.4, 0.03)), PINK)
    return _done(rig, (6.0, 4.0), budget="medium")


def garden_hose():
    """Dévidoir de tuyau d'arrosage vert, tuyau enroulé et déroulé au sol."""
    rig, bm = _rig("garden_hose")
    GREEN, BLACK, YELLOW = P(rig, "green"), P(rig, "black"), P(rig, "yellow")
    for s in (-1, 1):
        cyl(bm, (s * 0.2, 0, 0.3), (s * 0.22, 0, 0.3), 0.3, 0.3, BLACK, seg=10)
        cyl(bm, (s * 0.2, -0.15, 0.0), (s * 0.2, 0.0, 0.3), 0.025, 0.025, BLACK, seg=4)
    cyl(bm, (-0.2, 0, 0.3), (0.2, 0, 0.3), 0.2, 0.2, GREEN, seg=10)
    pts = [(0.0, -0.18, 0.12)] + [(0.3 * math.cos(a) + 0.2, -0.5 + 0.25 * math.sin(a), 0.03)
                                  for a in [k * 0.9 for k in range(7)]]
    tube_path(bm, pts, [0.025] * len(pts), 4, GREEN)
    cyl(bm, pts[-1], (pts[-1][0] + 0.1, pts[-1][1], 0.03), 0.03, 0.035, YELLOW, seg=5)
    return _done(rig)


# ---------------------------------------------------------------- Côté cimetière

def _tomb_rig(model):
    rig, bm = _rig(model)
    return rig, bm, rig.m("Env_TombStone"), rig.m("Env_CryptSlab"), rig.m("Env_Moss")


def tombstone_small_a():
    """Petite stèle arrondie, penchée."""
    rig, bm, STONE, SLAB, MOSS = _tomb_rig("tombstone_small_a")
    pts = [(-0.3, 0.0), (0.3, 0.0)] + [(0.3 * math.cos(math.radians(a)), 0.7 + 0.3 * math.sin(math.radians(a)))
                                       for a in range(0, 181, 30)]
    prism(bm, pts, 0.15, Matrix.Rotation(math.radians(-7), 4, 'X') @ Matrix.Rotation(math.radians(4), 4, 'Y'), STONE)
    box(bm, (0, -0.02, 0.05), (0.75, 0.32, 0.1), SLAB)
    return _done(rig)


def tombstone_small_b():
    """Croix de pierre sur petit socle."""
    rig, bm, STONE, SLAB, MOSS = _tomb_rig("tombstone_small_b")
    q = Quaternion((0, 1, 0), math.radians(-5))
    box(bm, (0, 0, 0.1), (0.5, 0.3, 0.2), SLAB)
    box(bm, (0, 0, 0.7), (0.14, 0.12, 1.05), STONE, rot=q, bevel=0.02)
    box(bm, (0.03, 0, 0.92), (0.55, 0.12, 0.14), STONE, rot=q, bevel=0.02)
    return _done(rig)


def tombstone_small_c():
    """Pierre tombale rectangulaire fendue en deux, morceau tombé dans l'herbe."""
    rig, bm, STONE, SLAB, MOSS = _tomb_rig("tombstone_small_c")
    slab(bm, (-0.1, 0, 0.35), (0.5, 0.14, 0.7), STONE, roll=-8, pitch=6, bevel=0.02)
    slab(bm, (0.35, -0.3, 0.07), (0.45, 0.4, 0.14), STONE, yaw=25, roll=80, bevel=0.02)
    blob(bm, (-0.15, 0.1, 0.0), (0.35, 0.25, 0.1), MOSS, subdiv=1, noise=0.3, seed=7, flatten_bottom=0.0)
    return _done(rig)


def open_grave():
    """Fosse ouverte : trou sombre bordé de terre, tas de déblais, pelle plantée,
    petite stèle. Emprise 2 × 4 m."""
    rig, bm = _rig("open_grave")
    DIRT, DARK, WOOD, STONE = rig.m("Env_GraveDirt"), P(rig, "black"), rig.m("Env_Trim:wood"), rig.m("Env_TombStone")
    hx, hy = 0.45, 0.95
    extrude_xy(bm, [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)], 0.0, 0.01, DARK)            # fond (illusion de trou)
    for x0, y0, x1, y1 in ((-0.8, -1.2, 0.8, -hy), (-0.8, hy, 0.8, 1.2), (-0.8, -hy, -hx, hy), (hx, -hy, 0.8, hy)):
        extrude_xy(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 0.0, 0.08, DIRT)
    for x0, y0, x1, y1 in ((-hx, -hy, hx, -hy + 0.02), (-hx, hy - 0.02, hx, hy), (-hx, -hy, -hx + 0.02, hy),
                           (hx - 0.02, -hy, hx, hy)):
        extrude_xy(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 0.0, 0.08, DIRT)
    blob(bm, (0.0, 1.5, 0.05), (0.75, 0.45, 0.4), DIRT, subdiv=2, noise=0.3, seed=11, flatten_bottom=-0.1)
    slab(bm, (0.25, 1.5, 0.75), (0.04, 0.04, 0.9), WOOD, roll=15)
    slab(bm, (0.36, 1.5, 0.22), (0.2, 0.03, 0.25), DARK, roll=15)
    slab(bm, (0.0, -1.55, 0.35), (0.6, 0.12, 0.7), STONE, pitch=8, bevel=0.03)
    return _done(rig, (2.0, 4.0), budget="medium")


def coffin():
    """Cercueil en bois sombre, couvercle de travers, poignées de laiton."""
    rig, bm = _rig("coffin")
    WOOD, GOLD, DARK = rig.m("Env_WoodDark"), P(rig, "yellow"), P(rig, "black")
    outline = [(-0.25, -0.95), (0.25, -0.95), (0.33, 0.45), (0.22, 0.95), (-0.22, 0.95), (-0.33, 0.45)]
    extrude_xy(bm, outline, 0.0, 0.42, WOOD)
    extrude_xy(bm, [(x * 0.82, y * 0.9) for x, y in outline], 0.4, 0.425, DARK)
    lid = Matrix.Translation((0.25, 0.02, 0.47)) @ Matrix.Rotation(math.radians(12), 4, 'Z') \
        @ Matrix.Rotation(math.radians(6), 4, 'Y')
    before = set(bm.verts)
    extrude_xy(bm, outline, 0.0, 0.08, WOOD)
    bmesh.ops.transform(bm, matrix=lid, verts=[v for v in bm.verts if v not in before])
    for y in (-0.5, 0.2):
        for s in (-1, 1):
            box(bm, (s * 0.33, y, 0.22), (0.04, 0.2, 0.05), GOLD)
    return _done(rig, budget="medium")


def bone_pile():
    """Tas d'os et crâne blanchis."""
    rig, bm = _rig("bone_pile")
    BONE, DARK = rig.m("Env_Bone"), P(rig, "black")
    rnd = random.Random(17)
    for i in range(6):
        c = Vector((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), 0.05 + 0.04 * (i % 3)))
        d = Quaternion((0, 0, 1), rnd.uniform(0, 6.28)) @ Vector((0.22, 0, 0.02))
        cyl(bm, c - d, c + d, 0.025, 0.025, BONE, seg=5)
        for e in (c - d, c + d):
            ellipsoid(bm, e, (0.04, 0.04, 0.035), BONE, u=4, v=3)
    ellipsoid(bm, (0.1, -0.15, 0.13), (0.12, 0.14, 0.12), BONE, u=8, v=6)
    for s in (-1, 1):
        ellipsoid(bm, (0.1 + s * 0.045, -0.27, 0.15), (0.03, 0.02, 0.035), DARK, u=5, v=3)
    return _done(rig, budget="medium")


BUILDERS = {f.__name__: f for f in (mailbox, street_lamp, fire_hydrant, garden_gnome, lawn_flamingo, lawn_mower,
                                    traffic_cone, bucket, road_sign, garden_bench, picnic_table, bbq_grill, bird_bath,
                                    doghouse, swing_set, pool, garden_hose, tombstone_small_a, tombstone_small_b,
                                    tombstone_small_c, open_grave, coffin, bone_pile)}

if __name__ == "__main__":
    run(BUILDERS)
