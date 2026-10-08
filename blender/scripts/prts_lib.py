# plantRTS — bibliothèque de modélisation partagée (Blender 5.x, bmesh).
#
# Garantit une DA et des conventions communes à tous les modèles :
# - palette de matériaux simples (Principled BSDF, sans texture) ;
# - primitives low-poly (ellipsoïdes, cylindres, boîtes chanfreinées, feuilles épaisses) ;
# - « Rig » : hiérarchie d'objets rigides avec pivots aux articulations, transformations
#   appliquées (rotation 0, échelle 1), avant du modèle vers -Y (→ +Z dans Godot) ;
# - vérifications (triangles, géométrie non manifold, encombrement) et export .glb.
#
# Utilisation dans Blender : exec(open(chemin).read()) puis construire avec Rig.

import bpy, bmesh, math, os
from mathutils import Vector, Matrix, Quaternion

FRONT = Vector((0, -1, 0))


# ---------------------------------------------------------------- Couleurs

def srgb(hex_color):
    """'#RRGGBB' (sRGB) → tuple linéaire, pour saisir les couleurs comme en peinture."""
    h = hex_color.lstrip('#')
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


# nom → (couleur, rugosité, métal, émission)
PALETTE = {
    # Plantes (valeurs reprises du Pisto-pois)
    "Plant_Green":  ((0.20, 0.62, 0.03), 0.55, 0.0, None),
    "Plant_Leaf":   ((0.04, 0.24, 0.015), 0.65, 0.0, None),
    "Plant_Dark":   ((0.008, 0.012, 0.006), 0.4, 0.0, None),
    "Plant_White":  ((0.85, 0.85, 0.85), 0.3, 0.0, None),
    "Plant_Yellow": (srgb("#FFD21F"), 0.5, 0.0, None),
    "Plant_Orange": (srgb("#FF8A1C"), 0.5, 0.0, None),
    "Plant_Brown":  (srgb("#7A4A22"), 0.7, 0.0, None),
    "Plant_Tan":    (srgb("#C98B4B"), 0.7, 0.0, None),
    "Plant_SunFace": (srgb("#E3A453"), 0.6, 0.0, None),
    "Plant_Purple": (srgb("#7D2E9E"), 0.5, 0.0, None),
    "Plant_PurpleLight": (srgb("#B36AD6"), 0.5, 0.0, None),
    "Plant_MouthRed": (srgb("#7A1430"), 0.6, 0.0, None),
    "Plant_Magenta": (srgb("#D11E6A"), 0.5, 0.0, None),
    "Plant_RoseFace": (srgb("#FFC6D8"), 0.55, 0.0, None),
    "Plant_Pink":   (srgb("#FF6FA8"), 0.5, 0.0, None),
    "Plant_Red":    (srgb("#D8262E"), 0.5, 0.0, None),
    "Plant_Cream":  (srgb("#FFF3C4"), 0.5, 0.0, None),
    "Plant_Bark":   (srgb("#8A5A32"), 0.8, 0.0, None),
    "Plant_Flame":  (srgb("#FF9A1F"), 0.5, 0.0, srgb("#FF7A10")),
    "Plant_FlameCore": (srgb("#FFE45C"), 0.5, 0.0, srgb("#FFD040")),
    "Plant_Magic":  (srgb("#FF5FD0"), 0.4, 0.0, srgb("#FF40C0")),
    # Palette de référence « qualité premium » des plantes (Pisto-pois v2) : mate, peu spéculaire
    "PlantRef_Head":     (srgb("#62B834"), 0.72, 0.0, None),
    "PlantRef_Stem":     (srgb("#4E9C2B"), 0.75, 0.0, None),
    "PlantRef_Lip":      (srgb("#93D84E"), 0.7, 0.0, None),
    "PlantRef_Mouth":    (srgb("#16300C"), 0.85, 0.0, None),
    "PlantRef_Leaf":     (srgb("#2F8C1F"), 0.78, 0.0, None),
    "PlantRef_LeafAlt":  (srgb("#26731A"), 0.78, 0.0, None),
    "PlantRef_Eye":      (srgb("#141414"), 0.38, 0.0, None),
    "PlantRef_EyeLight": (srgb("#FFFFFF"), 0.5, 0.0, None),
    "PlantRef_Yellow":   (srgb("#FFC21F"), 0.7, 0.0, None),
    "PlantRef_YellowDeep": (srgb("#F59A12"), 0.7, 0.0, None),
    "PlantRef_SunFace":  (srgb("#D9913F"), 0.72, 0.0, None),
    "PlantRef_Brown":    (srgb("#6E3F1C"), 0.8, 0.0, None),
    "PlantRef_Tan":      (srgb("#D2A064"), 0.78, 0.0, None),
    "PlantRef_Cream":    (srgb("#F4E6B8"), 0.7, 0.0, None),
    "PlantRef_Purple":   (srgb("#7B2A9E"), 0.7, 0.0, None),
    "PlantRef_PurpleLight": (srgb("#A95CCB"), 0.7, 0.0, None),
    "PlantRef_MouthRed": (srgb("#6A1030"), 0.85, 0.0, None),
    "PlantRef_Tongue":   (srgb("#E2557A"), 0.7, 0.0, None),
    "PlantRef_Pink":     (srgb("#FF6FA5"), 0.7, 0.0, None),
    "PlantRef_Magenta":  (srgb("#C41A62"), 0.72, 0.0, None),
    "PlantRef_RoseFace": (srgb("#FFC3D5"), 0.7, 0.0, None),
    "PlantRef_Orange":   (srgb("#F5841A"), 0.72, 0.0, None),
    "PlantRef_Bark":     (srgb("#8A5A30"), 0.85, 0.0, None),
    "PlantRef_BarkDark": (srgb("#5A381B"), 0.85, 0.0, None),
    "PlantRef_Wood":     (srgb("#D7A86A"), 0.8, 0.0, None),
    "PlantRef_Teeth":    (srgb("#F4F1E4"), 0.55, 0.0, None),
    "PlantRef_Flame":    (srgb("#FF8A1A"), 0.6, 0.0, srgb("#FF6A0A")),
    "PlantRef_FlameCore": (srgb("#FFE05A"), 0.6, 0.0, srgb("#FFD040")),
    "PlantRef_Magic":    (srgb("#FF63D2"), 0.5, 0.0, srgb("#FF3CC0")),
    "PlantRef_Cyan":     (srgb("#5EE6FF"), 0.35, 0.0, srgb("#25C0E8")),
    "PlantRef_Metal":    (srgb("#9AA2AB"), 0.45, 0.6, None),
    "PlantRef_MetalDark": (srgb("#3E434A"), 0.5, 0.55, None),
    # Palette de référence des zombies (mate, même langage que les plantes)
    "ZombieRef_Skin":    (srgb("#9DB085"), 0.78, 0.0, None),
    "ZombieRef_SkinDark": (srgb("#7D8F67"), 0.8, 0.0, None),
    "ZombieRef_Eye":     (srgb("#F3EBC3"), 0.5, 0.0, None),
    "ZombieRef_Pupil":   (srgb("#151515"), 0.4, 0.0, None),
    "ZombieRef_Mouth":   (srgb("#3A1820"), 0.85, 0.0, None),
    "ZombieRef_Teeth":   (srgb("#E9DFB2"), 0.6, 0.0, None),
    "Ref_Olive":     (srgb("#5F6E30"), 0.85, 0.0, None),
    "Ref_OliveDark": (srgb("#3F4A20"), 0.85, 0.0, None),
    "Ref_Brown":     (srgb("#7A5030"), 0.85, 0.0, None),
    "Ref_White":     (srgb("#ECECE4"), 0.75, 0.0, None),
    "Ref_Grey":      (srgb("#6C7076"), 0.85, 0.0, None),
    "Ref_Black":     (srgb("#27272C"), 0.8, 0.0, None),
    "Ref_Red":       (srgb("#C42E2A"), 0.75, 0.0, None),
    "Ref_Blue":      (srgb("#2F55C0"), 0.72, 0.0, None),
    "Ref_Denim":     (srgb("#3A5A8C"), 0.85, 0.0, None),
    "Ref_LightBlue": (srgb("#9CC2E4"), 0.78, 0.0, None),
    "Ref_Yellow":    (srgb("#F2C02C"), 0.7, 0.0, None),
    "Ref_Orange":    (srgb("#F2861C"), 0.72, 0.0, None),
    "Ref_Gold":      (srgb("#DDB03A"), 0.5, 0.5, None),
    "Ref_Leather":   (srgb("#5C3B22"), 0.8, 0.0, None),
    "Ref_Wood":      (srgb("#8B5E34"), 0.85, 0.0, None),
    "Ref_HairBlack": (srgb("#1F1C1B"), 0.85, 0.0, None),
    "Ref_HairGrey":  (srgb("#C2C2BC"), 0.85, 0.0, None),
    "Ref_Brain":     (srgb("#EE8CA4"), 0.7, 0.0, None),
    "Ref_Purple":    (srgb("#6E2E9A"), 0.72, 0.0, None),
    "Ref_Metal":     (srgb("#959CA4"), 0.45, 0.6, None),
    "Ref_MetalDark": (srgb("#3B4047"), 0.5, 0.55, None),
    "Ref_MechYellow": (srgb("#E8AE22"), 0.6, 0.15, None),
    "Ref_Cyan":      (srgb("#5EE6FF"), 0.35, 0.0, srgb("#25C0E8")),
    "Ref_Goo":       (srgb("#7CFF4A"), 0.4, 0.0, srgb("#50E020")),
    # Zombies
    "Zombie_Skin":  (srgb("#A4B58E"), 0.7, 0.0, None),
    "Zombie_Eye":   (srgb("#F4EDCB"), 0.3, 0.0, None),
    "Zombie_Mouth": (srgb("#3A1E22"), 0.6, 0.0, None),
    # Tissus et accessoires
    "Cloth_Olive":  (srgb("#5E6B33"), 0.8, 0.0, None),
    "Cloth_OliveDark": (srgb("#414A24"), 0.8, 0.0, None),
    "Cloth_Brown":  (srgb("#7B5434"), 0.8, 0.0, None),
    "Cloth_White":  (srgb("#EDEDE6"), 0.7, 0.0, None),
    "Cloth_Grey":   (srgb("#6E7175"), 0.8, 0.0, None),
    "Cloth_Black":  (srgb("#26262B"), 0.7, 0.0, None),
    "Cloth_Red":    (srgb("#C8302B"), 0.7, 0.0, None),
    "Cloth_Blue":   (srgb("#3157C4"), 0.6, 0.0, None),
    "Cloth_LightBlue": (srgb("#9EC3E6"), 0.7, 0.0, None),
    "Cloth_Yellow": (srgb("#F2C230"), 0.6, 0.0, None),
    "Cloth_Orange": (srgb("#F28A1E"), 0.6, 0.0, None),
    "Cloth_Gold":   (srgb("#E0B33C"), 0.4, 0.6, None),
    "Leather":      (srgb("#5A3A22"), 0.7, 0.0, None),
    "Wood":         (srgb("#8B5E34"), 0.8, 0.0, None),
    "Hair_Black":   (srgb("#1E1B1A"), 0.8, 0.0, None),
    "Hair_Grey":    (srgb("#BDBDB8"), 0.8, 0.0, None),
    "Brain_Pink":   (srgb("#F28FA6"), 0.5, 0.0, None),
    "Metal":        (srgb("#8C9299"), 0.35, 0.8, None),
    "Metal_Dark":   (srgb("#3C4046"), 0.4, 0.7, None),
    "Mech_Yellow":  (srgb("#E8B020"), 0.45, 0.3, None),
    "Glass_Cyan":   (srgb("#58E0FF"), 0.15, 0.0, srgb("#2AB8E0")),
    "Goo_Green":    (srgb("#7CFF4A"), 0.3, 0.0, srgb("#50E020")),
}


def mat(name):
    col, rough, metal, emit = PALETTE[name]
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (*col, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1.0)
        b.inputs["Emission Strength"].default_value = 1.5
    m.diffuse_color = (*col, 1.0)
    m.roughness = rough
    m.metallic = metal
    if name.startswith(("PlantRef_", "ZombieRef_", "Ref_")):
        # Reflet spéculaire atténué : rendu mat, pas d'aspect plastique.
        b.inputs["Specular IOR Level"].default_value = 0.3
    return m


# ---------------------------------------------------------------- Primitives
# Toutes ajoutent la géométrie en coordonnées monde dans le bmesh donné, avec
# l'index de matériau `mi` (int) ou une liste par bande pour lathe().

def _set_mi(faces, mi):
    for f in faces:
        f.material_index = mi


def lathe(bm, prof, seg, mtx, mi=0, ridge=0.0):
    """Surface de révolution d'un profil [(rayon, hauteur)] autour de l'axe Z local.
    `ridge` > 0 creuse un sommet sur deux (côtes de cactus, potiron…)."""
    rings = []
    for r, h in prof:
        if r < 1e-6:
            rings.append([bm.verts.new(mtx @ Vector((0, 0, h)))])
        else:
            rings.append([bm.verts.new(mtx @ Vector((r * (1 - ridge * (i % 2)) * math.cos(2 * math.pi * i / seg),
                                                     r * (1 - ridge * (i % 2)) * math.sin(2 * math.pi * i / seg), h)))
                          for i in range(seg)])
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        fs = []
        if len(a) == 1:
            for i in range(seg):
                fs.append(bm.faces.new((a[0], b[(i + 1) % seg], b[i])))
        elif len(b) == 1:
            for i in range(seg):
                fs.append(bm.faces.new((a[i], a[(i + 1) % seg], b[0])))
        else:
            for i in range(seg):
                fs.append(bm.faces.new((a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i])))
        _set_mi(fs, mi[k] if isinstance(mi, (list, tuple)) else mi)


def align_z(direction):
    """Rotation amenant +Z sur `direction`."""
    return Vector((0, 0, 1)).rotation_difference(Vector(direction).normalized())


def ellipsoid(bm, center, radii, mi, rot=None, u=12, v=8):
    rot = rot or Quaternion()
    m = Matrix.Translation(Vector(center)) @ rot.to_matrix().to_4x4() @ Matrix.Diagonal((*radii, 1))
    res = bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1.0, matrix=m)
    _set_mi({f for vv in res['verts'] for f in vv.link_faces}, mi)


def cyl(bm, p0, p1, r0, r1, mi, seg=8):
    """Cylindre / tronc de cône fermé de p0 à p1 (r1 = 0 → cône)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    mtx = Matrix.Translation(p0) @ align_z(d).to_matrix().to_4x4()
    L = d.length
    prof = [(0, 0), (r0, 0), (r1, L), (0, L)] if r1 > 1e-6 else [(0, 0), (r0, 0), (0, L)]
    lathe(bm, prof, seg, mtx, mi)


def box(bm, center, size, mi, rot=None, bevel=0.0):
    """Boîte, éventuellement chanfreinée (aspect cartoon plus doux)."""
    rot = rot or Quaternion()
    m = Matrix.Translation(Vector(center)) @ rot.to_matrix().to_4x4() @ Matrix.Diagonal((*size, 1))
    res = bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    verts = res['verts']
    _set_mi({f for vv in verts for f in vv.link_faces}, mi)
    if bevel > 0:
        edges = list({e for vv in verts for e in vv.link_edges})
        res = bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=1, affect='EDGES',
                              profile=0.5, clamp_overlap=True)
        _set_mi(res['faces'], mi)


def dome(bm, center, rx, ry, rz, mi, seg=12, steps=4, rot=None):
    """Demi-ellipsoïde fermé (casque, chapeau, cockpit), base dans le plan de `center`."""
    prof = [(0, 0)] + [(math.cos(t), math.sin(t)) for t in
                       [i * (math.pi / 2) / steps for i in range(steps)]] + [(0, 1)]
    rot = rot or Quaternion()
    m = Matrix.Translation(Vector(center)) @ rot.to_matrix().to_4x4() @ Matrix.Diagonal((rx, ry, rz, 1))
    lathe(bm, prof, seg, m, mi)


def leaf(bm, L, W, mtx, mi, n=6, lift=0.1, droop=0.1, cup=0.03, th=0.025, tip=0.8):
    """Feuille épaisse fermée le long de +Y local (largeur X, courbure Z)."""
    top, bot = [], []
    for j in range(n + 1):
        t = j / n
        y = L * t
        z = lift * math.sin(math.pi * t) - droop * t * t
        w = W * max(math.sin(math.pi * t ** tip), 0.0) ** 0.8
        if j in (0, n):
            v = bm.verts.new(mtx @ Vector((0, y, z)))
            top.append([v]); bot.append([v])
        else:
            e = cup * (w / W)
            top.append([bm.verts.new(mtx @ Vector((x, y, zz))) for x, zz in ((-w, z + e), (0, z), (w, z + e))])
            bot.append([bm.verts.new(mtx @ Vector((x, y, zz - th))) for x, zz in ((-w * 0.9, z + e), (0, z), (w * 0.9, z + e))])

    def strip(rows, flip):
        out = []
        for j in range(n):
            a, b = rows[j], rows[j + 1]
            if len(a) == 1:
                fs = [(a[0], b[1], b[0]), (a[0], b[2], b[1])]
            elif len(b) == 1:
                fs = [(a[0], a[1], b[0]), (a[1], a[2], b[0])]
            else:
                fs = [(a[0], a[1], b[1], b[0]), (a[1], a[2], b[2], b[1])]
            out += [bm.faces.new(tuple(reversed(f)) if flip else f) for f in fs]
        return out

    faces = strip(top, False) + strip(bot, True)
    for side in (0, -1):
        for j in range(n):
            q = [top[j][side], top[j + 1][side], bot[j + 1][side], bot[j][side]]
            uniq = []
            for vv in q:
                if vv not in uniq:
                    uniq.append(vv)
            faces.append(bm.faces.new(uniq if side == -1 else list(reversed(uniq))))
    _set_mi(faces, mi)


def leaf_at(bm, base, direction, L, W, mi, pitch=0.0, **kw):
    """Feuille partant de `base`, orientée (dans le plan XY) vers `direction`, inclinée de `pitch` (rad)."""
    d = Vector(direction); d.z = 0; d.normalize()
    yaw = math.atan2(-d.x, d.y)
    mtx = Matrix.Translation(Vector(base)) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(pitch, 4, 'X')
    leaf(bm, L, W, mtx, mi, **kw)


def leaf_dir(bm, base, direction, L, W, mi, roll=0.0, **kw):
    """Feuille partant de `base` dans une direction 3D quelconque (`roll` en rad autour d'elle)."""
    d = Vector(direction).normalized()
    q = Vector((0, 1, 0)).rotation_difference(d) @ Quaternion((0, 1, 0), roll)
    leaf(bm, L, W, Matrix.Translation(Vector(base)) @ q.to_matrix().to_4x4(), mi, **kw)


def smile(bm, center, width, height, mi_mouth, mi_skin, forward=FRONT, tongue_mi=None):
    """Sourire en croissant : bouche sombre masquée en haut par une pastille couleur peau."""
    f = Vector(forward).normalized()
    c = Vector(center)
    ellipsoid(bm, c, (width, 0.03, height), mi_mouth, f.to_track_quat('-Y', 'Z'), 14, 6)
    ellipsoid(bm, c + f * 0.006 + Vector((0, 0, height * 0.62)), (width * 1.08, 0.03, height * 0.78),
              mi_skin, f.to_track_quat('-Y', 'Z'), 14, 6)
    if tongue_mi is not None:
        ellipsoid(bm, c + f * 0.016 + Vector((0, 0, -height * 0.5)), (width * 0.48, 0.02, height * 0.34),
                  tongue_mi, f.to_track_quat('-Y', 'Z'), 10, 5)


def leaf_rosette(bm, count, L, W, mi, z=0.035, r0=0.05, start_deg=0.0, **kw):
    """Couronne de feuilles au sol ; avec start_deg=0, une feuille vers l'arrière (+Y)."""
    for k in range(count):
        a = math.radians(start_deg + 360.0 * k / count)
        mtx = Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation((0, r0, z))
        leaf(bm, L, W, mtx, mi, **kw)


def surface_point(c, R, d):
    """Point de la surface de l'ellipsoïde (centre c, rayons R) dans la direction d."""
    d = Vector(d).normalized()
    return Vector(c) + Vector((R[0] * d.x, R[1] * d.y, R[2] * d.z)), d


def plant_eyes(bm, c, R, mi_dark, mi_white, spread=0.40, up=0.44, size=(0.07, 0.04, 0.105),
               tilt=12.0, forward=FRONT, scale=1.0):
    """Yeux cartoon des plantes (ovales noirs + reflet blanc), comme le Pisto-pois."""
    f = Vector(forward).normalized()
    side = Vector((0, 0, 1)).cross(f).normalized()  # vers -X quand f = -Y : on symétrise
    for s in (-1, 1):
        d = (side * spread * s + f * 0.80 + Vector((0, 0, up))).normalized()
        p, d = surface_point(c, R, d)
        q = d.to_track_quat('-Y', 'Z') @ Quaternion((0, 1, 0), math.radians(-tilt * s))
        sz = tuple(x * scale for x in size)
        ellipsoid(bm, p - d * 0.012 * scale, sz, mi_dark, q, 10, 6)
        ellipsoid(bm, p + d * 0.02 * scale + q @ Vector((0.027 * s * scale, 0, 0.048 * scale)),
                  tuple(x * scale for x in (0.026, 0.02, 0.026)), mi_white, q, 8, 5)


def zombie_eye(bm, pos, r, mi_white, mi_dark, look=FRONT, pupil=0.38):
    """Œil de zombie : globe clair légèrement saillant + petite pupille."""
    look = Vector(look).normalized()
    q = look.to_track_quat('-Y', 'Z')
    ellipsoid(bm, pos, (r, r * 0.8, r), mi_white, q, 10, 6)
    ellipsoid(bm, Vector(pos) + look * r * 0.72, (r * pupil, r * pupil * 0.6, r * pupil), mi_dark, q, 8, 5)


# ---------------------------------------------------------------- Formes organiques (qualité de référence)
# Cages basse définition destinées à être lissées par subdivision (Rig.build(subdiv=...)).

def tube_path(bm, points, radii, seg, mi, cap_start=True, cap_end=True):
    """Tube lisse le long d'un chemin (repère par transport parallèle), rayon variable."""
    pts = [Vector(p) for p in points]
    tangents = []
    for i in range(len(pts)):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        tangents.append((b - a).normalized())
    normal = tangents[0].orthogonal().normalized()
    rings = []
    for i, (p, t, r) in enumerate(zip(pts, tangents, radii)):
        if i > 0:
            normal = (normal - t * normal.dot(t)).normalized()
        binormal = t.cross(normal)
        rings.append([bm.verts.new(p + (normal * math.cos(2 * math.pi * k / seg) +
                                         binormal * math.sin(2 * math.pi * k / seg)) * r) for k in range(seg)])
    faces = []
    for a, b in zip(rings, rings[1:]):
        for k in range(seg):
            faces.append(bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k])))
    for ring, p, on in ((rings[0], pts[0], cap_start), (rings[-1], pts[-1], cap_end)):
        if on:
            c = bm.verts.new(p)
            for k in range(seg):
                faces.append(bm.faces.new((ring[k], ring[(k + 1) % seg], c)))
    _set_mi(faces, mi)


def organic_leaf(bm, L, W, mtx, mi, n=6, lift=0.1, droop=0.1, fold=0.04, twist=0.0,
                 th=0.03, petiole=0.14, tip=0.75):
    """Feuille organique fermée le long de +Y local : nervure centrale en V (`fold`),
    torsion progressive (`twist`, rad), épaisseur décroissante vers la pointe,
    pétiole étroit à la base. Cinq colonnes pour une courbure propre une fois lissée."""
    cols = (-1.0, -0.5, 0.0, 0.5, 1.0)
    top, bot = [], []
    for j in range(n):
        t = j / n
        y = L * t
        zc = lift * math.sin(math.pi * t * 0.9) - droop * t * t
        w = max(W * math.sin(math.pi * t ** tip) ** 0.85, W * petiole * (1 - t))
        thick = th * (1.0 - 0.65 * t)
        rot = Matrix.Rotation(twist * t, 4, 'Y')
        rt, rb = [], []
        for c in cols:
            x = c * w
            z = zc + fold * abs(c) * (w / W)
            rt.append(bm.verts.new(mtx @ (Matrix.Translation((0, y, zc)) @ rot @ Vector((x, 0, z - zc)))))
            rb.append(bm.verts.new(mtx @ (Matrix.Translation((0, y, zc)) @ rot @ Vector((x * 0.92, 0, z - zc - thick)))))
        top.append(rt); bot.append(rb)
    tip_v = bm.verts.new(mtx @ Vector((0, L, lift * math.sin(math.pi * 0.9) - droop)))
    faces = []
    for rows, flip in ((top, False), (bot, True)):
        for j in range(n):
            for c in range(4):
                if j + 1 < n:
                    f = (rows[j][c], rows[j][c + 1], rows[j + 1][c + 1], rows[j + 1][c])
                else:
                    f = (rows[j][c], rows[j][c + 1], tip_v)
                faces.append(bm.faces.new(tuple(reversed(f)) if flip else f))
    for side in (0, 4):
        for j in range(n):
            if j + 1 < n:
                f = (top[j][side], top[j + 1][side], bot[j + 1][side], bot[j][side])
            else:
                f = (top[j][side], tip_v, bot[j][side])
            faces.append(bm.faces.new(f if side == 4 else tuple(reversed(f))))
    for c in range(4):
        faces.append(bm.faces.new((top[0][c + 1], top[0][c], bot[0][c], bot[0][c + 1])))
    _set_mi(faces, mi)


def ref_plant_eyes(bm, c, R, EYE, EYEL, LID=None, spread=0.43, up=0.5, fwd=-0.76, size=1.0,
                   tilt=10.0, lid_tilt=9.0, forward=FRONT):
    """Yeux de référence (Pisto-pois v2) : ovale noir enfoncé, reflet, paupière fondue
    dans la peau (`LID` = matériau de peau ; None = sans paupière, regard plus doux).
    `R` : rayons de la forme porteuse (ellipsoïde) ; `tilt` > 0 : regard déterminé."""
    f = Vector(forward).normalized()
    side = Vector((0, 0, 1)).cross(f).normalized()
    c = Vector(c)
    for s in (-1, 1):
        d = (side * spread * s + f * -fwd + Vector((0, 0, up))).normalized()
        p = c + Vector((R[0] * d.x, R[1] * d.y, R[2] * d.z))
        q = d.to_track_quat('-Y', 'Z') @ Quaternion((0, 1, 0), math.radians(-tilt * s))
        k = size
        ellipsoid(bm, p - d * 0.03 * k, (0.085 * k, 0.055 * k, 0.124 * k), EYE, q, 10, 6)
        ellipsoid(bm, p + d * 0.004 * k + q @ Vector((0.034 * s * k, 0, 0.052 * k)),
                  (0.031 * k, 0.018 * k, 0.035 * k), EYEL, q, 6, 4)
        if LID is not None:
            lq = q @ Quaternion((0, 1, 0), math.radians(-lid_tilt * s)) @ Quaternion((1, 0, 0), math.radians(-12))
            ellipsoid(bm, p - d * 0.042 * k + q @ Vector((0, 0, 0.088 * k)), (0.112 * k, 0.07 * k, 0.056 * k), LID, lq, 8, 5)


def ref_leaf_rosette(bm, mats, specs=None, z=0.04, r0=0.05):
    """Couronne de grandes feuilles organiques au sol (référence Pisto-pois v2).
    specs : [(angle°, longueur, largeur, torsion)] ; matériaux alternés ; avant -Y dégagé."""
    specs = specs or ((0, 0.56, 0.21, 0.15), (68, 0.5, 0.19, -0.2), (140, 0.47, 0.18, 0.2),
                      (220, 0.48, 0.18, -0.15), (292, 0.52, 0.2, 0.18))
    for i, (a, L, W, tw) in enumerate(specs):
        mtx = Matrix.Rotation(math.radians(a), 4, 'Z') @ Matrix.Translation((0, r0, z)) \
            @ Matrix.Rotation(math.radians(2), 4, 'X')
        organic_leaf(bm, L, W, mtx, mats[i % len(mats)], n=5, lift=0.13, droop=0.17, fold=0.05, twist=tw, th=0.035)


def open_mouth(bm, center, width, height, MOUTH, TONGUE=None, forward=FRONT, depth=0.05, frown=False):
    """Bouche ouverte en « D » (sourire, ou grimace si `frown`) : demi-volume sombre
    enfoncé dans la surface — le contour visible naît de l'intersection, sans bosse."""
    f = Vector(forward).normalized()
    base_q = f.to_track_quat('-Y', 'Z')
    flip = Quaternion((0, 1, 0), math.pi) if frown else Quaternion()
    q = base_q @ flip @ Quaternion((1, 0, 0), math.pi)          # dôme vers le bas, base plane en haut
    c = Vector(center)
    dome(bm, c, width, depth, height, MOUTH, seg=14, steps=3, rot=q)
    if TONGUE is not None:
        tz = -height * 0.62 if not frown else height * 0.62
        ellipsoid(bm, c + Vector((0, 0, tz)) + f * (depth * 0.15), (width * 0.5, depth * 0.6, height * 0.28),
                  TONGUE, base_q, 10, 5)


def clamp_to_ground(obj_name, z_min=0.004):
    """Remonte au niveau du sol les sommets d'une pièce qui le traversent (pointes de feuilles)."""
    ob = bpy.data.objects[obj_name]
    mw = ob.matrix_world
    inv = mw.inverted()
    for v in ob.data.vertices:
        w = mw @ v.co
        if w.z < z_min:
            w.z = z_min
            v.co = inv @ w


def zombie_ref(rig, M, bulk=1.0, pose="gun", head_scale=1.0, eye_sizes=(0.076, 0.062), hunch=1.0,
               jaw=1.0, lids=(0.35, 0.15)):
    """Gabarit de zombie de référence : formes organiques lissées (subdivision niveau 1).
    M : {'skin', 'shirt', 'pants', 'shoes', 'sleeve'?, 'forearm'?, 'hand'?}.
    Pièces : Hips → LegL/LegR, Torso → Head, ArmL/ArmR. Gauche = +X, avant = -Y.
    Caractère : grosse tête, mâchoire avancée, arcade, yeux dépareillés à paupières
    tombantes (`lids` = fermeture de chaque œil), dos voûté (`hunch`)."""
    SK = rig.m(M["skin"]); SKD = rig.m("ZombieRef_SkinDark")
    S, P, SH = rig.m(M["shirt"]), rig.m(M["pants"]), rig.m(M["shoes"])
    SL = rig.m(M.get("sleeve", M["shirt"]))
    FA = rig.m(M.get("forearm", M["skin"]))
    HA = rig.m(M.get("hand", M["skin"]))
    EYE, PUP, MO, TE = (rig.m(n) for n in ("ZombieRef_Eye", "ZombieRef_Pupil", "ZombieRef_Mouth", "ZombieRef_Teeth"))
    w = bulk
    k = {"hip": Vector((0, 0, 0.8))}

    bm = rig.part("Hips", k["hip"])
    lathe(bm, [(0, 0.64), (0.2 * w, 0.66), (0.25 * w, 0.76), (0.26 * w, 0.88), (0.23 * w, 0.96), (0, 0.98)], 12, Matrix(), P)
    for v in bm.verts:
        v.co.y *= 0.72
    for s, side in ((1, "L"), (-1, "R")):
        hip = Vector((0.13 * w * s, 0, 0.78))
        knee = Vector((0.145 * w * s, -0.05, 0.43))
        ankle = Vector((0.14 * w * s, 0.0, 0.13))
        bm = rig.part("Leg" + side, hip, "Hips")
        tube_path(bm, [hip + Vector((0, 0, 0.06)), hip, (hip + knee) / 2, knee, (knee + ankle) / 2, ankle],
                  [0.1 * w, 0.112 * w, 0.105 * w, 0.09 * w, 0.085 * w, 0.075 * w], 8, P)
        box(bm, ankle + Vector((0, -0.065, -0.065)), (0.18 * w, 0.33, 0.13), SH, bevel=0.05)
        k["ankle" + side] = ankle

    k["torso"] = Vector((0, 0, 0.88))
    k["chest_c"], k["chest_r"] = Vector((0, -0.03, 1.13)), (0.29 * w, 0.21 * w, 0.31)
    bm = rig.part("Torso", k["torso"], "Hips")
    torso_prof = [(0, 0.84), (0.24 * w, 0.85), (0.27 * w, 0.95), (0.29 * w, 1.08), (0.305 * w, 1.2),
                  (0.285 * w, 1.3), (0.2 * w, 1.38), (0.1, 1.42), (0, 1.43)]
    lathe(bm, torso_prof, 12, Matrix(), S)

    def torso_deform(co):
        t = max(0.0, (co.z - 0.9) / 0.5)
        co.y = co.y * 0.74 - 0.03 - 0.1 * hunch * t * t

    for v in bm.verts:
        torso_deform(v.co)

    def torso_r(z):
        for (r0, z0), (r1, z1) in zip(torso_prof[1:-1], torso_prof[2:-1]):
            if z0 <= z <= z1:
                return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
        return torso_prof[1][0] if z < torso_prof[1][1] else torso_prof[-2][0]

    def front(z, x=0.0):
        """Point de la face avant du torse à la hauteur z (pour poser chemise, cravate…)."""
        co = Vector((x, -math.sqrt(max(torso_r(z) ** 2 - x * x, 0.0)), z))
        torso_deform(co)
        return co

    def shell(bm_, z0, z1, mi, grow=0.03, seg=16, steps=6):
        """Coque de vêtement épousant le torse entre z0 et z1 (gilet, plastron…)."""
        prof = [(0, z0)] + [(torso_r(z0 + (z1 - z0) * i / steps) + grow, z0 + (z1 - z0) * i / steps)
                            for i in range(steps + 1)] + [(0, z1)]
        start = len(bm_.verts)
        lathe(bm_, prof, seg, Matrix(), mi)
        bm_.verts.ensure_lookup_table()
        for v in bm_.verts[start:]:
            torso_deform(v.co)

    k["front"], k["shell"] = front, shell
    tube_path(bm, [(0, -0.07, 1.33), (0, -0.1, 1.42), (0, -0.13, 1.52)], [0.09, 0.085, 0.08], 8, SK)
    dz = -0.1 * hunch

    hs = 1.3 * head_scale
    k["neck"] = Vector((0, -0.13, 1.45))
    hc = Vector((0, -0.15, 1.45 + 0.19 * hs))
    hr = (0.172 * hs, 0.165 * hs, 0.195 * hs)
    k["head_c"], k["head_r"] = hc, hr
    bm = rig.part("Head", k["neck"], "Torso")
    # Crâne + mâchoire d'un seul tenant (profil tourné, mâchoire poussée vers l'avant) : pas de couture
    prof = [(0, -0.2), (0.09, -0.196), (0.145, -0.17), (0.165, -0.11), (0.165, -0.03),
            (0.17, 0.05), (0.162, 0.12), (0.132, 0.172), (0.075, 0.2), (0, 0.208)]
    start = len(bm.verts)
    lathe(bm, [(r * hs, z * hs) for r, z in prof], 16, Matrix.Translation(hc), SK)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        p = v.co - hc
        p.y *= 0.96
        front = max(0.0, -p.y / (0.165 * hs))
        low = max(0.0, min(1.0, (-p.z / hs + 0.02) / 0.17))
        p.y -= 0.04 * hs * jaw * front * low
        v.co = hc + p
    # Nez
    ellipsoid(bm, hc + Vector((0, -0.17 * hs, -0.02 * hs)), (0.036 * hs, 0.045 * hs, 0.05 * hs), SK, u=8, v=6)
    for s in (-1, 1):
        ellipsoid(bm, hc + Vector((0.168 * hs * s, 0.01, 0.0)), (0.035 * hs, 0.055 * hs, 0.065 * hs), SK, u=8, v=5)
    # Yeux dépareillés, paupières tombantes
    for s, r, lid in ((1, eye_sizes[0], lids[0]), (-1, eye_sizes[1], lids[1])):
        p, d = surface_point(hc, hr, (0.4 * s, -0.86, 0.2))
        e = p - d * 0.012
        q = Vector((0.1 * s, -1, 0)).normalized().to_track_quat('-Y', 'Z')
        ellipsoid(bm, e, (r * hs, r * 0.85 * hs, r * hs), EYE, q, 10, 6)
        ellipsoid(bm, e + q @ Vector((0, 0, 0)) + Vector((0.1 * s, -1, 0)).normalized() * r * 0.75 * hs,
                  (r * 0.36 * hs, r * 0.2 * hs, r * 0.36 * hs), PUP, q, 8, 5)
        lq = q @ Quaternion((0, 1, 0), math.radians(12 * s)) @ Quaternion((1, 0, 0), math.radians(-10))
        ellipsoid(bm, e + q @ Vector((0, 0.005, r * hs * (1.15 - lid))), (r * 1.2 * hs, r * 0.95 * hs, r * 0.55 * hs), SKD, lq, 8, 5)
        k["eye" + ("L" if s > 0 else "R")] = p
    # Bouche et dents
    p, d = surface_point(hc + Vector((0, 0.0, -0.1 * hs)), (0.15 * hs, (0.155 + 0.03 * jaw) * hs, 0.1 * hs), (0.12, -1, 0.05))
    open_mouth(bm, p - d * 0.012, 0.09 * hs, 0.035 * hs, MO, None, forward=d, depth=0.035, frown=True)
    for x, h in ((-0.035, 0.022), (0.03, 0.018)):
        ellipsoid(bm, p - d * 0.006 + Vector((x * hs, 0, -0.002 * hs)), (0.017 * hs, 0.012, h * hs), TE, u=6, v=4)
    k["mouth"] = p

    poses = {
        "gun":    {1: ((0.36, -0.15, 1.04), (0.12, -0.52, 1.06)), -1: ((-0.35, -0.12, 1.03), (-0.12, -0.38, 1.0))},
        "zombie": {1: ((0.32, -0.33, 1.25), (0.27, -0.67, 1.22)), -1: ((-0.32, -0.33, 1.25), (-0.27, -0.67, 1.22))},
        "down":   {1: ((0.37, -0.06, 1.03), (0.38, -0.1, 0.8)), -1: ((-0.37, -0.06, 1.03), (-0.38, -0.1, 0.8))},
    }
    for s, side in ((1, "L"), (-1, "R")):
        shoulder = Vector((0.28 * w * s, -0.08, 1.29))
        elbow, hand = (Vector(v) for v in poses[pose][s])
        elbow.x *= w; hand.x *= w
        bm = rig.part("Arm" + side, shoulder, "Torso")
        ellipsoid(bm, shoulder, (0.105 * w, 0.105 * w, 0.1 * w), SL, u=10, v=6)
        tube_path(bm, [shoulder, (shoulder + elbow) / 2, elbow + (elbow - shoulder).normalized() * 0.03],
                  [0.09 * w, 0.085 * w, 0.08 * w], 8, SL)
        tube_path(bm, [elbow, (elbow + hand) / 2, hand], [0.072 * w, 0.068 * w, 0.06 * w], 8, FA)
        dh = (hand - elbow).normalized()
        q = dh.to_track_quat('Y', 'Z')
        ellipsoid(bm, hand + dh * 0.04, (0.075 * w, 0.09 * w, 0.065 * w), HA, q, 10, 6)       # main en moufle
        ellipsoid(bm, hand + dh * 0.02 + Vector((-0.06 * s * w, 0, 0.03)), (0.03 * w, 0.045 * w, 0.03 * w), HA, q, 6, 4)  # pouce
        k["shoulder" + side], k["elbow" + side], k["hand" + side] = shoulder, elbow, hand
    return k


class Group:
    """Applique une transformation à toute la géométrie ajoutée dans le bloc `with`
    (ex. ouvrir une mâchoire autour de sa charnière)."""

    def __init__(self, bm, matrix):
        self.bm, self.matrix = bm, matrix

    def __enter__(self):
        self.bm.verts.ensure_lookup_table()
        self.start = len(self.bm.verts)
        return self

    def __exit__(self, *exc):
        self.bm.verts.ensure_lookup_table()
        verts = self.bm.verts[self.start:]
        bmesh.ops.transform(self.bm, matrix=self.matrix, verts=verts)
        return False


def rot_about(point, axis, degrees):
    p = Vector(point)
    return Matrix.Translation(p) @ Matrix.Rotation(math.radians(degrees), 4, axis) @ Matrix.Translation(-p)


# ---------------------------------------------------------------- Rig

class Rig:
    """Modèle composé de pièces rigides : chaque pièce a son bmesh (coordonnées
    monde), son pivot (articulation) et son parent. build() crée les objets avec
    origine au pivot, rotation 0 et échelle 1, sous un objet vide racine."""

    def __init__(self, name, collection):
        self.name = name
        self.col = collection
        self.mat_names = []
        self.parts = {}       # nom → [bmesh, pivot, parent]
        self.empties = {}     # nom → [position, parent]

    def m(self, name):
        if name not in self.mat_names:
            self.mat_names.append(name)
        return self.mat_names.index(name)

    def part(self, name, pivot, parent=None):
        self.parts[name] = [bmesh.new(), Vector(pivot), parent]
        return self.parts[name][0]

    def bm(self, name):
        return self.parts[name][0]

    def empty(self, name, position, parent):
        self.empties[name] = [Vector(position), parent]

    def build(self, smooth_angle=50.0, subdiv=None):
        """`subdiv` : {nom de pièce: niveau} — lissage Catmull-Clark appliqué (formes organiques)."""
        root = self._build(smooth_angle)
        for name, level in (subdiv or {}).items():
            ob = bpy.data.objects[name]
            # Surface organique : entièrement lissée, sans arêtes vives.
            if "sharp_edge" in ob.data.attributes:
                ob.data.attributes.remove(ob.data.attributes["sharp_edge"])
            mod = ob.modifiers.new("Subdivision", 'SUBSURF')
            mod.levels = level
            mod.render_levels = level
            deps = bpy.context.evaluated_depsgraph_get()
            new_me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps))
            old = ob.data
            ob.modifiers.remove(mod)
            ob.data = new_me
            bpy.data.meshes.remove(old)
            new_me.name = name
            for p in new_me.polygons:
                p.use_smooth = True
        return root

    def _build(self, smooth_angle=50.0):
        root = bpy.data.objects.new(self.name, None)
        root.empty_display_type = 'ARROWS'
        root.empty_display_size = 0.5
        self.col.objects.link(root)
        objs = {None: root}
        pivots = {None: Vector()}
        thr = math.radians(smooth_angle)
        for name, (bm, pivot, parent) in self.parts.items():
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bmesh.ops.translate(bm, verts=bm.verts, vec=-pivot)
            used = sorted({f.material_index for f in bm.faces})
            remap = {old: i for i, old in enumerate(used)}
            for f in bm.faces:
                f.material_index = remap[f.material_index]
                f.smooth = True
            for e in bm.edges:
                e.smooth = e.is_manifold and e.calc_face_angle(0) <= thr
            me = bpy.data.meshes.new(name)
            bm.to_mesh(me)
            bm.free()
            for old in used:
                me.materials.append(mat(self.mat_names[old]))
            ob = bpy.data.objects.new(name, me)
            self.col.objects.link(ob)
            ob.parent = objs[parent]
            ob.location = pivot - pivots[parent]
            objs[name] = ob
            pivots[name] = pivot
        for name, (pos, parent) in self.empties.items():
            e = bpy.data.objects.new(name, None)
            e.empty_display_type = 'PLAIN_AXES'
            e.empty_display_size = 0.1
            self.col.objects.link(e)
            e.parent = objs[parent]
            e.location = pos - pivots[parent]
        return root


# ---------------------------------------------------------------- Gabarit de zombie

def zombie_base(rig, shirt, pants, shoes, skin="Zombie_Skin", sleeve=None, forearm=None,
                bulk=1.0, pose="gun", eye_sizes=(0.062, 0.05), head_scale=1.0):
    """Corps de zombie commun (≈ 1,95 m, grosse tête façon Garden Warfare) en pièces
    rigides : Hips → LegL/LegR, Torso → Head, ArmL/ArmR. Gauche = +X, avant = -Y.
    pose : 'gun' (arme tenue devant), 'zombie' (bras tendus), 'down' (bras le long du corps).
    Renvoie les positions utiles pour habiller le modèle."""
    S, P, SH, SK = rig.m(shirt), rig.m(pants), rig.m(shoes), rig.m(skin)
    SL = rig.m(sleeve or shirt)
    FA = rig.m(forearm or skin)
    EYE, DKE, MO = rig.m("Zombie_Eye"), rig.m("Plant_Dark"), rig.m("Zombie_Mouth")
    w = bulk
    k = {}
    k["hip"] = Vector((0, 0, 0.8))

    bm = rig.part("Hips", k["hip"])
    ellipsoid(bm, (0, 0.0, 0.83), (0.23 * w, 0.17 * w, 0.15), P, u=12, v=8)
    for s, side in ((1, "L"), (-1, "R")):
        hip = Vector((0.13 * w * s, 0, 0.78))
        knee = Vector((0.14 * w * s, -0.04, 0.42))
        ankle = Vector((0.14 * w * s, 0.0, 0.12))
        bm = rig.part("Leg" + side, hip, "Hips")
        cyl(bm, hip + Vector((0, 0, 0.05)), knee, 0.105 * w, 0.088 * w, P, seg=8)
        ellipsoid(bm, knee, (0.09 * w, 0.09 * w, 0.09 * w), P, u=8, v=6)
        cyl(bm, knee, ankle, 0.088 * w, 0.075 * w, P, seg=8)
        box(bm, ankle + Vector((0, -0.06, -0.06)), (0.17 * w, 0.32, 0.12), SH, bevel=0.035)
        k["ankle" + side] = ankle

    k["torso"] = Vector((0, 0, 0.88))
    k["chest_c"], k["chest_r"] = Vector((0, -0.03, 1.13)), (0.29 * w, 0.2 * w, 0.31)
    bm = rig.part("Torso", k["torso"], "Hips")
    ellipsoid(bm, k["chest_c"], k["chest_r"], S, u=14, v=10)
    cyl(bm, (0, -0.05, 1.36), (0, -0.08, 1.5), 0.085, 0.08, SK, seg=8)

    hs = 1.3 * head_scale
    k["neck"] = Vector((0, -0.08, 1.45))
    k["head_c"], k["head_r"] = Vector((0, -0.1, 1.45 + 0.19 * hs)), (0.175 * hs, 0.17 * hs, 0.2 * hs)
    hc, hr = k["head_c"], k["head_r"]
    bm = rig.part("Head", k["neck"], "Torso")
    ellipsoid(bm, hc, hr, SK, u=16, v=10)
    ellipsoid(bm, hc + Vector((0, -0.165 * hs, -0.03 * hs)), (0.035 * hs, 0.04 * hs, 0.045 * hs), SK, u=8, v=6)  # nez
    for s in (-1, 1):
        ellipsoid(bm, hc + Vector((0.17 * hs * s, 0.0, 0.0)), (0.03 * hs, 0.05 * hs, 0.06 * hs), SK, u=8, v=5)  # oreilles
    for s, r in ((1, eye_sizes[0]), (-1, eye_sizes[1])):
        p, d = surface_point(hc, hr, (0.42 * s, -0.85, 0.14))
        zombie_eye(bm, p - d * 0.015, r * hs, EYE, DKE, look=(0.12 * s, -1, 0))
        k["eye" + ("L" if s > 0 else "R")] = p
    p, d = surface_point(hc, hr, (0.08, -1, -0.55))
    ellipsoid(bm, p, (0.075 * hs, 0.03, 0.03 * hs), MO, d.to_track_quat('-Y', 'Z'), 12, 6)
    for x in (-0.03, 0.025):
        ellipsoid(bm, p + Vector((x * hs, -0.012, 0.02 * hs)), (0.015 * hs, 0.01, 0.017 * hs), EYE, u=6, v=4)
    k["mouth"] = p

    poses = {
        "gun":    {1: ((0.35, -0.13, 1.05), (0.12, -0.5, 1.06)), -1: ((-0.34, -0.1, 1.04), (-0.12, -0.36, 1.0))},
        "zombie": {1: ((0.31, -0.3, 1.27), (0.26, -0.64, 1.24)), -1: ((-0.31, -0.3, 1.27), (-0.26, -0.64, 1.24))},
        "down":   {1: ((0.36, -0.03, 1.03), (0.37, -0.07, 0.8)), -1: ((-0.36, -0.03, 1.03), (-0.37, -0.07, 0.8))},
    }
    for s, side in ((1, "L"), (-1, "R")):
        shoulder = Vector((0.28 * w * s, -0.03, 1.3))
        elbow, hand = (Vector(v) for v in poses[pose][s])
        elbow.x *= w; hand.x *= w
        bm = rig.part("Arm" + side, shoulder, "Torso")
        ellipsoid(bm, shoulder, (0.1 * w, 0.1 * w, 0.1 * w), SL, u=8, v=6)
        cyl(bm, shoulder, elbow, 0.085 * w, 0.075 * w, SL, seg=8)
        ellipsoid(bm, elbow, (0.074 * w, 0.074 * w, 0.074 * w), FA, u=8, v=6)
        cyl(bm, elbow, hand, 0.07 * w, 0.062 * w, FA, seg=8)
        ellipsoid(bm, hand, (0.08 * w, 0.085 * w, 0.08 * w), SK, u=8, v=6)
        k["shoulder" + side], k["elbow" + side], k["hand" + side] = shoulder, elbow, hand
    return k


# ---------------------------------------------------------------- Scène, contrôle, export

def reset_scene(collection_name):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for d in list(coll):
            if d.users == 0:
                coll.remove(d)
    col = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(col)
    return col


def report(collection_name):
    """Triangles, arêtes non manifold, encombrement et transformations de la collection."""
    col = bpy.data.collections[collection_name]
    bpy.context.view_layer.update()
    tris, nonman = 0, {}
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    bad_transforms = []
    for o in col.objects:
        if any(abs(a) > 1e-6 for a in o.rotation_euler) or any(abs(s - 1) > 1e-6 for s in o.scale):
            bad_transforms.append(o.name)
        if o.type != 'MESH':
            continue
        bm = bmesh.new(); bm.from_mesh(o.data)
        tris += sum(len(f.verts) - 2 for f in bm.faces)
        n = sum(1 for e in bm.edges if not e.is_manifold)
        if n:
            nonman[o.name] = n
        bm.free()
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    mats = sorted({s.material.name for o in col.objects if o.type == 'MESH'
                   for s in o.material_slots if s.material})
    return {"triangles": tris, "non_manifold": nonman, "bad_transforms": bad_transforms,
            "min": [round(x, 3) for x in lo], "max": [round(x, 3) for x in hi],
            "size": [round(x, 3) for x in hi - lo], "materials": mats,
            "objects": [o.name for o in col.objects]}


def save_and_export(collection_name, blend_path, glb_path):
    os.makedirs(os.path.dirname(blend_path), exist_ok=True)
    os.makedirs(os.path.dirname(glb_path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    col = bpy.data.collections[collection_name]
    for o in bpy.data.objects:
        o.select_set(o.name in col.objects)
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB', use_selection=True,
                              export_yup=True, export_apply=True, export_materials='EXPORT',
                              export_cameras=False, export_lights=False, export_animations=False)
    return {"blend": os.path.getsize(blend_path), "glb": os.path.getsize(glb_path)}


def preview_render(path, target=(0, 0, 0.7), distance=3.0, yaw_deg=-35.0, pitch_deg=20.0,
                   lens=50.0, size=(900, 900), ground=True, instances=()):
    """Rendu EEVEE de contrôle (studio temporaire : soleil, ciel, sol). Les objets
    temporaires sont supprimés ensuite : rien n'est ajouté au modèle.
    `instances` : [(nom de collection, position, yaw en degrés)] — copies du modèle
    (ex. une escouade complète pour juger la lisibilité en vue RTS)."""
    scene = bpy.context.scene
    temp = bpy.data.collections.new("_Preview")
    scene.collection.children.link(temp)
    for coll_name, pos, yaw_i in instances:
        inst = bpy.data.objects.new("_PreviewInstance", None)
        inst.instance_type = 'COLLECTION'
        inst.instance_collection = bpy.data.collections[coll_name]
        inst.location = pos
        inst.rotation_euler = (0, 0, math.radians(yaw_i))
        temp.objects.link(inst)
    cam_data = bpy.data.cameras.new("_PreviewCam"); cam_data.lens = lens
    cam = bpy.data.objects.new("_PreviewCam", cam_data); temp.objects.link(cam)
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    t = Vector(target)
    cam.location = t + Vector((math.sin(yaw) * math.cos(pitch), -math.cos(yaw) * math.cos(pitch), math.sin(pitch))) * distance
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sun_data = bpy.data.lights.new("_PreviewSun", 'SUN'); sun_data.energy = 3.5; sun_data.angle = math.radians(8)
    sun = bpy.data.objects.new("_PreviewSun", sun_data); temp.objects.link(sun)
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-30))
    if ground:
        gm = bpy.data.meshes.new("_PreviewGround")
        gbm = bmesh.new(); bmesh.ops.create_grid(gbm, x_segments=1, y_segments=1, size=30); gbm.to_mesh(gm); gbm.free()
        g = bpy.data.objects.new("_PreviewGround", gm); temp.objects.link(g)
        gmat = bpy.data.materials.new("_PreviewGroundMat")
        next(n for n in gmat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs["Base Color"].default_value = (*srgb("#6B8A4A"), 1)
        gm.materials.append(gmat)
    world_old = scene.world
    world = bpy.data.worlds.new("_PreviewWorld")
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs["Color"].default_value = (*srgb("#BFD6EA"), 1); bg.inputs["Strength"].default_value = 0.9
    scene.world = world
    old_cam = scene.camera
    scene.camera = cam
    r = scene.render
    old = (r.engine, r.resolution_x, r.resolution_y, r.filepath, scene.view_settings.view_transform)
    r.engine = 'BLENDER_EEVEE'
    r.resolution_x, r.resolution_y = size
    r.filepath = path
    scene.view_settings.view_transform = 'Standard'
    bpy.ops.render.render(write_still=True)
    r.engine, r.resolution_x, r.resolution_y, r.filepath, scene.view_settings.view_transform = old
    scene.camera = old_cam
    scene.world = world_old
    for o in list(temp.objects):
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if isinstance(data, bpy.types.Mesh): bpy.data.meshes.remove(data)
        elif isinstance(data, bpy.types.Camera): bpy.data.cameras.remove(data)
        elif isinstance(data, bpy.types.Light): bpy.data.lights.remove(data)
    bpy.data.collections.remove(temp)
    bpy.data.worlds.remove(world)
    for m in list(bpy.data.materials):
        if m.name.startswith("_Preview"):
            bpy.data.materials.remove(m)
    return path


def model_check(collection_name, out_dir, tag, target_z=0.7, distance=3.0, squad=False, yaw_deg=-30.0):
    """Contrôle d'un modèle : rapport + rendu 3/4 avant (+ escouade en vue moyenne si demandé)."""
    os.makedirs(out_dir, exist_ok=True)
    res = report(collection_name)
    res["per_object"] = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons)
                         for o in bpy.data.collections[collection_name].objects if o.type == 'MESH'}
    res["vertices"] = sum(len(o.data.vertices) for o in bpy.data.collections[collection_name].objects if o.type == 'MESH')
    preview_render(os.path.join(out_dir, tag + "_close.png"), target=(0, 0, target_z), distance=distance,
                   yaw_deg=yaw_deg, pitch_deg=14, size=(640, 640))
    if squad:
        inst = [(collection_name, (x * 1.8, y * 1.8 + 1.8, 0), 0) for x in (-1, 0, 1) for y in (0, 1)]
        preview_render(os.path.join(out_dir, tag + "_mid.png"), target=(0, 1.5, target_z * 0.8), distance=distance * 3.2,
                       yaw_deg=-25, pitch_deg=35, lens=35, size=(960, 540), instances=inst)
    for o in bpy.data.objects:
        o.select_set(False)
    return res


def view(target_z=0.7, distance=3.2, yaw_deg=-35.0, pitch_deg=68.0, shading='SOLID'):
    """Cadre la vue 3D (3/4 avant par défaut) pour les captures de contrôle."""
    from mathutils import Euler
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            sp = area.spaces.active
            sp.shading.type = shading
            if shading == 'SOLID':
                sp.shading.color_type = 'MATERIAL'
            sp.overlay.show_face_orientation = False
            r3d = sp.region_3d
            r3d.view_perspective = 'PERSP'
            r3d.view_rotation = Euler((math.radians(pitch_deg), 0, math.radians(yaw_deg)), 'XYZ').to_quaternion()
            r3d.view_location = (0, 0, target_z)
            r3d.view_distance = distance
