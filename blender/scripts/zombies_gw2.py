# plantRTS — Zombies reconstruits à partir des modèles de Garden Warfare 2 fournis
# dans blender/zombies imp/ (fichiers .blend riggés : squelette « Reference »,
# maillages en pose de référence, textures intégrées ou dans Textures/).
# Usage personnel et éducatif uniquement (voir CLAUDE.md) : ne pas diffuser. Les
# fichiers produits vont dans des dossiers ignorés par Git (blender/gw2/, assets/gw2/) ;
# le jeu les utilise en local via UnitData.local_visual_path.
#
# Exécution (Blender 5.x, en arrière-plan) :
#   blender -b --python blender/scripts/zombies_gw2.py -- [ids…] [--no-export] [--preview=<dossier>]
# Sans id : tous les zombies.
#
# Par zombie : ouverture du .blend → pose du squelette (bras abaissés vers le corps,
# avant-bras vers l'avant, arme placée dans la main : Wep_Root sur RightHand_Prop) →
# pose figée dans les maillages (squelette supprimé) → échelle commune (Soldat à
# 2,0 m ; Z-Mech à la hauteur de l'ancien modèle), pivot au sol sous les hanches →
# matériaux refaits (texture de couleur seule, 512 px ; peau et yeux communs pris
# dans les dossiers Textures/) → réduction des polygones → pièces rigides Body, Head
# (pivot au cou) et Weapon → .blend + .glb.
# Coordonnées de la source : Z en haut, avant vers -Y ; bras droit du côté -X.

import bpy, math, os, re, sys
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gw2_lib as L

SRC = os.path.join(L.ROOT, "blender", "zombies imp", "Playable-20261009T091309Z-1-001", "Playable")
# Échelle commune : le casque du Soldat (2,27 m dans la source) à 2,0 m, comme les
# zombies procéduraux. Les proportions entre zombies restent celles du jeu.
COMMON_SCALE = 2.0 / 2.27
# Textures absentes des .blend : cherchées par nom dans tous les dossiers Textures/,
# avec des remplacements (la peau commune des zombies est celle de l'Ingénieur).
TEXTURE_ALIASES = {"ZombieSkin_Color.png": "Skin_Color.png"}

# Chaque zombie :
#   blend    : source
#   arms     : (abaissement du bras °, flexion de l'avant-bras vers l'avant °)
#   weapons  : {os de l'arme: os de la main}
#   drop     : motifs des maillages supprimés (doublons de LOD, vitres, voyants)
#   target   : triangles visés au total (réduction proportionnelle)
#   height   : hauteur imposée (m) au lieu de l'échelle commune
ZOMBIES = {
    "foot_soldier": {"blend": "Soldier/Soldier.blend", "arms": (30, 40),
                     "weapons": {"Wep_Root": "RightHand_Prop"}, "drop": [r"lod\.001$"], "target": 6000},
    "all_star": {"blend": "Allstar/Allstar.blend", "arms": (25, 45),
                 "weapons": {"Gun_All": "RightHand_Prop"}, "drop": [r"DefaultLight_M"], "target": 7000},
    "engineer": {"blend": "Engineer/Engineer.blend", "arms": (25, 40),
                 "weapons": {"Wep_Root": "RightHand_Prop"}, "drop": [r"EngineerLights_M"], "target": 6000},
    "scientist": {"blend": "Scientist/Scientist.blend", "arms": (30, 40),
                  "weapons": {"Wep_Root": "RightHand_Prop"}, "drop": [r"ScientistGlass_M"], "target": 6000},
    "deadbeard": {"blend": "Pirate/Pirate.blend", "arms": (25, 35),
                  "weapons": {"Wep_Root": "RightHand_Prop"}, "drop": [r"^Lens"], "target": 6500},
    "super_brainz": {"blend": "Super Brainz/SuperBrainz.blend", "arms": (25, 30), "weapons": {},
                     "drop": [r"^Brain_pulse"], "target": 6000},
    "imp": {"blend": "Imp/Imp.blend", "arms": (70, 45),
            "weapons": {"Wep_Root": "RightHand_Prop", "Wep_Root_02": "LeftHand_Prop"},
            "drop": [r"^blinking_lights", r"Weapon_Default_Light_M"], "target": 4500},
    "z_mech": {"blend": "Z-Mech/Z-Mech.blend", "arms": (12, 25), "weapons": {"Wep_Root": "RightHand"},
               "drop": [r"^Speech_M", r"Glass_M", r"Blinking_Lights", r"Circleblinking", r"ConsoleLights",
                        r"Siren_lights"], "target": 9000, "height": 3.57},
}

WEAPON_PATTERN = r"(?i)weapon|^gun|wep_|canister|renegade"
HEAD_PATTERN = r"(?i)^head|eye|faceprop|mouthprop|hair|headprop|^pirate(head|eye)|^captainbrainz_faceprop|^body_armleghead.*:.*head"


# ---------------------------------------------------------------- Pose

AXES = {'X': Vector((1, 0, 0)), 'Y': Vector((0, 1, 0)), 'Z': Vector((0, 0, 1))}


def rotate_bone(arm, name, axis, degrees):
    """Tourne un os (et ses enfants) autour d'un axe MONDE passant par sa tête (le
    squelette des sources est tourné : l'axe est ramené dans son repère)."""
    pb = arm.pose.bones.get(name)
    if pb is None:
        return
    local_axis = (arm.matrix_world.inverted().to_3x3() @ AXES[axis]).normalized()
    head = pb.matrix.translation.copy()
    rot = Matrix.Translation(head) @ Matrix.Rotation(math.radians(degrees), 4, local_axis) @ Matrix.Translation(-head)
    pb.matrix = rot @ pb.matrix
    bpy.context.view_layer.update()


def pose(arm, cfg):
    down, forward = cfg["arms"]
    # Bras gauche côté +X, droit côté -X (personnage tourné vers -Y).
    rotate_bone(arm, "LeftArm", 'Y', down)
    rotate_bone(arm, "RightArm", 'Y', -down)
    rotate_bone(arm, "LeftForeArm", 'X', -forward)
    rotate_bone(arm, "RightForeArm", 'X', -forward)
    # Arme : gardée dans son orientation de repos (canon vers l'avant), poignée
    # (tête de l'os de l'arme) amenée dans la main.
    for weapon, hand in cfg["weapons"].items():
        pw, ph = arm.pose.bones.get(weapon), arm.pose.bones.get(hand)
        if pw is not None and ph is not None:
            rest = arm.data.bones[weapon].matrix_local
            pw.matrix = Matrix.Translation(ph.matrix.translation) @ rest.to_3x3().to_4x4()
            bpy.context.view_layer.update()


def bake_meshes(arm):
    """Fige la pose : un maillage neuf par objet, sommets en coordonnées monde."""
    dg = bpy.context.evaluated_depsgraph_get()
    baked = []
    for o in [o for o in bpy.data.objects if o.type == 'MESH']:
        if o.hide_render or o.hide_get():
            bpy.data.objects.remove(o)
            continue
        # Les sources ont un modificateur Armature sans cible en plus du vrai.
        for m in list(o.modifiers):
            if m.type == 'ARMATURE' and m.object is None:
                o.modifiers.remove(m)
        dg.update()
        ev = o.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
        me.transform(o.matrix_world)
        name = o.name
        bpy.data.objects.remove(o)
        new = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(new)
        baked.append(new)
    return baked


# ---------------------------------------------------------------- Matériaux

def texture_index():
    index = {}
    for root, _, files in os.walk(SRC):
        for f in files:
            if f.lower().endswith(".png"):
                index.setdefault(f, os.path.join(root, f))
    return index


def color_image(mat, index):
    """Texture de couleur du matériau : intégrée, sinon retrouvée par nom de fichier."""
    if not mat or not mat.use_nodes:
        return None
    for n in mat.node_tree.nodes:
        if n.type != 'TEX_IMAGE' or n.image is None or "color" not in n.image.name.lower():
            continue
        img = n.image
        if img.packed_file is not None or (img.filepath and os.path.exists(bpy.path.abspath(img.filepath))):
            if img.has_data or img.size[0] > 0:
                return img
        name = os.path.basename(img.filepath) or img.name
        name = TEXTURE_ALIASES.get(name, name)
        if name in index:
            return bpy.data.images.load(index[name], check_existing=True)
    return None


def rebuild_materials(meshes, index):
    """Un matériau simple par matériau source : texture de couleur, mat."""
    cache = {}
    for o in meshes:
        for i, mat in enumerate(o.data.materials):
            if mat is None:
                continue
            if mat.name not in cache:
                img = color_image(mat, index)
                new = bpy.data.materials.new("Z_" + mat.name)
                new.use_nodes = True
                bsdf = new.node_tree.nodes.get("Principled BSDF")
                if img is not None:
                    tex = new.node_tree.nodes.new("ShaderNodeTexImage")
                    tex.image = img
                    new.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
                else:
                    bsdf.inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1.0)
                    print("  sans texture :", mat.name)
                cache[mat.name] = new
            o.data.materials[i] = cache[mat.name]


# ---------------------------------------------------------------- Construction

def bone_point(arm, name, tail=False):
    pb = arm.pose.bones[name]
    return arm.matrix_world @ (pb.tail if tail else pb.head)


def build(zid, export=True, preview_dir=None):
    cfg = ZOMBIES[zid]
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, cfg["blend"]))
    for o in list(bpy.data.objects):
        if o.type in ('CAMERA', 'LIGHT'):
            bpy.data.objects.remove(o)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    pose(arm, cfg)
    hips = bone_point(arm, "Hips")
    neck = bone_point(arm, next(b for b in ("Neck", "Head", "Spine1", "Hips") if b in arm.pose.bones))
    meshes = bake_meshes(arm)
    bpy.data.objects.remove(arm)
    L.drop_meshes(meshes, cfg.get("drop", ()))
    rebuild_materials(meshes, texture_index())

    # Échelle et pivot : axe des hanches à l'origine, pieds au sol.
    lo, hi = L.world_bounds(meshes)
    body_lo = min(v.co.z for o in meshes if not re.search(WEAPON_PATTERN, o.name) for v in o.data.vertices)
    scale = cfg["height"] / (hi.z - body_lo) if "height" in cfg else COMMON_SCALE
    m = Matrix.Scale(scale, 4) @ Matrix.Translation(Vector((-hips.x, -hips.y, -body_lo)))
    for o in meshes:
        o.data.transform(m)
        o.data.update()
    neck = m @ neck

    # Réduction : même part de triangles conservée partout, pour viser `target`.
    total = sum(L.tri_count(o) for o in meshes)
    ratio = min(1.0, cfg["target"] / total)
    for o in meshes:
        L.decimate(o, ratio)

    weapon = [o.name for o in meshes if re.search(WEAPON_PATTERN, o.name)]
    head = [o.name for o in meshes if o.name not in weapon and re.search(HEAD_PATTERN, o.name)]
    body = [o.name for o in meshes if o.name not in weapon and o.name not in head]
    esc = lambda names: ["^%s$" % re.escape(n) for n in names]  # noqa: E731
    parts = {"Body": (esc(body), 1.0)}
    if head:
        parts["Head"] = (esc(head), 1.0)
    if weapon:
        parts["Weapon"] = (esc(weapon), 1.0)
    name = "".join(w.title() for w in zid.split("_"))
    col, built = L.build_parts(meshes, name, parts, {"Head": neck}, {"Head": "Body", "Weapon": "Body"})
    L.simplify_materials()
    rep = L.report(col)
    rep["footprint_radius"] = round(max(math.hypot(*(o.matrix_world @ v.co).xy) for o in col.objects
                                        if o.type == 'MESH' for v in o.data.vertices), 3)
    rep["height"] = rep["max"][2]
    rep["source_triangles"] = total
    print("REPORT", zid, rep)
    if preview_dir:
        import prts_lib as P
        os.makedirs(preview_dir, exist_ok=True)
        h = rep["height"]
        P.preview_render(os.path.join(preview_dir, zid + "_front.png"), target=(0, 0, h / 2),
                         distance=h * 2.4, yaw_deg=-30, pitch_deg=12, size=(520, 520))
        P.preview_render(os.path.join(preview_dir, zid + "_side.png"), target=(0, 0, h / 2),
                         distance=h * 2.4, yaw_deg=90, pitch_deg=12, size=(520, 520))
    if export:
        blend = os.path.join(L.ROOT, "blender", "gw2", "zombies", zid + ".blend")
        glb = os.path.join(L.ROOT, "assets", "gw2", "zombies", zid + ".glb")
        L.export(col, blend, glb)
        print("EXPORTED", zid, os.path.getsize(glb))
    return rep


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ids = [a for a in argv if not a.startswith("--")] or list(ZOMBIES)
    preview = next((a.split("=", 1)[1] for a in argv if a.startswith("--preview=")), None)
    for zid in ids:
        build(zid, export="--no-export" not in argv, preview_dir=preview)
