# plantRTS — Super Brainz (qualité de référence, gabarit zombie_ref).
import math
from mathutils import Vector, Matrix, Quaternion

SMOOTH = {"Hips": 1, "LegL": 1, "LegR": 1, "Torso": 1, "Head": 1, "ArmL": 1, "ArmR": 1}


def build():
    col = reset_scene("SuperBrainz")
    rig = Rig("SuperBrainz", col)
    k = zombie_ref(rig, {"skin": "ZombieRef_Skin", "shirt": "Ref_Blue", "pants": "Ref_Blue", "shoes": "Ref_Red",
                         "forearm": "Ref_Yellow", "hand": "Ref_Yellow"}, bulk=1.45, pose="down", head_scale=0.95,
                   eye_sizes=(0.066, 0.066), lids=(0.3, 0.3), jaw=1.8, hunch=0.2)
    BL, RED, YE, PU, BR = (rig.m(n) for n in ("Ref_Blue", "Ref_Red", "Ref_Yellow", "Ref_Purple", "Ref_Brain"))
    hc, hr = k["head_c"], k["head_r"]

    # Masque violet (bande autour des yeux) et cerveau apparent
    bm = rig.part("Mask", k["neck"], "Head")
    eye_z = k["eyeL"].z
    lathe(bm, [(0, -0.05), (hr[0] * 1.03, -0.05), (hr[0] * 1.07, 0.0), (hr[0] * 1.03, 0.05), (0, 0.05)], 16,
          Matrix.Translation(Vector((hc.x, hc.y, eye_z))) @ Matrix.Diagonal((1, 0.98, 1, 1)), PU)
    bm = rig.part("Brain", k["neck"], "Head")
    lathe(bm, [(0, 0), (hr[0] * 0.92, 0), (hr[0] * 0.96, 0.08), (hr[0] * 0.78, 0.17), (hr[0] * 0.36, 0.23), (0, 0.24)],
          16, Matrix.Translation(hc + Vector((0, 0.01, hr[2] * 0.6))), BR, ridge=0.14)
    tube_path(bm, [hc + Vector((0, -0.12, hr[2] * 0.6 + 0.18)), hc + Vector((0, 0.0, hr[2] * 0.6 + 0.25)),
                   hc + Vector((0, 0.13, hr[2] * 0.6 + 0.18))], [0.02, 0.02, 0.02], 6, BR)

    # Cape, emblème, ceinture, slip rouge
    bm = rig.part("Cape", k["torso"], "Torso")
    c, cr = k["chest_c"], k["chest_r"]
    for s in (-1, 1):
        ellipsoid(bm, k["shoulder" + ("L" if s > 0 else "R")] + Vector((0, 0.06, 0.05)), (0.14, 0.11, 0.08), RED, u=10, v=6)
    box(bm, Vector((0, 0.2, 0.95)), (0.7, 0.05, 0.95), RED, rot=Quaternion((1, 0, 0), math.radians(-10)), bevel=0.025)
    f = k["front"]
    p0 = f(1.18)
    lathe(bm, [(0, 0), (0.13, 0), (0.13, 0.03), (0, 0.03)], 20, Matrix.Translation(p0 + Vector((0, 0.01, 0))) @ align_z((0, -1, 0)).to_matrix().to_4x4(), YE)
    for dz, ry in ((0.055, 0), (-0.055, 0), (0.0, 50)):
        box(bm, p0 + Vector((0, -0.03, dz)), (0.16, 0.02, 0.035), RED, rot=Quaternion((0, 1, 0), math.radians(ry)), bevel=0.006)
    bm = rig.part("Belt", k["hip"], "Hips")
    lathe(bm, [(0, 0.86), (0.4, 0.86), (0.41, 0.95), (0, 0.95)], 16, Matrix(), YE)
    lathe(bm, [(0, 0.64), (0.33, 0.64), (0.385, 0.76), (0.395, 0.87), (0, 0.87)], 16, Matrix(), RED)
    for v in bm.verts:
        v.co.y *= 0.75

    # Gros poings jaunes
    for s in (-1, 1):
        side = "L" if s > 0 else "R"
        ellipsoid(rig.bm("Arm" + side), k["hand" + side] + Vector((0, 0, -0.04)), (0.14, 0.14, 0.14), YE, u=12, v=8)
    rig.empty("Muzzle", (0, -0.6, 1.2), "Torso")

    rig.build(smooth_angle=45.0, subdiv=dict(SMOOTH, Mask=1, Brain=1, Cape=1, Belt=1))
    return col
