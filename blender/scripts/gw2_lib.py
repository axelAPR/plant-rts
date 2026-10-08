# plantRTS — Outils communs pour reconstruire les modèles issus de Garden Warfare 2
# (et de Battle for Neighborville) fournis dans blender/plants imp/.
# Usage personnel et éducatif uniquement (voir CLAUDE.md) : ne pas diffuser. Les
# fichiers produits vont dans des dossiers ignorés par Git (blender/gw2/, assets/gw2/) ;
# le jeu les utilise en local via UnitData.local_visual_path.
#
# Chaîne : import (.obj, .fbx ou .dae — Blender 5 n'a plus d'import Collada, d'où le
# lecteur minimal ci-dessous) → sommets en coordonnées monde, pose de repos →
# mise à l'échelle (hauteur cible) et pivot au sol → réduction des polygones →
# pièces rigides nommées avec pivots → textures de couleur réduites, matériaux
# mats → enregistrement du .blend et export .glb.
# Avant : -Y dans Blender (→ +Z dans Godot), comme tous les modèles.

import bpy, math, os, re
import xml.etree.ElementTree as ET
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_ROOT = os.path.join(ROOT, "blender", "plants imp")
TEXTURE_SIZE = 512        # px, suffisant vu de la caméra RTS


# --- Lecteur Collada minimal (fichiers exportés par Blender : <triangles>) ---------

def _floats(text):
    return [float(x) for x in text.split()]


def _matrix(text):
    f = _floats(text)
    return Matrix([f[0:4], f[4:8], f[8:12], f[12:16]])


def import_dae(path):
    """Importe la géométrie d'un .dae (maillages, UV, matériaux à texture de couleur).

    Les sommets sont placés en coordonnées monde, pose de repos : matrice monde du
    nœud × (bind_shape_matrix pour un maillage skinné). Les squelettes sont ignorés.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    ns = {"c": root.tag[1:root.tag.index("}")]}
    base_dir = os.path.dirname(path)
    up_axis = root.findtext("c:asset/c:up_axis", "Z_UP", ns)

    images = {}
    for img in root.iterfind("c:library_images/c:image", ns):
        src = img.findtext("c:init_from", "", ns)
        images[img.get("id")] = os.path.join(base_dir, src.replace("%20", " "))
    effects = {}
    for eff in root.iterfind("c:library_effects/c:effect", ns):
        tex = eff.find(".//c:diffuse/c:texture", ns)
        image_path = None
        if tex is not None:
            sampler = tex.get("texture")
            surface = None
            for p in eff.iterfind(".//c:newparam", ns):
                if p.get("sid") == sampler:
                    surface = p.findtext("c:sampler2D/c:source", None, ns)
            for p in eff.iterfind(".//c:newparam", ns):
                if p.get("sid") == surface:
                    image_path = images.get(p.findtext("c:surface/c:init_from", "", ns))
            if image_path is None:
                image_path = images.get(sampler)
        effects[eff.get("id")] = image_path
    materials = {}
    for mat in root.iterfind("c:library_materials/c:material", ns):
        inst = mat.find("c:instance_effect", ns)
        materials[mat.get("id")] = (mat.get("name") or mat.get("id"),
                                    effects.get(inst.get("url")[1:]) if inst is not None else None)

    geometries = {g.get("id"): g for g in root.iterfind("c:library_geometries/c:geometry", ns)}
    controllers = {c.get("id"): c for c in root.iterfind("c:library_controllers/c:controller", ns)}

    created = []
    blender_materials = {}

    def get_material(mat_id):
        if mat_id not in blender_materials:
            name, image_path = materials.get(mat_id, (mat_id, None))
            mat = bpy.data.materials.new(name)
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if image_path and os.path.exists(image_path):
                tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
                tex.image = bpy.data.images.load(image_path, check_existing=True)
                mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
            blender_materials[mat_id] = mat
        return blender_materials[mat_id]

    def build(geom, name, world, bind_materials):
        mesh_el = geom.find("c:mesh", ns)
        sources = {}
        for s in mesh_el.iterfind("c:source", ns):
            fa = s.find("c:float_array", ns)
            acc = s.find("c:technique_common/c:accessor", ns)
            stride = int(acc.get("stride", "1"))
            data = _floats(fa.text or "")
            sources[s.get("id")] = [data[i:i + stride] for i in range(0, len(data), stride)]
        vertices_el = mesh_el.find("c:vertices", ns)
        pos_src = vertices_el.find("c:input[@semantic='POSITION']", ns).get("source")[1:]
        positions = [world @ Vector(p[:3]) for p in sources[pos_src]]
        faces, uvs, mat_idx, mat_list = [], [], [], []
        for tri in mesh_el.iterfind("c:triangles", ns):
            inputs = tri.findall("c:input", ns)
            n_off = max(int(i.get("offset")) for i in inputs) + 1
            v_off = next(int(i.get("offset")) for i in inputs if i.get("semantic") == "VERTEX")
            uv_in = [i for i in inputs if i.get("semantic") == "TEXCOORD"]
            uv_in.sort(key=lambda i: int(i.get("set", "0")))
            uv_off = int(uv_in[0].get("offset")) if uv_in else None
            uv_data = sources[uv_in[0].get("source")[1:]] if uv_in else None
            symbol = tri.get("material")
            mat_id = bind_materials.get(symbol, symbol)
            if mat_id not in mat_list:
                mat_list.append(mat_id)
            mi = mat_list.index(mat_id)
            p = [int(x) for x in (tri.findtext("c:p", "", ns)).split()]
            step = n_off * 3
            for k in range(0, len(p) - step + 1, step):
                faces.append([p[k + j * n_off + v_off] for j in range(3)])
                uvs.append([uv_data[p[k + j * n_off + uv_off]][:2] if uv_data else (0.0, 0.0) for j in range(3)])
                mat_idx.append(mi)
        if not faces:
            return None
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in positions], [], faces)
        uv_layer = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for j, li in enumerate(poly.loop_indices):
                uv_layer.data[li].uv = uvs[poly.index][j]
            poly.material_index = mat_idx[poly.index]
        for mat_id in mat_list:
            me.materials.append(get_material(mat_id) if mat_id else None)
        me.validate()
        obj = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(obj)
        created.append(obj)
        return obj

    def walk(node, parent_world):
        local = Matrix.Identity(4)
        for child in node:
            tag = child.tag.split("}")[1]
            if tag == "matrix":
                local = local @ _matrix(child.text)
            elif tag == "translate":
                local = local @ Matrix.Translation(Vector(_floats(child.text)))
            elif tag == "scale":
                s = _floats(child.text)
                local = local @ Matrix.Diagonal(Vector((s[0], s[1], s[2], 1.0)))
            elif tag == "rotate":
                r = _floats(child.text)
                local = local @ Matrix.Rotation(math.radians(r[3]), 4, Vector(r[:3]))
        world = parent_world @ local
        name = node.get("name") or node.get("id") or "Mesh"
        for inst in node.findall("c:instance_geometry", ns) + node.findall("c:instance_controller", ns):
            binds = {im.get("symbol"): im.get("target")[1:]
                     for im in inst.iterfind(".//c:instance_material", ns)}
            url = inst.get("url")[1:]
            if inst.tag.endswith("instance_controller"):
                ctrl = controllers[url]
                skin = ctrl.find("c:skin", ns)
                bsm = skin.findtext("c:bind_shape_matrix", None, ns)
                geom = geometries[skin.get("source")[1:]]
                # Maillage skinné : bind_shape_matrix donne la pose de repos dans
                # l'espace du squelette ; le nœud porte la matrice de l'objet.
                m = world @ (_matrix(bsm) if bsm else Matrix.Identity(4))
            else:
                geom = geometries[url]
                m = world
            build(geom, name, m, binds)
        for child in node.findall("c:node", ns):
            walk(child, world)

    up = Matrix.Identity(4)
    if up_axis == "Y_UP":
        up = Matrix.Rotation(math.pi / 2, 4, 'X')
    for vs in root.iterfind("c:library_visual_scenes/c:visual_scene", ns):
        for node in vs.findall("c:node", ns):
            walk(node, up)
    return created


# --- Chaîne commune ----------------------------------------------------------------

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_more(path):
    """Importe une source dans la scène courante ; renvoie ses maillages, sans
    parent ni squelette, transformations appliquées (sommets en coordonnées monde)."""
    before = set(bpy.data.objects)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".dae":
        import_dae(path)
    else:
        raise ValueError(path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    for o in meshes:
        o.modifiers.clear()
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return meshes


def import_source(path):
    """Scène vide puis import de la source."""
    reset_scene()
    return import_more(path)


def drop_meshes(meshes, patterns):
    """Supprime (en place) les maillages dont le nom correspond à un motif."""
    for o in list(meshes):
        if any(re.search(p, o.name) for p in patterns):
            meshes.remove(o)
            bpy.data.objects.remove(o)


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def world_bounds(objs):
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in objs:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


def normalize(meshes, target_height, yaw_degrees=0.0, center=True):
    """Rotation autour de Z (pour regarder vers -Y), hauteur cible, pivot au sol.

    center : recentre en X/Y sur le milieu de la boîte englobante du corps (sinon
    garde l'origine de la source, souvent déjà sur l'axe du personnage).
    """
    rot = Matrix.Rotation(math.radians(yaw_degrees), 4, 'Z')
    for o in meshes:
        o.data.transform(rot)
    lo, hi = world_bounds(meshes)
    scale = target_height / (hi.z - lo.z)
    off = Vector(((lo.x + hi.x) / 2 if center else 0.0, (lo.y + hi.y) / 2 if center else 0.0, lo.z))
    for o in meshes:
        o.data.transform(Matrix.Scale(scale, 4) @ Matrix.Translation(-off))
        o.data.update()
    return scale


def decimate(obj, ratio):
    if ratio >= 1.0:
        return
    mod = obj.modifiers.new("Decimate", 'DECIMATE')
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def build_parts(meshes, name, parts, pivots, parents, drop=()):
    """Regroupe les maillages source en pièces rigides nommées.

    parts   : {pièce: (motifs regex des noms source, part de triangles conservée)}
    pivots  : {pièce: Vector} pivot en coordonnées modèle (défaut : origine au sol)
    parents : {pièce: parent} (défaut : racine)
    drop    : motifs des maillages source à supprimer (LOD, doublons…)
    """
    drop_meshes(meshes, drop)
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    root = bpy.data.objects.new(name, None)
    root.empty_display_type = 'ARROWS'
    col.objects.link(root)
    groups = {}
    used = set()
    for part, (patterns, ratio) in parts.items():
        sources = [o for o in meshes if o.name not in used and any(re.search(p, o.name) for p in patterns)]
        if not sources:
            raise RuntimeError("Aucun maillage pour %s %s" % (part, patterns))
        used.update(o.name for o in sources)
        groups[part] = (sources, ratio)
    leftover = [o.name for o in meshes if o.name not in used]
    if leftover:
        raise RuntimeError("Maillages non attribués : %s" % leftover)
    built = {}
    for part, (sources, ratio) in groups.items():
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
    world_pivot = {p: pivots.get(p, Vector()) for p in built}
    for part, obj in built.items():
        obj.data.transform(Matrix.Translation(-world_pivot[part]))
    for part, obj in built.items():
        parent = parents.get(part)
        if parent:
            obj.parent = built[parent]
            obj.location = world_pivot[part] - world_pivot[parent]
        else:
            obj.parent = root
            obj.location = world_pivot[part]
    bpy.context.view_layer.update()
    # Rien ne traverse le sol.
    for obj in built.values():
        for v in obj.data.vertices:
            w = obj.matrix_world @ v.co
            if w.z < 0.004:
                v.co.z += 0.004 - w.z
    return col, built


def simplify_materials():
    """Textures de couleur réduites et intégrées ; matériaux mats ; un seul jeu d'UV."""
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        nodes = mat.node_tree.nodes
        bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is None:
            continue
        # Ne garder que la texture de couleur (pas de normales ni de masques).
        for link in list(mat.node_tree.links):
            if link.to_node == bsdf and link.to_socket.name != "Base Color":
                mat.node_tree.links.remove(link)
        bsdf.inputs["Roughness"].default_value = 0.85
        bsdf.inputs["Specular IOR Level"].default_value = 0.2
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Alpha"].default_value = 1.0
        for n in list(nodes):
            if n.type == 'TEX_IMAGE' and not n.outputs["Color"].is_linked:
                nodes.remove(n)
            elif n.type == 'NORMAL_MAP':
                nodes.remove(n)
    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)
            continue
        if image.size[0] > TEXTURE_SIZE or image.size[1] > TEXTURE_SIZE:
            w, h = image.size
            k = TEXTURE_SIZE / max(w, h)
            image.scale(max(1, int(w * k)), max(1, int(h * k)))
        image.pack()
    for o in bpy.data.objects:
        if o.type == 'MESH':
            while len(o.data.uv_layers) > 1:
                o.data.uv_layers.remove(o.data.uv_layers[-1])


def report(col):
    meshes = [o for o in col.objects if o.type == 'MESH']
    bpy.context.view_layer.update()
    lo, hi = world_bounds(meshes)
    tris = {o.name: tri_count(o) for o in meshes}
    return {"triangles": tris, "total": sum(tris.values()),
            "min": [round(x, 3) for x in lo], "max": [round(x, 3) for x in hi]}


def export(col, blend_path, glb_path, animations=False):
    """`animations` : exporte les pistes NLA (voir prts_lib.add_animation)."""
    os.makedirs(os.path.dirname(blend_path), exist_ok=True)
    os.makedirs(os.path.dirname(glb_path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    for o in bpy.data.objects:
        o.select_set(o.name in col.objects)
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB', use_selection=True,
                              export_yup=True, export_apply=True, export_materials='EXPORT',
                              export_image_format='AUTO', export_cameras=False,
                              export_lights=False, export_animations=animations,
                              **({"export_animation_mode": 'NLA_TRACKS'} if animations else {}))
