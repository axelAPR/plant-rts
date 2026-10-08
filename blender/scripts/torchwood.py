# plantRTS — Torchwood (qualité de référence, langage visuel du Pisto-pois v2).
import math
from mathutils import Vector, Matrix, Quaternion

TOP = 0.95


def flame(bm, base, tip, r, mi, seg=10, lean=Vector((0, 0, 0))):
    """Langue de flamme : bulbe à la base, pointe effilée légèrement recourbée."""
    base, tip = Vector(base), Vector(tip)
    pts, radii = [], []
    for i, (t, rr) in enumerate(((0.0, 0.85), (0.18, 1.1), (0.42, 0.95), (0.66, 0.6), (0.86, 0.28), (1.0, 0.05))):
        pts.append(base.lerp(tip, t) + lean * (t * t))
        radii.append(r * rr)
    tube_path(bm, pts, radii, seg, mi)


def build():
    col = reset_scene("Torchwood")
    rig = Rig("Torchwood", col)
    BARK, BD, WOOD, HEAD = (rig.m(n) for n in ("PlantRef_Bark", "PlantRef_BarkDark", "PlantRef_Wood", "PlantRef_Head"))
    FL, FC, EYE, EYEL, MOUTH = (rig.m(n) for n in ("PlantRef_Flame", "PlantRef_FlameCore", "PlantRef_Eye", "PlantRef_EyeLight", "PlantRef_MouthRed"))

    # Souche : écorce côtelée, sommet en bois clair avec cernes
    bm = rig.part("Body", (0, 0, 0))
    lathe(bm, [(0, 0.0), (0.38, 0.0), (0.34, 0.1), (0.31, 0.35), (0.315, 0.65), (0.32, TOP - 0.03),
               (0.3, TOP), (0.27, TOP + 0.005), (0.0, TOP + 0.005)], 16, Matrix(),
          [BARK, BARK, BARK, BARK, BARK, BARK, WOOD, WOOD], ridge=0.09)
    for r in (0.18, 0.1):
        cyl(bm, (0, 0, TOP - 0.01), (0, 0, TOP + 0.012), r + 0.012, r + 0.012, BD, seg=16)
        cyl(bm, (0, 0, TOP - 0.008), (0, 0, TOP + 0.014), r, r, WOOD, seg=16)
    # Racines
    for a in (35, 145, 215, 325, 90):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        tube_path(bm, [d * 0.22 + Vector((0, 0, 0.22)), d * 0.38 + Vector((0, 0, 0.08)), d * 0.52 + Vector((0, 0, 0.02))],
                  [0.09, 0.065, 0.03], 8, BARK)
    # Visage furieux : yeux, sourcils lourds, bouche grimaçante
    c, R = Vector((0, 0, 0.58)), (0.33, 0.33, 0.4)
    ref_plant_eyes(bm, c, R, EYE, EYEL, BARK, spread=0.4, up=0.24, fwd=-0.82, size=1.0, tilt=16, lid_tilt=16)
    for s in (-1, 1):
        p, d = surface_point(c, R, (0.4 * s, -0.8, 0.6))
        q = d.to_track_quat('-Y', 'Z') @ Quaternion((0, 1, 0), math.radians(-26 * s))
        ellipsoid(bm, p + d * 0.02 + Vector((0, 0, -0.01)), (0.14, 0.055, 0.05), BD, q, 10, 6)
    p, d = surface_point(c, R, (0, -1, -0.42))
    open_mouth(bm, p - d * 0.012, 0.16, 0.085, MOUTH, None, depth=0.06, frown=True)

    # Flammes : couronne de langues + cœur jaune, pièce séparée (animation)
    bm = rig.part("Flame", (0, 0, TOP), "Body")
    for a, r, h, lean in ((0, 0.12, 0.4, 0.1), (72, 0.11, 0.32, 0.09), (144, 0.12, 0.38, 0.1), (216, 0.1, 0.3, 0.09), (288, 0.11, 0.35, 0.1)):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        base = d * 0.14 + Vector((0, 0, TOP - 0.02))
        flame(bm, base, base + Vector((0, 0, h)), r, FL, lean=d * lean)
    flame(bm, (0, 0.02, TOP - 0.02), (0, 0.02, TOP + 0.62), 0.18, FL, seg=12, lean=Vector((0.04, 0.06, 0)))
    flame(bm, (0, -0.1, TOP - 0.01), (0, -0.16, TOP + 0.36), 0.1, FC, seg=10, lean=Vector((-0.02, -0.04, 0)))
    rig.empty("Muzzle", (0, -0.1, TOP + 0.3), "Flame")

    # Bras-branches avec rameau feuillu
    for s, side in ((1, "L"), (-1, "R")):
        shoulder = Vector((0.28 * s, 0, 0.55))
        hand = Vector((0.6 * s, -0.12, 0.72))
        bm = rig.part("Arm" + side, shoulder, "Body")
        tube_path(bm, [shoulder, shoulder + Vector((0.15 * s, -0.04, 0.03)), hand], [0.075, 0.06, 0.045], 8, BARK)
        tube_path(bm, [hand, hand + Vector((0.06 * s, -0.03, 0.08)), hand + Vector((0.09 * s, -0.05, 0.17))], [0.04, 0.03, 0.012], 6, BARK)
        tube_path(bm, [hand, hand + Vector((0.09 * s, -0.04, 0.0)), hand + Vector((0.17 * s, -0.07, -0.03))], [0.04, 0.03, 0.012], 6, BARK)
        mtx = Matrix.Translation(hand + Vector((0.07 * s, -0.04, 0.1))) @ Matrix.Rotation(math.radians(-60 * s), 4, 'Z') \
            @ Matrix.Rotation(math.radians(55), 4, 'X')
        organic_leaf(bm, 0.17, 0.08, mtx, HEAD, n=4, lift=0.02, droop=0.04, fold=0.03, twist=0.1, th=0.02)

    rig.build(smooth_angle=55.0, subdiv={"Body": 1, "Flame": 1, "ArmL": 1, "ArmR": 1})
    return col
