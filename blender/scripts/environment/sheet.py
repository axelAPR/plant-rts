# plantRTS — Kit d'environnement : planche de contrôle d'une famille de modèles.
# blender -b --python blender/scripts/environment/sheet.py -- <nom> <catégorie/id> […] [--cols=N] [--gap=M]
#
# Importe les .glb exportés (assets/environment/<catégorie>/<id>.glb), les range en
# grille (ordre donné, espacement selon leur emprise), ajoute une escouade de
# Pisto-pois et deux Zombies classiques pour l'échelle, puis rend une vue d'ensemble
# rapprochée et une vue en caméra de jeu dans tests/environment_test/captures/.

import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import bpy
from mathutils import Vector
import env_lib as E
import prts_lib as P


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    return new, roots


def bounds(objs):
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    bpy.context.view_layer.update()
    for o in objs:
        if o.type == 'MESH':
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    name = argv[0]
    items = [a for a in argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=") for a in argv[1:] if a.startswith("--"))
    cols = int(opts.get("cols", 4))
    gap = float(opts.get("gap", 2.0))
    hide = opts.get("hide", "").split(",") if opts.get("hide") else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    placed = []
    for item in items:
        objs, roots = import_glb(os.path.join(E.ROOT, "assets", "environment", item + ".glb"))
        for o in objs:
            if o.name.split(".")[0] in hide:
                o.hide_render = True
        lo, hi = bounds(objs)
        placed.append((item, roots, lo, hi))
    # Grille : largeur de colonne = plus grande emprise de la rangée.
    x_cursor_rows = []
    rows = [placed[i:i + cols] for i in range(0, len(placed), cols)]
    y = 0.0               # bord supérieur (côté +Y) de la rangée courante
    for row in rows:
        depth = max(hi.y - lo.y for _, _, lo, hi in row)
        x = 0.0
        for item, roots, lo, hi in row:
            w = hi.x - lo.x
            for r in roots:
                r.location.x += x - lo.x
                r.location.y += (y - depth / 2) - (lo.y + hi.y) / 2
            x += w + gap
        x_cursor_rows.append(x)
        y -= depth + gap
    width = max(x_cursor_rows) - gap
    total_depth = -y - gap
    first_half = max(hi.y - lo.y for _, _, lo, hi in rows[0]) / 2
    center = Vector((width / 2, -(total_depth + 4.0) / 2, 0))
    # Échelle : escouade de Pisto-pois et deux zombies devant la planche.
    pea = E.scale_collection("_ScalePeashooter", os.path.join(E.ROOT, "assets", "plants", "peashooter.glb"))
    zom = E.scale_collection("_ScaleBrowncoat", os.path.join(E.ROOT, "assets", "zombies", "browncoat.glb"))
    base_y = y - 0.5      # devant la dernière rangée, côté caméra
    inst = [(pea, (1.0 + (i % 3) * 1.8, base_y - (i // 3) * 1.8, 0), 0.0) for i in range(6)]
    inst += [(zom, (7.0 + i * 1.6, base_y - 0.9, 0), 0.0) for i in range(2)]
    span = max(width, total_depth)
    # Sol d'herbe sous toute la planche (le sol de prts_lib.preview_render est petit).
    bpy.ops.mesh.primitive_plane_add(size=1, location=(center.x, center.y, -0.01))
    ground = bpy.context.active_object
    ground.scale = (span * 3 + 60, span * 3 + 60, 1)
    gm = bpy.data.materials.new("_SheetGround")
    gm.diffuse_color = (*P.srgb("#6B8A4A"), 1)
    bsdf = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Base Color"].default_value = (*P.srgb("#6B8A4A"), 1)
    bsdf.inputs["Roughness"].default_value = 0.95
    ground.data.materials.append(gm)
    out_dir = E.CAPTURE_DIR
    os.makedirs(out_dir, exist_ok=True)
    P.preview_render(os.path.join(out_dir, "sheet_%s.png" % name), target=center, distance=span * 0.95 + 6,
                     yaw_deg=-20, pitch_deg=38, lens=35.0, size=(1400, 900), instances=inst, ground=False)
    P.preview_render(os.path.join(out_dir, "sheet_%s_rts.png" % name), target=center, distance=max(span * 1.05, 30),
                     yaw_deg=-20, pitch_deg=E.rts_pitch(max(span * 1.05, 30)), lens=E.RTS_LENS, size=(1280, 720),
                     instances=inst, ground=False)
    print("SHEET", name, len(placed), round(width, 1), round(total_depth, 1))


main()
