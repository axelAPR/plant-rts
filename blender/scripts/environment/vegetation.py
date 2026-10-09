# plantRTS — Kit d'environnement : végétation (arbres, buissons, fleurs…).
# blender -b --python blender/scripts/environment/vegetation.py -- [ids…] [--render]
#
# Arbres au tronc dégagé (couronne au-dessus de 2,6 m : les unités restent visibles
# dessous de près) et au feuillage compact. Feuillage en deux tons : faces tournées
# vers le ciel claires (Env_Foliage), dessous sombres (Env_FoliageDark) — volume
# lisible sans texture, verts plus bleus que ceux des plantes jouables.

import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from env_lib import *  # noqa: F401,F403
from mathutils import Vector, Matrix


def _two_tone(verts, center, radii, light, dark, band=-0.3):
    """Faces du feuillage : claires au-dessus, sombres sous la ligne `band` (hauteur
    relative dans la masse, −1..1) — une ombre propre, sans taches."""
    faces = {f for v in verts for f in v.link_faces}
    for f in faces:
        rel = (f.calc_center_median().z - center[2]) / radii[2]
        f.material_index = light if rel > band else dark


def tree_large():
    """Grand feuillu : tronc courbe à racines évasées, deux charpentières, couronne en
    cinq masses. Emprise 4 × 4 m, hauteur ≈ 6 m."""
    model = "tree_large"
    col = start(model)
    rig = Rig(model, col)
    BARK, LEAF, LEAF_DARK = rig.m("Env_Bark"), rig.m("Env_Foliage"), rig.m("Env_FoliageDark")
    rnd = random.Random(11)
    bm = rig.part("Tree", (0, 0, 0))
    # Tronc : léger S, évasé au pied, court sous la couronne.
    trunk = [(0, 0, 0.0), (0.02, 0.0, 0.45), (0.07, 0.03, 1.2), (0.04, 0.05, 2.0), (-0.04, 0.04, 2.7),
             (-0.08, 0.02, 3.2)]
    tube_path(bm, trunk, [0.46, 0.34, 0.29, 0.27, 0.24, 0.2], 9, BARK, cap_start=False)
    # Racines : quatre contreforts qui plongent dans le sol.
    for k in range(4):
        a = math.radians(25 + 90 * k + rnd.uniform(-15, 15))
        d = Vector((math.cos(a), math.sin(a), 0))
        pts = [d * 0.08 + Vector((0, 0, 0.5)), d * 0.38 + Vector((0, 0, 0.16)), d * 0.7 + Vector((0, 0, -0.02))]
        tube_path(bm, pts, [0.17, 0.12, 0.05], 6, BARK, cap_start=False)
    # Charpentières vers les masses de feuillage.
    for end in ((0.85, -0.35, 3.4), (-0.85, 0.4, 3.5), (0.15, 0.7, 3.7)):
        tube_path(bm, [(0.0, 0.03, 2.3), (end[0] * 0.5, end[1] * 0.5, (2.3 + end[2]) / 2 + 0.15), end],
                  [0.16, 0.11, 0.07], 6, BARK)
    # Moignons de branches coupées.
    for p0, p1 in (((0.06, 0.02, 1.55), (0.4, -0.12, 1.75)), ((0.0, 0.05, 2.05), (-0.32, 0.25, 2.3))):
        tube_path(bm, [p0, p1], [0.1, 0.07], 6, BARK)
    # Couronne : masses arrondies, compacte (rayon ≤ 2 m), dessous vers 2,6 m.
    masses = (((0.0, 0.05, 4.4), (1.5, 1.45, 1.2), 3),
              ((0.95, -0.5, 3.65), (0.95, 0.9, 0.82), 3),
              ((-0.95, 0.4, 3.7), (0.98, 0.92, 0.85), 3),
              ((0.35, 0.95, 3.8), (0.78, 0.75, 0.7), 2),
              ((0.2, -0.2, 5.35), (0.75, 0.72, 0.55), 2))
    for i, (c, r, sub) in enumerate(masses):
        verts = blob(bm, c, r, LEAF, subdiv=sub, noise=0.26, seed=20 + i)
        # Petites masses (facettes larges) : ombre plus basse, bord moins dentelé.
        _two_tone(verts, c, r, LEAF, LEAF_DARK, band=-0.3 if sub >= 3 else -0.55)
    finish(rig, smooth_angle=85.0)
    return {"category": "vegetation", "budget": "medium", "footprint": (4.0, 4.0),
            "render": {"target_z": 2.8, "close_distance": 13.0, "squad_offset": (0.0, -4.5), "close_pitch": 12.0}}


def _veg(footprint, budget="medium"):
    return {"category": "vegetation", "budget": budget, "footprint": footprint}


def tree_small():
    """Jeune arbre aux couleurs d'automne : tronc fin dégagé jusqu'à 1,7 m, couronne
    ronde de trois masses. Emprise 2 × 2 m, hauteur ≈ 3,6 m."""
    rig = Rig("tree_small", start("tree_small"))
    BARK, LEAF, DARK = rig.m("Env_Bark"), rig.m("Env_FoliageAutumn"), rig.m("Env_FoliageAutumnDark")
    bm = rig.part("Tree", (0, 0, 0))
    tube_path(bm, [(0, 0, 0), (0.03, 0, 0.8), (-0.02, 0.02, 1.7), (0.0, 0.0, 2.3)], [0.18, 0.12, 0.1, 0.08], 7, BARK,
              cap_start=False)
    for k in range(3):
        a = math.radians(40 + 120 * k)
        d = Vector((math.cos(a), math.sin(a), 0))
        tube_path(bm, [d * 0.03 + Vector((0, 0, 0.3)), d * 0.3 + Vector((0, 0, -0.02))], [0.08, 0.03], 5, BARK,
                  cap_start=False)
    for i, (c, r, sub) in enumerate((((0.0, 0.0, 2.75), (0.9, 0.85, 0.8), 3), ((0.38, -0.2, 2.35), (0.5, 0.48, 0.45), 2),
                                     ((-0.4, 0.25, 2.4), (0.5, 0.48, 0.45), 2))):
        verts = blob(bm, c, r, LEAF, subdiv=sub, noise=0.24, seed=80 + i)
        _two_tone(verts, c, r, LEAF, DARK, band=-0.3 if sub >= 3 else -0.55)
    finish(rig, smooth_angle=85.0)
    return _veg((2.0, 2.0))


def tree_dead():
    """Arbre mort tordu (côté zombies) : écorce grise, branches nues crochues, cavité.
    Emprise 4 × 4 m, hauteur ≈ 5 m."""
    rig = Rig("tree_dead", start("tree_dead"))
    BARK, HOLE = rig.m("Env_BarkDead"), rig.m("Env_Paint:black")
    bm = rig.part("Tree", (0, 0, 0))
    rnd = random.Random(90)
    trunk = [(0, 0, 0), (0.1, 0.0, 0.8), (0.25, 0.1, 1.7), (0.1, 0.2, 2.6), (-0.15, 0.15, 3.3), (-0.2, 0.0, 3.9)]
    tube_path(bm, trunk, [0.42, 0.3, 0.26, 0.22, 0.17, 0.12], 8, BARK, cap_start=False)
    for k in range(4):
        a = math.radians(10 + 90 * k + rnd.uniform(-20, 20))
        d = Vector((math.cos(a), math.sin(a), 0))
        tube_path(bm, [d * 0.08 + Vector((0, 0, 0.45)), d * 0.45 + Vector((0, 0, 0.15)), d * 0.8 + Vector((0, 0, -0.02))],
                  [0.15, 0.1, 0.04], 5, BARK, cap_start=False)

    def branch(start_pt, direction, length, radius, depth):
        pts, p, d = [Vector(start_pt)], Vector(start_pt), Vector(direction).normalized()
        for i in range(3):
            d = (d + Vector((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), rnd.uniform(-0.1, 0.3)))).normalized()
            p = p + d * length / 3
            pts.append(p.copy())
        tube_path(bm, pts, [radius, radius * 0.7, radius * 0.45, radius * 0.15], 5, BARK)
        if depth > 0:
            for k in (1, 2):
                side = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0.2, 0.8)))
                branch(pts[k], side, length * 0.55, radius * 0.55, depth - 1)
    for sp, dr in (((0.22, 0.12, 2.0), (1, -0.3, 0.6)), ((0.0, 0.2, 2.8), (-1, 0.4, 0.5)),
                   ((-0.18, 0.05, 3.6), (0.2, 0.8, 0.9))):
        branch(sp, dr, 1.6, 0.11, 1)
    ellipsoid(bm, (0.12, -0.27, 1.05), (0.13, 0.08, 0.2), HOLE, u=8, v=5)
    finish(rig, smooth_angle=60.0)
    return _veg((4.0, 4.0))


def _bush(model, flowers=False, seed=0):
    rig = Rig(model, start(model))
    LEAF, DARK = rig.m("Env_Hedge"), rig.m("Env_FoliageDark")
    FLOW = rig.m("Env_Flowers") if flowers else None
    bm = rig.part("Bush", (0, 0, 0))
    rnd = random.Random(seed)
    masses = []
    for i in range(4):
        c = (rnd.uniform(-0.35, 0.35), rnd.uniform(-0.3, 0.3), 0.45 + rnd.uniform(0, 0.25))
        r = (rnd.uniform(0.45, 0.6), rnd.uniform(0.42, 0.55), rnd.uniform(0.4, 0.5))
        verts = blob(bm, c, r, LEAF, subdiv=2, noise=0.25, seed=seed + i, flatten_bottom=-0.6)
        _two_tone(verts, c, r, LEAF, DARK, band=-0.55)
        masses.append((Vector(c), Vector(r)))
    if flowers:
        for i in range(9):                    # touffes fleuries posées sur une masse
            c, r = masses[i % len(masses)]
            a, e = rnd.uniform(0, 2 * math.pi), rnd.uniform(0.55, 1.35)
            d = Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))
            p = c + Vector((d.x * r.x, d.y * r.y, d.z * r.z)) * 0.8
            p.x, p.y = max(-0.72, min(0.72, p.x)), max(-0.72, min(0.72, p.y))   # dans l'emprise
            blob(bm, tuple(p), (0.24, 0.24, 0.13), FLOW, subdiv=2, noise=0.2, seed=seed + 20 + i)
    # Pose au sol : les masses aplaties commencent au-dessus de 0 ; on abaisse le tout.
    low = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= low
    finish(rig, smooth_angle=70.0)
    return _veg((2.0, 2.0))


def bush_a():
    """Buisson rond, deux verts. Emprise 2 × 2 m."""
    return _bush("bush_a", seed=100)


def bush_b():
    """Buisson fleuri (touffes de fleurs roses, jaunes et blanches). Emprise 2 × 2 m."""
    return _bush("bush_b", flowers=True, seed=110)


def _flower_patch(model, heads, seed, tall=False):
    """Massif de fleurs au sol : feuilles en rosette et fleurs à corolle (couleurs de
    l'atlas de peintures). Emprise 2 × 2 m."""
    rig = Rig(model, start(model))
    LEAF, SOIL = rig.m("Env_Hedge"), rig.m("Env_Dirt")
    H = [rig.m("Env_Paint:" + c) for c in heads]
    bm = rig.part("Flowers", (0, 0, 0))
    rnd = random.Random(seed)
    poly = [(0.85 * math.cos(2 * math.pi * k / 10) * rnd.uniform(0.85, 1.0),
             0.85 * math.sin(2 * math.pi * k / 10) * rnd.uniform(0.85, 1.0)) for k in range(10)]
    extrude_xy(bm, poly, 0.0, 0.04, SOIL)
    for i in range(7):
        a, r = rnd.uniform(0, 2 * math.pi), rnd.uniform(0.0, 0.6)
        x, y = r * math.cos(a), r * math.sin(a)
        h = rnd.uniform(0.45, 0.75) if tall else rnd.uniform(0.25, 0.4)
        for k in range(1):                       # une feuille par plant
            mtx = Matrix.Translation((x, y, 0.04)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, 'Z') \
                @ Matrix.Rotation(math.radians(30), 4, 'X')
            organic_leaf(bm, 0.28, 0.1, mtx, LEAF, n=3, lift=0.08, droop=0.08, fold=0.03, th=0.02)
        top = Vector((x, y, h))
        cyl(bm, (x, y, 0.04), top, 0.015, 0.012, LEAF, seg=4)
        mi = H[i % len(H)]
        if tall:                                   # tulipe : coupe fermée
            ellipsoid(bm, top + Vector((0, 0, 0.06)), (0.07, 0.07, 0.1), mi, u=6, v=4)
        else:                                      # marguerite : corolle étoilée (5 pétales) et cœur
            lathe(bm, [(0.0, -0.012), (0.12, 0.0), (0.0, 0.012)], 10, Matrix.Translation(top), mi, ridge=0.55)
            ellipsoid(bm, top + Vector((0, 0, 0.012)), (0.035, 0.035, 0.025), H[-1], u=5, v=3)
    finish(rig, smooth_angle=50.0)
    return _veg((2.0, 2.0))


def flower_patch_a():
    """Tulipes rouges et jaunes."""
    return _flower_patch("flower_patch_a", ("red", "yellow"), 120, tall=True)


def flower_patch_b():
    """Marguerites blanches à cœur jaune."""
    return _flower_patch("flower_patch_b", ("white", "white", "yellow"), 121)


def flower_patch_c():
    """Fleurs roses et bleues à cœur jaune."""
    return _flower_patch("flower_patch_c", ("pink", "blue", "yellow"), 122)


def tall_grass():
    """Touffes d'herbes hautes (lames effilées, deux tons). Emprise 2 × 2 m."""
    rig = Rig("tall_grass", start("tall_grass"))
    GRASS, DRY = rig.m("Env_Grass"), rig.m("Env_DryGrass")
    bm = rig.part("Grass", (0, 0, 0))
    rnd = random.Random(130)
    for t in range(5):
        cx, cy = rnd.uniform(-0.55, 0.55), rnd.uniform(-0.55, 0.55)
        for b in range(7):
            a = rnd.uniform(0, 2 * math.pi)
            lean = rnd.uniform(0.15, 0.45)
            h = rnd.uniform(0.5, 0.95)
            base = Vector((cx + 0.06 * math.cos(a), cy + 0.06 * math.sin(a), 0))
            tip = base + Vector((lean * math.cos(a), lean * math.sin(a), h))
            w = 0.05
            side = Vector((-math.sin(a), math.cos(a), 0)) * w
            mid = base.lerp(tip, 0.5) + Vector((0, 0, 0.05))
            v = [bm.verts.new(p) for p in (base - side, base + side, mid + side * 0.6, tip, mid - side * 0.6)]
            f = bm.faces.new(v)
            f.material_index = GRASS if b % 3 else DRY
            f2 = bm.faces.new(list(reversed([bm.verts.new(p.co + Vector((0, 0, 0.002))) for p in v])))
            f2.material_index = f.material_index
    finish(rig, clean_bottom=False, smooth_angle=60.0)
    return _veg((2.0, 2.0), "small")


def pumpkin_patch():
    """Carré de citrouilles : butte de terre, cinq citrouilles côtelées à pédoncule,
    tiges rampantes et feuilles. Emprise 4 × 4 m."""
    rig = Rig("pumpkin_patch", start("pumpkin_patch"))
    PUMPKIN, LEAF, DIRT, STEM = (rig.m(n) for n in ("Env_Paint:orange", "Env_Hedge", "Env_Dirt", "Env_Trim:wood"))
    bm = rig.part("Pumpkins", (0, 0, 0))
    rnd = random.Random(140)
    poly = [(1.7 * math.cos(2 * math.pi * k / 12) * rnd.uniform(0.85, 1.0),
             1.5 * math.sin(2 * math.pi * k / 12) * rnd.uniform(0.85, 1.0)) for k in range(12)]
    extrude_xy(bm, poly, 0.0, 0.05, DIRT)
    spots = ((-0.8, -0.5, 0.42), (0.6, -0.7, 0.32), (0.2, 0.6, 0.5), (-0.9, 0.7, 0.28), (1.1, 0.3, 0.36))
    for x, y, r in spots:
        prof = [(0.0, 0.02), (r * 0.6, 0.04), (r, r * 0.45), (r * 0.95, r * 0.95), (r * 0.5, r * 1.18), (0.0, r * 1.12)]
        lathe(bm, prof, 14, Matrix.Translation((x, y, 0.02)), PUMPKIN, ridge=0.12)
        cyl(bm, (x, y, r * 1.1), (x + 0.04, y, r * 1.1 + 0.16), 0.045, 0.03, STEM, seg=5)
    for (x0, y0, _), (x1, y1, _) in zip(spots, spots[1:]):     # tige rampante qui relie les fruits
        mid = Vector(((x0 + x1) / 2 + rnd.uniform(-0.2, 0.2), (y0 + y1) / 2 + rnd.uniform(-0.2, 0.2), 0.08))
        tube_path(bm, [(x0, y0, 0.08), mid, (x1, y1, 0.08)], [0.03, 0.03, 0.03], 4, LEAF)
        mtx = Matrix.Translation(mid) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, 'Z') @ Matrix.Rotation(0.3, 4, 'X')
        organic_leaf(bm, 0.5, 0.25, mtx, LEAF, n=3, lift=0.1, droop=0.12, fold=0.05, th=0.03)
    finish(rig, smooth_angle=50.0)
    return _veg((4.0, 4.0))


def stump():
    """Souche coupée : écorce, cerne du bois sur le dessus, racines, champignons.
    Emprise 2 × 2 m."""
    rig = Rig("stump", start("stump"))
    BARK, WOOD, RED, WHITE = (rig.m(n) for n in ("Env_Bark", "Env_Trim:wood", "Env_Paint:red", "Env_Paint:white"))
    bm = rig.part("Stump", (0, 0, 0))
    rnd = random.Random(150)
    lathe(bm, [(0.55, 0.0), (0.46, 0.15), (0.42, 0.45), (0.43, 0.6)], 10, Matrix.Identity(4), BARK, ridge=0.06)
    lathe(bm, [(0.43, 0.6), (0.38, 0.62), (0.0, 0.64)], 10, Matrix.Identity(4), WOOD)
    for k in range(4):
        a = math.radians(30 + 90 * k + rnd.uniform(-15, 15))
        d = Vector((math.cos(a), math.sin(a), 0))
        tube_path(bm, [d * 0.3 + Vector((0, 0, 0.25)), d * 0.6 + Vector((0, 0, 0.1)), d * 0.85 + Vector((0, 0, -0.02))],
                  [0.14, 0.09, 0.04], 5, BARK, cap_start=False)
    for x, y, s in ((0.52, -0.25, 1.0), (0.6, -0.05, 0.7), (-0.3, -0.55, 0.85)):
        cyl(bm, (x, y, 0.0), (x, y, 0.13 * s), 0.035 * s, 0.03 * s, WHITE, seg=5)
        dome(bm, (x, y, 0.12 * s), 0.1 * s, 0.1 * s, 0.07 * s, RED, seg=8, steps=2)
    finish(rig, smooth_angle=50.0)
    return _veg((2.0, 2.0))


def log():
    """Tronc couché de 3,4 m, extrémités sciées, mousse sur le dessus. Emprise 4 × 2 m."""
    rig = Rig("log", start("log"))
    BARK, WOOD, MOSS = rig.m("Env_Bark"), rig.m("Env_Trim:wood"), rig.m("Env_Moss")
    bm = rig.part("Log", (0, 0, 0))
    r = 0.32
    mtx = Matrix.Translation((-1.7, 0, r)) @ Matrix.Rotation(math.radians(90), 4, 'Y')
    lathe(bm, [(0.0, 0.0), (r * 0.9, 0.0), (r, 0.08), (r * 0.95, 1.7), (r * 0.98, 3.32), (r * 0.9, 3.4), (0.0, 3.4)],
          10, mtx, BARK, ridge=0.05)
    for x in (-1.7, 1.7):                           # faces sciées en bois clair
        lathe(bm, [(0.0, 0.0), (r * 0.85, 0.0)], 10,
              Matrix.Translation((x + (0.005 if x > 0 else -0.005), 0, r)) @ Matrix.Rotation(math.radians(90 if x > 0 else -90), 4, 'Y'),
              WOOD)
    for x, w in ((-0.6, 0.6), (0.7, 0.45)):
        blob(bm, (x, 0.0, 2 * r - 0.04), (w, 0.26, 0.09), MOSS, subdiv=2, noise=0.3, seed=int(x * 10) + 160)
    blob(bm, (1.2, 0.0, 0.05), (0.22, 0.2, 0.1), MOSS, subdiv=2, noise=0.3, seed=170)
    finish(rig, smooth_angle=50.0)
    return _veg((4.0, 2.0))


BUILDERS = {f.__name__: f for f in (tree_large, tree_small, tree_dead, bush_a, bush_b, flower_patch_a,
                                    flower_patch_b, flower_patch_c, tall_grass, pumpkin_patch, stump, log)}

if __name__ == "__main__":
    run(BUILDERS)
