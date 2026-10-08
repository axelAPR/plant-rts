# plantRTS — Plantes reconstruites à partir des modèles de Garden Warfare 2 (et de
# Battle for Neighborville pour le Citron, des cartes AR mobiles pour le Chomper)
# fournis dans blender/plants imp/. Le Tournesol a son propre script
# (sunflower_gw2.py).
# Usage personnel et éducatif uniquement (voir CLAUDE.md) : ne pas diffuser. Les
# fichiers produits vont dans des dossiers ignorés par Git (blender/gw2/, assets/gw2/) ;
# le jeu les utilise en local via UnitData.local_visual_path.
#
# Exécution (Blender 5.x, en arrière-plan) :
#   blender -b --python blender/scripts/plants_gw2.py -- [ids…] [--no-export] [--preview=<dossier>]
# Sans id : toutes les plantes.
#
# Par plante : import → pose (bras abaissés depuis la pose de référence, arme placée
# dans la main) → hauteur de l'ancien modèle procédural, pivot au sol, centré sur
# l'axe du corps → réduction des polygones → pièces rigides avec pivots → textures
# de couleur seules, 512 px, matériaux mats → .blend + .glb.
# Toutes les coordonnées ci-dessous sont celles de la source (avant mise à
# l'échelle), Z en haut, avant vers -Y.

import bpy, math, os, sys
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gw2_lib as L

GW2 = "PC _ Computer - Plants vs. Zombies_ Garden Warfare 2 - "
BFN = "PC _ Computer - Plants vs. Zombies_ Battle for Neighborville - Playable Plants - "


def src(*parts):
    return os.path.join(L.SRC_ROOT, *parts)


# Chaque plante :
#   sources  : fichiers importés ensemble
#   drop     : maillages source supprimés (LOD, reflets)
#   height   : hauteur finale (m) = celle de l'ancien modèle procédural
#   axis     : (x, y) de l'axe du corps dans la source → origine du modèle
#   bends    : bras abaissés : (motif de maillage, x épaule, z épaule, angle °,
#              début et fin du fondu en |x| [, z min, z max]) — rotation autour de
#              l'axe avant/arrière, limitée à une tranche de hauteur si précisée
#   attach   : (motif, point d'accroche dans la maillage, point cible, rotation °)
#              où point cible = « hand:<motif>,<x>,<z> » (point du bras après flexion)
#   parts    : {pièce: ([motifs regex], part de triangles conservée)}
#   pivots   : {pièce: (x, y, z)} ; parents : {pièce: parent}
PLANTS = {
    "peashooter": {
        "name": "Peashooter",
        "sources": [src(GW2 + "Plants - Peashooter", "Peashooter", "peashooter.dae")],
        "height": 1.25,
        "axis": (0.0, 0.0),
        # Bras : gousses (Arms) et tiges des bras (dans le corps, tranche 0,64–0,73 m).
        "bends": [("^Arms_", 0.06, 0.70, 45.0, 0.06, 0.30),
                  ("^PeaShooter_Body_", 0.06, 0.70, 45.0, 0.06, 0.30, 0.64, 0.73)],
        "parts": {
            "Stem": (["^PeaShooter_Body_"], 0.3),
            "Arms": (["^Arms_"], 0.3),
            "Head": (["^DefaultPea_", "^HeadProp_"], 0.35),
        },
        "pivots": {"Head": (0.0, 0.0, 0.9)},
        "parents": {"Arms": "Stem", "Head": "Stem"},
        "walk": True,
    },
    "cactus": {
        "name": "Cactus",
        "sources": [src(GW2 + "Plants - Cactus", "Cactus", "cactus.dae")],
        "height": 1.55,
        "axis": (0.0, 0.0),
        "parts": {
            "Body": (["^Body_", "Eye_M"], 0.3),
            "Arms": (["^Arms_"], 0.3),
            "Head": (["HeadProp"], 0.2),
        },
        "pivots": {"Head": (0.0, 0.0, 1.85)},
        "parents": {"Arms": "Body", "Head": "Body"},
    },
    "kernel_corn": {
        "name": "KernelCorn",
        "sources": [src(GW2 + "Plants - Kernal Corn", "Kernal Corn", "kernalcorn.dae")],
        "height": 1.55,
        "axis": (0.0, 0.0),
        "parts": {
            "Body": (["^Corn_Body_", "^Corn_Neck_"], 0.28),
            "Guns": (["^Corn_Weapon_"], 0.06),
            "Head": (["^Corn_Head_", "^Corn_Eyes_"], 0.32),
        },
        # Les grains de l'épi sont en relief : réduction plus douce sur la tête.
        "ratios": {"assaultcorn_head_defaultcorn": 0.6},
        "pivots": {"Head": (0.0, 0.0, 1.8)},
        "parents": {"Guns": "Body", "Head": "Body"},
    },
    "rose": {
        "name": "Rose",
        "sources": [src(GW2 + "Plants - Rose", "Rose", "Rose.dae")],
        "height": 1.72,
        "axis": (0.0, 0.0),
        # Bras : gants (Arms) et bras fins (dans le corps, tranche 1,04–1,17 m).
        "bends": [("^Arms_", 0.10, 1.10, 62.0, 0.10, 0.30),
                  ("^Body_DefaultRose_M", 0.10, 1.10, 62.0, 0.10, 0.30, 1.04, 1.17)],
        # Baguette dans la main droite (côté -X), pointée vers l'avant et un peu
        # vers le haut.
        "attach": [("^Weapon_", (0.0, -0.06, 0.0), "hand:-0.60,1.10", (12.0, 0.0, 0.0))],
        "parts": {
            "Body": (["^Body_"], 0.3),
            "Arms": (["^Arms_"], 0.3),
            "Staff": (["^Weapon_"], 0.2),
            "Head": (["^Head_DefaultRose_M", "^FaceProp_", "^Head_DefaultRoseEyes_", "^HeadProp_"], 0.3),
        },
        "ratios": {"^FaceProp_": 0.6, "^Head_DefaultRose_M": 0.5},
        "pivots": {"Head": (0.0, 0.0, 1.42)},
        "parents": {"Arms": "Body", "Staff": "Arms", "Head": "Body"},
    },
    "chomper": {
        "name": "Chomper",
        "sources": [src("Mobile - Plants vs. Zombies AR Trading Cards - Plants - Chomper", "PVZ10_468.obj")],
        "height": 1.49,
        "axis": None,  # centre de la tige, calculé
        "parts": {"Body": (["."], 0.55)},
    },
    "citron": {
        "name": "Citron",
        "sources": [src(BFN + "Citron", "Citron", f) for f in
                    ("Citron.dae", "CitronFace.dae", "CitronHead.dae", "CitronMouth.dae", "CitronWeapon.dae")],
        # LOD 1 à 3, reflets des yeux, vitre transparente de la visière.
        "drop": [r"\.00\d$", "_HL_M", "^Citron_FaceProp_Default_M$"],
        "height": 1.42,
        "axis": (0.0, 0.0),
        "parts": {
            "Body": (["^Citron_Body_", "^Citron_FaceProp_", "^Citron_HeadProp_", "^Citron_MouthProp_"], 0.4),
            "Weapon": (["^Citron_Weapon_"], 0.4),
        },
        "ratios": {"_Pulp_": 0.3, "FaceProp": 1.0, "MouthProp": 1.0, "HeadProp": 0.6},
        "parents": {"Weapon": "Body"},
        "eye_color": (0.95, 0.97, 1.0),
    },
    "torchwood": {
        "name": "Torchwood",
        "sources": [src(GW2 + "Plant Bosses - Giga Torchwood", "Giga Torchwood PvZGW2",
                        "torchwood_body_gigatorchwood_Mesh.dae")],
        "height": 1.57,
        "axis": None,
        "parts": {"Body": (["."], 0.3)},
        "ratios": {"_Eye_": 0.4},
    },
}


def bend_point(p, shoulder_x, shoulder_z, angle, x0, x1):
    """Abaisse un point du bras : rotation autour de l'axe Y passant par l'épaule,
    fondue entre |x| = x0 et x1 (épaule souple, avant-bras rigide)."""
    ax = abs(p.x)
    if ax <= x0:
        return p.copy()
    t = min(1.0, (ax - x0) / (x1 - x0))
    w = t * t * (3 - 2 * t)
    side = 1.0 if p.x > 0 else -1.0
    a = math.radians(angle) * w * side
    pivot = Vector((side * shoulder_x, 0.0, shoulder_z))
    return pivot + Matrix.Rotation(a, 3, 'Y') @ (p - pivot)


def find(meshes, pattern):
    import re
    return [o for o in meshes if re.search(pattern, o.name)]


def pose(meshes, cfg):
    for pattern, sx, sz, angle, x0, x1, *z_window in cfg.get("bends", []):
        z_lo, z_hi = z_window or (-1e9, 1e9)
        for o in find(meshes, pattern):
            for v in o.data.vertices:
                if z_lo <= v.co.z <= z_hi:
                    v.co = bend_point(v.co, sx, sz, angle, x0, x1)
            o.data.update()
    for pattern, grip, target, rot in cfg.get("attach", []):
        if target.startswith("hand:"):
            hx, hz = (float(x) for x in target[5:].split(","))
            bend = cfg["bends"][0]
            target_pt = bend_point(Vector((hx, 0.0, hz)), *bend[1:6])
        else:
            target_pt = Vector(target)
        r = Matrix.Rotation(math.radians(rot[0]), 4, 'X') @ Matrix.Rotation(math.radians(rot[2]), 4, 'Z')
        m = Matrix.Translation(target_pt) @ r @ Matrix.Translation(-Vector(grip))
        for o in find(meshes, pattern):
            o.data.transform(m)
            o.data.update()


def stem_axis(meshes, band=0.15):
    """Axe du corps : centre des sommets dans la tranche basse (tige, pied)."""
    lo, hi = L.world_bounds(meshes)
    z_min = lo.z + (hi.z - lo.z) * 0.08
    z_max = lo.z + (hi.z - lo.z) * (0.08 + band)
    pts = [v.co for o in meshes for v in o.data.vertices if z_min <= v.co.z <= z_max]
    xs = sorted(p.x for p in pts); ys = sorted(p.y for p in pts)
    return (xs[len(xs) // 2], ys[len(ys) // 2])


def normalize(meshes, cfg):
    """Matrice source → modèle : axe du corps à l'origine, pied au sol, hauteur cible."""
    axis = cfg["axis"] or stem_axis(meshes)
    lo, hi = L.world_bounds(meshes)
    scale = cfg["height"] / (hi.z - lo.z)
    m = Matrix.Scale(scale, 4) @ Matrix.Translation(Vector((-axis[0], -axis[1], -lo.z)))
    for o in meshes:
        o.data.transform(m)
        o.data.update()
    return m


def per_mesh_ratios(meshes, cfg):
    """Réduction maillage par maillage (avant regroupement), la pièce donnant le défaut."""
    import re
    for part, (patterns, ratio) in cfg["parts"].items():
        for o in meshes:
            if any(re.search(p, o.name) for p in patterns) and "_ratio" not in o:
                r = ratio
                for pat, rr in cfg.get("ratios", {}).items():
                    if re.search(pat, o.name):
                        r = rr
                o["_ratio"] = r
    for o in meshes:
        L.decimate(o, o.get("_ratio", 1.0))


def fill_missing_materials(meshes, color):
    mat = None
    for o in meshes:
        if not o.data.materials or all(m is None for m in o.data.materials):
            if mat is None:
                mat = bpy.data.materials.new("Eye")
                mat.use_nodes = True
                mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (*color, 1.0)
            o.data.materials.clear()
            o.data.materials.append(mat)


def footprint(col):
    r = 0.0
    for o in col.objects:
        if o.type == 'MESH':
            for v in o.data.vertices:
                w = o.matrix_world @ v.co
                r = max(r, math.hypot(w.x, w.y))
    return round(r, 3)


def add_walk(cfg):
    """Pisto-pois : même trot sautillant que le modèle procédural (peashooter_anim.py)."""
    import prts_lib
    ns = dict(vars(prts_lib))
    ns["__name__"] = "peashooter_anim"
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "peashooter_anim.py"), encoding="utf-8") as f:
        exec(f.read(), ns)
    keys = {}
    for i, side in enumerate((1, -1)):
        for obj, frames in ns["_walk_hop"](side).items():
            if obj not in bpy.data.objects:
                continue
            dst = keys.setdefault(obj, {})
            for fr, p in frames.items():
                dst[i * 8 + fr] = p
    for obj in keys:
        keys[obj][ns["WALK_FRAMES"]] = keys[obj][0]
    prts_lib.add_animation("Walk", keys)
    scene = bpy.context.scene
    scene.render.fps = 24
    scene.frame_start, scene.frame_end = 0, ns["WALK_FRAMES"]
    scene.frame_set(0)  # pose de repos


def build(plant_id, export=True, preview_dir=None):
    cfg = PLANTS[plant_id]
    L.reset_scene()
    meshes = []
    for path in cfg["sources"]:
        meshes += L.import_more(path)
    L.drop_meshes(meshes, cfg.get("drop", ()))
    if "eye_color" in cfg:
        fill_missing_materials(meshes, cfg["eye_color"])
    pose(meshes, cfg)
    m = normalize(meshes, cfg)
    per_mesh_ratios(meshes, cfg)
    parts = {k: (v[0], 1.0) for k, v in cfg["parts"].items()}
    pivots = {k: m @ Vector(p) for k, p in cfg.get("pivots", {}).items()}
    col, built = L.build_parts(meshes, cfg["name"], parts, pivots, cfg.get("parents", {}))
    L.simplify_materials()
    if cfg.get("walk"):
        add_walk(cfg)
    rep = L.report(col)
    rep["footprint_radius"] = footprint(col)
    print("REPORT", plant_id, rep)
    if preview_dir:
        import prts_lib as P
        os.makedirs(preview_dir, exist_ok=True)
        h = cfg["height"]
        P.preview_render(os.path.join(preview_dir, plant_id + "_front.png"), target=(0, 0, h / 2),
                         distance=h * 2.4, yaw_deg=-30, pitch_deg=12, size=(520, 520))
        P.preview_render(os.path.join(preview_dir, plant_id + "_side.png"), target=(0, 0, h / 2),
                         distance=h * 2.4, yaw_deg=90, pitch_deg=12, size=(520, 520))
    if export:
        blend = os.path.join(L.ROOT, "blender", "gw2", "plants", plant_id + ".blend")
        glb = os.path.join(L.ROOT, "assets", "gw2", "plants", plant_id + ".glb")
        L.export(col, blend, glb, animations=bool(cfg.get("walk")))
        print("EXPORTED", plant_id, os.path.getsize(glb))
    return rep


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ids = [a for a in argv if not a.startswith("--")] or list(PLANTS)
    preview = next((a.split("=", 1)[1] for a in argv if a.startswith("--preview=")), None)
    for pid in ids:
        build(pid, export="--no-export" not in argv, preview_dir=preview)
