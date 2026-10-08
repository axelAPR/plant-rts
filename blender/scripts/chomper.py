# plantRTS — Chomper (qualité de référence, langage visuel du Pisto-pois v2).
import math
from mathutils import Vector, Matrix, Quaternion

HINGE = Vector((0, 0.3, 1.02))


def jaw_shell(bm, center, rx, ry, rz, inner, lip, outer, down=False, steps=5):
    """Coque de mâchoire : intérieur (base plane), lèvre ourlée, dôme extérieur."""
    prof = [(0, 0), (0.87, 0.0), (0.97, 0.02), (1.0, 0.07)]
    prof += [(math.cos(t), math.sin(t)) for t in [math.radians(15 + i * 75 / steps) for i in range(1, steps)]]
    prof += [(0, 1)]
    mats = [inner, lip, lip] + [outer] * (len(prof) - 4)
    rot = Quaternion((1, 0, 0), math.pi) if down else Quaternion()
    m = Matrix.Translation(Vector(center)) @ rot.to_matrix().to_4x4() @ Matrix.Diagonal((rx, ry, rz, 1))
    lathe(bm, prof, 16, m, mats)


def teeth(bm, c, rx, ry, z, down, count, mi, length=0.15):
    for k in range(count):
        t = math.radians(200 + 140 * k / (count - 1))
        p = Vector((c.x + rx * 0.95 * math.cos(t), c.y + ry * 0.95 * math.sin(t), z))
        L = length * (1.0 - 0.35 * abs(k - (count - 1) / 2) / ((count - 1) / 2))
        cyl(bm, p, p + Vector((0, 0, -L if down else L)), 0.04, 0.0, mi, seg=6)


def build():
    col = reset_scene("Chomper")
    rig = Rig("Chomper", col)
    STEM, LEAF, LEAF2, GREEN = rig.m("PlantRef_Stem"), rig.m("PlantRef_Leaf"), rig.m("PlantRef_LeafAlt"), rig.m("PlantRef_Head")
    PU, PL, MR, TO, TE = (rig.m(n) for n in ("PlantRef_Purple", "PlantRef_PurpleLight", "PlantRef_MouthRed", "PlantRef_Tongue", "PlantRef_Teeth"))

    bm = rig.part("Leaves", (0, 0, 0))
    ref_leaf_rosette(bm, (LEAF, LEAF2), specs=((0, 0.62, 0.23, 0.15), (72, 0.56, 0.21, -0.2), (144, 0.54, 0.2, 0.2),
                                                (216, 0.55, 0.2, -0.15), (288, 0.58, 0.22, 0.18)))

    bm = rig.part("Stem", (0, 0, 0))
    tube_path(bm, [(0, 0, 0.012), (0, 0.006, 0.07), (0, 0.03, 0.2), (0, 0.06, 0.4), (0, 0.08, 0.6),
                   (0, 0.12, 0.78), (0, 0.17, 0.92)],
              [0.19, 0.145, 0.12, 0.112, 0.11, 0.115, 0.13], 10, STEM)

    # Tête : raccord de nuque + mâchoire supérieure ouverte
    bm = rig.part("Head", (0, 0.15, 0.88), "Stem")
    ellipsoid(bm, (0, 0.26, 0.98), (0.23, 0.22, 0.2), PU, u=12, v=8)
    ellipsoid(bm, (0, 0.12, 1.08), (0.3, 0.12, 0.2), MR, u=12, v=8)          # gorge (fond de la gueule)
    with Group(bm, rot_about(HINGE, 'X', -14)):
        c = Vector((0, -0.04, 1.02))
        jaw_shell(bm, c, 0.4, 0.5, 0.38, MR, PL, PU)
        for p, r in (((0.13, -0.16, 1.33), 0.085), ((-0.17, 0.0, 1.35), 0.075), ((0.05, 0.14, 1.37), 0.065),
                     ((-0.05, -0.33, 1.25), 0.06), ((0.27, 0.06, 1.25), 0.06), ((-0.29, -0.14, 1.18), 0.055)):
            ellipsoid(bm, p, (r, r, r * 0.45), PL, u=8, v=5)
        for a, L in ((-45, 0.34), (0, 0.4), (45, 0.34)):
            d = Vector((math.sin(math.radians(a)), 1, 0)).normalized()
            mtx = Matrix.Translation((0, 0.33, 1.2)) @ Matrix.Rotation(math.atan2(-d.x, d.y), 4, 'Z') @ Matrix.Rotation(math.radians(40), 4, 'X')
            organic_leaf(bm, L, 0.14, mtx, GREEN, n=5, lift=0.06, droop=0.2, fold=0.04, twist=0.15, th=0.03)
    bm = rig.part("TeethUpper", (0, 0.15, 0.88), "Head")
    with Group(bm, rot_about(HINGE, 'X', -14)):
        teeth(bm, Vector((0, -0.04, 1.02)), 0.4, 0.5, 1.02, True, 9, TE)

    # Mâchoire inférieure (pivot à la charnière) et langue
    bm = rig.part("Jaw", HINGE, "Head")
    with Group(bm, rot_about(HINGE, 'X', 24)):
        c = Vector((0, -0.04, 1.0))
        jaw_shell(bm, c, 0.37, 0.47, 0.22, MR, PL, PU, down=True)
        ellipsoid(bm, (0, -0.1, 1.01), (0.19, 0.3, 0.06), TO, u=12, v=6)
    bm = rig.part("TeethLower", HINGE, "Jaw")
    with Group(bm, rot_about(HINGE, 'X', 24)):
        teeth(bm, Vector((0, -0.04, 1.0)), 0.37, 0.47, 0.99, False, 7, TE, length=0.1)

    rig.empty("Muzzle", (0, -0.6, 1.05), "Head")
    rig.build(subdiv={"Leaves": 1, "Stem": 1, "Head": 1, "Jaw": 1})
    clamp_to_ground("Leaves")
    return col
