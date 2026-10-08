# plantRTS — Deadbeard, capitaine pirate zombie (qualité de référence, gabarit zombie_ref).
import math
import bmesh
from mathutils import Vector, Matrix, Quaternion

SMOOTH = {"Hips": 1, "LegL": 1, "LegR": 1, "Torso": 1, "Head": 1, "ArmL": 1, "ArmR": 1}


def build():
    col = reset_scene("Deadbeard")
    rig = Rig("Deadbeard", col)
    k = zombie_ref(rig, {"skin": "ZombieRef_Skin", "shirt": "Ref_Red", "pants": "Ref_Black", "shoes": "Ref_Black"},
                   pose="gun", eye_sizes=(0.082, 0.06), lids=(0.2, 0.3), jaw=1.3)
    RED, WH, BK, GOLD, HB, WD, MD, MET = (rig.m(n) for n in ("Ref_Red", "Ref_White", "Ref_Black", "Ref_Gold", "Ref_HairBlack",
                                                             "Ref_Wood", "Ref_MetalDark", "Ref_Metal"))
    GR, YE, RD = rig.m("PlantRef_Head"), rig.m("PlantRef_Yellow"), rig.m("PlantRef_Orange")
    hc, hr = k["head_c"], k["head_r"]

    # Jambe de bois à droite (remplace la jambe du gabarit)
    hip = Vector((-0.13, 0, 0.78))
    rig.parts["LegR"][0].free()
    bm = rig.parts["LegR"][0] = bmesh.new()
    tube_path(bm, [hip + Vector((0, 0, 0.06)), hip, Vector((-0.14, -0.04, 0.5)), Vector((-0.14, -0.04, 0.42))],
              [0.1, 0.112, 0.1, 0.09], 8, rig.m("Ref_Black"))
    lathe(bm, [(0, 0.0), (0.035, 0.0), (0.045, 0.04), (0.06, 0.3), (0.075, 0.42), (0, 0.44)], 10,
          Matrix.Translation((-0.14, -0.03, 0.004)), WD)

    # Tricorne et tête de mort
    bm = rig.part("Hat", k["neck"], "Head")
    dome(bm, hc + Vector((0, 0.03, 0.12)), hr[0] * 1.05, hr[1] * 1.05, hr[2] * 0.75, BK, seg=14, steps=4)
    for a in (90, 210, 330):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        box(bm, hc + Vector((0, 0.03, 0.2)) + d * 0.2, (0.46, 0.06, 0.14), BK,
            rot=Quaternion((0, 0, 1), math.radians(a + 90)) @ Quaternion((1, 0, 0), math.radians(-28)), bevel=0.03)
    box(bm, hc + Vector((0, -0.17, 0.2)), (0.46, 0.065, 0.15), GOLD, rot=Quaternion((1, 0, 0), math.radians(28)), bevel=0.03)
    ellipsoid(bm, hc + Vector((0, -0.235, 0.24)), (0.05, 0.03, 0.05), WH, u=10, v=6)
    for s in (-1, 1):
        ellipsoid(bm, hc + Vector((0.022 * s, -0.262, 0.245)), (0.012, 0.008, 0.014), BK, u=6, v=4)

    # Barbe fournie, moustache, cache-œil
    bm = rig.part("Beard", k["neck"], "Head")
    for p, r in (((0, -0.16, -0.2), (0.18, 0.13, 0.14)), ((0.13, -0.1, -0.12), (0.09, 0.11, 0.13)),
                 ((-0.13, -0.1, -0.12), (0.09, 0.11, 0.13)), ((0, -0.2, -0.34), (0.11, 0.09, 0.11))):
        ellipsoid(bm, hc + Vector(p), r, HB, u=12, v=8)
    for s in (-1, 1):
        q = Quaternion((0, 1, 0), math.radians(-18 * s))
        ellipsoid(bm, hc + Vector((0.075 * s, -0.24, -0.055)), (0.085, 0.035, 0.032), HB, q, 10, 6)
    pe = k["eyeR"]
    lathe(bm, [(0, 0), (0.085, 0), (0.08, 0.025), (0, 0.032)], 12, Matrix.Translation(pe + Vector((0, -0.06, 0))) @ align_z((0, -1, 0)).to_matrix().to_4x4(), BK)
    tube_path(bm, [pe + Vector((-0.07, -0.04, 0.06)), hc + Vector((-0.05, -0.15, 0.17)), hc + Vector((0.18, -0.05, 0.12))], [0.012] * 3, 5, BK)

    # Manteau : plastron, galons dorés, boutons ; pans
    bm = rig.part("Coat", k["torso"], "Torso")
    f = k["front"]
    ellipsoid(bm, f(1.2) + Vector((0, 0.03, 0)), (0.13, 0.06, 0.21), WH, u=12, v=8)
    for s in (-1, 1):
        for z in (1.04, 1.14, 1.24):
            ellipsoid(bm, f(z, 0.12 * s) + Vector((0, -0.01, 0)), (0.026, 0.02, 0.026), GOLD, u=8, v=5)
        tube_path(bm, [f(1.33, 0.15 * s) + Vector((0, -0.01, 0)), f(1.15, 0.17 * s) + Vector((0, -0.01, 0)),
                       f(0.95, 0.16 * s) + Vector((0, -0.01, 0))], [0.02] * 3, 6, GOLD)
    bm = rig.part("CoatTails", k["hip"], "Hips")
    lathe(bm, [(0, 0.88), (0.275, 0.88), (0.28, 0.95), (0, 0.95)], 16, Matrix(), BK)
    for v in bm.verts:
        v.co.y *= 0.75
    box(bm, (0, -0.21, 0.915), (0.1, 0.03, 0.08), GOLD, bevel=0.012)
    for x, y, rz, w in ((0.17, -0.1, 15, 0.26), (-0.17, -0.1, -15, 0.26), (0.0, 0.12, 0, 0.5)):
        box(bm, (x, y, 0.6), (w, 0.09, 0.5), RED, rot=Quaternion((0, 0, 1), math.radians(rz)), bevel=0.035)

    # Perroquet sur l'épaule gauche
    sh = k["shoulderL"] + Vector((0.02, 0.03, 0.15))
    bm = rig.part("Parrot", sh, "Torso")
    ellipsoid(bm, sh, (0.075, 0.085, 0.12), GR, u=12, v=8)
    ellipsoid(bm, sh + Vector((0, -0.03, 0.13)), (0.065, 0.065, 0.065), RD, u=10, v=6)
    cyl(bm, sh + Vector((0, -0.085, 0.13)), sh + Vector((0, -0.14, 0.1)), 0.028, 0.0, YE, seg=8)
    for s in (-1, 1):
        ellipsoid(bm, sh + Vector((0.048 * s, -0.065, 0.15)), (0.016, 0.012, 0.016), BK, u=6, v=4)
    organic_leaf(bm, 0.2, 0.06, Matrix.Translation(sh + Vector((0, 0.05, -0.05))) @ Matrix.Rotation(math.radians(-130), 4, 'X'),
                 GR, n=3, lift=0.0, droop=0.0, fold=0.02, twist=0.0, th=0.02)

    # Long fusil de tireur d'élite
    hand = k["handR"]
    bm = rig.part("Weapon", hand, "ArmR")
    x, z = -0.06, 1.06
    box(bm, (x, -0.2, z - 0.03), (0.08, 0.44, 0.11), WD, bevel=0.03)
    cyl(bm, (x, -0.35, z + 0.02), (x, -1.26, z + 0.02), 0.03, 0.026, MD, seg=10)
    lathe(bm, [(0, 0), (0.045, 0), (0.04, 0.34), (0.05, 0.36), (0, 0.36)], 10,
          Matrix.Translation((x, -0.27, z + 0.12)) @ align_z((0, -1, 0)).to_matrix().to_4x4(), MET)
    box(bm, (x, -0.45, z + 0.07), (0.03, 0.04, 0.06), MD)
    rig.empty("Muzzle", (x, -1.29, z + 0.02), "Weapon")

    rig.build(smooth_angle=45.0, subdiv=dict(SMOOTH, Hat=1))
    clamp_to_ground("LegR")
    return col
