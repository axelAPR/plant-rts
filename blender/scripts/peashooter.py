# plantRTS — Pisto-pois, modèle de RÉFÉRENCE artistique des plantes.
# Exécution dans Blender : exec(open(chemin).read()) après prts_lib.py.
#
# Langage visuel de référence :
# - formes organiques lissées (cages basse définition + subdivision niveau 1) ;
# - tête d'un seul tenant : bulbe, cou du canon, lèvres et bouche creuse continus ;
# - tige en courbe douce, base évasée, col sous la tête ;
# - feuilles à nervure en V, torsion légère, épaisseur décroissante, tailles variées ;
# - yeux ovales noirs + reflet, paupières de la couleur de la peau (caractère) ;
# - palette mate PlantRef_* (peu spéculaire).

import math
from mathutils import Vector, Matrix, Quaternion

NECK = 0.62                                  # pivot de la tête (haut de la tige)
HEAD_C = Vector((0, 0.03, NECK + 0.32))      # centre du bulbe (monde)
HEAD_R = 0.335


def build_peashooter():
    col = reset_scene("Peashooter")
    rig = Rig("Peashooter", col)
    HEAD, STEM, LIP, MOUTH = (rig.m(n) for n in ("PlantRef_Head", "PlantRef_Stem", "PlantRef_Lip", "PlantRef_Mouth"))
    LEAF, LEAF2, EYE, EYEL = (rig.m(n) for n in ("PlantRef_Leaf", "PlantRef_LeafAlt", "PlantRef_Eye", "PlantRef_EyeLight"))

    # ---------------------------------------------------------------- Feuilles de base
    bm = rig.part("Leaves", (0, 0, 0))
    # Grandes feuilles (l'avant -Y reste dégagé), tailles et angles variés
    for a, L, W, tw, mi in ((0, 0.56, 0.21, 0.15, LEAF), (68, 0.5, 0.19, -0.2, LEAF2), (140, 0.47, 0.18, 0.2, LEAF),
                            (220, 0.48, 0.18, -0.15, LEAF2), (292, 0.52, 0.2, 0.18, LEAF)):
        mtx = Matrix.Rotation(math.radians(a), 4, 'Z') @ Matrix.Translation((0, 0.05, 0.04)) \
            @ Matrix.Rotation(math.radians(2), 4, 'X')
        organic_leaf(bm, L, W, mtx, mi, n=5, lift=0.13, droop=0.17, fold=0.05, twist=tw, th=0.035)
    # ---------------------------------------------------------------- Tige
    # Base évasée qui recouvre la naissance des feuilles ; le haut s'enfonce dans la tête.
    bm = rig.part("Stem", (0, 0, 0))
    path = [(0, 0, 0.012), (0, 0.004, 0.06), (0, 0.014, 0.14), (0, 0.03, 0.27), (0, 0.03, 0.4),
            (0, 0.012, 0.52), (0, 0.005, 0.63), (0, 0.01, 0.78)]
    radii = [0.165, 0.125, 0.1, 0.09, 0.087, 0.09, 0.098, 0.1]
    tube_path(bm, path, radii, 10, STEM)

    # ---------------------------------------------------------------- Tête (une seule surface)
    bm = rig.part("Head", (0, 0, NECK), "Stem")
    R = HEAD_R
    prof = [(0, -R)]
    for deg in range(165, 30, -15):                       # bulbe, de l'arrière vers l'avant
        a = math.radians(deg)
        prof.append((R * math.sin(a), R * math.cos(a)))
    prof += [(0.168, 0.33), (0.138, 0.4), (0.132, 0.47),   # cou du canon (creux de raccord)
             (0.145, 0.53), (0.18, 0.575), (0.192, 0.615), # renflement des lèvres
             (0.178, 0.648), (0.145, 0.662), (0.118, 0.648),
             (0.108, 0.6), (0.1, 0.52), (0.085, 0.45), (0, 0.44)]   # bouche creuse
    n_bulb = 1 + len(range(165, 30, -15))
    mats = [HEAD] * (n_bulb + 2) + [LIP] * 6 + [MOUTH] * 4
    mats = mats[:len(prof) - 1]
    mats += [MOUTH] * (len(prof) - 1 - len(mats))
    mtx = Matrix.Translation(HEAD_C) @ Matrix.Rotation(math.radians(90), 4, 'X')
    lathe(bm, prof, 16, mtx, mats)
    # Déformations organiques : bulbe légèrement écrasé, arrière plus volumineux,
    # canon un peu abaissé, sommet légèrement plus large
    for v in bm.verts:
        p = v.co - HEAD_C
        fwd = -p.y / R
        if fwd < 0.75:
            back = max(0.0, -fwd)
            p.x *= 1.0 + 0.07 * back
            p.z *= 0.94 + 0.06 * back
        if fwd > 0.85:
            p.z -= 0.03 * min(1.0, (fwd - 0.85) / 0.4)
        v.co = HEAD_C + p

    # Yeux : ovales noirs + reflet, paupières (regard déterminé)
    for s in (-1, 1):
        d = Vector((0.43 * s, -0.76, 0.5)).normalized()
        p = HEAD_C + Vector((R * d.x, R * d.y, R * 0.94 * d.z))
        q = d.to_track_quat('-Y', 'Z') @ Quaternion((0, 1, 0), math.radians(-10 * s))
        ellipsoid(bm, p - d * 0.03, (0.085, 0.055, 0.124), EYE, q, 10, 6)
        ellipsoid(bm, p + d * 0.004 + q @ Vector((0.034 * s, 0, 0.052)), (0.031, 0.018, 0.035), EYEL, q, 6, 4)
        lid_q = q @ Quaternion((0, 1, 0), math.radians(-9 * s)) @ Quaternion((1, 0, 0), math.radians(-12))
        ellipsoid(bm, p - d * 0.042 + q @ Vector((0, 0, 0.088)), (0.112, 0.07, 0.056), HEAD, lid_q, 8, 5)

    # Touffe arrière : grande feuille + petite feuille secondaire
    for L, W, yaw, pitch, tw in ((0.42, 0.15, 0, 28, 0.2), (0.26, 0.1, 35, 45, -0.25)):
        d = Vector((math.sin(math.radians(yaw)) * 0.4, 0.62, 0.78)).normalized()
        base = HEAD_C + Vector((R * d.x, R * d.y, R * 0.94 * d.z)) - d * 0.04
        mtx = Matrix.Translation(base) @ Matrix.Rotation(math.radians(-yaw), 4, 'Z') \
            @ Matrix.Rotation(math.radians(pitch), 4, 'X')
        organic_leaf(bm, L, W, mtx, LEAF, n=5, lift=0.1, droop=0.26, fold=0.04, twist=tw, th=0.03)

    tip_y = HEAD_C.y - 0.662
    rig.empty("Muzzle", (0, tip_y - 0.02, HEAD_C.z - 0.03), "Head")
    rig.build(subdiv={"Leaves": 1, "Stem": 1, "Head": 1})
    # Les pointes des feuilles reposent sur le sol, sans le traverser.
    for v in bpy.data.objects["Leaves"].data.vertices:
        v.co.z = max(v.co.z, 0.004)
    return col
