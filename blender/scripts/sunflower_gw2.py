# plantRTS — Tournesol reconstruit à partir du modèle de Garden Warfare 2
# (blender/plants imp/…/Sunflower : maillage .obj + textures de couleur).
# Usage personnel et éducatif uniquement (voir CLAUDE.md) : ne pas diffuser. Les
# fichiers produits vont dans des dossiers ignorés par Git (blender/gw2/, assets/gw2/) ;
# le jeu les utilise en local via UnitData.local_visual_path.
#
# Exécution (Blender 5.x, en arrière-plan) :
#   blender -b --python blender/scripts/sunflower_gw2.py
#
# Étapes : import → mise à l'échelle (hauteur 1,45 m, celle du Tournesol précédent) →
# pivot au sol → réduction des polygones (budget RTS) → pièces rigides avec pivots
# (Body, Head enfant de Body au cou, Arms) → textures de couleur réduites à 512 px,
# matériaux mats → enregistrement du .blend et export .glb.
# Avant : -Y dans Blender (→ +Z dans Godot), comme tous les modèles.

import bpy, os, sys
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIR = os.path.join(ROOT, "blender", "plants imp",
                       "PC _ Computer - Plants vs. Zombies_ Garden Warfare 2 - Plants - Sunflower", "Sunflower")
SRC_OBJ = os.path.join(SRC_DIR, "sunflower_defaultflower_mesh.obj")
BLEND_PATH = os.path.join(ROOT, "blender", "gw2", "plants", "sunflower.blend")
GLB_PATH = os.path.join(ROOT, "assets", "gw2", "plants", "sunflower.glb")

TARGET_HEIGHT = 1.45      # m, hauteur du Tournesol précédent (échelle commune)
TEXTURE_SIZE = 512        # px, suffisant vu de la caméra RTS
NECK_Z = 0.95             # m (après mise à l'échelle) : pivot de la tête
# Pièce cible ← objets source (préfixes) et part des triangles conservée.
PARTS = {
    "Body": (("Body_",), 0.4),
    "Arms": (("Arms_",), 0.35),
    "Head": (("Head_DefaultFlower_M", "SunflowerPetals_", "DefaultFlower_Head_DarkSunFlowerEye"), 0.3),
}


def import_source():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=SRC_OBJ)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    # L'import oriente les objets (Y-up → Z-up) par leur rotation : on l'applique aux
    # sommets pour travailler directement en coordonnées monde.
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    lo = min(v.co.z for o in meshes for v in o.data.vertices)
    hi = max(v.co.z for o in meshes for v in o.data.vertices)
    scale = TARGET_HEIGHT / (hi - lo)
    for o in meshes:
        for v in o.data.vertices:
            v.co = Vector((v.co.x * scale, v.co.y * scale, (v.co.z - lo) * scale))
    return meshes


def decimate(obj, ratio):
    mod = obj.modifiers.new("Decimate", 'DECIMATE')
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def build_parts(meshes):
    col = bpy.data.collections.new("Sunflower")
    bpy.context.scene.collection.children.link(col)
    root = bpy.data.objects.new("Sunflower", None)
    root.empty_display_type = 'ARROWS'
    col.objects.link(root)
    built = {}
    for part, (prefixes, ratio) in PARTS.items():
        sources = [o for o in meshes if o.name.startswith(prefixes)]
        for o in sources:
            decimate(o, ratio)
        bpy.ops.object.select_all(action='DESELECT')
        for o in sources:
            o.select_set(True)
        bpy.context.view_layer.objects.active = sources[0]
        if len(sources) > 1:
            bpy.ops.object.join()
        obj = bpy.context.view_layer.objects.active
        obj.name = obj.data.name = part
        for c in obj.users_collection:
            c.objects.unlink(obj)
        col.objects.link(obj)
        for p in obj.data.polygons:
            p.use_smooth = True
        built[part] = obj
    # Pivots : corps et bras au sol, tête au cou ; la tête suit le corps.
    pivots = {"Body": Vector(), "Arms": Vector(), "Head": Vector((0.0, 0.0, NECK_Z))}
    for part, obj in built.items():
        obj.data.transform(Matrix.Translation(-pivots[part]))
        obj.location = pivots[part]
    built["Body"].parent = root
    built["Arms"].parent = built["Body"]
    built["Head"].parent = built["Body"]
    built["Head"].location = pivots["Head"]
    # Les pointes des feuilles reposent sur le sol sans le traverser.
    for v in built["Body"].data.vertices:
        v.co.z = max(v.co.z, 0.004)
    return col, built


def simplify_materials():
    """Textures de couleur réduites et intégrées ; matériaux mats (palette plantes)."""
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is None:
            continue
        bsdf.inputs["Roughness"].default_value = 0.85
        bsdf.inputs["Specular IOR Level"].default_value = 0.2
        bsdf.inputs["Metallic"].default_value = 0.0
    for image in bpy.data.images:
        if image.size[0] > TEXTURE_SIZE:
            image.scale(TEXTURE_SIZE, TEXTURE_SIZE)
        image.pack()


def report(col):
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in col.objects if o.type == 'MESH'}
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    bpy.context.view_layer.update()
    for o in col.objects:
        if o.type != 'MESH':
            continue
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return {"triangles": tris, "total": sum(tris.values()),
            "min": [round(x, 3) for x in lo], "max": [round(x, 3) for x in hi]}


def export(col):
    os.makedirs(os.path.dirname(BLEND_PATH), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    for o in bpy.data.objects:
        o.select_set(o.name in col.objects)
    bpy.ops.export_scene.gltf(filepath=GLB_PATH, export_format='GLB', use_selection=True,
                              export_yup=True, export_apply=True, export_materials='EXPORT',
                              export_image_format='AUTO', export_cameras=False,
                              export_lights=False, export_animations=False)


if __name__ == "__main__":
    col, parts = build_parts(import_source())
    simplify_materials()
    print("REPORT", report(col))
    if "--no-export" not in sys.argv:
        export(col)
        print("EXPORTED", os.path.getsize(BLEND_PATH), os.path.getsize(GLB_PATH))
