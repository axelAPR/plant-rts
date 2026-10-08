# plantRTS — Zombie classique / Browncoat (qualité de référence, gabarit zombie_ref).
import math
from mathutils import Vector, Matrix, Quaternion

SMOOTH = {"Hips": 1, "LegL": 1, "LegR": 1, "Torso": 1, "Head": 1, "ArmL": 1, "ArmR": 1}


def build():
    col = reset_scene("Browncoat")
    rig = Rig("Browncoat", col)
    k = zombie_ref(rig, {"skin": "ZombieRef_Skin", "shirt": "Ref_Brown", "pants": "Ref_Grey", "shoes": "Ref_Black",
                         "forearm": "Ref_Brown"}, pose="zombie", eye_sizes=(0.082, 0.06), lids=(0.15, 0.5), hunch=1.4)
    BRN, WH, RED, HB = rig.m("Ref_Brown"), rig.m("Ref_White"), rig.m("Ref_Red"), rig.m("Ref_HairBlack")
    c = k["chest_c"]

    # Chemise, cravate, revers
    bm = rig.part("Shirt", k["torso"], "Torso")
    f = k["front"]
    ellipsoid(bm, f(1.2) + Vector((0, 0.03, 0)), (0.13, 0.06, 0.2), WH, u=12, v=8)
    tie_top, tie_bot = f(1.3) + Vector((0, -0.02, 0)), f(1.02) + Vector((0, -0.03, 0))
    box(bm, (tie_top + tie_bot) / 2, (0.065, 0.025, (tie_top - tie_bot).length), RED, rot=align_z(tie_top - tie_bot), bevel=0.012)
    box(bm, tie_top + Vector((0, -0.005, 0.0)), (0.08, 0.04, 0.06), RED, bevel=0.015)
    for s_ in (-1, 1):
        p_ = f(1.22, 0.12 * s_)
        box(bm, p_ + Vector((0, -0.01, 0)), (0.08, 0.035, 0.24), BRN, rot=Quaternion((0, 1, 0), math.radians(-20 * s_)), bevel=0.015)

    # Pans du manteau
    bm = rig.part("Coat", k["hip"], "Hips")
    for x, y, rz, w in ((0.17, -0.1, 15, 0.25), (-0.17, -0.1, -15, 0.25), (0.0, 0.12, 0, 0.5)):
        box(bm, (x, y, 0.62), (w, 0.09, 0.44), BRN, rot=Quaternion((0, 0, 1), math.radians(rz)), bevel=0.035)

    # Cheveux en bataille (mèches)
    hc, hr = k["head_c"], k["head_r"]
    bm = rig.part("Hair", k["neck"], "Head")
    for d in ((0.2, 0.25, 1), (-0.3, 0.2, 1), (0.0, 0.6, 0.8), (0.5, 0.45, 0.6), (-0.5, 0.55, 0.5), (0.1, -0.15, 1)):
        dv = Vector(d).normalized()
        p, _ = surface_point(hc, hr, dv)
        q = Vector((0, 1, 0)).rotation_difference((dv + Vector((0, 0.35, 0.2))).normalized())
        organic_leaf(bm, 0.15, 0.055, Matrix.Translation(p - dv * 0.03) @ q.to_matrix().to_4x4(), HB,
                     n=3, lift=0.02, droop=0.05, fold=0.02, twist=0.4, th=0.02, petiole=0.5)

    rig.empty("Muzzle", (0, -0.8, 1.22), "Torso")
    rig.build(smooth_angle=45.0, subdiv=dict(SMOOTH, Shirt=1, Coat=1, Hair=1))
    return col
