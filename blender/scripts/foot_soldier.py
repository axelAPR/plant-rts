# plantRTS — Soldat zombie (qualité de référence, gabarit zombie_ref).
import math
from mathutils import Vector, Matrix, Quaternion


def build():
    col = reset_scene("FootSoldier")
    rig = Rig("FootSoldier", col)
    k = zombie_ref(rig, {"skin": "ZombieRef_Skin", "shirt": "Ref_Olive", "pants": "Ref_OliveDark", "shoes": "Ref_Black"},
                   pose="gun", lids=(0.4, 0.15))
    OL, OD, LE, MD, MET = (rig.m(n) for n in ("Ref_Olive", "Ref_OliveDark", "Ref_Leather", "Ref_MetalDark", "Ref_Metal"))

    # Casque : coque arrondie, rebord, jugulaire
    hc, hr = k["head_c"], k["head_r"]
    bm = rig.part("Helmet", k["neck"], "Head")
    dome(bm, hc + Vector((0, 0.03, 0.1)), hr[0] * 1.15, hr[1] * 1.2, hr[2] * 0.82, OL, seg=16, steps=5)
    lathe(bm, [(0, 0), (hr[0] * 1.28, 0), (hr[0] * 1.26, 0.03), (0, 0.03)], 16, Matrix.Translation(hc + Vector((0, 0.03, 0.09))), OD)

    # Gilet tactique (pièce du torse), poches, ceinturon
    c = k["chest_c"]
    bm = rig.part("Vest", k["torso"], "Torso")
    box(bm, c + Vector((0, -0.04, -0.03)), (0.6, 0.44, 0.46), OD, bevel=0.09)
    for x in (-0.14, 0.0, 0.14):
        box(bm, c + Vector((x, -0.27, -0.12)), (0.11, 0.07, 0.13), OL, bevel=0.025)
    box(bm, c + Vector((0.18, -0.27, 0.1)), (0.08, 0.04, 0.03), MET, bevel=0.01)
    bm = rig.part("Belt", k["hip"], "Hips")
    lathe(bm, [(0, 0.88), (0.27, 0.88), (0.275, 0.95), (0, 0.95)], 16, Matrix(), LE)
    for v in bm.verts:
        v.co.y *= 0.75
    box(bm, (0, -0.205, 0.915), (0.08, 0.03, 0.06), MET, bevel=0.01)

    # Fusil d'assaut (non lissé : objet manufacturé)
    hand = k["handR"]
    bm = rig.part("Weapon", hand, "ArmR")
    x, z = -0.05, 1.07
    box(bm, (x, -0.46, z), (0.09, 0.38, 0.14), MD, bevel=0.025)
    box(bm, (x, -0.16, z - 0.03), (0.08, 0.26, 0.13), OD, bevel=0.03)
    box(bm, (x, -0.72, z - 0.01), (0.085, 0.16, 0.1), OD, bevel=0.02)
    cyl(bm, (x, -0.77, z + 0.01), (x, -1.06, z + 0.01), 0.028, 0.028, MD, seg=10)
    box(bm, (x, -0.52, z - 0.14), (0.065, 0.09, 0.17), MD, rot=Quaternion((1, 0, 0), math.radians(-12)), bevel=0.012)
    box(bm, (x, -0.46, z + 0.1), (0.045, 0.17, 0.05), MD, bevel=0.012)
    rig.empty("Muzzle", (x, -1.08, z + 0.01), "Weapon")

    rig.build(smooth_angle=45.0, subdiv={"Hips": 1, "LegL": 1, "LegR": 1, "Torso": 1, "Head": 1, "ArmL": 1, "ArmR": 1,
                                          "Helmet": 1, "Vest": 1})
    return col
