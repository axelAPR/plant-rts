# plantRTS — All-Star zombie (qualité de référence, gabarit zombie_ref).
import math
from mathutils import Vector, Matrix, Quaternion

SMOOTH = {"Hips": 1, "LegL": 1, "LegR": 1, "Torso": 1, "Head": 1, "ArmL": 1, "ArmR": 1}


def build():
    col = reset_scene("AllStar")
    rig = Rig("AllStar", col)
    k = zombie_ref(rig, {"skin": "ZombieRef_Skin", "shirt": "Ref_Red", "pants": "Ref_White", "shoes": "Ref_Black"},
                   bulk=1.3, pose="gun", eye_sizes=(0.07, 0.07), lids=(0.45, 0.45), hunch=0.6)
    RED, WH, MD, MET, BRN = (rig.m(n) for n in ("Ref_Red", "Ref_White", "Ref_MetalDark", "Ref_Metal", "Ref_Leather"))
    hc, hr = k["head_c"], k["head_r"]

    # Casque de football : coque, bande, protège-joues, grille
    bm = rig.part("Helmet", k["neck"], "Head")
    dome(bm, hc + Vector((0, 0.035, 0.07)), hr[0] * 1.17, hr[1] * 1.16, hr[2] * 0.98, RED, seg=16, steps=5)
    box(bm, hc + Vector((0, 0.06, 0.28)), (0.07, 0.4, 0.06), WH, bevel=0.025)
    for s in (-1, 1):
        box(bm, hc + Vector((0.205 * s, 0.03, -0.04)), (0.06, 0.24, 0.24), RED, bevel=0.04)
    bm = rig.part("Facemask", k["neck"], "Helmet")
    fy = hc.y - hr[1] - 0.06
    for dz in (-0.1, -0.19):
        tube_path(bm, [(-0.21, fy + 0.07, hc.z + dz), (0, fy, hc.z + dz), (0.21, fy + 0.07, hc.z + dz)], [0.014] * 3, 6, MD)
    for x in (-0.07, 0.07):
        cyl(bm, (x, fy + 0.005, hc.z - 0.22), (x, fy + 0.01, hc.z - 0.06), 0.014, 0.014, MD, seg=6)
    for s in (-1, 1):
        cyl(bm, (0.21 * s, fy + 0.07, hc.z - 0.1), (0.21 * s, hc.y - 0.02, hc.z - 0.02), 0.014, 0.014, MD, seg=6)

    # Épaulières, numéro, bandes de manches
    bm = rig.part("Pads", k["torso"], "Torso")
    for s in (-1, 1):
        dome(bm, k["shoulder" + ("L" if s > 0 else "R")] + Vector((-0.05 * s, 0.0, 0.03)), 0.24, 0.23, 0.15, RED, seg=14, steps=4)
    f = k["front"]
    box(bm, f(1.15) + Vector((0, -0.02, 0)), (0.22, 0.04, 0.22), WH, bevel=0.02)
    box(bm, f(1.15) + Vector((0, -0.04, 0)), (0.12, 0.04, 0.13), RED, bevel=0.015)
    for s in (-1, 1):
        side = "L" if s > 0 else "R"
        mid = (k["elbow" + side] + k["shoulder" + side]) / 2
        cyl(bm, mid + Vector((0, 0, -0.035)), mid + Vector((0, 0, 0.035)), 0.125, 0.125, WH, seg=12)

    # Canon à ballons
    hand = k["handR"]
    bm = rig.part("Weapon", hand, "ArmR")
    x, z = -0.1, 1.05
    lathe(bm, [(0, 0), (0.17, 0), (0.18, 0.05), (0.18, 0.32), (0.16, 0.36), (0, 0.36)], 16,
          Matrix.Translation((x, -0.14, z)) @ align_z((0, -1, 0)).to_matrix().to_4x4(), MET)
    for a in range(6):
        t = math.radians(60 * a)
        o = Vector((math.cos(t) * 0.085, 0, math.sin(t) * 0.085))
        cyl(bm, Vector((x, -0.48, z)) + o, Vector((x, -0.96, z)) + o, 0.036, 0.036, MD, seg=8)
    cyl(bm, (x, -0.9, z), (x, -0.97, z), 0.135, 0.135, MD, seg=16)
    ellipsoid(bm, (x - 0.02, -0.25, z + 0.22), (0.1, 0.16, 0.1), BRN, u=12, v=8)
    box(bm, (x - 0.02, -0.25, z + 0.3), (0.02, 0.12, 0.02), WH, bevel=0.005)
    rig.empty("Muzzle", (x, -1.02, z), "Weapon")

    rig.build(smooth_angle=45.0, subdiv=dict(SMOOTH, Helmet=1, Pads=1))
    return col
