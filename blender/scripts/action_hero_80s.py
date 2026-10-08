# plantRTS — 80s Action Hero zombie (qualité de référence, gabarit zombie_ref).
import math
from mathutils import Vector, Matrix, Quaternion

SMOOTH = {"Hips": 1, "LegL": 1, "LegR": 1, "Torso": 1, "Head": 1, "ArmL": 1, "ArmR": 1}


def build():
    col = reset_scene("ActionHero")
    rig = Rig("ActionHero", col)
    k = zombie_ref(rig, {"skin": "ZombieRef_Skin", "shirt": "Ref_Black", "pants": "Ref_Olive", "shoes": "Ref_Black",
                         "sleeve": "ZombieRef_Skin"}, bulk=1.25, pose="gun", eye_sizes=(0.064, 0.058), lids=(0.5, 0.45),
                   jaw=1.5, hunch=0.5)
    RED, HB, LE, GOLD, OD, MD, SK = (rig.m(n) for n in ("Ref_Red", "Ref_HairBlack", "Ref_Leather", "Ref_Gold",
                                                        "Ref_OliveDark", "Ref_MetalDark", "ZombieRef_Skin"))
    hc, hr = k["head_c"], k["head_r"]

    # Coupe mulet + bandeau rouge flottant
    bm = rig.part("Hair", k["neck"], "Head")
    dome(bm, hc + Vector((0, 0.02, 0.08)), hr[0] * 1.06, hr[1] * 1.08, hr[2] * 0.84, HB, seg=16, steps=5)
    tube_path(bm, [hc + Vector((0, 0.1, 0.0)), hc + Vector((0, 0.16, -0.15)), hc + Vector((0, 0.2, -0.32))],
              [hr[0] * 0.85, hr[0] * 0.7, hr[0] * 0.45], 12, HB)
    bm = rig.part("Headband", k["neck"], "Head")
    lathe(bm, [(0, 0), (hr[0] * 1.08, 0), (hr[0] * 1.09, 0.03), (hr[0] * 1.08, 0.065), (0, 0.065)], 16,
          Matrix.Translation(hc + Vector((0, 0.0, 0.06))), RED)
    for s in (-1, 1):
        mtx = Matrix.Translation(hc + Vector((0.04 * s, hr[1] * 0.98, 0.09))) @ Matrix.Rotation(math.radians(20 * s), 4, 'Z') \
            @ Matrix.Rotation(math.radians(-35), 4, 'X')
        organic_leaf(bm, 0.32, 0.065, mtx, RED, n=4, lift=0.03, droop=0.08, fold=0.0, twist=0.5 * s, th=0.02, petiole=0.9)

    # Débardeur moulant (pectoraux), cartouchière en bandoulière, ceinturon
    bm = rig.part("Gear", k["torso"], "Torso")
    f = k["front"]
    ellipsoid(bm, f(1.34) + Vector((0, 0.02, 0.0)), (0.13, 0.05, 0.05), SK, u=10, v=6)      # encolure
    a, b = f(1.34, 0.2), f(0.94, -0.2)
    for t in range(10):
        p = a.lerp(b, (t + 0.5) / 10)
        x = p.x
        z = p.z
        p = f(z, x) + Vector((0, -0.025, 0))
        rot = align_z(b - a)
        box(bm, p, (0.075, 0.035, 0.055), LE, rot=rot, bevel=0.01)
        cyl(bm, p + Vector((0, -0.02, -0.01)), p + Vector((0, -0.02, 0.05)), 0.013, 0.008, GOLD, seg=6)
    bm = rig.part("Belt", k["hip"], "Hips")
    lathe(bm, [(0, 0.88), (0.33, 0.88), (0.335, 0.955), (0, 0.955)], 16, Matrix(), LE)
    for v in bm.verts:
        v.co.y *= 0.75
    box(bm, (0, -0.25, 0.915), (0.1, 0.03, 0.07), GOLD, bevel=0.012)

    # Lance-roquettes sur l'épaule droite
    hand = k["handR"]
    bm = rig.part("Weapon", hand, "ArmR")
    x, z = -0.52, 1.5
    lathe(bm, [(0, 0), (0.14, 0), (0.14, 0.08), (0.12, 0.1), (0.12, 1.08), (0.145, 1.12), (0.145, 1.2), (0, 1.2)], 16,
          Matrix.Translation((x, 0.5, z)) @ align_z((0, -1, 0)).to_matrix().to_4x4(), OD)
    box(bm, (x - 0.13, -0.1, z + 0.06), (0.06, 0.15, 0.1), MD, bevel=0.02)
    tube_path(bm, [Vector((x, -0.25, z - 0.1)), hand + Vector((0, 0, 0.05))], [0.03, 0.03], 8, MD)
    rig.empty("Muzzle", (x, -0.76, z), "Weapon")

    rig.build(smooth_angle=45.0, subdiv=dict(SMOOTH, Hair=1, Headband=1))
    return col
