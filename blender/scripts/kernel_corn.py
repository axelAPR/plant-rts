# plantRTS — Maïs / Kernel Corn (qualité de référence, langage visuel du Pisto-pois v2).
import math
from mathutils import Vector, Matrix, Quaternion


def cob_profile(z0, z1, r_mid, r_end, rows, bump):
    """Profil d'épi : rangées de grains alternées (reliefs en damier après lissage)."""
    prof = [(0, z0)]
    for i in range(rows + 1):
        t = i / rows
        r = r_end + (r_mid - r_end) * math.sin(math.pi * min(1.0, t * 1.05))
        prof.append((r + (bump if i % 2 else 0.0), z0 + (z1 - z0) * t))
    prof.append((0, z1 + (z1 - z0) * 0.025))
    return prof


def kernel_cob(bm, z0, z1, r_mid, r_end, rows, seg, depth, mtx, mi):
    """Épi à grains en quinconce : anneaux décalés d'un demi-pas, sommets alternés
    creux / bombés ; le lissage transforme ce damier en grains arrondis lisibles."""
    rings = []
    for i in range(rows + 1):
        t = i / rows
        r = r_end + (r_mid - r_end) * math.sin(math.pi * min(1.0, t * 1.05))
        z = z0 + (z1 - z0) * t
        off = (i % 2) * math.pi / seg
        rings.append([bm.verts.new(mtx @ Vector((r * (1 - depth * (k % 2)) * math.cos(2 * math.pi * k / seg + off),
                                                 r * (1 - depth * (k % 2)) * math.sin(2 * math.pi * k / seg + off), z)))
                      for k in range(seg)])
    faces = []
    for a, b in zip(rings, rings[1:]):
        for k in range(seg):
            faces.append(bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k])))
    for ring, z, top in ((rings[0], z0, False), (rings[-1], z1 + (z1 - z0) * 0.03, True)):
        c = bm.verts.new(mtx @ Vector((0, 0, z)))
        for k in range(seg):
            faces.append(bm.faces.new((ring[k], ring[(k + 1) % seg], c) if top else (ring[(k + 1) % seg], ring[k], c)))
    for f in faces:
        f.material_index = mi


def build():
    col = reset_scene("KernelCorn")
    rig = Rig("KernelCorn", col)
    YE, YD, HEAD, LEAF, LEAF2 = (rig.m(n) for n in ("PlantRef_Yellow", "PlantRef_YellowDeep", "PlantRef_Head", "PlantRef_Leaf", "PlantRef_LeafAlt"))
    EYE, EYEL, MOUTH, TAN = rig.m("PlantRef_Eye"), rig.m("PlantRef_EyeLight"), rig.m("PlantRef_MouthRed"), rig.m("PlantRef_Tan")

    # Épi (non lissé : les grains en quinconce restent lisibles)
    bm = rig.part("Body", (0, 0, 0))
    kernel_cob(bm, 0.0, 1.42, 0.28, 0.17, 24, 22, 0.13, Matrix(), YE)

    # Spathes en manteau (ouvert devant)
    bm = rig.part("Husk", (0, 0, 0), "Body")
    for i, a in enumerate((65, 110, 155, 205, 250, 295)):
        d = Vector((math.sin(math.radians(a)), -math.cos(math.radians(a)), 0))
        mtx = Matrix.Translation(d * 0.17 + Vector((0, 0, 0.02))) @ Matrix.Rotation(math.atan2(-d.x, d.y), 4, 'Z')             @ Matrix.Rotation(math.radians(80), 4, 'X')
        organic_leaf(bm, 1.0, 0.22, mtx, LEAF if i % 2 else HEAD, n=5, lift=-0.13, droop=0.06, fold=0.06,
                     twist=0.25 * (1 if i % 2 else -1), th=0.035, petiole=0.45)

    # Visage et barbe de soie : regard dur, grimace
    bm = rig.part("Face", (0, 0, 0), "Body")
    for a in (-35, 0, 35, 160, 200):
        d = Vector((math.sin(math.radians(a)), 0.5, 0)).normalized()
        mtx = Matrix.Translation((0, 0.02, 1.43)) @ Matrix.Rotation(math.atan2(-d.x, d.y), 4, 'Z') @ Matrix.Rotation(math.radians(55), 4, 'X')
        organic_leaf(bm, 0.24, 0.05, mtx, TAN, n=4, lift=0.03, droop=0.14, fold=0.0, twist=0.3, th=0.015, petiole=0.5)
    c, R = Vector((0, 0, 1.12)), (0.28, 0.28, 0.3)
    ref_plant_eyes(bm, c, R, EYE, EYEL, YE, spread=0.38, up=0.36, fwd=-0.82, size=0.82, tilt=14, lid_tilt=14)
    p, d = surface_point(c, R, (0, -1, -0.3))
    open_mouth(bm, p - d * 0.005 + Vector((0, 0, 0.02)), 0.075, 0.04, MOUTH, None, depth=0.04, frown=True)

    # Bras (feuilles roulées) + épis-canons (pièces d'arme séparées)
    for s, side in ((1, "L"), (-1, "R")):
        shoulder = Vector((0.24 * s, 0, 0.88))
        hand = Vector((0.38 * s, -0.3, 0.76))
        bm = rig.part("Arm" + side, shoulder, "Body")
        tube_path(bm, [shoulder, shoulder + Vector((0.09 * s, -0.08, -0.06)), hand], [0.07, 0.062, 0.055], 8, HEAD)
        ellipsoid(bm, hand, (0.08, 0.085, 0.075), HEAD, u=8, v=6)
        for k in range(3):
            mtx = Matrix.Translation(hand + Vector((0, 0.12, 0.03))) @ Matrix.Rotation(math.pi, 4, 'Z')                 @ Matrix.Rotation(math.radians(120 * k), 4, 'Y') @ Matrix.Translation((0, 0, 0.065)) @ Matrix.Rotation(math.radians(-14), 4, 'X')
            organic_leaf(bm, 0.24, 0.08, mtx, LEAF, n=4, lift=0.02, droop=0.0, fold=0.02, twist=0.1, th=0.02)
        bm = rig.part("Gun" + side, hand, "Arm" + side)
        gun = Matrix.Translation(hand + Vector((0, 0.1, 0.03))) @ align_z((0, -1, 0)).to_matrix().to_4x4()
        kernel_cob(bm, 0.0, 0.56, 0.1, 0.065, 12, 12, 0.14, gun, YE)
        rig.empty("Muzzle" + side, hand + Vector((0, -0.5, 0.03)), "Gun" + side)

    rig.build(smooth_angle=58.0, subdiv={"Husk": 1, "Face": 1, "ArmL": 1, "ArmR": 1})
    return col
