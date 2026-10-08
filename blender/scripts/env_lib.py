# plantRTS — bibliothèque des décors (kit d'environnement), s'appuie sur prts_lib.
#
# Ajoute à prts_lib ce qui manque pour des décors statiques :
# - matériaux communs Env_* texturés (pack peint à la main de blender/Texture imp/,
#   complété par textures_gen.py ; copies dans blender/environment/textures/),
#   légèrement désaturés pour rester en retrait des unités ; verts du décor plus
#   bleus et plus sombres que ceux des plantes jouables. Quelques matériaux restent
#   unis (couleurs d'équipe des points de jeu) ;
# - UV automatiques : projection en mètres selon l'axe dominant de chaque face
#   (densité de texture identique sur tout le kit) ; régions d'atlas (« Env_Trim:glass »)
#   ajustées à la face ;
# - primitives de décor : prisme (pignons, dalles), boîte biseautée orientée, « blob »
#   organique bruité (feuillages, rochers), bruit déterministe ;
# - nettoyage : suppression des faces de dessous (invisibles depuis la caméra RTS) ;
# - contrôles du kit : grille de 2 m, budget de triangles, 4 matériaux au plus,
#   pivot au sol, transformations appliquées ;
# - rendus de contrôle : de près, et caméra de jeu RTS avec une escouade pour l'échelle.
#
# Conventions : 1 unité = 1 m, Z en haut, avant -Y (→ +Z dans Godot), pivot au sol au
# centre de l'emprise ; segments modulaires alignés sur X.
#
# Exécution : chaque famille a son script dans blender/scripts/environment/, lancé par
#   blender -b --python blender/scripts/environment/<famille>.py -- [ids…] [--render]

import bpy, bmesh, math, os, random, sys
from mathutils import Vector, Matrix, Quaternion

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prts_lib as P
from prts_lib import srgb, box, cyl, ellipsoid, dome, lathe, tube_path, organic_leaf, align_z, Rig  # noqa: F401

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CAPTURE_DIR = os.path.join(ROOT, "tests", "environment_test", "captures")

# ---------------------------------------------------------------- Palette du décor
# nom → (couleur, rugosité, métal, émission). Noms communs à tout le kit.
ENV_PALETTE = {
    # Bâtiments
    "Env_Wall":       (srgb("#E2CDA4"), 0.9, 0.0, None),   # crépi crème
    "Env_WallBlue":   (srgb("#6FA3A0"), 0.9, 0.0, None),   # bardage peint
    "Env_Roof":       (srgb("#985450"), 0.85, 0.0, None),  # tuiles
    "Env_RoofDark":   (srgb("#5E3A48"), 0.85, 0.0, None),
    "Env_Trim":       (srgb("#EEE8DA"), 0.8, 0.0, None),   # boiseries blanches
    "Env_Glass":      (srgb("#3C5468"), 0.35, 0.0, None),
    "Env_Brick":      (srgb("#9C5A40"), 0.9, 0.0, None),
    # Bois, pierre, métal
    "Env_Wood":       (srgb("#8A6244"), 0.85, 0.0, None),
    "Env_WoodLight":  (srgb("#C4A27C"), 0.85, 0.0, None),
    "Env_Stone":      (srgb("#8E8A98"), 0.9, 0.0, None),
    "Env_StoneDark":  (srgb("#5F5B6E"), 0.9, 0.0, None),
    "Env_Moss":       (srgb("#5E7848"), 0.95, 0.0, None),
    "Env_Concrete":   (srgb("#B3AEA4"), 0.9, 0.0, None),
    "Env_Metal":      (srgb("#8F959C"), 0.5, 0.4, None),
    "Env_MetalDark":  (srgb("#3F434A"), 0.6, 0.3, None),
    # Végétation (plus bleue et plus sombre que les plantes jouables)
    "Env_Foliage":    (srgb("#4C8458"), 0.95, 0.0, None),
    "Env_FoliageDark": (srgb("#2E5C45"), 0.95, 0.0, None),
    "Env_Bark":       (srgb("#6A4B3C"), 0.95, 0.0, None),
    "Env_Grass":      (srgb("#5D8C52"), 0.95, 0.0, None),
    "Env_Dirt":       (srgb("#7D5B46"), 0.95, 0.0, None),
    # Véhicules
    "Env_CarPaint":   (srgb("#5C86AE"), 0.5, 0.1, None),
    "Env_Rubber":     (srgb("#2C2C31"), 0.9, 0.0, None),
    # Points de jeu (couleurs des ressources : data/factions)
    "Env_Neutral":    (srgb("#D8D2C2"), 0.8, 0.0, None),
    "Env_Sun":        (srgb("#FFD140"), 0.6, 0.0, srgb("#7A5A10")),
    "Env_Brain":      (srgb("#F58CB3"), 0.6, 0.0, srgb("#B0405E")),
    "Env_Fertilizer": (srgb("#7ACC4D"), 0.6, 0.0, srgb("#3E7A20")),
    "Env_Gears":      (srgb("#ADBACC"), 0.45, 0.4, None),
    "Env_Soil":       (srgb("#B8804D"), 0.8, 0.0, None),
    "Env_Pesticide":  (srgb("#BDDB33"), 0.5, 0.0, srgb("#6E8A10")),
    "Env_PlantTeam":  (srgb("#4DE64D"), 0.6, 0.0, None),
    "Env_ZombieTeam": (srgb("#AD52F2"), 0.6, 0.0, None),
}
# Matériaux texturés : nom → (fichier dans blender/environment/textures/, taille d'une
# répétition en m, régions d'atlas {nom: (u0, u1, ajusté_en_v)}).
TEXTURE_DIR = os.path.join(ROOT, "blender", "environment", "textures")
TEXTURE_SIZE = 512          # px dans les .glb (lisible à la caméra RTS, poids contenu)
DESATURATE = 0.12           # part de désaturation appliquée aux textures du décor
TEXTURES = {
    "Env_Siding":     ("pack_bardage_bois.png", 1.8, None),
    "Env_RoofTiles":  ("pack_toit_tuiles.png", 2.0, None),
    "Env_Brick":      ("pack_mur_briques.png", 1.6, None),
    "Env_Plaster":    ("pack_mur_crepi.png", 3.0, None),
    "Env_WoodPlanks": ("pack_planches_bois.png", 1.6, None),
    "Env_Trim":       ("trim_atlas.png", 1.5, {"white": (0.0, 0.4, False), "red": (0.4, 0.6, False),
                                               "wood": (0.6, 0.8, False), "glass": (0.8, 1.0, True)}),
    "Env_Bark":       ("bark.png", 1.4, None),
    "Env_Foliage":    ("foliage.png", 1.6, None),
    "Env_FoliageDark": ("foliage_shadow.png", 1.6, None),
    "Env_FoliageAutumn": ("foliage_autumn.png", 1.6, None),
    "Env_FoliageAutumnDark": ("foliage_autumn_shadow.png", 1.6, None),
    "Env_BarkDead":   ("bark_dead.png", 1.4, None),
    "Env_CarPaint":   ("car_paint.png", 3.0, None),
    "Env_Metal":      ("metal.png", 1.0, None),
    "Env_Rubber":     ("rubber.png", 0.7, None),
    "Env_TombStone":  ("pack_pierre_tombale.png", 2.6, None),
    "Env_CryptSlab":  ("pack_dalles_crypte.png", 2.0, None),
    "Env_Moss":       ("moss.png", 1.0, None),
    "Env_GraveDirt":  ("pack_terre_cimetiere.png", 2.0, None),
    "Env_Paving":     ("pack_paves.png", 3.0, None),
    "Env_Cloth":      ("cloth.png", 1.5, None),
    # Variantes de couleur (textures_gen.variants)
    "Env_SidingYellow":   ("siding_yellow.png", 1.8, None),
    "Env_SidingPink":     ("siding_pink.png", 1.8, None),
    "Env_SidingWhite":    ("siding_white.png", 1.8, None),
    "Env_SidingMint":     ("siding_mint.png", 1.8, None),
    "Env_SidingLavender": ("siding_lavender.png", 1.8, None),
    "Env_SidingRotten":   ("siding_rotten.png", 1.8, None),
    "Env_RoofSlate":      ("roof_slate.png", 2.0, None),
    "Env_RoofGreen":      ("roof_green.png", 2.0, None),
    "Env_RoofBrown":      ("roof_brown.png", 2.0, None),
    "Env_RoofPurple":     ("roof_purple.png", 2.0, None),
    "Env_RoofRotten":     ("roof_rotten.png", 2.0, None),
    "Env_PlasterPink":    ("plaster_pink.png", 3.0, None),
    "Env_PlasterMint":    ("plaster_mint.png", 3.0, None),
    "Env_PlasterGrey":    ("plaster_grey.png", 3.0, None),
    "Env_PlasterDamaged": ("pack_crepi_abime.png", 3.0, None),
    "Env_BrickGrey":      ("brick_grey.png", 1.6, None),
    "Env_WoodDark":       ("wood_dark.png", 1.6, None),
    "Env_CarPaintRed":    ("car_paint_red.png", 3.0, None),
    "Env_CarPaintYellow": ("car_paint_yellow.png", 3.0, None),
    "Env_CarPaintGreen":  ("car_paint_green.png", 3.0, None),
    "Env_CarPaintWhite":  ("car_paint_white.png", 3.0, None),
    # Sols et matières
    "Env_Asphalt":    ("asphalt.png", 4.0, None),
    "Env_Concrete":   ("concrete.png", 4.0, None),
    "Env_Grass":      ("pack_herbe.png", 3.0, None),
    "Env_DryGrass":   ("pack_herbe_seche.png", 3.0, None),
    "Env_DeadGrass":  ("pack_herbe_morte.png", 3.0, None),
    "Env_Dirt":       ("pack_terre.png", 2.5, None),
    "Env_Path":       ("pack_chemin.png", 2.5, None),
    "Env_Sand":       ("pack_sable.png", 3.0, None),
    "Env_Cursed":     ("pack_sol_corrompu.png", 3.0, None),
    "Env_StoneWall":  ("pack_mur_ruine.png", 2.0, None),
    "Env_Rock":       ("rock_grey.png", 2.5, None),
    "Env_RustyIron":  ("rust_dull.png", 1.5, None),
    "Env_Iron":       ("iron.png", 1.0, None),
    "Env_Hedge":      ("hedge.png", 1.6, None),
    "Env_Straw":      ("straw.png", 1.2, None),
    "Env_Burlap":     ("burlap.png", 1.0, None),
    "Env_Water":      ("water.png", 3.0, None),
    "Env_Pumpkin":    ("pumpkin.png", 1.2, None),
    "Env_Bone":       ("bone.png", 0.8, None),
    "Env_Flowers":    ("flowers.png", 1.6, None),
    "Env_Terracotta": ("terracotta.png", 1.0, None),
    # Atlas de peintures vives (petits accessoires) : une bande par couleur.
    "Env_Paint":      ("paint_atlas.png", 1.0, {c: (i / 8, (i + 1) / 8, False) for i, c in enumerate(
                       ("red", "orange", "yellow", "green", "blue", "pink", "white", "black"))}),
}
for _name in TEXTURES:
    ENV_PALETTE.setdefault(_name, (srgb("#B0B0B0"), 0.9, 0.0, None))
ENV_PALETTE["Env_Metal"] = (srgb("#9AA0A8"), 0.45, 0.5, None)
ENV_PALETTE["Env_CarPaint"] = (srgb("#5C86AE"), 0.45, 0.1, None)
ENV_PALETTE["Env_Trim"] = (srgb("#EEE8DA"), 0.7, 0.0, None)
P.PALETTE.update(ENV_PALETTE)


def load_texture(file_name):
    """Image du kit : chargée une fois, désaturée, réduite à TEXTURE_SIZE et intégrée
    au .blend (et donc au .glb)."""
    key = "env_" + os.path.splitext(file_name)[0]
    im = bpy.data.images.get(key)
    if im is not None:
        return im
    import numpy as np
    im = bpy.data.images.load(os.path.join(TEXTURE_DIR, file_name))
    im.name = key
    if im.size[0] > TEXTURE_SIZE:
        im.scale(TEXTURE_SIZE, TEXTURE_SIZE)
    px = np.array(im.pixels[:], dtype=np.float32).reshape(-1, 4)
    grey = px[:, :3] @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    px[:, :3] = px[:, :3] * (1 - DESATURATE) + grey[:, None] * DESATURATE
    im.pixels = px.ravel()
    im.pack()
    return im


_plain_mat = P.mat


def env_mat(name):
    """Matériau du kit : texturé s'il figure dans TEXTURES, uni sinon (prts_lib.mat)."""
    if name not in TEXTURES:
        return _plain_mat(name)
    m = bpy.data.materials.get(name)
    if m is not None and m.get("env_textured"):
        return m
    m = _plain_mat(name)
    nodes, links = m.node_tree.nodes, m.node_tree.links
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = load_texture(TEXTURES[name][0])
    tex.location = (-400, 200)
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.25
    m["env_textured"] = True
    return m


P.mat = env_mat     # Rig.build crée ses matériaux via prts_lib.mat


def _face_coords(f):
    """Coordonnées (a, b) en m des coins d'une face, projetées selon l'axe dominant de
    sa normale : murs → (horizontal, hauteur) ; dessus/dessous → (x, y)."""
    n = f.normal
    ax = max(range(3), key=lambda i: abs(n[i]))
    out = []
    for loop in f.loops:
        c = loop.vert.co
        if ax == 0:
            out.append((c.y * (1 if n.x > 0 else -1), c.z))
        elif ax == 1:
            out.append((c.x * (-1 if n.y > 0 else 1), c.z))
        elif abs(n.x) > 0.2 and abs(n.x) >= abs(n.y):
            out.append((c.y, c.x * (-1 if n.x > 0 else 1)))   # pente vers ±X
        elif abs(n.y) > 0.2:
            out.append((c.x, c.y * (-1 if n.y > 0 else 1)))   # pente : v monte vers le faîte
        else:
            out.append((c.x, c.y))
    return out


def apply_uvs(rig):
    """UV de toutes les pièces d'un Rig, puis matériaux « Nom:région » ramenés à leur
    nom de base (l'atlas reste un seul matériau)."""
    base_index = {}
    for i, full in enumerate(list(rig.mat_names)):
        base_index[i] = rig.m(full.partition(":")[0])
    for name, (bm, pivot, parent) in rig.parts.items():
        bm.normal_update()
        uv = bm.loops.layers.uv.verify()
        for f in bm.faces:
            full = rig.mat_names[f.material_index]
            base, _, region = full.partition(":")
            spec = TEXTURES.get(base)
            coords = _face_coords(f)
            if spec is None:
                uvs = [(0.0, 0.0)] * len(coords)
            elif region:
                u0, u1, fit_v = spec[2][region]
                pad = (u1 - u0) * 0.03
                a = [c[0] for c in coords]; b = [c[1] for c in coords]
                if max(a) - min(a) > max(b) - min(b) and not fit_v:
                    a, b = b, a                       # la longueur suit le fil du bois (v)
                ar = max(max(a) - min(a), 1e-6)
                br = max(max(b) - min(b), 1e-6)
                uvs = []
                for x, y in zip(a, b):
                    u = u0 + pad + (x - min(a)) / ar * (u1 - u0 - 2 * pad)
                    v = (y - min(b)) / br if fit_v else y / spec[1]
                    uvs.append((u, v))
            else:
                uvs = [(x / spec[1], y / spec[1]) for x, y in coords]
            for loop, (u, v) in zip(f.loops, uvs):
                loop[uv].uv = (u, v)
            f.material_index = base_index[f.material_index]

# Budgets de triangles (indicatifs) par taille de pièce.
BUDGET = {"small": 300, "medium": 1500, "building": 3000}
GRID = 2.0
MAX_MATERIALS = 4


# ---------------------------------------------------------------- Primitives de décor

def prism(bm, pts, depth, mtx, mi):
    """Prisme fermé : polygone convexe `pts` [(x, z)] dans le plan XZ local, extrudé de
    -depth/2 à +depth/2 le long de Y local (pignon, dalle de toit, planche découpée)."""
    n = len(pts)
    front = [bm.verts.new(mtx @ Vector((x, -depth / 2, z))) for x, z in pts]
    back = [bm.verts.new(mtx @ Vector((x, depth / 2, z))) for x, z in pts]
    faces = [bm.faces.new(front), bm.faces.new(list(reversed(back)))]
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((front[j], front[i], back[i], back[j])))
    for f in faces:
        f.material_index = mi
    return faces


def slab(bm, center, size, mi, yaw=0.0, pitch=0.0, roll=0.0, bevel=0.0):
    """Boîte orientée (lacet Z, tangage X, roulis Y en degrés), éventuellement biseautée."""
    q = Quaternion((0, 0, 1), math.radians(yaw)) @ Quaternion((1, 0, 0), math.radians(pitch)) \
        @ Quaternion((0, 1, 0), math.radians(roll))
    box(bm, center, size, mi, rot=q, bevel=bevel)


def blob(bm, center, radii, mi, subdiv=2, noise=0.12, seed=0, flatten_bottom=None):
    """Volume organique : icosphère déformée par un bruit radial déterministe (touffe de
    feuillage, rocher, buisson). `flatten_bottom` : hauteur relative (−1..1) sous
    laquelle la forme est aplatie (pose au sol)."""
    rnd = random.Random(seed)
    m = Matrix.Translation(Vector(center)) @ Matrix.Diagonal((*radii, 1))
    res = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0, matrix=Matrix.Identity(4))
    verts = res['verts']
    # Bruit lisse : somme de quelques bosses aléatoires sur la sphère.
    bumps = [(Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized(),
              rnd.uniform(-1, 1)) for _ in range(9)]
    for v in verts:
        d = v.co.normalized()
        k = 1.0 + noise * sum(a * max(0.0, d.dot(b)) ** 3 for b, a in bumps)
        co = d * k
        if flatten_bottom is not None and co.z < flatten_bottom:
            co.z = flatten_bottom + (co.z - flatten_bottom) * 0.15
        v.co = m @ co
    for f in {f for v in verts for f in v.link_faces}:
        f.material_index = mi
        f.smooth = True
    return verts


def text_mesh(bm, text, mtx, size, depth, mi):
    """Texte en relief (police par défaut de Blender) ajouté au bmesh : lettres dans le
    plan XZ local, épaisseur `depth` vers -Y local, centrées sur l'origine de `mtx`."""
    curve = bpy.data.curves.new("_text", 'FONT')
    curve.body = text
    curve.size = size
    curve.extrude = depth / 2
    curve.align_x = 'CENTER'
    curve.align_y = 'CENTER'
    curve.resolution_u = 2      # courbes des lettres : peu de segments (budget)
    obj = bpy.data.objects.new("_text", curve)
    bpy.context.scene.collection.objects.link(obj)
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(deps))
    before = set(bm.faces)
    # Police dans le plan XY, épaisseur en Z : on la redresse dans le plan XZ.
    me.transform(mtx @ Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Translation((0, 0, depth / 2)))
    bm.from_mesh(me)
    for f in set(bm.faces) - before:
        f.material_index = mi
    bpy.data.objects.remove(obj)
    bpy.data.curves.remove(curve)
    bpy.data.meshes.remove(me)


def build_transformed(bm, mtx, build):
    """Construit une partie dans un bmesh temporaire (`build(tmp)`), la transforme par
    `mtx`, puis la fusionne dans `bm` (matériaux conservés). Plus sûr que de repérer
    les sommets créés quand des opérateurs bmesh réorganisent le maillage."""
    tmp = bmesh.new()
    build(tmp)
    bmesh.ops.transform(tmp, matrix=mtx, verts=tmp.verts)
    me = bpy.data.meshes.new("_part")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def jitter(verts, amount, seed=0):
    """Décalage aléatoire déterministe des sommets (aspect fait main, moins rigide)."""
    rnd = random.Random(seed)
    for v in verts:
        v.co += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * amount


def extrude_xy(bm, pts, z0, z1, mi, mi_side=None):
    """Dalle verticale : polygone `pts` [(x, y)] (l'un ou l'autre sens) du plan XY,
    de z0 à z1 (dessus + flancs ; le dessous est supprimé au nettoyage)."""
    mi_side = mi if mi_side is None else mi_side
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts)))
    if area < 0:
        pts = list(reversed(pts))       # toujours dans le sens trigonométrique (dessus vers +Z)
    lo = [bm.verts.new((x, y, z0)) for x, y in pts]
    hi = [bm.verts.new((x, y, z1)) for x, y in pts]
    top = bm.faces.new(hi)
    top.material_index = mi
    bottom = bm.faces.new(list(reversed(lo)))
    bottom.material_index = mi
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
        f.material_index = mi_side
    return top


def arc_pts(center, radius, a0, a1, n):
    """Points d'un arc (angles en degrés, de a0 à a1)."""
    return [(center[0] + radius * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             center[1] + radius * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def remove_bottom_faces(bm, z_max=0.03):
    """Supprime les faces tournées vers le bas posées au sol : jamais visibles."""
    bm.normal_update()
    dead = [f for f in bm.faces if f.normal.z < -0.95 and all(v.co.z <= z_max for v in f.verts)]
    bmesh.ops.delete(bm, geom=dead, context='FACES_ONLY')


# ---------------------------------------------------------------- Construction et contrôles

def start(model_id):
    """Scène vide et collection du modèle."""
    return P.reset_scene(model_id)


def finish(rig, clean_bottom=True, **build_kw):
    """Pose tout au-dessus du sol, nettoie les dessous de chaque pièce, puis construit
    le modèle (prts_lib.Rig)."""
    for name, (bm_, pivot, parent) in rig.parts.items():
        for v in bm_.verts:
            v.co.z = max(v.co.z, 0.0)
        if clean_bottom:
            remove_bottom_faces(bm_)
    apply_uvs(rig)
    return rig.build(**build_kw)


def check(model_id, budget, footprint, require_grid=True):
    """Contrôles du kit sur la collection `model_id`. `footprint` = (x, y) en m,
    multiples de 2 m, centré sur le pivot. Renvoie le rapport (prts_lib.report) enrichi
    et la liste des problèmes."""
    rep = P.report(model_id)
    problems = []
    if rep["triangles"] > BUDGET[budget]:
        problems.append("triangles %d > %d (%s)" % (rep["triangles"], BUDGET[budget], budget))
    if len(rep["materials"]) > MAX_MATERIALS:
        problems.append("%d matériaux > %d : %s" % (len(rep["materials"]), MAX_MATERIALS, rep["materials"]))
    if rep["bad_transforms"]:
        problems.append("transformations non appliquées : %s" % rep["bad_transforms"])
    if rep["min"][2] < -0.01:
        problems.append("sous le sol : z min %.3f" % rep["min"][2])
    fx, fy = footprint
    if require_grid and (abs(fx / GRID - round(fx / GRID)) > 1e-6 or abs(fy / GRID - round(fy / GRID)) > 1e-6):
        problems.append("emprise %s hors grille de 2 m" % (footprint,))
    for axis, (lo, hi, half) in enumerate(((rep["min"][0], rep["max"][0], fx / 2), (rep["min"][1], rep["max"][1], fy / 2))):
        if lo < -half - 0.01 or hi > half + 0.01:
            problems.append("dépasse l'emprise sur %s : [%.2f, %.2f] pour ±%.2f" % ("XY"[axis], lo, hi, half))
    rep["footprint"] = list(footprint)
    rep["height"] = rep["max"][2]
    rep["problems"] = problems
    return rep


def export(model_id, category):
    """Enregistre blender/environment/<catégorie>/<id>.blend et
    assets/environment/<catégorie>/<id>.glb."""
    blend = os.path.join(ROOT, "blender", "environment", category, model_id + ".blend")
    glb = os.path.join(ROOT, "assets", "environment", category, model_id + ".glb")
    sizes = P.save_and_export(model_id, blend, glb)
    return {"blend": blend, "glb": glb, **sizes}


# ---------------------------------------------------------------- Rendus de contrôle

def scale_collection(name, glb_path):
    """Collection hors scène contenant une unité importée (référence d'échelle)."""
    col = bpy.data.collections.get(name)
    if col is not None:
        return name
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=glb_path)
    col = bpy.data.collections.new(name)
    for o in set(bpy.data.objects) - before:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    return name


# Caméra de jeu (camera/rts_camera.gd) : champ vertical 50°, inclinaison 40° (près) à
# 65° (loin) selon la distance (10 à 80 m).
RTS_LENS = 18.0 / math.tan(math.radians(25.0)) * (540 / 960)


def rts_pitch(distance):
    t = (distance - 10.0) / 70.0
    return 40.0 + 25.0 * max(0.0, min(1.0, t))


def render_reference(model_id, target_z, close_distance, squad_offset=(0.0, -4.0), yaw=-30.0,
                     rts_distance=25.0, zombies=False, close_pitch=18.0):
    """Rendu de près + rendu en caméra de jeu (distance `rts_distance`) avec une escouade
    de Pisto-pois (et deux Zombies classiques si `zombies`) à côté pour l'échelle."""
    os.makedirs(CAPTURE_DIR, exist_ok=True)
    pea = scale_collection("_ScalePeashooter", os.path.join(ROOT, "assets", "plants", "peashooter.glb"))
    zom = scale_collection("_ScaleBrowncoat", os.path.join(ROOT, "assets", "zombies", "browncoat.glb"))
    close = os.path.join(CAPTURE_DIR, model_id + "_close.png")
    P.preview_render(close, target=(0, 0, target_z), distance=close_distance, yaw_deg=yaw,
                     pitch_deg=close_pitch, lens=50.0, size=(900, 700))
    sx, sy = squad_offset
    inst = [(pea, (sx + (i % 3 - 1) * 1.8, sy + (i // 3) * -1.8, 0), 180.0 + 8 * (i - 2)) for i in range(6)]
    if zombies:
        inst += [(zom, (sx + 4.5 + i * 1.6, sy - 1.0, 0), 160.0 + 20 * i) for i in range(2)]
    rts = os.path.join(CAPTURE_DIR, model_id + "_rts.png")
    P.preview_render(rts, target=(sx * 0.5, sy * 0.5, 0.5), distance=rts_distance, yaw_deg=yaw,
                     pitch_deg=rts_pitch(rts_distance), lens=RTS_LENS, size=(960, 540), instances=inst)
    return close, rts


def run(builders, argv=None):
    """Point d'entrée d'un script de famille : construit, contrôle, exporte et (option
    --render) rend les modèles demandés. `builders` : {id: fonction() → dict de
    paramètres (category, budget, footprint, render…)}."""
    argv = argv if argv is not None else (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    ids = [a for a in argv if not a.startswith("--")] or list(builders)
    results = {}
    for model_id in ids:
        info = builders[model_id]()
        rep = check(model_id, info["budget"], info["footprint"], info.get("grid", True))
        rep.update(export(model_id, info["category"]))
        if "--render" in argv:
            render_reference(model_id, **info.get("render", {}))
        print("REPORT", model_id, {k: rep[k] for k in ("triangles", "materials", "footprint", "height",
                                                       "size", "non_manifold", "problems")})
        results[model_id] = rep
    return results
