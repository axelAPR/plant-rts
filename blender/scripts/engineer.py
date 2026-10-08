# plantRTS — Ingénieur zombie (qualité de référence, gabarit zombie_ref).
import math
from mathutils import Vector, Matrix, Quaternion

SMOOTH = {"Hips": 1, "LegL": 1, "LegR": 1, "Torso": 1, "Head": 1, "ArmL": 1, "ArmR": 1}


def build():
    col = reset_scene("Engineer")
    rig = Rig("Engineer", col)
    k = zombie_ref(rig, {"skin": "ZombieRef_Skin", "shirt": "Ref_LightBlue", "pants": "Ref_Denim", "shoes": "Ref_Leather"},
                   pose="gun", eye_sizes=(0.066, 0.078), lids=(0.2, 0.45))
    YE, OR, WH, LE, MD, MY, WD, MET = (rig.m(n) for n in ("Ref_Yellow", "Ref_Orange", "Ref_White", "Ref_Leather",
                                                          "Ref_MetalDark", "Ref_MechYellow", "Ref_Wood", "Ref_Metal"))
    hc, hr = k["head_c"], k["head_r"]

    # Casque de chantier : coque, visière avant, nervure
    bm = rig.part("Hardhat", k["neck"], "Head")
    dome(bm, hc + Vector((0, 0.02, 0.1)), hr[0] * 1.12, hr[1] * 1.15, hr[2] * 0.85, YE, seg=16, steps=5)
    lathe(bm, [(0, 0), (hr[0] * 1.3, 0), (hr[0] * 1.28, 0.025), (0, 0.025)], 16,
          Matrix.Translation(hc + Vector((0, -0.04, 0.09))) @ Matrix.Diagonal((1, 1.12, 1, 1)), YE)
    box(bm, hc + Vector((0, 0.02, 0.27)), (0.06, 0.38, 0.06), YE, bevel=0.025)

    # Gilet haute visibilité + bandes réfléchissantes
    c = k["chest_c"]
    bm = rig.part("Vest", k["torso"], "Torso")
    k["shell"](bm, 0.9, 1.33, OR, grow=0.035)
    for z in (1.0, 1.15):
        k["shell"](bm, z, z + 0.065, WH, grow=0.05, steps=1)

    # Ceinture à outils
    bm = rig.part("Belt", k["hip"], "Hips")
    lathe(bm, [(0, 0.88), (0.28, 0.88), (0.285, 0.955), (0, 0.955)], 16, Matrix(), LE)
    for v in bm.verts:
        v.co.y *= 0.75
    box(bm, (0.25, -0.08, 0.86), (0.1, 0.12, 0.15), LE, bevel=0.025)
    cyl(bm, (-0.28, -0.04, 0.98), (-0.28, -0.04, 0.72), 0.022, 0.022, WD, seg=8)
    box(bm, (-0.28, -0.04, 0.99), (0.05, 0.16, 0.05), MD, bevel=0.012)

    # Lance-béton
    hand = k["handR"]
    bm = rig.part("Weapon", hand, "ArmR")
    x, z = -0.06, 1.06
    box(bm, (x, -0.4, z), (0.21, 0.44, 0.23), MY, bevel=0.05)
    lathe(bm, [(0, 0), (0.085, 0), (0.075, 0.38), (0.1, 0.4), (0.1, 0.46), (0, 0.46)], 14,
          Matrix.Translation((x, -0.58, z)) @ align_z((0, -1, 0)).to_matrix().to_4x4(), MD)
    lathe(bm, [(0, 0), (0.1, 0), (0.13, 0.18), (0, 0.18)], 14, Matrix.Translation((x, -0.36, z + 0.1)), MET)
    box(bm, (x, -0.12, z - 0.04), (0.12, 0.2, 0.12), MD, bevel=0.025)
    rig.empty("Muzzle", (x, -1.06, z), "Weapon")

    rig.build(smooth_angle=45.0, subdiv=dict(SMOOTH, Hardhat=1, Vest=1))
    return col
