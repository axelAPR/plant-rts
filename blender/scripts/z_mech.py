# plantRTS — Z-Mech piloté par un Imp (qualité de référence).
import math
import bmesh
from mathutils import Vector, Matrix, Quaternion


def beam(bm, p0, p1, w, d, mi, bevel=0.05):
    p0, p1 = Vector(p0), Vector(p1)
    dv = p1 - p0
    box(bm, (p0 + p1) / 2, (w, d, dv.length), mi, rot=align_z(dv), bevel=bevel)


def build():
    col = reset_scene("ZMech")
    rig = Rig("ZMech", col)
    MY, MD, MET, CY, RED, BK = (rig.m(n) for n in ("Ref_MechYellow", "Ref_MetalDark", "Ref_Metal", "Ref_Cyan", "Ref_Red", "Ref_Black"))
    SK, EYE, PUP, MO, TE = (rig.m(n) for n in ("ZombieRef_Skin", "ZombieRef_Eye", "ZombieRef_Pupil", "ZombieRef_Mouth", "ZombieRef_Teeth"))

    bm = rig.part("Hips", (0, 0, 1.55))
    box(bm, (0, 0.02, 1.55), (0.74, 0.54, 0.32), MD, bevel=0.08)
    for s, side in ((1, "L"), (-1, "R")):
        hip, knee, ankle = Vector((0.41 * s, 0, 1.5)), Vector((0.45 * s, -0.32, 0.96)), Vector((0.45 * s, 0.08, 0.31))
        bm = rig.part("Leg" + side, hip, "Hips")
        ellipsoid(bm, hip, (0.18, 0.18, 0.18), MET, u=12, v=8)
        beam(bm, hip, knee, 0.28, 0.32, MY, bevel=0.07)
        ellipsoid(bm, knee, (0.17, 0.17, 0.17), MD, u=12, v=8)
        lathe(bm, [(0, 0), (0.12, 0), (0.12, 0.05), (0.095, 0.62), (0, 0.66)], 12,
              Matrix.Translation(knee) @ align_z(ankle - knee).to_matrix().to_4x4(), MD)
        cyl(bm, knee + (ankle - knee) * 0.2 + Vector((0, 0.13, 0)), ankle + Vector((0, 0.13, 0.2)), 0.045, 0.045, MET, seg=8)
        ellipsoid(bm, ankle, (0.12, 0.12, 0.12), MET, u=10, v=6)
        box(bm, ankle + Vector((0, -0.14, -0.215)), (0.38, 0.72, 0.19), MY, bevel=0.08)
        for x in (-0.12, 0.12):
            box(bm, ankle + Vector((x, -0.54, -0.24)), (0.11, 0.17, 0.13), MD, bevel=0.04)

    bm = rig.part("Torso", (0, 0, 1.65), "Hips")
    box(bm, (0, 0.05, 2.18), (1.28, 1.0, 0.92), MY, bevel=0.2)
    box(bm, (0, -0.44, 2.05), (0.82, 0.12, 0.52), MD, bevel=0.06)
    for x in (-0.29, 0.29):
        lathe(bm, [(0, 0), (0.1, 0), (0.1, 0.05), (0.085, 0.06), (0, 0.06)], 16,
              Matrix.Translation((x, -0.49, 2.2)) @ align_z((0, -1, 0)).to_matrix().to_4x4(), CY)
    for x in (-0.3, -0.15, 0.0, 0.15, 0.3):
        box(bm, (x, -0.51, 1.95), (0.08, 0.02, 0.2), BK, bevel=0.01)
    box(bm, (0, 0.57, 2.2), (0.62, 0.16, 0.62), MD, bevel=0.06)
    for x in (-0.18, 0.18):
        lathe(bm, [(0, 0), (0.07, 0), (0.06, 0.28), (0.075, 0.3), (0, 0.3)], 10, Matrix.Translation((x, 0.64, 2.45)), MET)
    box(bm, (0, -0.08, 2.67), (0.8, 0.68, 0.16), MD, bevel=0.05)

    # L'Imp pilote : petit zombie à grosse tête, lunettes d'aviateur, écharpe
    bm = rig.part("Pilot", (0, -0.08, 2.72), "Torso")
    lathe(bm, [(0, 2.72), (0.17, 2.72), (0.21, 2.82), (0.18, 2.92), (0.08, 2.98), (0, 2.99)], 12, Matrix.Translation((0, -0.08, 0)), BK)
    hc, hr = Vector((0, -0.12, 3.18)), (0.21, 0.2, 0.22)
    prof = [(0, -0.2), (0.11, -0.19), (0.17, -0.12), (0.2, -0.03), (0.205, 0.06), (0.18, 0.15), (0.11, 0.21), (0, 0.22)]
    lathe(bm, prof, 16, Matrix.Translation(hc), SK)
    for s, r in ((1, 0.075), (-1, 0.062)):
        p, d = surface_point(hc, hr, (0.42 * s, -0.85, 0.08))
        q = Vector((0.1 * s, -1, 0)).normalized().to_track_quat('-Y', 'Z')
        ellipsoid(bm, p - d * 0.012, (r, r * 0.85, r), EYE, q, 10, 6)
        ellipsoid(bm, p - d * 0.012 + Vector((0.1 * s, -1, 0)).normalized() * r * 0.75, (r * 0.36, r * 0.2, r * 0.36), PUP, q, 8, 5)
    p, d = surface_point(hc, hr, (0.06, -1, -0.5))
    open_mouth(bm, p - d * 0.01, 0.1, 0.04, MO, None, forward=d, depth=0.035)
    for x in (-0.04, 0.035):
        ellipsoid(bm, p - d * 0.004 + Vector((x, 0, 0.018)), (0.018, 0.012, 0.022), TE, u=6, v=4)
    for s in (-1, 1):
        ellipsoid(bm, hc + Vector((0.21 * s, 0.0, 0.03)), (0.04, 0.065, 0.075), SK, u=8, v=5)
    lathe(bm, [(0, 0), (0.215, 0), (0.22, 0.025), (0.215, 0.05), (0, 0.05)], 16, Matrix.Translation(hc + Vector((0, 0.0, 0.1))), BK)
    for s in (-1, 1):
        lathe(bm, [(0, 0), (0.065, 0), (0.07, 0.03), (0.06, 0.07), (0, 0.07)], 14,
              Matrix.Translation(hc + Vector((0.085 * s, -0.17, 0.14))) @ align_z((0, -1, 0)).to_matrix().to_4x4(), MET)
        cyl(bm, hc + Vector((0.085 * s, -0.235, 0.14)), hc + Vector((0.085 * s, -0.245, 0.14)), 0.05, 0.05, CY, seg=12)
    tube_path(bm, [(0, -0.08, 2.98), (0, -0.08, 3.03)], [0.13, 0.12], 12, RED)
    organic_leaf(bm, 0.3, 0.085, Matrix.Translation((0.06, 0.03, 3.0)) @ Matrix.Rotation(math.radians(-25), 4, 'Z') @ Matrix.Rotation(math.radians(-30), 4, 'X'),
                 RED, n=4, lift=0.03, droop=0.06, fold=0.0, twist=0.4, th=0.02, petiole=0.9)

    for s, side in ((1, "L"), (-1, "R")):
        sh = Vector((0.73 * s, 0.05, 2.3))
        elbow = Vector((0.84 * s, -0.05, 1.85))
        bm = rig.part("Arm" + side, sh, "Torso")
        ellipsoid(bm, sh, (0.27, 0.27, 0.27), MD, u=14, v=10)
        beam(bm, sh, elbow, 0.24, 0.26, MY, bevel=0.06)
        ellipsoid(bm, elbow, (0.16, 0.16, 0.16), MET, u=12, v=8)
        if side == "R":
            lathe(bm, [(0, 0), (0.22, 0), (0.23, 0.05), (0.23, 0.6), (0.2, 0.68), (0, 0.68)], 16,
                  Matrix.Translation((elbow.x, 0.15, 1.75)) @ align_z((0, -1, 0)).to_matrix().to_4x4(), MET)
            for a in range(6):
                t = math.radians(60 * a)
                o = Vector((math.cos(t) * 0.1, 0, math.sin(t) * 0.1))
                cyl(bm, Vector((elbow.x, -0.5, 1.75)) + o, Vector((elbow.x, -1.25, 1.75)) + o, 0.042, 0.042, MD, seg=8)
            cyl(bm, (elbow.x, -1.08, 1.75), (elbow.x, -1.15, 1.75), 0.165, 0.165, MD, seg=16)
            rig.empty("MuzzleR", (elbow.x, -1.3, 1.75), "ArmR")
        else:
            box(bm, (elbow.x + 0.05, -0.25, 1.8), (0.52, 0.82, 0.52), MY, bevel=0.09)
            box(bm, (elbow.x + 0.05, -0.67, 1.8), (0.45, 0.04, 0.45), MD, bevel=0.03)
            for ix in (-0.12, 0.12):
                for iz in (-0.12, 0.0, 0.12):
                    lathe(bm, [(0, 0), (0.048, 0), (0.048, 0.06), (0.03, 0.12), (0, 0.14)], 10,
                          Matrix.Translation((elbow.x + 0.05 + ix, -0.67, 1.8 + iz)) @ align_z((0, -1, 0)).to_matrix().to_4x4(), RED)
            rig.empty("MuzzleL", (elbow.x + 0.05, -0.84, 1.8), "ArmL")

    # Imp agrandi de 25 % autour de sa base : lisible depuis la caméra RTS
    pb = rig.bm("Pilot")
    piv = Vector((0, -0.08, 2.72))
    bmesh.ops.scale(pb, vec=(1.25, 1.25, 1.25), space=Matrix.Translation(-piv), verts=pb.verts)
    rig.build(smooth_angle=40.0, subdiv={"Pilot": 1})
    return col
