# plantRTS — Kit d'environnement : couvert léger (clôtures, haies, accessoires).
# blender -b --python blender/scripts/environment/cover_light.py -- [ids…] [--render]
#
# Segments modulaires : 4 m exactement le long de X, centrés sur le pivot (de -2 à
# +2 m). Angles et extrémités : emprise 2 × 2 m, bras de 1 m depuis le centre vers -X
# (et -Y pour un angle) ; un segment droit centré à 3 m du centre s'y raccorde. Les
# piquets sont au pas de 0,25 m, décalés d'un demi-pas depuis chaque extrémité : deux
# pièces bout à bout gardent le même pas, sans trou ni chevauchement.

import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from env_lib import *  # noqa: F401,F403
import bmesh
from mathutils import Vector, Matrix, Quaternion

FENCE_HEIGHT = 1.0      # hauteur d'un piquet (pointe comprise)
PICKET_W, PICKET_T = 0.15, 0.045
PICKET_STEP = 0.25
SEGMENT = 4.0
TO_Y = Matrix.Rotation(math.radians(90), 4, 'Z')     # bras -X tourné en bras -Y


def _transformed(bm, mtx, build):
    """Construit une partie avec `build(b)` dans un maillage à part, la transforme par
    `mtx` et la fusionne dans `bm` (env_lib.build_transformed)."""
    build_transformed(bm, mtx, build)


def _picket(bm, x, height, mi, rnd, lean=0.0):
    """Piquet à pointe, légèrement irrégulier (hauteur, inclinaison)."""
    w = PICKET_W
    tip = 0.1
    pts = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, height - tip), (0.0, height), (-w / 2, height - tip)]
    tilt = math.radians(rnd.uniform(-1.6, 1.6) + lean)
    mtx = Matrix.Translation((x, -0.035, 0.0)) @ Matrix.Rotation(tilt, 4, 'Y')
    prism(bm, pts, PICKET_T, mtx, mi)


def _picket_run(bm, a, b, M, rnd, skip=(), missing=()):
    """Piquets et lisses de x = a à x = b (le long de X). Les piquets suivent la grille
    globale (x = 0,125 + k × 0,25) : le pas reste régulier d'une pièce à l'autre."""
    k0 = math.ceil((a - PICKET_STEP / 2) / PICKET_STEP - 1e-6)
    k1 = math.floor((b - PICKET_STEP / 2) / PICKET_STEP + 1e-6)
    for i, k in enumerate(range(k0, k1 + 1)):
        x = PICKET_STEP / 2 + k * PICKET_STEP
        if not (a < x < b) or any(abs(x - s) < 0.13 for s in skip) or i in missing:
            continue
        _picket(bm, x, FENCE_HEIGHT - rnd.uniform(0.0, 0.05), M["white"], rnd)
    for z in (0.28, 0.7):
        box(bm, ((a + b) / 2, 0.03, z), (b - a, 0.035, 0.1), M["wood"], bevel=0.006)


def _picket_post(bm, x, y, M):
    box(bm, (x, y, 0.55), (0.13, 0.13, 1.1), M["white"], bevel=0.02)
    box(bm, (x, y, 1.12), (0.18, 0.18, 0.05), M["white"], bevel=0.015)
    cyl(bm, (x, y, 1.145), (x, y, 1.27), 0.1, 0.0, M["white"], seg=4)


def _fence_rig(model):
    rig = Rig(model, start(model))
    M = {"white": rig.m("Env_Trim:white"), "wood": rig.m("Env_Trim:wood")}
    return rig, M, rig.part("Fence", (0, 0, 0))


def _light(footprint, budget="medium", render=None):
    info = {"category": "cover_light", "budget": budget, "footprint": footprint}
    if render:
        info["render"] = render
    return info


def picket_fence_straight():
    rig, M, bm = _fence_rig("picket_fence_straight")
    rnd = random.Random(7)
    _picket_run(bm, -2.0, 2.0, M, rnd)
    _picket_post(bm, 0.0, 0.115, M)          # poteau central derrière les lisses
    finish(rig)
    return _light((4.0, 2.0), render={"target_z": 0.5, "close_distance": 5.5, "squad_offset": (0.0, -3.5),
                                      "rts_distance": 22.0})


def picket_fence_corner():
    """Angle : bras de 1 m vers -X et vers -Y, poteau d'angle."""
    rig, M, bm = _fence_rig("picket_fence_corner")
    rnd = random.Random(8)
    _picket_run(bm, -1.0, 0.0, M, rnd, skip=(-0.125,))
    _transformed(bm, TO_Y, lambda b: _picket_run(b, -1.0, 0.0, M, rnd, skip=(-0.125,)))
    _picket_post(bm, 0.0, 0.0, M)
    finish(rig)
    return _light((2.0, 2.0))


def picket_fence_gate():
    """Segment de 4 m avec portillon central (1,2 m) entre deux poteaux."""
    rig, M, bm = _fence_rig("picket_fence_gate")
    rnd = random.Random(9)
    _picket_run(bm, -2.0, -0.6, M, rnd)
    _picket_run(bm, 0.6, 2.0, M, rnd)
    for x in (-0.68, 0.68):
        _picket_post(bm, x, 0.03, M)
    # Portillon entrouvert : piquets sur cadre, écharpe en Z, charnières côté gauche.
    gate = Matrix.Translation((-0.6, 0.0, 0.05)) @ Matrix.Rotation(math.radians(-25), 4, 'Z')

    def leaf(b):
        for i in range(5):
            _picket(b, 0.12 + i * 0.23, 0.92, M["white"], rnd)
        for z in (0.25, 0.68):
            box(b, (0.6, 0.03, z), (1.15, 0.035, 0.09), M["wood"])
        box(b, (0.6, 0.05, 0.47), (0.08, 0.03, 0.6), M["wood"], rot=Quaternion((0, 1, 0), math.radians(55)))
    _transformed(bm, gate, leaf)
    finish(rig)
    return _light((4.0, 2.0))


def picket_fence_broken():
    """Segment de 4 m abîmé : piquets manquants ou tombés, lisse cassée qui pend."""
    rig, M, bm = _fence_rig("picket_fence_broken")
    rnd = random.Random(10)
    n = round(SEGMENT / PICKET_STEP)
    for i in range(n):
        x = -2.0 + PICKET_STEP * (i + 0.5)
        if i in (5, 6, 7, 10):
            continue
        lean = rnd.uniform(6, 14) * (1 if i % 2 else -1) if i in (4, 8, 9) else 0.0
        _picket(bm, x, FENCE_HEIGHT - rnd.uniform(0.0, 0.25 if i in (8, 9) else 0.05), M["white"], rnd, lean=lean)
    box(bm, (0, 0.03, 0.28), (4.0, 0.035, 0.1), M["wood"])
    box(bm, (-1.3, 0.03, 0.7), (1.4, 0.035, 0.1), M["wood"])
    box(bm, (1.25, 0.03, 0.7), (1.5, 0.035, 0.1), M["wood"])
    slab(bm, (-0.2, 0.06, 0.48), (1.0, 0.035, 0.1), M["wood"], roll=28)               # lisse qui pend
    for x, yaw in ((-0.4, 70), (0.3, 100), (1.6, 80)):                                # piquets au sol
        slab(bm, (x, -0.45, 0.03), (0.15, 0.95, 0.045), M["white"], yaw=yaw * 0 + rnd.uniform(-25, 25))
    _picket_post(bm, 0.0, 0.115, M)
    finish(rig)
    return _light((4.0, 2.0))


# ---------------------------------------------------------------- Haies
# Profil arrondi (largeur 0,9 m, hauteur 1,2 m) extrudé sur la longueur : les bouts
# sont plats pour se raccorder ; touffes en relief sur le dessus pour la silhouette.

HEDGE_H, HEDGE_W = 1.2, 0.9


def _hedge_profile():
    r = 0.32
    pts = [(-HEDGE_W / 2, 0.0), (HEDGE_W / 2, 0.0)]
    for i in range(5):
        a = math.radians(90 * i / 4)
        pts.append((HEDGE_W / 2 - r + r * math.cos(a), HEDGE_H - r + r * math.sin(a)))
    for i in range(5):
        a = math.radians(90 + 90 * i / 4)
        pts.append((-HEDGE_W / 2 + r + r * math.cos(a), HEDGE_H - r + r * math.sin(a)))
    return pts


def _hedge_run(bm, a, b, M, rnd):
    """Haie de x = a à x = b : corps profilé, touffes, paillis au pied."""
    mtx = Matrix.Translation(((a + b) / 2, 0, 0)) @ Matrix.Rotation(math.radians(90), 4, 'Z')
    prism(bm, _hedge_profile(), b - a, mtx, M["leaf"])
    n = max(1, round((b - a) / 0.8))
    for i in range(n):
        r = min(0.42, (b - a) / 3.2)
        x = a + (b - a) * (i + 0.5) / n + rnd.uniform(-0.05, 0.05)
        x = min(max(x, a + r * 1.5), b - r * 1.5) if b - a > 3.2 * r else (a + b) / 2      # touffe (bruit compris) dans le tronçon
        blob(bm, (x, rnd.uniform(-0.1, 0.1), HEDGE_H - 0.12), (r, 0.36, 0.22), M["leaf"], subdiv=2, noise=0.3,
             seed=rnd.randint(0, 999))
    box(bm, ((a + b) / 2, 0, 0.02), (b - a, HEDGE_W + 0.2, 0.04), M["mulch"])


def _hedge_rig(model):
    rig = Rig(model, start(model))
    M = {"leaf": rig.m("Env_Hedge"), "mulch": rig.m("Env_Dirt")}
    return rig, M, rig.part("Hedge", (0, 0, 0))


def hedge_straight():
    rig, M, bm = _hedge_rig("hedge_straight")
    _hedge_run(bm, -2.0, 2.0, M, random.Random(20))
    finish(rig, smooth_angle=60.0)
    return _light((4.0, 2.0))


def hedge_corner():
    """Angle : bras vers -X et -Y, bloc d'angle arrondi."""
    rig, M, bm = _hedge_rig("hedge_corner")
    rnd = random.Random(21)
    _hedge_run(bm, -1.0, HEDGE_W / 2, M, rnd)
    _transformed(bm, TO_Y, lambda b: _hedge_run(b, -1.0, -HEDGE_W / 2, M, rnd))
    finish(rig, smooth_angle=60.0)
    return _light((2.0, 2.0))


def hedge_end():
    """Extrémité : bras vers -X, bout arrondi (demi-dôme)."""
    rig, M, bm = _hedge_rig("hedge_end")
    rnd = random.Random(22)
    _hedge_run(bm, -1.0, 0.0, M, rnd)
    blob(bm, (0.0, 0.0, HEDGE_H / 2), (0.5, HEDGE_W / 2, HEDGE_H / 2), M["leaf"], subdiv=3, noise=0.15, seed=23,
         flatten_bottom=-0.95)
    finish(rig, smooth_angle=60.0)
    return _light((2.0, 2.0))


# ---------------------------------------------------------------- Grilles en fer forgé

IRON_H = 1.6


def _iron_run(bm, a, b, M, skip=()):
    """Barreaux à pointe de lance au pas de 0,16 m, deux traverses, de x = a à b."""
    step = 0.16
    n = round((b - a) / step)
    for i in range(n):
        x = a + step * (i + 0.5)
        if any(abs(x - s) < 0.12 for s in skip):
            continue
        cyl(bm, (x, 0, 0.0), (x, 0, IRON_H), 0.018, 0.018, M["iron"], seg=4)
        cyl(bm, (x, 0, IRON_H), (x, 0, IRON_H + 0.14), 0.045, 0.0, M["iron"], seg=4)
    for z in (0.18, IRON_H - 0.18):
        box(bm, ((a + b) / 2, 0, z), (b - a, 0.05, 0.05), M["iron"])


def _iron_post(bm, x, y, M):
    box(bm, (x, y, 0.3), (0.42, 0.42, 0.6), M["stone"], bevel=0.03)
    box(bm, (x, y, IRON_H / 2 + 0.3), (0.12, 0.12, IRON_H + 0.0), M["iron"])
    ellipsoid(bm, (x, y, IRON_H + 0.38), (0.11, 0.11, 0.11), M["iron"], u=8, v=5)


def _iron_rig(model):
    rig = Rig(model, start(model))
    M = {"iron": rig.m("Env_Iron"), "stone": rig.m("Env_CryptSlab")}
    return rig, M, rig.part("Fence", (0, 0, 0))


def iron_fence_straight():
    rig, M, bm = _iron_rig("iron_fence_straight")
    _iron_run(bm, -2.0, 2.0, M, skip=(0.0,))
    _iron_post(bm, 0.0, 0.0, M)
    finish(rig, smooth_angle=40.0)
    return _light((4.0, 2.0))


def iron_fence_corner():
    rig, M, bm = _iron_rig("iron_fence_corner")
    _iron_run(bm, -1.0, 0.0, M, skip=(-0.08,))
    _transformed(bm, TO_Y, lambda b: _iron_run(b, -1.0, 0.0, M, skip=(-0.08,)))
    _iron_post(bm, 0.0, 0.0, M)
    finish(rig, smooth_angle=40.0)
    return _light((2.0, 2.0))


def iron_fence_gate():
    """Segment de 4 m à portail double (1,8 m) entre deux piliers, arc en haut."""
    rig, M, bm = _iron_rig("iron_fence_gate")
    _iron_run(bm, -2.0, -0.9, M, skip=(-0.95,))
    _iron_run(bm, 0.9, 2.0, M, skip=(0.95,))
    for x in (-1.0, 1.0):
        _iron_post(bm, x, 0.0, M)
    for s, ang in ((-1, -12), (1, 20)):          # deux vantaux entrouverts
        hinge = Matrix.Translation((s * 0.88, 0, 0.05)) @ Matrix.Rotation(math.radians(ang), 4, 'Z')

        def leaf(b, s=s):
            for i in range(5):
                x = -s * (0.08 + i * 0.17)
                h = IRON_H + 0.25 * math.sin(math.pi * (i + 1) / 10)
                cyl(b, (x, 0, 0.1), (x, 0, h), 0.018, 0.018, M["iron"], seg=4)
                cyl(b, (x, 0, h), (x, 0, h + 0.12), 0.04, 0.0, M["iron"], seg=4)
            for z in (0.2, IRON_H - 0.2):
                box(b, (-s * 0.42, 0, z), (0.84, 0.05, 0.05), M["iron"])
            arc = [(-s * (0.84 * k / 6), 0, IRON_H + 0.25 * math.sin(math.pi * (6 - k) / 12) - 0.05) for k in range(7)]
            tube_path(b, arc, [0.025] * 7, 4, M["iron"])
        _transformed(bm, hinge, leaf)
    finish(rig, smooth_angle=40.0)
    return _light((4.0, 2.0))


# ---------------------------------------------------------------- Accessoires (couvert léger)

def crate_stack():
    """Trois caisses de bois cloutées, empilées de travers. Emprise 2 × 2 m."""
    rig = Rig("crate_stack", start("crate_stack"))
    PLANK, EDGE = rig.m("Env_WoodPlanks"), rig.m("Env_Trim:wood")
    bm = rig.part("Crates", (0, 0, 0))

    def crate(c, size, yaw):
        q = Quaternion((0, 0, 1), math.radians(yaw))
        box(bm, c, size, PLANK, rot=q, bevel=0.02)
        sx, sy, sz = size
        for dx in (-1, 1):                       # montants d'angle
            for dy in (-1, 1):
                p = Vector(c) + q @ Vector((dx * (sx / 2 - 0.03), dy * (sy / 2 - 0.03), 0))
                box(bm, p, (0.08, 0.08, sz + 0.01), EDGE, rot=q)
        for dz in (-1, 1):                       # cerclages haut et bas
            box(bm, Vector(c) + Vector((0, 0, dz * (sz / 2 - 0.04))), (sx + 0.02, sy + 0.02, 0.07), EDGE, rot=q)
    crate((-0.4, 0.0, 0.4), (0.8, 0.8, 0.8), 4)
    crate((0.45, 0.1, 0.35), (0.7, 0.7, 0.7), -9)
    crate((-0.25, 0.05, 1.15), (0.7, 0.7, 0.7), 18)
    finish(rig, smooth_angle=30.0)
    return _light((2.0, 2.0))


def barrel_group():
    """Trois tonneaux de métal cerclés (un rouge, deux rouillés), un couché. 2 × 2 m."""
    rig = Rig("barrel_group", start("barrel_group"))
    RUST, RED, IRON = rig.m("Env_RustyIron"), rig.m("Env_Paint:red"), rig.m("Env_Iron")
    bm = rig.part("Barrels", (0, 0, 0))
    prof = [(0.0, 0.0), (0.27, 0.0), (0.3, 0.2), (0.31, 0.45), (0.3, 0.7), (0.27, 0.88), (0.0, 0.88)]

    def barrel(mtx, mi):
        lathe(bm, prof, 12, mtx, mi)
        for z in (0.2, 0.68):
            lathe(bm, [(0.312, z - 0.03), (0.322, z), (0.312, z + 0.03)], 12, mtx, IRON)
    barrel(Matrix.Translation((-0.4, -0.25, 0)), RED)
    barrel(Matrix.Translation((0.35, -0.3, 0)), RUST)
    barrel(Matrix.Translation((0.0, 0.45, 0.3)) @ Matrix.Rotation(math.radians(90), 4, 'Y')
           @ Matrix.Translation((0, 0, -0.44)), RUST)
    finish(rig, smooth_angle=45.0)
    return _light((2.0, 2.0))


def hay_bale():
    """Trois bottes de foin rectangulaires ficelées (deux au sol, une dessus). 2 × 2 m."""
    rig = Rig("hay_bale", start("hay_bale"))
    STRAW, TWINE = rig.m("Env_Straw"), rig.m("Env_Paint:red")
    bm = rig.part("Hay", (0, 0, 0))
    rnd = random.Random(30)
    for c, yaw in (((-0.42, -0.1, 0.25), 3), ((0.42, 0.05, 0.25), -6), ((0.0, 0.0, 0.75), 12)):
        before = set(bm.verts)
        slab(bm, c, (0.72, 1.05, 0.5), STRAW, yaw=90 + yaw, bevel=0.06)
        jitter([v for v in bm.verts if v not in before], 0.025, seed=rnd.randint(0, 99))
        for k in (-0.3, 0.3):
            q = Quaternion((0, 0, 1), math.radians(90 + yaw))
            box(bm, Vector(c) + q @ Vector((k, 0, 0)), (0.04, 0.75, 0.53), TWINE, rot=q)
    finish(rig, smooth_angle=40.0)
    return _light((2.0, 2.0))


def planter_box():
    """Jardinière en bois de 1,8 × 0,7 m : terreau, arbustes taillés, fleurs. 2 × 2 m."""
    rig = Rig("planter_box", start("planter_box"))
    PLANK, EDGE, LEAF, FLOWERS = (rig.m(n) for n in ("Env_WoodPlanks", "Env_Trim:wood", "Env_Hedge", "Env_Flowers"))
    bm = rig.part("Planter", (0, 0, 0))
    box(bm, (0, 0, 0.3), (1.8, 0.7, 0.6), PLANK, bevel=0.02)
    box(bm, (0, 0, 0.62), (1.9, 0.8, 0.06), EDGE, bevel=0.01)
    for x in (-0.85, 0.85):
        box(bm, (x, 0, 0.32), (0.1, 0.74, 0.64), EDGE)
    for i, x in enumerate((-0.55, 0.55)):
        blob(bm, (x, 0, 0.92), (0.32, 0.28, 0.33), LEAF, subdiv=2, noise=0.2, seed=40 + i)
    blob(bm, (0.0, 0.0, 0.7), (0.32, 0.27, 0.16), FLOWERS, subdiv=2, noise=0.25, seed=42)
    finish(rig, smooth_angle=45.0)
    return _light((2.0, 2.0))


def trash_cans():
    """Deux poubelles en métal à couvercle, une renversée avec ses déchets. 2 × 2 m."""
    rig = Rig("trash_cans", start("trash_cans"))
    METAL, BAG, PAPER = rig.m("Env_Metal"), rig.m("Env_Paint:black"), rig.m("Env_Paint:white")
    bm = rig.part("Cans", (0, 0, 0))
    prof = [(0.0, 0.0), (0.26, 0.0), (0.3, 0.85), (0.0, 0.85)]
    lid = [(0.0, 0.85), (0.34, 0.86), (0.33, 0.92), (0.12, 0.98), (0.0, 1.0)]

    def can(mtx, with_lid=True):
        lathe(bm, prof, 12, mtx, METAL)
        for z in (0.25, 0.6):
            lathe(bm, [(0.285, z - 0.02), (0.3, z), (0.29, z + 0.02)], 12, mtx, METAL)
        if with_lid:
            lathe(bm, lid, 12, mtx, METAL)
            cyl(bm, mtx @ Vector((-0.08, 0, 1.0)), mtx @ Vector((0.08, 0, 1.0)), 0.025, 0.025, METAL, seg=4)
    can(Matrix.Translation((-0.45, 0.2, 0)))
    can(Matrix.Translation((0.25, 0.4, 0)))
    can(Matrix.Translation((0.2, -0.35, 0.3)) @ Matrix.Rotation(math.radians(90), 4, 'X')
        @ Matrix.Rotation(math.radians(70), 4, 'Y') @ Matrix.Translation((0, 0, -0.42)), with_lid=False)
    lathe(bm, lid, 12, Matrix.Translation((-0.55, -0.55, -0.84)), METAL)
    for i, (x, y) in enumerate(((0.65, -0.6), (0.5, -0.75))):
        blob(bm, (x, y, 0.15), (0.2, 0.17, 0.15), BAG, subdiv=2, noise=0.25, seed=50 + i)
    for x, y in ((0.2, -0.8), (-0.1, -0.7)):
        slab(bm, (x, y, 0.01), (0.2, 0.15, 0.02), PAPER, yaw=x * 200)
    finish(rig, smooth_angle=45.0)
    return _light((2.0, 2.0))


def wheelbarrow():
    """Brouette rouge chargée de terre, roue avant, brancards en bois. 2 × 2 m."""
    rig = Rig("wheelbarrow", start("wheelbarrow"))
    RED, WOOD, RUBBER, DIRT = rig.m("Env_Paint:red"), rig.m("Env_Trim:wood"), rig.m("Env_Rubber"), rig.m("Env_Dirt")
    bm = rig.part("Wheelbarrow", (0, 0, 0))
    # Caisse évasée (avant vers +X), posée sur deux pieds et la roue.
    profile = [(-0.35, 0.35), (0.3, 0.35), (0.55, 0.72), (-0.5, 0.72)]
    prism(bm, profile, 0.62, Matrix.Translation((0, 0.0, 0.0)), RED)
    blob(bm, (0.0, 0.0, 0.72), (0.45, 0.26, 0.12), DIRT, subdiv=2, noise=0.3, seed=60)
    cyl(bm, (0.62, -0.06, 0.2), (0.62, 0.06, 0.2), 0.2, 0.2, RUBBER, seg=10)
    for s in (-1, 1):
        cyl(bm, (0.62, s * 0.08, 0.2), (-0.95, s * 0.3, 0.62), 0.03, 0.03, WOOD, seg=5)       # brancards
        cyl(bm, (-0.25, s * 0.22, 0.38), (-0.3, s * 0.24, 0.0), 0.025, 0.025, WOOD, seg=4)    # pieds
    finish(rig, smooth_angle=40.0)
    return _light((2.0, 2.0))


BUILDERS = {f.__name__: f for f in (picket_fence_straight, picket_fence_corner, picket_fence_gate,
                                    picket_fence_broken, hedge_straight, hedge_corner, hedge_end,
                                    iron_fence_straight, iron_fence_corner, iron_fence_gate, crate_stack,
                                    barrel_group, hay_bale, planter_box, trash_cans, wheelbarrow)}

if __name__ == "__main__":
    run(BUILDERS)
