# plantRTS — Citron (qualité de référence, langage visuel du Pisto-pois v2).
import math
from mathutils import Vector, Matrix, Quaternion

HIP_Z = 0.38
C, RAD = Vector((0, 0, 0.78)), 0.47


def build():
    col = reset_scene("Citron")
    rig = Rig("Citron", col)
    ORA, HEAD, LEAF, BR = rig.m("PlantRef_Orange"), rig.m("PlantRef_Head"), rig.m("PlantRef_Leaf"), rig.m("PlantRef_BarkDark")
    MET, MD, CY, EYE, EYEL = (rig.m(n) for n in ("PlantRef_Metal", "PlantRef_MetalDark", "PlantRef_Cyan", "PlantRef_Eye", "PlantRef_EyeLight"))
    MOUTH, TE = rig.m("PlantRef_MouthRed"), rig.m("PlantRef_Teeth")

    # Jambes mécaniques (non lissées : aspect usiné)
    for s, side in ((1, "L"), (-1, "R")):
        hip = Vector((0.2 * s, 0, HIP_Z))
        knee = Vector((0.26 * s, -0.08, 0.21))
        ankle = Vector((0.25 * s, 0.0, 0.085))
        bm = rig.part("Leg" + side, hip)
        cyl(bm, hip, knee, 0.065, 0.055, MD, seg=10)
        ellipsoid(bm, knee, (0.07, 0.07, 0.07), MET, u=10, v=6)
        cyl(bm, knee, ankle, 0.055, 0.048, MD, seg=10)
        box(bm, ankle + Vector((0, -0.05, -0.04)), (0.16, 0.28, 0.09), MET, bevel=0.03)

    # Corps-fruit : sphère à pores (léger relief), pédoncule et feuille
    bm = rig.part("Body", (0, 0, HIP_Z))
    lathe(bm, [(0, C.z - RAD)] + [(RAD * math.sin(math.radians(a)), C.z - RAD * math.cos(math.radians(a))) for a in range(12, 180, 12)] + [(0, C.z + RAD)],
          18, Matrix(), ORA, ridge=0.025)
    tube_path(bm, [C + Vector((0, 0, RAD * 0.92)), C + Vector((0.01, 0, RAD + 0.06)), C + Vector((0.03, 0, RAD + 0.1))], [0.035, 0.03, 0.025], 6, BR)
    mtx = Matrix.Translation(C + Vector((0.02, 0, RAD + 0.06))) @ Matrix.Rotation(math.radians(-70), 4, 'Z') @ Matrix.Rotation(math.radians(30), 4, 'X')
    organic_leaf(bm, 0.26, 0.11, mtx, LEAF, n=4, lift=0.04, droop=0.08, fold=0.04, twist=0.2, th=0.025)
    # Bouche : sourire carnassier
    p, d = surface_point(C, (RAD, RAD, RAD), (0, -1, -0.38))
    open_mouth(bm, p - d * 0.01, 0.16, 0.075, MOUTH, None, depth=0.06)
    for k in range(5):
        x = (k - 2) * 0.055
        ellipsoid(bm, p - d * 0.02 + Vector((x, -0.005, -0.012)), (0.022, 0.012, 0.024), TE, u=6, v=4)

    # Bandeau cybernétique + visière (pièce usinée, non lissée)
    bm = rig.part("Visor", C, "Body")
    z0, z1 = 0.92, 1.08
    rz = lambda z: math.sqrt(RAD ** 2 - (z - C.z) ** 2) + 0.03
    lathe(bm, [(0, z0), (rz(z0), z0), (rz((z0 + z1) / 2) + 0.012, (z0 + z1) / 2), (rz(z1), z1), (0, z1)], 24, Matrix(), MET)
    vz = (z0 + z1) / 2
    # Visière : bande cyan épousant le bandeau sur l'avant
    vz0, vz1 = vz - 0.055, vz + 0.055
    for i in range(10):
        a0 = math.radians(-145 + i * 11)
        a1 = math.radians(-145 + (i + 1) * 11)
        r = rz(vz) + 0.02
        p0 = Vector((r * math.cos(a0), r * math.sin(a0), vz))
        p1 = Vector((r * math.cos(a1), r * math.sin(a1), vz))
        mid = (p0 + p1) / 2
        box(bm, mid, ((p1 - p0).length + 0.004, 0.03, vz1 - vz0), CY,
            rot=Quaternion((0, 0, 1), math.atan2(p1.y - p0.y, p1.x - p0.x)))
    box(bm, (0.38, -0.27, vz), (0.08, 0.09, 0.18), MD, rot=Quaternion((0, 0, 1), math.radians(-40)), bevel=0.02)
    cyl(bm, (0.42, -0.22, vz + 0.08), (0.46, -0.2, vz + 0.24), 0.012, 0.012, MD, seg=6)         # antenne
    ellipsoid(bm, (0.46, -0.2, vz + 0.25), (0.025, 0.025, 0.025), CY, u=8, v=5)

    # Bras gauche (+X) : pince ; bras droit (-X) : canon à plasma
    bm = rig.part("ArmL", (0.44, 0, 0.72), "Body")
    cyl(bm, (0.44, 0, 0.72), (0.6, -0.12, 0.56), 0.05, 0.045, MD, seg=10)
    ellipsoid(bm, (0.62, -0.15, 0.54), (0.085, 0.085, 0.085), MET, u=10, v=6)
    for a in (-25, 25):
        cyl(bm, (0.62, -0.18, 0.54), (0.62 + math.sin(math.radians(a)) * 0.08, -0.3, 0.54 + math.cos(math.radians(a)) * 0.04), 0.025, 0.012, MD, seg=6)
    bm = rig.part("ArmR", (-0.44, 0, 0.72), "Body")
    cyl(bm, (-0.44, 0, 0.72), (-0.58, 0.0, 0.66), 0.075, 0.075, MD, seg=10)
    lathe(bm, [(0, 0.2), (0.12, 0.2), (0.135, 0.12), (0.13, -0.3), (0.11, -0.38), (0.12, -0.44), (0.12, -0.5), (0.08, -0.5), (0.08, -0.46), (0, -0.46)],
          16, Matrix.Translation((-0.62, 0, 0.64)) @ align_z((0, 1, 0)).to_matrix().to_4x4(), MET)
    cyl(bm, (-0.62, -0.455, 0.64), (-0.62, -0.47, 0.64), 0.08, 0.08, CY, seg=14)
    box(bm, (-0.62, 0.0, 0.79), (0.09, 0.28, 0.06), MD, bevel=0.02)
    for y in (-0.18, -0.06, 0.06):
        cyl(bm, (-0.62, y, 0.64), (-0.62, y + 0.03, 0.64), 0.142, 0.142, MD, seg=16)
    rig.empty("Muzzle", (-0.62, -0.53, 0.64), "ArmR")

    rig.build(smooth_angle=40.0, subdiv={"Body": 1})
    return col
