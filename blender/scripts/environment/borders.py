# plantRTS — Kit d'environnement : bordures de carte (lot 9).
# blender -b --python blender/scripts/environment/borders.py -- [ids…] [--render]
#
# Pièces hautes qui ferment les bords de la carte : segments de 8 m le long de X
# (de -4 à +4 m), centrés sur leur pivot ; angle de 2 × 2 m à bras de 1 m vers -X et
# -Y (un segment centré à 5 m du centre s'y raccorde). Haie haute de 3 m, palissade
# de 2,5 m : elles bornent la vue sans écraser les maisons (≤ 5,5 m).

import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from env_lib import *  # noqa: F401,F403
import bmesh
from mathutils import Vector, Matrix

TALL_H, TALL_W = 3.0, 1.4
TO_Y = Matrix.Rotation(math.radians(90), 4, 'Z')


def _profile():
    r = 0.5
    pts = [(-TALL_W / 2, 0.0), (TALL_W / 2, 0.0)]
    for i in range(5):
        a = math.radians(90 * i / 4)
        pts.append((TALL_W / 2 - r + r * math.cos(a), TALL_H - r + r * math.sin(a)))
    for i in range(5):
        a = math.radians(90 + 90 * i / 4)
        pts.append((-TALL_W / 2 + r + r * math.cos(a), TALL_H - r + r * math.sin(a)))
    return pts


def _tall_hedge(bm, a, b, M, rnd):
    """Haie haute de x = a à b : corps profilé, touffes en relief (dessus et flancs)."""
    mtx = Matrix.Translation(((a + b) / 2, 0, 0)) @ Matrix.Rotation(math.radians(90), 4, 'Z')
    prism(bm, _profile(), b - a, mtx, M["leaf"])
    n = max(1, round((b - a) / 1.3))
    r = min(0.6, (b - a) / 3.2)
    for i in range(n):
        x = a + (b - a) * (i + 0.5) / n
        x = min(max(x, a + r * 1.5), b - r * 1.5) if b - a > 3.2 * r else (a + b) / 2
        blob(bm, (x, rnd.uniform(-0.15, 0.15), TALL_H - 0.15), (r, 0.5, 0.3), M["leaf"], subdiv=2, noise=0.3,
             seed=rnd.randint(0, 999))
        for s in (-1, 1):
            blob(bm, (x, s * (TALL_W / 2 - 0.05), rnd.uniform(0.8, 2.2)), (r * 0.8, 0.18, 0.45),
                 M["dark"], subdiv=2, noise=0.3, seed=rnd.randint(0, 999))
    box(bm, ((a + b) / 2, 0, 0.02), (b - a, TALL_W + 0.3, 0.04), M["mulch"])


def _hedge_rig(model):
    rig = Rig(model, start(model))
    M = {"leaf": rig.m("Env_Hedge"), "dark": rig.m("Env_FoliageDark"), "mulch": rig.m("Env_Dirt")}
    return rig, M, rig.part("Border", (0, 0, 0))


def border_hedge_straight():
    rig, M, bm = _hedge_rig("border_hedge_straight")
    _tall_hedge(bm, -4.0, 4.0, M, random.Random(400))
    finish(rig, smooth_angle=60.0)
    return {"category": "borders", "budget": "medium", "footprint": (8.0, 2.0)}


def border_hedge_corner():
    rig, M, bm = _hedge_rig("border_hedge_corner")
    rnd = random.Random(401)
    _tall_hedge(bm, -1.0, TALL_W / 2, M, rnd)
    build_transformed(bm, TO_Y, lambda b: _tall_hedge(b, -1.0, -TALL_W / 2, M, rnd))
    finish(rig, smooth_angle=60.0)
    return {"category": "borders", "budget": "medium", "footprint": (2.0, 2.0)}


def border_fence_straight():
    """Palissade de bois de 2,5 m sur 8 m : planches jointives à pointes, deux lisses,
    poteaux tous les 2 m (décalés d'1 m depuis les bouts : pas régulier d'une pièce à
    l'autre), quelques planches de travers."""
    rig = Rig("border_fence_straight", start("border_fence_straight"))
    PLANK, WOOD, DARK = rig.m("Env_WoodPlanks"), rig.m("Env_Trim:wood"), rig.m("Env_WoodDark")
    bm = rig.part("Border", (0, 0, 0))
    rnd = random.Random(402)
    step = 0.4
    for i in range(round(8.0 / step)):
        x = -4.0 + step * (i + 0.5)
        h = 2.5 - rnd.uniform(0, 0.08)
        pts = [(-0.19, 0.0), (0.19, 0.0), (0.19, h - 0.15), (0.0, h), (-0.19, h - 0.15)]
        tilt = math.radians(rnd.uniform(-1.2, 1.2)) if 0 < i < round(8.0 / step) - 1 else 0.0
        prism(bm, pts, 0.05, Matrix.Translation((x, -0.03, 0)) @ Matrix.Rotation(tilt, 4, 'Y'),
              DARK if i % 7 == 3 else PLANK)
    for z in (0.5, 2.0):
        box(bm, (0, 0.05, z), (8.0, 0.05, 0.14), WOOD)
    for x in (-3.0, -1.0, 1.0, 3.0):
        box(bm, (x, 0.12, 1.2), (0.16, 0.12, 2.4), WOOD)
    finish(rig, smooth_angle=30.0)
    return {"category": "borders", "budget": "medium", "footprint": (8.0, 2.0)}


BUILDERS = {f.__name__: f for f in (border_hedge_straight, border_hedge_corner, border_fence_straight)}

if __name__ == "__main__":
    run(BUILDERS)
