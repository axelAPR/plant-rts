# plantRTS — Rose (qualité de référence, langage visuel du Pisto-pois v2).
import math
from mathutils import Vector, Matrix, Quaternion

WAIST, NECK = 0.7, 1.08
HEAD_C = Vector((0, 0, 1.31))
HEAD_R = (0.185, 0.175, 0.205)


def build():
    col = reset_scene("Rose")
    rig = Rig("Rose", col)
    STEM, LEAF, LEAF2, HEAD = (rig.m(n) for n in ("PlantRef_Stem", "PlantRef_Leaf", "PlantRef_LeafAlt", "PlantRef_Head"))
    FACE, MAG, PINK, EYE, EYEL = (rig.m(n) for n in ("PlantRef_RoseFace", "PlantRef_Magenta", "PlantRef_Pink", "PlantRef_Eye", "PlantRef_EyeLight"))
    MOUTH, BARK, MAGIC, TE = rig.m("PlantRef_MouthRed"), rig.m("PlantRef_BarkDark"), rig.m("PlantRef_Magic"), rig.m("PlantRef_Teeth")

    # Corps : jupe de feuilles + buste
    bm = rig.part("Body", (0, 0, 0))
    tube_path(bm, [(0, 0, 0.01), (0, 0, 0.25), (0, 0.0, WAIST + 0.05)], [0.2, 0.16, 0.1], 10, STEM)
    for k in range(8):
        a = math.radians(360 * k / 8 + 22)
        d = Vector((math.sin(a), -math.cos(a), 0))
        mtx = Matrix.Translation(d * 0.06 + Vector((0, 0, WAIST))) @ Matrix.Rotation(math.atan2(-d.x, d.y), 4, 'Z') \
            @ Matrix.Rotation(math.radians(-52), 4, 'X')
        organic_leaf(bm, 0.8, 0.25, mtx, LEAF if k % 2 else LEAF2, n=4, lift=0.12, droop=-0.04, fold=0.05,
                     twist=0.2 * (1 if k % 2 else -1), th=0.035, petiole=0.35)
    tube_path(bm, [(0, 0, WAIST - 0.04), (0, -0.01, 0.84), (0, -0.015, 0.98), (0, -0.01, NECK + 0.08)],
              [0.11, 0.13, 0.11, 0.065], 10, STEM)
    for a in (-55, 0, 55, 180):                                                     # col de feuilles
        d = Vector((math.sin(math.radians(a)), -math.cos(math.radians(a)), 0))
        mtx = Matrix.Translation(d * 0.04 + Vector((0, 0, NECK - 0.05))) @ Matrix.Rotation(math.atan2(-d.x, d.y), 4, 'Z') \
            @ Matrix.Rotation(math.radians(30), 4, 'X')
        organic_leaf(bm, 0.18, 0.08, mtx, HEAD, n=4, lift=0.03, droop=0.06, fold=0.03, twist=0.1, th=0.02)

    # Tête : visage + chevelure de pétales enroulés + chignon en bouton
    bm = rig.part("Head", (0, 0, NECK), "Body")
    ellipsoid(bm, HEAD_C, HEAD_R, FACE, u=14, v=10)
    ref_plant_eyes(bm, HEAD_C, HEAD_R, EYE, EYEL, FACE, spread=0.42, up=0.3, fwd=-0.8, size=0.7, tilt=-6, lid_tilt=-6)
    p, d = surface_point(HEAD_C, HEAD_R, (0, -1, -0.42))
    open_mouth(bm, p - d * 0.008, 0.05, 0.03, MOUTH, None, depth=0.03)
    for dv, L, W in (((0, 1, 0.2), 0.42, 0.26), ((0.8, 0.6, 0.1), 0.4, 0.25), ((-0.8, 0.6, 0.1), 0.4, 0.25),
                     ((1, -0.05, -0.25), 0.34, 0.22), ((-1, -0.05, -0.25), 0.34, 0.22), ((0, 0.85, -0.5), 0.36, 0.23),
                     ((0.7, 0.2, 0.7), 0.36, 0.23), ((-0.7, 0.2, 0.7), 0.36, 0.23)):
        dv = Vector(dv).normalized()
        q = Vector((0, 1, 0)).rotation_difference(dv)
        organic_leaf(bm, L, W, Matrix.Translation(HEAD_C + dv * 0.1) @ q.to_matrix().to_4x4(), MAG,
                     n=3, lift=0.12, droop=0.06, fold=0.1, twist=0.25, th=0.03, petiole=0.45)
    top = HEAD_C + Vector((0, 0.05, 0.19))
    for ring, (n, L, pitch, mi) in enumerate(((5, 0.18, 30, MAG), (3, 0.12, 62, PINK))):
        for k in range(n):
            mtx = Matrix.Translation(top) @ Matrix.Rotation(math.radians(360 * k / n + ring * 37), 4, 'Z')                 @ Matrix.Rotation(math.radians(pitch), 4, 'X')
            organic_leaf(bm, L, L * 0.8, mtx, mi, n=3, lift=0.04, droop=-0.02, fold=0.06, twist=0.2, th=0.025, petiole=0.5)
    ellipsoid(bm, top + Vector((0, 0, 0.03)), (0.07, 0.07, 0.07), MAG, u=10, v=6)

    # Bras fins et mains-feuilles ; bâton dans la main droite
    for s, side in ((1, "L"), (-1, "R")):
        shoulder = Vector((0.1 * s, -0.01, 1.0))
        hand = Vector((0.36 * s, -0.2, 0.84))
        bm = rig.part("Arm" + side, shoulder, "Body")
        tube_path(bm, [shoulder, shoulder + Vector((0.13 * s, -0.06, -0.06)), hand], [0.045, 0.04, 0.035], 8, STEM)
        mtx = Matrix.Translation(hand) @ Matrix.Rotation(math.atan2(-0.4 * s, -1), 4, 'Z') @ Matrix.Rotation(math.radians(-20), 4, 'X')
        organic_leaf(bm, 0.17, 0.09, mtx, HEAD, n=4, lift=0.02, droop=0.03, fold=0.04, twist=0.2, th=0.025)
    hand = Vector((-0.36, -0.2, 0.84))
    bm = rig.part("Staff", hand, "ArmR")
    tube_path(bm, [hand + Vector((0, 0, -0.52)), hand + Vector((0.01, 0, 0.0)), hand + Vector((-0.01, 0, 0.4)),
                   hand + Vector((0.02, 0, 0.6)), hand + Vector((0.05, 0, 0.7))], [0.026, 0.03, 0.028, 0.025, 0.02], 8, BARK)
    for dz, a in ((-0.35, 0), (-0.12, 140), (0.15, 260), (0.4, 40)):
        p0 = hand + Vector((0, 0, dz))
        dv = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0.5)).normalized()
        cyl(bm, p0, p0 + dv * 0.07, 0.015, 0.0, BARK, seg=5)
    top = hand + Vector((0.05, 0, 0.7))
    for k in range(5):
        mtx = Matrix.Translation(top) @ Matrix.Rotation(math.radians(72 * k), 4, 'Z') @ Matrix.Rotation(math.radians(30), 4, 'X')
        organic_leaf(bm, 0.12, 0.07, mtx, MAG, n=3, lift=0.03, droop=-0.03, fold=0.03, twist=0.1, th=0.02)
    ellipsoid(bm, top + Vector((0, 0, 0.1)), (0.075, 0.075, 0.075), MAGIC, u=12, v=8)
    rig.empty("Muzzle", top + Vector((0, 0, 0.1)), "Staff")

    rig.build(subdiv={"Body": 1, "Head": 1, "ArmL": 1, "ArmR": 1})
    clamp_to_ground("Body")
    return col
