# plantRTS — Tournesol (qualité de référence, langage visuel du Pisto-pois v2).
import math
from mathutils import Vector, Matrix, Quaternion

NECK = 0.74
HEAD_C = Vector((0, 0.0, NECK + 0.26))


def build():
    col = reset_scene("Sunflower")
    rig = Rig("Sunflower", col)
    STEM, LEAF, LEAF2 = rig.m("PlantRef_Stem"), rig.m("PlantRef_Leaf"), rig.m("PlantRef_LeafAlt")
    HEAD, FACE, YE, YD = rig.m("PlantRef_Head"), rig.m("PlantRef_SunFace"), rig.m("PlantRef_Yellow"), rig.m("PlantRef_YellowDeep")
    EYE, EYEL, MOUTH, TONGUE = rig.m("PlantRef_Eye"), rig.m("PlantRef_EyeLight"), rig.m("PlantRef_MouthRed"), rig.m("PlantRef_Tongue")

    bm = rig.part("Leaves", (0, 0, 0))
    ref_leaf_rosette(bm, (LEAF, LEAF2))

    bm = rig.part("Stem", (0, 0, 0))
    tube_path(bm, [(0, 0, 0.012), (0, 0.004, 0.06), (0, 0.014, 0.15), (0, 0.03, 0.3), (0, 0.028, 0.45),
                   (0, 0.01, 0.6), (0, 0.0, 0.72), (0, 0.02, 0.86)],
              [0.165, 0.125, 0.098, 0.088, 0.085, 0.088, 0.095, 0.09], 10, STEM)

    # Feuilles-bras sur la tige
    for s, name in ((1, "ArmL"), (-1, "ArmR")):
        base = Vector((0.06 * s, 0.02, 0.42))
        bm = rig.part(name, base, "Stem")
        d = Vector((s, -0.4, 0)).normalized()
        mtx = Matrix.Translation(base) @ Matrix.Rotation(math.atan2(-d.x, d.y), 4, 'Z') @ Matrix.Rotation(math.radians(35), 4, 'X')
        organic_leaf(bm, 0.36, 0.13, mtx, LEAF, n=5, lift=0.06, droop=0.16, fold=0.04, twist=0.25 * s, th=0.03)

    # Tête : coussin du visage + calice vert, une seule surface tournée autour de l'axe avant
    bm = rig.part("Head", (0, 0, NECK), "Stem")
    prof = [(0, -0.11), (0.12, -0.11), (0.2, -0.085), (0.245, -0.04), (0.258, 0.0),
            (0.252, 0.035), (0.232, 0.07), (0.18, 0.103), (0.1, 0.12), (0, 0.126)]
    mats = [HEAD, HEAD, HEAD, HEAD, FACE, FACE, FACE, FACE, FACE]
    lathe(bm, prof, 16, Matrix.Translation(HEAD_C) @ Matrix.Rotation(math.radians(90), 4, 'X'), mats)
    R = (0.24, 0.12, 0.24)
    ref_plant_eyes(bm, HEAD_C, R, EYE, EYEL, None, spread=0.42, up=0.42, fwd=-0.8, size=0.82, tilt=-6)
    # Bouche ouverte en D, enfoncée dans le dôme du visage
    open_mouth(bm, HEAD_C + Vector((0, -0.098, -0.052)), 0.13, 0.09, MOUTH, TONGUE, depth=0.05)

    # Pétales : deux couronnes décalées, légèrement incurvées vers l'avant
    bm = rig.part("Petals", (0, 0, NECK), "Head")
    for n, L, W, off, dy, mi, curl in ((14, 0.25, 0.085, 0.0, 0.02, YE, 0.05), (14, 0.23, 0.08, 360 / 28, 0.06, YD, 0.03)):
        for k in range(n):
            a = math.radians(off + 360.0 * k / n)
            mtx = Matrix.Translation(HEAD_C + Vector((0, dy, 0))) @ Matrix.Rotation(a, 4, 'Y') \
                @ Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Translation((0, 0.2, 0))
            organic_leaf(bm, L, W, mtx, mi, n=4, lift=curl, droop=0.0, fold=0.015, twist=0.0, th=0.022, petiole=0.35)

    rig.empty("Muzzle", HEAD_C + Vector((0, -0.2, 0)), "Head")
    rig.build(subdiv={"Leaves": 1, "Stem": 1, "Head": 1, "ArmL": 1, "ArmR": 1})
    clamp_to_ground("Leaves")
    return col
