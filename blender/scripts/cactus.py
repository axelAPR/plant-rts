# plantRTS — Cactus (qualité de référence, langage visuel du Pisto-pois v2).
import math
from mathutils import Vector, Matrix, Quaternion


def build():
    col = reset_scene("Cactus")
    rig = Rig("Cactus", col)
    HEAD, LEAF, LEAF2 = rig.m("PlantRef_Head"), rig.m("PlantRef_Leaf"), rig.m("PlantRef_LeafAlt")
    EYE, EYEL, MOUTH = rig.m("PlantRef_Eye"), rig.m("PlantRef_EyeLight"), rig.m("PlantRef_Mouth")
    PINK, MAG, YE, CREAM = rig.m("PlantRef_Pink"), rig.m("PlantRef_Magenta"), rig.m("PlantRef_Yellow"), rig.m("PlantRef_Cream")

    bm = rig.part("Leaves", (0, 0, 0))
    ref_leaf_rosette(bm, (LEAF, LEAF2), specs=((20, 0.42, 0.17, 0.15), (110, 0.38, 0.16, -0.2),
                                                (200, 0.4, 0.16, 0.2), (290, 0.4, 0.17, -0.15)), r0=0.12)

    # Corps côtelé (côtes douces après lissage), légèrement évasé à la base
    bm = rig.part("Body", (0, 0, 0))
    prof = [(0, 0.0), (0.25, 0.0), (0.29, 0.08), (0.3, 0.3), (0.295, 0.65), (0.29, 0.95),
            (0.275, 1.15), (0.24, 1.3), (0.17, 1.41), (0.07, 1.46), (0, 1.47)]
    lathe(bm, prof, 16, Matrix(), HEAD, ridge=0.13)
    c, R = Vector((0, 0, 1.1)), (0.3, 0.3, 0.33)
    ref_plant_eyes(bm, c, R, EYE, EYEL, HEAD, spread=0.4, up=0.38, fwd=-0.8, size=0.85, tilt=12)
    p, d = surface_point(c, R, (0, -1, -0.32))
    ellipsoid(bm, p - d * 0.03, (0.05, 0.04, 0.042), MOUTH, d.to_track_quat('-Y', 'Z'), 10, 6)
    # Fleur au sommet
    top = Vector((0, 0, 1.43))
    for k in range(6):
        mtx = Matrix.Translation(top) @ Matrix.Rotation(math.radians(60 * k + 15), 4, 'Z') @ Matrix.Rotation(math.radians(28), 4, 'X')
        organic_leaf(bm, 0.32, 0.15, mtx, PINK if k % 2 else MAG, n=4, lift=0.05, droop=0.1, fold=0.03, twist=0.1, th=0.025, petiole=0.3)
    ellipsoid(bm, top + Vector((0, 0, 0.05)), (0.09, 0.09, 0.06), YE, u=10, v=6)

    # Bras en L, courbes
    for s, side in ((1, "L"), (-1, "R")):
        base = Vector((0.22 * s, 0, 0.68))
        bm = rig.part("Arm" + side, base, "Body")
        tube_path(bm, [base, base + Vector((0.16 * s, 0, 0.0)), base + Vector((0.27 * s, 0, 0.06)),
                       base + Vector((0.3 * s, 0, 0.2)), base + Vector((0.3 * s, 0, 0.36)), base + Vector((0.29 * s, 0, 0.46))],
                  [0.1, 0.1, 0.098, 0.095, 0.085, 0.05], 10, HEAD, cap_end=True)

    # Épines : pièce séparée, non lissée, pour rester pointues
    bm = rig.part("Spines", (0, 0, 0), "Body")
    for z, a in ((0.3, 35), (0.3, 145), (0.3, 255), (0.58, 90), (0.58, 200), (0.58, 330),
                 (0.85, 30), (0.85, 150), (1.2, 115), (1.2, 245), (0.58, -25), (1.05, 0)):
        dv = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0.18)).normalized()
        p0 = Vector((0, 0, z)) + Vector((dv.x, dv.y, 0)) * 0.27
        cyl(bm, p0, p0 + dv * 0.11, 0.02, 0.0, CREAM, seg=5)
    for s in (1, -1):
        for dz in (0.2, 0.33):
            p0 = Vector((0.52 * s, 0, 0.68 + dz))
            cyl(bm, p0, p0 + Vector((0.1 * s, -0.02, 0.03)), 0.018, 0.0, CREAM, seg=5)

    rig.empty("Muzzle", (0, -0.36, 1.0), "Body")
    rig.build(subdiv={"Leaves": 1, "Body": 1, "ArmL": 1, "ArmR": 1})
    clamp_to_ground("Leaves")
    return col
