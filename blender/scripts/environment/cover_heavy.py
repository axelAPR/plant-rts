# plantRTS — Kit d'environnement : couvert lourd (murets, véhicules, tombes…).
# blender -b --python blender/scripts/environment/cover_heavy.py -- [ids…] [--render]

import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from env_lib import *  # noqa: F401,F403
import bmesh
from mathutils import Vector, Matrix, Quaternion


def _bevel_all(bm, faces, offset, segments, mi):
    """Arrondit toutes les arêtes d'un volume (aspect jouet, pas de cube visible)."""
    edges = list({e for f in faces for e in f.edges})
    res = bmesh.ops.bevel(bm, geom=edges, offset=offset, segments=segments, affect='EDGES',
                          profile=0.5, clamp_overlap=True)
    for f in res['faces']:
        f.material_index = mi


# ---------------------------------------------------------------- Voiture

def _car(model, paint="Env_CarPaint", wreck=False, seed=0):
    """Berline cartoon, trapue, le long de X (avant vers +X). Emprise 4 × 2 m.
    `wreck` : épave rouillée, vitres crevées, roue manquante, cabossée, affaissée."""
    col = start(model)
    rig = Rig(model, col)
    rnd = random.Random(seed)
    PAINT, RUBBER = rig.m("Env_RustyIron" if wreck else paint), rig.m("Env_Rubber")
    METAL = rig.m("Env_Iron" if wreck else "Env_Metal")
    GLASS = rig.m("Env_Iron") if wreck else rig.m("Env_Trim:glass")
    RED = METAL if wreck else rig.m("Env_Trim:red")
    WHITE = METAL if wreck else rig.m("Env_Trim:white")
    bm = rig.part("Car", (0, 0, 0))
    W = 1.78
    # Caisse : profil latéral extrudé sur la largeur, arêtes arrondies.
    body = [(-1.86, 0.32), (1.86, 0.32), (1.9, 0.5), (1.84, 0.78), (1.12, 0.9), (-1.17, 0.92),
            (-1.84, 0.86), (-1.9, 0.55)]
    faces = prism(bm, body, W, Matrix.Identity(4), PAINT)
    if wreck:
        jitter(list({v for f in faces for v in f.verts}), 0.04, seed=seed)       # tôle cabossée
    _bevel_all(bm, faces, 0.12, 2, PAINT)
    # Habitacle : vitres tout autour (crevées sur l'épave), pavillon peint par-dessus.
    cabin = [(-1.12, 0.86), (0.78, 0.86), (0.36, 1.38), (-0.86, 1.38)]
    faces = prism(bm, cabin, W - 0.22, Matrix.Identity(4), GLASS)
    _bevel_all(bm, faces, 0.07, 1, GLASS)
    box(bm, (-0.25, 0, 1.4 - (0.08 if wreck else 0)), (1.3, W - 0.18, 0.07), PAINT, bevel=0.03,
        rot=Quaternion((1, 0, 0), math.radians(6 if wreck else 0)))
    # Montants (pavillon → caisse) : la vitre se lit en panneaux.
    for x0, x1 in ((0.78, 0.36), (-1.12, -0.86), (-0.17, -0.2)):
        for s in (-1, 1):
            a, b = Vector((x0, s * (W - 0.2) / 2, 0.86)), Vector((x1, s * (W - 0.2) / 2, 1.38))
            box(bm, (a + b) / 2, (0.09, 0.05, (b - a).length), PAINT, rot=align_z(b - a), bevel=0.015)
    # Roues : pneu, enjoliveur (l'épave a perdu sa roue arrière droite).
    for x in (-1.25, 1.25):
        for s in (-1, 1):
            if wreck and x < 0 and s < 0:
                continue
            y = s * (W / 2 - 0.1)
            r = 0.3 if wreck else 0.36                  # pneus à plat
            cyl(bm, (x, y - s * 0.13, r), (x, y + s * 0.13, r), r, r, RUBBER, seg=10)
            cyl(bm, (x, y + s * 0.125, r), (x, y + s * 0.16, r), 0.2, 0.15, METAL, seg=8)
    # Pare-chocs (avant tombé au sol sur l'épave), phares, calandre, poignées.
    for x, sx in ((1.92, 1), (-1.92, -1)):
        if wreck and sx > 0:
            box(bm, (2.0 - 0.35, -0.2, 0.08), (0.13, W - 0.2, 0.16), METAL,
                rot=Quaternion((0, 0, 1), math.radians(18)), bevel=0.05)
        else:
            box(bm, (x, 0, 0.42), (0.13, W + 0.04, 0.16), METAL, bevel=0.05)
        for s in (-1, 1):
            cyl(bm, (x - sx * 0.08, s * 0.6, 0.66), (x + sx * 0.0, s * 0.6, 0.66), 0.11, 0.1,
                WHITE if sx > 0 else RED, seg=8)
        box(bm, (x + sx * 0.02, 0, 0.6), (0.04, 0.44, 0.14), WHITE)        # plaque
    box(bm, (1.88, 0, 0.6), (0.06, 0.56, 0.13), RUBBER, bevel=0.02)
    for x in (0.25, -0.65):
        for s in (-1, 1):
            box(bm, (x, s * (W / 2 + 0.005), 0.78), (0.18, 0.04, 0.045), METAL)
    # Passages de roue (joncs sombres), rétroviseurs, antenne.
    for x in (-1.25, 1.25):
        for s in (-1, 1):
            arc = [Vector((x + 0.45 * math.cos(math.radians(a)), s * (W / 2 + 0.01), 0.36 + 0.45 * math.sin(math.radians(a))))
                   for a in (5, 50, 90, 130, 175)]
            tube_path(bm, arc, [0.05] * 5, 4, RUBBER)
    for s in (-1, 1):
        if not (wreck and s > 0):
            box(bm, (0.66, s * (W / 2 + 0.03), 0.98), (0.12, 0.12, 0.1), PAINT, bevel=0.02)
    if not wreck:
        cyl(bm, (-1.55, 0.62, 0.88), (-1.62, 0.62, 1.55), 0.012, 0.008, METAL, seg=4)
    else:
        # Affaissée côté roue manquante : bascule vers l'arrière droit.
        tilt = Matrix.Rotation(math.radians(-5), 4, 'X') @ Matrix.Rotation(math.radians(3), 4, 'Y')
        bmesh.ops.transform(bm, matrix=tilt, verts=bm.verts)
        low = min(v.co.z for v in bm.verts)
        bmesh.ops.translate(bm, vec=(0, 0, -low), verts=bm.verts)
        bmesh.ops.scale(bm, vec=(1.0, 0.96, 1.0), verts=bm.verts)
    # Dessous jamais vu depuis la caméra : supprimé.
    remove_bottom_faces(bm, z_max=0.35)
    finish(rig)
    return {"category": "cover_heavy", "budget": "medium", "footprint": (4.0, 2.0),
            "render": {"target_z": 0.7, "close_distance": 7.0, "squad_offset": (0.0, -4.5)}}


def car_sedan():
    """Berline cartoon, bleue. Emprise 4 × 2 m."""
    return _car("car_sedan")


def car_wreck():
    """Épave de berline rouillée (côté zombies). Emprise 4 × 2 m."""
    return _car("car_wreck", wreck=True, seed=9)


def pickup_truck():
    """Pick-up rouge : cabine courte, plateau à ridelles, roues larges. Emprise 6 × 2 m."""
    model = "pickup_truck"
    col = start(model)
    rig = Rig(model, col)
    PAINT, RUBBER, METAL = rig.m("Env_CarPaintRed"), rig.m("Env_Rubber"), rig.m("Env_Metal")
    GLASS, WHITE, RED = rig.m("Env_Trim:glass"), rig.m("Env_Trim:white"), rig.m("Env_Trim:red")
    bm = rig.part("Truck", (0, 0, 0))
    W = 1.88
    # Capot et cabine (avant vers +X), plateau à l'arrière.
    hood = [(0.6, 0.42), (2.75, 0.42), (2.85, 0.6), (2.78, 1.0), (0.6, 1.08)]
    faces = prism(bm, hood, W, Matrix.Identity(4), PAINT)
    _bevel_all(bm, faces, 0.1, 2, PAINT)
    cab = [(-0.6, 0.42), (0.75, 0.42), (0.75, 1.05), (0.42, 1.78), (-0.6, 1.78)]
    faces = prism(bm, cab, W, Matrix.Identity(4), PAINT)
    _bevel_all(bm, faces, 0.08, 1, PAINT)
    box(bm, (0.32, 0, 1.38), (0.52, W + 0.02, 0.6), GLASS, rot=Quaternion((0, 1, 0), math.radians(-24)))
    for s in (-1, 1):
        box(bm, (0.05, s * (W / 2 + 0.005), 1.4), (0.85, 0.02, 0.5), GLASS)
    # Plateau : fond, ridelles, hayon.
    box(bm, (-1.85, 0, 0.55), (2.5, W, 0.12), PAINT)
    for s in (-1, 1):
        box(bm, (-1.85, s * (W / 2 - 0.05), 0.85), (2.5, 0.1, 0.5), PAINT, bevel=0.03)
    box(bm, (-3.05, 0, 0.85), (0.1, W, 0.5), PAINT, bevel=0.03)
    box(bm, (-1.9, 0.2, 0.75), (0.8, 0.8, 0.3), METAL, bevel=0.04)          # caisse à outils
    # Roues, pare-chocs, phares, feux, calandre.
    for x in (-2.0, 1.95):
        for s in (-1, 1):
            y = s * (W / 2 - 0.12)
            cyl(bm, (x, y - s * 0.15, 0.42), (x, y + s * 0.15, 0.42), 0.42, 0.42, RUBBER, seg=10)
            cyl(bm, (x, y + s * 0.145, 0.42), (x, y + s * 0.18, 0.42), 0.24, 0.18, METAL, seg=8)
            arc = [Vector((x + 0.52 * math.cos(math.radians(a)), s * (W / 2 + 0.01), 0.42 + 0.52 * math.sin(math.radians(a))))
                   for a in (5, 50, 90, 130, 175)]
            tube_path(bm, arc, [0.055] * 5, 4, RUBBER)
    box(bm, (2.92, 0, 0.5), (0.14, W + 0.04, 0.2), METAL, bevel=0.05)
    box(bm, (-3.12, 0, 0.5), (0.12, W + 0.04, 0.18), METAL, bevel=0.05)
    box(bm, (2.88, 0, 0.78), (0.06, 0.9, 0.25), METAL)
    for s in (-1, 1):
        cyl(bm, (2.82, s * 0.68, 0.82), (2.9, s * 0.68, 0.82), 0.12, 0.11, WHITE, seg=8)
        box(bm, (-3.1, s * 0.75, 0.88), (0.06, 0.18, 0.3), RED)
        box(bm, (0.55, s * (W / 2 - 0.02), 1.25), (0.12, 0.08, 0.12), PAINT, bevel=0.02)
    bmesh.ops.translate(bm, vec=(0.09, 0, 0), verts=bm.verts)     # centré sur l'emprise
    bmesh.ops.scale(bm, vec=(0.965, 1.0, 1.0), verts=bm.verts)    # 6 m hors tout
    remove_bottom_faces(bm, z_max=0.45)
    finish(rig)
    return {"category": "cover_heavy", "budget": "medium", "footprint": (6.0, 2.0),
            "render": {"target_z": 0.9, "close_distance": 9.0, "squad_offset": (0.0, -4.5)}}


# ---------------------------------------------------------------- Pierre tombale

def _arch_outline(width, height, segments=10):
    """Contour d'une stèle à sommet en arc (x, z), sens trigonométrique."""
    r = width / 2
    pts = [(-r, 0.0), (r, 0.0)]
    for i in range(segments + 1):
        a = math.pi * i / segments
        pts.append((r * math.cos(a), height - r + r * math.sin(a)))
    return pts


def _chip(pts, index, depth):
    """Ébréchure : rentre le point `index` du contour vers le centre de la stèle."""
    x, z = pts[index]
    cx, cz = 0.0, z * 0.6
    pts[index] = (x + (cx - x) * depth, z + (cz - z) * depth)
    return pts


def tombstone_large():
    """Grande stèle penchée sur socle, ébréchée et moussue. Emprise 2 × 2 m."""
    model = "tombstone_large"
    col = start(model)
    rig = Rig(model, col)
    STONE, DARK, MOSS, DIRT = (rig.m(n) for n in ("Env_TombStone", "Env_CryptSlab", "Env_Moss", "Env_GraveDirt"))
    rnd = random.Random(3)
    bm = rig.part("Tombstone", (0, 0, 0))
    # Socle en deux gradins.
    box(bm, (0, 0.05, 0.12), (1.8, 0.95, 0.24), DARK, bevel=0.05)
    box(bm, (0, 0.05, 0.31), (1.5, 0.7, 0.16), DARK, bevel=0.04)
    # Stèle : arc épais, penchée vers l'arrière et de côté.
    tilt = Matrix.Translation((0, 0.08, 0.37)) @ Matrix.Rotation(math.radians(-6), 4, 'X') \
        @ Matrix.Rotation(math.radians(3), 4, 'Y')
    outline = _chip(_arch_outline(1.25, 1.45, 10), 4, 0.22)
    faces = prism(bm, outline, 0.32, tilt, STONE)
    verts = list({v for f in faces for v in f.verts})
    jitter(verts, 0.015, seed=5)
    _bevel_all(bm, faces, 0.05, 1, STONE)
    # Face avant : croix et épitaphe en relief, liseré.
    front = tilt @ Matrix.Translation((0, -0.17, 0))
    q = Quaternion((1, 0, 0), math.radians(-6))
    for (x, z, w, h) in ((0, 0.9, 0.09, 0.42), (0, 0.98, 0.32, 0.09)):
        box(bm, front @ Vector((x, 0, z)), (w, 0.04, h), DARK, rot=q, bevel=0.015)
    text_mesh(bm, "R.I.P.", front @ Matrix.Translation((0, -0.005, 0.5)), 0.3, 0.035, DARK)
    box(bm, front @ Vector((0, 0, 0.26)), (0.8, 0.04, 0.06), DARK, rot=q, bevel=0.015)
    # Touffes de mousse au pied du socle (volumes arrondis, pas de plaques plates).
    for c, r, seed in (((-0.68, -0.36, 0.05), (0.26, 0.2, 0.2), 1), ((-0.4, -0.5, 0.04), (0.18, 0.15, 0.14), 2),
                       ((0.7, 0.45, 0.05), (0.22, 0.22, 0.18), 3), ((0.78, -0.25, 0.04), (0.15, 0.14, 0.12), 4)):
        blob(bm, c, r, MOSS, subdiv=2, noise=0.25, seed=seed, flatten_bottom=-0.2)
    # Tertre de terre devant la tombe.
    blob(bm, (0, -0.62, 0.0), (0.75, 0.32, 0.16), DIRT, subdiv=2, noise=0.2, seed=9, flatten_bottom=0.0)
    for _ in range(5):
        x, y = rnd.uniform(-0.6, 0.6), rnd.uniform(-0.8, -0.45)
        blob(bm, (x, y, 0.1), (0.07, 0.06, 0.05), DARK, subdiv=1, noise=0.3, seed=rnd.randint(0, 99))
    finish(rig)
    return {"category": "cover_heavy", "budget": "medium", "footprint": (2.0, 2.0),
            "render": {"target_z": 0.8, "close_distance": 4.5, "squad_offset": (2.5, -3.5), "zombies": True,
                       "rts_distance": 20.0}}


# ---------------------------------------------------------------- Murets de pierre
# Segment de 4 m le long de X (de -2 à +2 m), 1,1 m de haut, 0,5 m d'épaisseur ;
# angle et extrémité : emprise 2 × 2 m, bras de 1 m depuis le centre (un segment
# droit centré à 3 m du centre s'y raccorde exactement).

WALL_H, WALL_T = 1.1, 0.5


def _stone_run(bm, x0, x1, M, rnd, axis='x', height=WALL_H, broken=None):
    """Tronçon de muret : corps texturé, couronnement de pierres plates irrégulières.
    `broken` : (début, fin) d'une brèche (hauteur réduite, éboulis)."""
    def put(a, b, h):
        if axis == 'x':
            box(bm, ((a + b) / 2, 0, h / 2), (b - a, WALL_T, h), M["wall"])
        else:
            box(bm, (0, (a + b) / 2, h / 2), (WALL_T, b - a, h), M["wall"])
    spans = [(x0, x1, height)]
    if broken:
        b0, b1 = broken
        spans = [(x0, b0, height), (b0, b1, 0.35), (b1, x1, height)]
    for a, b, h in spans:
        if b - a > 0.01:
            put(a, b, h)
            # Couronnement : pierres plates de 0,4 à 0,7 m, légèrement décalées.
            c = a
            while c < b - 0.05:
                w = min(rnd.uniform(0.4, 0.7), b - c)
                center = (c + w / 2, rnd.uniform(-0.03, 0.03), h + 0.06)
                size = (w - 0.03, WALL_T + 0.08, 0.13)
                if axis == 'y':
                    center = (center[1], center[0], center[2])
                    size = (size[1], size[0], size[2])
                box(bm, center, size, M["cap"], rot=Quaternion((0, 0, 1), math.radians(rnd.uniform(-3, 3))), bevel=0.03)
                c += w


def _stone_pillar(bm, M):
    box(bm, (0, 0, (WALL_H + 0.25) / 2), (0.7, 0.7, WALL_H + 0.25), M["wall"], bevel=0.03)
    box(bm, (0, 0, WALL_H + 0.3), (0.8, 0.8, 0.12), M["cap"], bevel=0.03)
    cyl(bm, (0, 0, WALL_H + 0.36), (0, 0, WALL_H + 0.6), 0.22, 0.0, M["cap"], seg=4)


def _wall_rig(model):
    col = start(model)
    rig = Rig(model, col)
    M = {"wall": rig.m("Env_StoneWall"), "cap": rig.m("Env_Rock"), "moss": rig.m("Env_Moss")}
    return rig, M, rig.part("Wall", (0, 0, 0))


def _moss(bm, M, rnd, spots):
    for x, y, z in spots:
        blob(bm, (x, y, z), (rnd.uniform(0.2, 0.3), rnd.uniform(0.15, 0.22), rnd.uniform(0.1, 0.16)), M["moss"],
             subdiv=2, noise=0.3, seed=rnd.randint(0, 99))


def stone_wall_straight():
    rig, M, bm = _wall_rig("stone_wall_straight")
    rnd = random.Random(41)
    _stone_run(bm, -2.0, 2.0, M, rnd)
    _moss(bm, M, rnd, ((-1.2, 0.0, WALL_H + 0.1), (0.9, -0.2, 0.1)))
    finish(rig, smooth_angle=35.0)
    return {"category": "cover_heavy", "budget": "medium", "footprint": (4.0, 2.0)}


def stone_wall_corner():
    """Angle : bras vers -X et vers -Y, pilier au centre."""
    rig, M, bm = _wall_rig("stone_wall_corner")
    rnd = random.Random(42)
    _stone_run(bm, -1.0, -0.3, M, rnd)
    _stone_run(bm, -1.0, -0.3, M, rnd, axis='y')
    _stone_pillar(bm, M)
    finish(rig, smooth_angle=35.0)
    return {"category": "cover_heavy", "budget": "medium", "footprint": (2.0, 2.0)}


def stone_wall_end():
    """Extrémité : bras vers -X terminé par un pilier."""
    rig, M, bm = _wall_rig("stone_wall_end")
    rnd = random.Random(43)
    _stone_run(bm, -1.0, -0.3, M, rnd)
    _stone_pillar(bm, M)
    finish(rig, smooth_angle=35.0)
    return {"category": "cover_heavy", "budget": "small", "footprint": (2.0, 2.0)}


def stone_wall_broken():
    """Segment de 4 m effondré en son milieu : brèche basse et pierres éboulées."""
    rig, M, bm = _wall_rig("stone_wall_broken")
    rnd = random.Random(44)
    _stone_run(bm, -2.0, 2.0, M, rnd, broken=(-0.6, 0.8))
    for _ in range(7):
        x, y = rnd.uniform(-0.7, 0.9), rnd.uniform(-0.85, 0.85)
        s = rnd.uniform(0.18, 0.32)
        box(bm, (x, y, s / 2), (s * 1.4, s, s), M["cap"], rot=Quaternion((0, 0, 1), rnd.uniform(0, 3)), bevel=0.04)
    _moss(bm, M, rnd, ((1.4, 0.0, WALL_H + 0.1), (-1.5, 0.2, 0.08)))
    finish(rig, smooth_angle=35.0)
    return {"category": "cover_heavy", "budget": "medium", "footprint": (4.0, 2.0)}


# ---------------------------------------------------------------- Sacs de sable

def _sandbag(bm, center, yaw, mi, rnd, length=0.72):
    """Sac de toile rembourré : boîte très arrondie, légèrement irrégulière."""
    res_before = set(bm.verts)
    slab(bm, center, (length, 0.4, 0.22), mi, yaw=yaw + rnd.uniform(-5, 5), roll=rnd.uniform(-3, 3), bevel=0.08)
    jitter([v for v in bm.verts if v not in res_before], 0.015, seed=rnd.randint(0, 999))


def _sandbag_rows(bm, pts_fn, length, mi, rnd, rows=4):
    """Rangées de sacs en quinconce le long d'un tracé (t de 0 à 1 → (x, y), cap°)."""
    per_row = max(1, round(length / 0.7))
    for r in range(rows):
        offset = 0.5 if r % 2 else 0.0
        count = per_row if r % 2 == 0 else per_row - 1
        for i in range(count):
            t = (i + 0.5 + offset) / per_row
            (x, y), yaw = pts_fn(t)
            _sandbag(bm, (x, y, 0.11 + r * 0.2), yaw, mi, rnd, length=length / per_row - 0.06)


def sandbag_straight():
    """Mur de sacs de sable sur 4 m, quatre rangées en quinconce (≈ 0,9 m)."""
    model = "sandbag_straight"
    rig = Rig(model, start(model))
    BAG = rig.m("Env_Burlap")
    bm = rig.part("Sandbags", (0, 0, 0))
    _sandbag_rows(bm, lambda t: ((-2.0 + 4.0 * t, 0.0), 0.0), 4.0, BAG, random.Random(51))
    finish(rig, smooth_angle=60.0)
    return {"category": "cover_heavy", "budget": "medium", "footprint": (4.0, 2.0)}


def sandbag_curve():
    """Quart de cercle de sacs (rayon 2 m) : se raccorde à un mur droit par le bord -X
    (y = 0) et par le bord -Y (x = 0), comme les chemins courbes. Emprise 4 × 4 m."""
    model = "sandbag_curve"
    rig = Rig(model, start(model))
    BAG = rig.m("Env_Burlap")
    bm = rig.part("Sandbags", (0, 0, 0))

    def along(t):
        a = math.radians(90 * t)
        return (-2.0 + 2.0 * math.cos(a), -2.0 + 2.0 * math.sin(a)), math.degrees(a) + 90
    _sandbag_rows(bm, along, math.pi, BAG, random.Random(52))
    finish(rig, smooth_angle=60.0)
    return {"category": "cover_heavy", "budget": "medium", "footprint": (4.0, 4.0)}


# ---------------------------------------------------------------- Divers

def dumpster():
    """Benne à ordures verte : caisse évasée, couvercles relevés, roulettes, sacs
    poubelle qui dépassent. Emprise 2 × 2 m."""
    model = "dumpster"
    rig = Rig(model, start(model))
    PAINT, METAL, RUBBER, BAG = (rig.m(n) for n in ("Env_CarPaintGreen", "Env_Metal", "Env_Rubber", "Env_Paint:black"))
    bm = rig.part("Dumpster", (0, 0, 0))
    profile = [(-0.75, 0.18), (0.75, 0.18), (0.82, 1.25), (-0.82, 1.25)]
    faces = prism(bm, profile, 1.6, Matrix.Rotation(math.radians(90), 4, 'Z'), PAINT)
    _bevel_all(bm, faces, 0.04, 1, PAINT)
    box(bm, (0, 0, 1.27), (1.72, 1.72, 0.06), METAL)
    for s in (-1, 1):
        slab(bm, (s * 0.42, 0.62, 1.55), (0.82, 0.08, 0.7), PAINT, pitch=-12, roll=s * 4, bevel=0.02)
    for x in (-0.65, 0.65):
        for y in (-0.6, 0.6):
            cyl(bm, (x, y - 0.04, 0.09), (x, y + 0.04, 0.09), 0.09, 0.09, RUBBER, seg=8)
    for s in (-1, 1):
        box(bm, (0, s * 0.83, 0.85), (1.2, 0.06, 0.08), METAL)
    for i, (x, y) in enumerate(((-0.3, -0.2), (0.25, 0.15), (0.0, -0.45))):
        blob(bm, (x, y, 1.3), (0.32, 0.28, 0.25), BAG, subdiv=2, noise=0.25, seed=60 + i)
    remove_bottom_faces(bm, z_max=0.2)
    finish(rig, smooth_angle=40.0)
    return {"category": "cover_heavy", "budget": "medium", "footprint": (2.0, 2.0)}


def rock_large():
    """Gros rocher moussu, à facettes, posé de travers. Emprise 4 × 4 m."""
    model = "rock_large"
    rig = Rig(model, start(model))
    ROCK, MOSS = rig.m("Env_Rock"), rig.m("Env_Moss")
    bm = rig.part("Rock", (0, 0, 0))
    blob(bm, (0.0, 0.0, 0.55), (1.55, 1.15, 1.0), ROCK, subdiv=3, noise=0.32, seed=70, flatten_bottom=-0.55)
    blob(bm, (0.95, 0.6, 0.3), (0.7, 0.6, 0.55), ROCK, subdiv=2, noise=0.3, seed=71, flatten_bottom=-0.5)
    for x, y, z in ((-0.4, -0.2, 1.42), (0.5, -0.3, 1.3), (-1.2, 0.3, 0.6)):
        blob(bm, (x, y, z), (0.45, 0.35, 0.16), MOSS, subdiv=2, noise=0.3, seed=int(10 * x + 7))
    finish(rig, smooth_angle=45.0)
    return {"category": "cover_heavy", "budget": "medium", "footprint": (4.0, 4.0)}


def concrete_barrier():
    """Séparateur de chantier en béton (profil « New Jersey ») de 4 m, bandes rouges et
    blanches, anneaux de levage. Emprise 4 × 2 m."""
    model = "concrete_barrier"
    rig = Rig(model, start(model))
    CONC, RED, WHITE, METAL = (rig.m(n) for n in ("Env_Concrete", "Env_Paint:red", "Env_Paint:white", "Env_Metal"))
    bm = rig.part("Barrier", (0, 0, 0))
    profile = [(-0.3, 0.0), (0.3, 0.0), (0.3, 0.08), (0.18, 0.25), (0.1, 0.85), (-0.1, 0.85), (-0.18, 0.25),
               (-0.3, 0.08)]
    for x0, x1 in ((-1.98, -0.01), (0.01, 1.98)):              # deux éléments de 2 m
        mtx = Matrix.Translation(((x0 + x1) / 2, 0, 0)) @ Matrix.Rotation(math.radians(90), 4, 'Z')
        faces = prism(bm, profile, x1 - x0, mtx, CONC)
        _bevel_all(bm, faces, 0.02, 1, CONC)
        for k in range(4):                                    # bandes peintes en biais
            x = x0 + 0.25 + k * 0.48
            for s in (-1, 1):
                slab(bm, (x, s * 0.16, 0.55), (0.22, 0.02, 0.5), RED if k % 2 else WHITE, yaw=0,
                     pitch=s * -7.6, roll=30)
        cyl(bm, ((x0 + x1) / 2, -0.06, 0.85), ((x0 + x1) / 2, 0.06, 0.85), 0.07, 0.07, METAL, seg=6)
    finish(rig, smooth_angle=30.0)
    return {"category": "cover_heavy", "budget": "medium", "footprint": (4.0, 2.0)}


BUILDERS = {f.__name__: f for f in (stone_wall_straight, stone_wall_corner, stone_wall_end, stone_wall_broken,
                                    sandbag_straight, sandbag_curve, car_sedan, car_wreck, pickup_truck, dumpster,
                                    rock_large, concrete_barrier, tombstone_large)}

if __name__ == "__main__":
    run(BUILDERS)
