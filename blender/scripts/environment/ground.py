# plantRTS — Kit d'environnement : routes et sols (lot 2).
# blender -b --python blender/scripts/environment/ground.py -- [ids…]
#
# Tuiles de route de 8 × 8 m, raccordables : chaussée de 6 m (asphalte) le long de X,
# trottoirs de 1 m (dalles de béton, 0,15 m de haut) ; ligne médiane en tirets de
# 1,5 m au pas de 4 m (continue d'une tuile à l'autre). Les entrées de route se font
# toujours au milieu d'un bord de tuile. Sols : allée, chemins (modules de 4 m),
# terre, massif fleuri. Dessous supprimés : posés sur le terrain.

import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from env_lib import *  # noqa: F401,F403
from mathutils import Vector, Matrix

T = 4.0             # demi-tuile
LANE = 3.0          # demi-chaussée
WALK_Z = 0.15       # dessus du trottoir
ROAD_Z = 0.02       # dessus de la chaussée
PAINT_Z = ROAD_Z + 0.006


def _mats(rig):
    return {"asphalt": rig.m("Env_Asphalt"), "walk": rig.m("Env_Concrete"),
            "yellow": rig.m("Env_Paint:yellow"), "white": rig.m("Env_Paint:white")}


def _rect(bm, x0, y0, x1, y1, z0, z1, mi, mi_side=None):
    extrude_xy(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mi, mi_side)


def _dashes_x(bm, x0, x1, mi, y=0.0):
    """Tirets de ligne médiane le long de X (1,5 m au pas de 4 m, alignés sur la grille)."""
    for c in (-2.0, 2.0):
        a, b = max(c - 0.75, x0), min(c + 0.75, x1)
        if b > a:
            _rect(bm, a, y - 0.07, b, y + 0.07, ROAD_Z, PAINT_Z, mi)


def _dashes_y(bm, y0, y1, mi, x=0.0):
    for c in (-2.0, 2.0):
        a, b = max(c - 0.75, y0), min(c + 0.75, y1)
        if b > a:
            _rect(bm, x - 0.07, a, x + 0.07, b, ROAD_Z, PAINT_Z, mi)


def _start(model):
    col = start(model)
    rig = Rig(model, col)
    return rig, _mats(rig), rig.part("Ground", (0, 0, 0))


def _done(rig, footprint=(8.0, 8.0), budget="medium"):
    finish(rig, smooth_angle=20.0)
    return {"category": "ground", "budget": budget, "footprint": footprint}


def road_straight():
    rig, M, bm = _start("road_straight")
    _rect(bm, -T, -LANE, T, LANE, 0.0, ROAD_Z, M["asphalt"])
    for s in (-1, 1):
        _rect(bm, -T, s * LANE if s > 0 else -T, T, T if s > 0 else -LANE, 0.0, WALK_Z, M["walk"])
    _dashes_x(bm, -T, T, M["yellow"])
    return _done(rig)


def road_crosswalk():
    rig, M, bm = _start("road_crosswalk")
    _rect(bm, -T, -LANE, T, LANE, 0.0, ROAD_Z, M["asphalt"])
    for s in (-1, 1):
        _rect(bm, -T, LANE if s > 0 else -T, T, T if s > 0 else -LANE, 0.0, WALK_Z, M["walk"])
    for i in range(7):                      # bandes blanches de 0,5 m au pas de 0,85 m
        y = -LANE + 0.3 + i * 0.85
        _rect(bm, -1.4, y, 1.4, y + 0.5, ROAD_Z, PAINT_Z, M["white"])
    for s in (-1, 1):                       # lignes d'arrêt
        _rect(bm, s * 2.0 - 0.1, -LANE + 0.1, s * 2.0 + 0.1, LANE - 0.1, ROAD_Z, PAINT_Z, M["white"])
    return _done(rig)


def road_curve():
    """Virage à 90° : entrée par le bord -X, sortie par le bord -Y (centre du virage au
    coin (-4, -4)). Trottoir intérieur en quart de disque, extérieur jusqu'au coin."""
    rig, M, bm = _start("road_curve")
    c = (-T, -T)
    n = 10
    inner, outer = 1.0, 7.0
    for k in range(n):
        a0, a1 = 90.0 * k / n, 90.0 * (k + 1) / n
        p = arc_pts(c, inner, a0, a1, 1) + list(reversed(arc_pts(c, outer, a0, a1, 1)))
        extrude_xy(bm, p, 0.0, ROAD_Z, M["asphalt"])
        # Trottoir intérieur.
        extrude_xy(bm, [c] + arc_pts(c, inner, a0, a1, 1), 0.0, WALK_Z, M["walk"])
        # Trottoir extérieur : de l'arc de 7 m au bord carré de la tuile.
        o = arc_pts(c, outer, a0, a1, 1)
        far = []
        for x, y in o:
            d = Vector((x - c[0], y - c[1]))
            t = min((2 * T) / max(abs(d.x), 1e-6), (2 * T) / max(abs(d.y), 1e-6))
            far.append((c[0] + d.x * t, c[1] + d.y * t))
        extrude_xy(bm, [o[1], o[0], far[0], far[1]], 0.0, WALK_Z, M["walk"])
    # Tirets sur l'arc médian (rayon 4 m).
    for a0, a1 in ((15, 36), (54, 75)):
        p = arc_pts(c, 3.93, a0, a1, 3) + list(reversed(arc_pts(c, 4.07, a0, a1, 3)))
        extrude_xy(bm, p, ROAD_Z, PAINT_Z, M["yellow"])
    return _done(rig)


def _junction(model, arms):
    """Carrefour : `arms` = bords ouverts parmi ('-x', '+x', '-y', '+y')."""
    rig, M, bm = _start(model)
    _rect(bm, -LANE, -LANE, LANE, LANE, 0.0, ROAD_Z, M["asphalt"])
    for arm in ('-x', '+x', '-y', '+y'):
        s = -1 if arm[0] == '-' else 1
        if arm in arms:
            if arm[1] == 'x':
                _rect(bm, min(s * LANE, s * T), -LANE, max(s * LANE, s * T), LANE, 0.0, ROAD_Z, M["asphalt"])
                _dashes_x(bm, min(s * LANE, s * T), max(s * LANE, s * T), M["yellow"])
            else:
                _rect(bm, -LANE, min(s * LANE, s * T), LANE, max(s * LANE, s * T), 0.0, ROAD_Z, M["asphalt"])
                _dashes_y(bm, min(s * LANE, s * T), max(s * LANE, s * T), M["yellow"])
        else:
            # Bord fermé : trottoir sur toute la largeur de la chaussée.
            if arm[1] == 'x':
                _rect(bm, min(s * LANE, s * T), -LANE, max(s * LANE, s * T), LANE, 0.0, WALK_Z, M["walk"])
            else:
                _rect(bm, -LANE, min(s * LANE, s * T), LANE, max(s * LANE, s * T), 0.0, WALK_Z, M["walk"])
    for sx in (-1, 1):
        for sy in (-1, 1):
            _rect(bm, min(sx * LANE, sx * T), min(sy * LANE, sy * T), max(sx * LANE, sx * T),
                  max(sy * LANE, sy * T), 0.0, WALK_Z, M["walk"])
    return rig


def road_t():
    rig = _junction("road_t", ('-x', '+x', '-y'))
    return _done(rig)


def road_cross():
    rig = _junction("road_cross", ('-x', '+x', '-y', '+y'))
    return _done(rig)


def road_end():
    """Fin de route en impasse : entrée par -X, demi-cercle de retournement fermé par
    le trottoir côté +X."""
    rig, M, bm = _start("road_end")
    _rect(bm, -T, -LANE, 0.0, LANE, 0.0, ROAD_Z, M["asphalt"])
    half = arc_pts((0.0, 0.0), LANE, -90, 90, 10)
    extrude_xy(bm, [(0.0, -LANE)] + half[1:-1] + [(0.0, LANE)], 0.0, ROAD_Z, M["asphalt"])
    for s in (-1, 1):
        _rect(bm, -T, LANE if s > 0 else -T, T, T if s > 0 else -LANE, 0.0, WALK_Z, M["walk"])
    # Trottoir autour du demi-cercle, jusqu'au bord +X.
    for k in range(10):
        a0, a1 = -90 + 18 * k, -90 + 18 * (k + 1)
        p0, p1 = arc_pts((0.0, 0.0), LANE, a0, a1, 1)
        extrude_xy(bm, [p0, (T, p0[1]), (T, p1[1]), p1], 0.0, WALK_Z, M["walk"])
    _dashes_x(bm, -T, -0.5, M["yellow"])
    return _done(rig)


def driveway():
    """Allée de garage en béton, 4 × 8 m le long de Y : quatre dalles à joints,
    bordures de terre."""
    rig = Rig("driveway", start("driveway"))
    CONC, DIRT = rig.m("Env_Concrete"), rig.m("Env_Dirt")
    bm = rig.part("Ground", (0, 0, 0))
    for i in range(4):                      # quatre dalles séparées par des joints
        y0 = -4.0 + i * 2.0 + 0.03
        _rect(bm, -1.6, y0, 1.6, y0 + 1.94, 0.0, 0.06, CONC)
    for x in (-1.75, 1.75):                 # bordures de terre
        _rect(bm, x - 0.15, -4.0, x + 0.15, 4.0, 0.0, 0.03, DIRT)
    finish(rig)
    return {"category": "ground", "budget": "medium", "footprint": (4.0, 8.0)}


def _stones_along(bm, pts_fn, count, mi, rnd, size=(0.35, 0.5)):
    """Pierres de gué plates et irrégulières le long d'une courbe paramétrée."""
    for i in range(count):
        t = (i + 0.5) / count
        (x, y), yaw = pts_fn(t)
        r = rnd.uniform(*size)
        poly = []
        for k in range(7):
            a = 2 * math.pi * k / 7 + rnd.uniform(-0.2, 0.2)
            rr = r * rnd.uniform(0.75, 1.0)
            poly.append((x + rr * math.cos(a) * 1.1, y + rr * math.sin(a) * 0.85))
        extrude_xy(bm, poly, 0.0, 0.07, mi)


def path_straight():
    """Chemin de jardin : bande de terre battue de 1,2 m, pas japonais en pierre ;
    module de 4 m le long de X (centré)."""
    rig = Rig("path_straight", start("path_straight"))
    PATH, ROCK = rig.m("Env_Path"), rig.m("Env_Rock")
    bm = rig.part("Ground", (0, 0, 0))
    _rect(bm, -2.0, -0.6, 2.0, 0.6, 0.0, 0.02, PATH)
    _stones_along(bm, lambda t: ((-2.0 + 4.0 * t, 0.05 * math.sin(t * 9)), 0.0), 5, ROCK, random.Random(4))
    finish(rig)
    return {"category": "ground", "budget": "small", "footprint": (4.0, 2.0)}


def path_curve():
    """Chemin en quart de cercle (rayon 2 m) : entre par le bord -X (y = 0), sort par
    le bord -Y (x = 0), comme un chemin droit de chaque côté. Emprise 4 × 4 m."""
    rig = Rig("path_curve", start("path_curve"))
    PATH, ROCK = rig.m("Env_Path"), rig.m("Env_Rock")
    bm = rig.part("Ground", (0, 0, 0))
    c = (-2.0, -2.0)
    n = 8
    for k in range(n):
        a0, a1 = 90.0 * k / n, 90.0 * (k + 1) / n
        p = arc_pts(c, 1.4, a0, a1, 1) + list(reversed(arc_pts(c, 2.6, a0, a1, 1)))
        extrude_xy(bm, p, 0.0, 0.02, PATH)

    def along(t):
        a = math.radians(90 * t)
        return (c[0] + 2.0 * math.cos(a), c[1] + 2.0 * math.sin(a)), 0.0
    _stones_along(bm, along, 3, ROCK, random.Random(5))
    finish(rig)
    return {"category": "ground", "budget": "small", "footprint": (4.0, 4.0)}


def dirt_patch():
    """Plaque de terre retournée, bosselée, avec quelques cailloux. 4 × 4 m."""
    rig = Rig("dirt_patch", start("dirt_patch"))
    DIRT, ROCK = rig.m("Env_Dirt"), rig.m("Env_Rock")
    bm = rig.part("Ground", (0, 0, 0))
    rnd = random.Random(8)
    poly = []
    for k in range(14):
        a = 2 * math.pi * k / 14
        r = rnd.uniform(1.4, 1.9)
        poly.append((r * math.cos(a), r * math.sin(a)))
    extrude_xy(bm, poly, 0.0, 0.03, DIRT)
    for _ in range(5):
        x, y = rnd.uniform(-1.0, 1.0), rnd.uniform(-1.0, 1.0)
        blob(bm, (x, y, 0.0), (rnd.uniform(0.3, 0.5), rnd.uniform(0.3, 0.5), 0.1), DIRT, subdiv=2, noise=0.3,
             seed=rnd.randint(0, 99), flatten_bottom=0.0)
    for _ in range(6):
        x, y = rnd.uniform(-1.4, 1.4), rnd.uniform(-1.4, 1.4)
        blob(bm, (x, y, 0.03), (0.09, 0.08, 0.06), ROCK, subdiv=1, noise=0.3, seed=rnd.randint(0, 99))
    finish(rig)
    return {"category": "ground", "budget": "medium", "footprint": (4.0, 4.0)}


def flowerbed():
    """Massif surélevé de 2 × 4 m : bordure en brique, terreau bombé fleuri, quelques
    grandes fleurs en relief."""
    rig = Rig("flowerbed", start("flowerbed"))
    BRICK, FLOWERS, PAINT_Y, PAINT_P = (rig.m(n) for n in ("Env_Brick", "Env_Flowers", "Env_Paint:yellow",
                                                            "Env_Paint:pink"))
    bm = rig.part("Ground", (0, 0, 0))
    rnd = random.Random(12)
    W, D, H = 1.95, 0.95, 0.3
    for x0, y0, x1, y1 in ((-W, -D, W, -D + 0.14), (-W, D - 0.14, W, D), (-W, -D, -W + 0.14, D),
                           (W - 0.14, -D, W, D)):
        _rect(bm, x0, y0, x1, y1, 0.0, H, BRICK)
    blob(bm, (0, 0, H - 0.05), (W - 0.2, D - 0.2, 0.22), FLOWERS, subdiv=3, noise=0.12, seed=3,
         flatten_bottom=-0.2)
    for i in range(6):                      # grandes fleurs : tige + corolle
        x, y = rnd.uniform(-W + 0.4, W - 0.4), rnd.uniform(-D + 0.35, D - 0.35)
        top = Vector((x, y, H + 0.35 + rnd.uniform(0, 0.15)))
        cyl(bm, (x, y, H + 0.05), top, 0.02, 0.015, FLOWERS, seg=4)
        mi = PAINT_Y if i % 2 else PAINT_P
        for k in range(5):
            a = 2 * math.pi * k / 5
            ellipsoid(bm, top + Vector((0.07 * math.cos(a), 0.07 * math.sin(a), 0)), (0.06, 0.06, 0.02), mi, u=5, v=3)
        ellipsoid(bm, top + Vector((0, 0, 0.015)), (0.035, 0.035, 0.025), PAINT_Y if mi == PAINT_P else PAINT_P,
                  u=6, v=3)
    finish(rig)
    return {"category": "ground", "budget": "medium", "footprint": (4.0, 2.0)}


BUILDERS = {f.__name__: f for f in (road_straight, road_curve, road_t, road_cross, road_end, road_crosswalk,
                                    driveway, path_straight, path_curve, dirt_patch, flowerbed)}

if __name__ == "__main__":
    run(BUILDERS)
