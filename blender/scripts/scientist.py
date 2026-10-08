# plantRTS — Scientifique zombie (qualité de référence, gabarit zombie_ref).
import math
from mathutils import Vector, Matrix, Quaternion

SMOOTH = {"Hips": 1, "LegL": 1, "LegR": 1, "Torso": 1, "Head": 1, "ArmL": 1, "ArmR": 1}


def build():
    col = reset_scene("Scientist")
    rig = Rig("Scientist", col)
    k = zombie_ref(rig, {"skin": "ZombieRef_Skin", "shirt": "Ref_White", "pants": "Ref_Grey", "shoes": "Ref_Black",
                         "sleeve": "Ref_White"}, pose="gun", eye_sizes=(0.072, 0.068), lids=(0.1, 0.1))
    WH, LB, RED, HG, MD, MET, GOO = (rig.m(n) for n in ("Ref_White", "Ref_LightBlue", "Ref_Red", "Ref_HairGrey",
                                                        "Ref_MetalDark", "Ref_Metal", "Ref_Goo"))
    c = k["chest_c"]

    # Blouse : col ouvert, chemise, nœud papillon, stylos ; pans longs
    bm = rig.part("Shirt", k["torso"], "Torso")
    f = k["front"]
    ellipsoid(bm, f(1.2) + Vector((0, 0.03, 0)), (0.12, 0.06, 0.2), LB, u=12, v=8)
    for s_ in (-1, 1):
        ellipsoid(bm, f(1.31) + Vector((0.045 * s_, -0.015, 0)), (0.05, 0.025, 0.034), RED, u=8, v=5)
        p_ = f(1.2, 0.13 * s_)
        box(bm, p_ + Vector((0, -0.01, 0)), (0.08, 0.035, 0.26), WH, rot=Quaternion((0, 1, 0), math.radians(-18 * s_)), bevel=0.015)
    for x, m in ((0.17, RED), (0.2, LB)):
        p_ = f(1.12, x)
        cyl(bm, p_ + Vector((0, -0.02, 0)), p_ + Vector((0, -0.02, 0.11)), 0.013, 0.013, m, seg=6)
    bm = rig.part("Coat", k["hip"], "Hips")
    for x, y, rz, w in ((0.17, -0.1, 15, 0.26), (-0.17, -0.1, -15, 0.26), (0.0, 0.12, 0, 0.5)):
        box(bm, (x, y, 0.58), (w, 0.09, 0.54), WH, rot=Quaternion((0, 0, 1), math.radians(rz)), bevel=0.035)

    # Calvitie + touffes grises ; lunettes rondes (montures seules)
    hc, hr = k["head_c"], k["head_r"]
    bm = rig.part("Hair", k["neck"], "Head")
    for s in (-1, 1):
        for dz, dy, r in ((0.03, 0.05, 0.07), (-0.05, 0.09, 0.065), (0.07, 0.13, 0.06)):
            ellipsoid(bm, hc + Vector((0.2 * s, dy, dz)), (r, r * 1.1, r), HG, u=10, v=6)
    bm = rig.part("Glasses", k["neck"], "Head")
    for s in (-1, 1):
        p = k["eye" + ("L" if s > 0 else "R")]
        lathe(bm, [(0.085, 0), (0.105, 0), (0.105, 0.025), (0.085, 0.025), (0.085, 0)], 16,
              Matrix.Translation(p + Vector((0, -0.06, 0))) @ align_z((0, 1, 0)).to_matrix().to_4x4(), MD)
    cyl(bm, k["eyeL"] + Vector((-0.1, -0.065, 0)), k["eyeR"] + Vector((0.1, -0.065, 0)), 0.013, 0.013, MD, seg=6)

    # Pistolet à gelée
    hand = k["handR"]
    bm = rig.part("Weapon", hand, "ArmR")
    x, z = -0.06, 1.06
    box(bm, (x, -0.42, z), (0.13, 0.34, 0.16), MET, bevel=0.04)
    lathe(bm, [(0, 0), (0.05, 0), (0.07, 0.26), (0.08, 0.3), (0, 0.3)], 12, Matrix.Translation((x, -0.57, z)) @ align_z((0, -1, 0)).to_matrix().to_4x4(), MD)
    cyl(bm, (x, -0.3, z + 0.11), (x, -0.52, z + 0.11), 0.075, 0.075, GOO, seg=12)
    box(bm, (x, -0.26, z - 0.1), (0.07, 0.08, 0.17), MD, rot=Quaternion((1, 0, 0), math.radians(15)), bevel=0.02)
    rig.empty("Muzzle", (x, -0.89, z), "Weapon")

    rig.build(smooth_angle=45.0, subdiv=dict(SMOOTH, Shirt=1, Coat=1, Hair=1))
    return col
