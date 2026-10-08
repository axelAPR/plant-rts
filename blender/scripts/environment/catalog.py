# plantRTS — Kit d'environnement : génération du catalogue de données Godot.
# python blender/scripts/environment/catalog.py      (Python seul, sans Blender)
#
# Écrit data/environment/<id>.tres (EnvironmentPieceData) pour chaque modèle du kit et
# data/environment/environment_catalog.tres (liste complète). La hauteur est mesurée
# dans le .glb (bornes des sommets, translations des nœuds) ; le reste vient de la
# table PIECES ci-dessous (nom affiché, emprise de la grille, propriétés de jeu).

import json, os, struct

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.join(ROOT, "data", "environment")

CATEGORY = {"ground": "GROUND", "buildings": "BUILDINGS", "cover_heavy": "COVER_HEAVY",
            "cover_light": "COVER_LIGHT", "vegetation": "VEGETATION", "props": "PROPS",
            "gameplay": "GAMEPLAY", "borders": "BORDERS"}
ENUMS = {
    "Category": ["GROUND", "BUILDINGS", "COVER_HEAVY", "COVER_LIGHT", "VEGETATION", "PROPS", "GAMEPLAY", "BORDERS"],
    "Cover": ["NONE", "LIGHT", "HEAVY"],
    "ResourceKind": ["NONE", "PRIMARY", "SECONDARY", "TERTIARY"],
}

# id: (catégorie, nom affiché, emprise (x, z) en m ou rayon, bloque le déplacement,
#      bloque la vue, couvert, ressource)
N, L, H = "NONE", "LIGHT", "HEAVY"
PIECES = {
    # Routes et sols
    "road_straight":   ("ground", "Route droite", (8, 8), False, False, N, N),
    "road_curve":      ("ground", "Route en virage", (8, 8), False, False, N, N),
    "road_t":          ("ground", "Carrefour en T", (8, 8), False, False, N, N),
    "road_cross":      ("ground", "Carrefour", (8, 8), False, False, N, N),
    "road_end":        ("ground", "Impasse", (8, 8), False, False, N, N),
    "road_crosswalk":  ("ground", "Passage piéton", (8, 8), False, False, N, N),
    "driveway":        ("ground", "Allée de garage", (4, 8), False, False, N, N),
    "path_straight":   ("ground", "Chemin droit", (4, 2), False, False, N, N),
    "path_curve":      ("ground", "Chemin en virage", (4, 4), False, False, N, N),
    "dirt_patch":      ("ground", "Terre retournée", (4, 4), False, False, N, N),
    "flowerbed":       ("ground", "Massif surélevé", (4, 2), True, False, L, N),
    # Bâtiments
    "house_a":         ("buildings", "Maison bleue", (10, 8), True, True, H, N),
    "house_b":         ("buildings", "Maison jaune à galerie", (10, 8), True, True, H, N),
    "house_two_story": ("buildings", "Maison à étage", (10, 8), True, True, H, N),
    "house_haunted":   ("buildings", "Maison abandonnée", (10, 8), True, True, H, N),
    "garage":          ("buildings", "Garage", (6, 8), True, True, H, N),
    "garden_shed":     ("buildings", "Abri de jardin", (4, 4), True, True, H, N),
    "greenhouse":      ("buildings", "Serre", (4, 6), True, True, H, N),
    "crypt":           ("buildings", "Crypte", (6, 6), True, True, H, N),
    "corner_shop":     ("buildings", "Épicerie", (10, 10), True, True, H, N),
    # Couvert lourd
    "stone_wall_straight": ("cover_heavy", "Muret de pierre", (4, 2), True, False, H, N),
    "stone_wall_corner":   ("cover_heavy", "Angle de muret", (2, 2), True, False, H, N),
    "stone_wall_end":      ("cover_heavy", "Bout de muret", (2, 2), True, False, H, N),
    "stone_wall_broken":   ("cover_heavy", "Muret effondré", (4, 2), True, False, H, N),
    "sandbag_straight":    ("cover_heavy", "Sacs de sable", (4, 2), True, False, H, N),
    "sandbag_curve":       ("cover_heavy", "Sacs de sable en arc", (4, 4), True, False, H, N),
    "car_sedan":           ("cover_heavy", "Berline", (4, 2), True, False, H, N),
    "car_wreck":           ("cover_heavy", "Épave de voiture", (4, 2), True, False, H, N),
    "pickup_truck":        ("cover_heavy", "Pick-up", (6, 2), True, False, H, N),
    "dumpster":            ("cover_heavy", "Benne à ordures", (2, 2), True, False, H, N),
    "rock_large":          ("cover_heavy", "Gros rocher", (4, 4), True, True, H, N),
    "concrete_barrier":    ("cover_heavy", "Séparateur en béton", (4, 2), True, False, H, N),
    "tombstone_large":     ("cover_heavy", "Grande pierre tombale", (2, 2), True, False, H, N),
    # Couvert léger
    "picket_fence_straight": ("cover_light", "Clôture à piquets", (4, 2), True, False, L, N),
    "picket_fence_corner":   ("cover_light", "Angle de clôture", (2, 2), True, False, L, N),
    "picket_fence_gate":     ("cover_light", "Portillon", (4, 2), True, False, L, N),
    "picket_fence_broken":   ("cover_light", "Clôture cassée", (4, 2), True, False, L, N),
    "hedge_straight":        ("cover_light", "Haie", (4, 2), True, False, L, N),
    "hedge_corner":          ("cover_light", "Angle de haie", (2, 2), True, False, L, N),
    "hedge_end":             ("cover_light", "Bout de haie", (2, 2), True, False, L, N),
    "iron_fence_straight":   ("cover_light", "Grille en fer forgé", (4, 2), True, False, L, N),
    "iron_fence_corner":     ("cover_light", "Angle de grille", (2, 2), True, False, L, N),
    "iron_fence_gate":       ("cover_light", "Portail en fer forgé", (4, 2), True, False, L, N),
    "crate_stack":           ("cover_light", "Caisses empilées", (2, 2), True, False, L, N),
    "barrel_group":          ("cover_light", "Tonneaux", (2, 2), True, False, L, N),
    "hay_bale":              ("cover_light", "Bottes de foin", (2, 2), True, False, L, N),
    "planter_box":           ("cover_light", "Jardinière", (2, 2), True, False, L, N),
    "trash_cans":            ("cover_light", "Poubelles", (2, 2), True, False, L, N),
    "wheelbarrow":           ("cover_light", "Brouette", (2, 2), True, False, L, N),
    # Végétation
    "tree_large":      ("vegetation", "Grand arbre", (4, 4), True, True, L, N),
    "tree_small":      ("vegetation", "Petit arbre d'automne", (2, 2), True, False, L, N),
    "tree_dead":       ("vegetation", "Arbre mort", (4, 4), True, False, L, N),
    "bush_a":          ("vegetation", "Buisson", (2, 2), False, False, L, N),
    "bush_b":          ("vegetation", "Buisson fleuri", (2, 2), False, False, L, N),
    "flower_patch_a":  ("vegetation", "Tulipes", (2, 2), False, False, N, N),
    "flower_patch_b":  ("vegetation", "Marguerites", (2, 2), False, False, N, N),
    "flower_patch_c":  ("vegetation", "Fleurs roses et bleues", (2, 2), False, False, N, N),
    "tall_grass":      ("vegetation", "Herbes hautes", (2, 2), False, False, N, N),
    "pumpkin_patch":   ("vegetation", "Carré de citrouilles", (4, 4), False, False, N, N),
    "stump":           ("vegetation", "Souche", (2, 2), True, False, L, N),
    "log":             ("vegetation", "Tronc couché", (4, 2), True, False, L, N),
    # Petit décor
    "mailbox":         ("props", "Boîte aux lettres", (2, 2), False, False, N, N),
    "street_lamp":     ("props", "Réverbère", (2, 2), False, False, N, N),
    "fire_hydrant":    ("props", "Bouche d'incendie", (2, 2), False, False, N, N),
    "garden_gnome":    ("props", "Nain de jardin", (2, 2), False, False, N, N),
    "lawn_flamingo":   ("props", "Flamant de jardin", (2, 2), False, False, N, N),
    "lawn_mower":      ("props", "Tondeuse", (2, 2), False, False, N, N),
    "traffic_cone":    ("props", "Plot de chantier", (2, 2), False, False, N, N),
    "bucket":          ("props", "Seau", (2, 2), False, False, N, N),
    "road_sign":       ("props", "Panneau stop", (2, 2), False, False, N, N),
    "garden_bench":    ("props", "Banc de jardin", (2, 2), True, False, L, N),
    "picnic_table":    ("props", "Table de pique-nique", (2, 2), True, False, L, N),
    "bbq_grill":       ("props", "Barbecue", (2, 2), True, False, N, N),
    "bird_bath":       ("props", "Bain d'oiseaux", (2, 2), True, False, N, N),
    "doghouse":        ("props", "Niche", (2, 2), True, False, L, N),
    "swing_set":       ("props", "Balançoire", (4, 2), True, False, N, N),
    "pool":            ("props", "Piscine", (6, 4), True, False, N, N),
    "garden_hose":     ("props", "Tuyau d'arrosage", (2, 2), False, False, N, N),
    "tombstone_small_a": ("props", "Petite stèle", (2, 2), True, False, L, N),
    "tombstone_small_b": ("props", "Croix de pierre", (2, 2), True, False, L, N),
    "tombstone_small_c": ("props", "Stèle brisée", (2, 2), True, False, L, N),
    "open_grave":      ("props", "Fosse ouverte", (2, 4), True, False, N, N),
    "coffin":          ("props", "Cercueil", (2, 2), True, False, L, N),
    "bone_pile":       ("props", "Tas d'os", (2, 2), False, False, N, N),
    # Points de jeu
    "capture_point":            ("gameplay", "Point stratégique", 5.0, False, False, N, N),
    "resource_point_primary":   ("gameplay", "Point de ressource principale", 5.0, False, False, N, "PRIMARY"),
    "resource_point_secondary": ("gameplay", "Point de ressource secondaire", 5.0, False, False, N, "SECONDARY"),
    "resource_point_tertiary":  ("gameplay", "Point de ressource tertiaire", 5.0, False, False, N, "TERTIARY"),
    # Bordures
    "border_hedge_straight": ("borders", "Haie de bordure", (8, 2), True, True, N, N),
    "border_hedge_corner":   ("borders", "Angle de haie de bordure", (2, 2), True, True, N, N),
    "border_fence_straight": ("borders", "Palissade de bordure", (8, 2), True, True, N, N),
}


def glb_height(path):
    """Hauteur (axe Y du glTF) : bornes POSITION des maillages + translations des nœuds."""
    with open(path, "rb") as f:
        data = f.read()
    length = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + length])
    nodes = gltf["nodes"]
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i

    def offset_y(i):
        y = 0.0
        while i is not None:
            y += nodes[i].get("translation", [0, 0, 0])[1]
            i = parent.get(i)
        return y
    top = 0.0
    for i, n in enumerate(nodes):
        if "mesh" not in n:
            continue
        for prim in gltf["meshes"][n["mesh"]]["primitives"]:
            acc = gltf["accessors"][prim["attributes"]["POSITION"]]
            top = max(top, acc["max"][1] + offset_y(i))
    return round(top, 2)


def fmt(v):
    return ("%.3f" % v).rstrip("0").rstrip(".") if v != int(v) else "%d.0" % v


def write_piece(pid, spec):
    cat, name, footprint, blocks, vision, cover, res = spec
    rel = "assets/environment/%s/%s.glb" % (cat, pid)
    height = glb_height(os.path.join(ROOT, rel))
    lines = ['[gd_resource type="Resource" script_class="EnvironmentPieceData" format=3]', "",
             '[ext_resource type="Script" path="res://data/environment/environment_piece_data.gd" id="1_script"]',
             '[ext_resource type="PackedScene" path="res://%s" id="2_scene"]' % rel, "", "[resource]",
             'script = ExtResource("1_script")', 'id = &"%s"' % pid, 'display_name = "%s"' % name,
             "category = %d" % ENUMS["Category"].index(CATEGORY[cat]), 'scene = ExtResource("2_scene")']
    if isinstance(footprint, float):
        lines += ["footprint_shape = 1", "footprint_size = Vector2(%s, %s)" % (fmt(2 * footprint), fmt(2 * footprint)),
                  "footprint_radius = %s" % fmt(footprint)]
    else:
        lines += ["footprint_size = Vector2(%s, %s)" % (fmt(footprint[0]), fmt(footprint[1]))]
    lines += ["height = %s" % fmt(height), "blocks_movement = %s" % str(blocks).lower(),
              "blocks_vision = %s" % str(vision).lower(), "cover = %d" % ENUMS["Cover"].index(cover),
              "resource = %d" % ENUMS["ResourceKind"].index(res)]
    with open(os.path.join(OUT, pid + ".tres"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return height


def write_catalog():
    ids = list(PIECES)
    lines = ['[gd_resource type="Resource" script_class="EnvironmentCatalog" format=3]', "",
             '[ext_resource type="Script" path="res://data/environment/environment_catalog.gd" id="1_script"]',
             '[ext_resource type="Script" path="res://data/environment/environment_piece_data.gd" id="2_piece"]']
    for i, pid in enumerate(ids):
        lines.append('[ext_resource type="Resource" path="res://data/environment/%s.tres" id="p%d"]' % (pid, i))
    lines += ["", "[resource]", 'script = ExtResource("1_script")',
              'pieces = Array[ExtResource("2_piece")]([%s])' % ", ".join('ExtResource("p%d")' % i for i in range(len(ids)))]
    with open(os.path.join(OUT, "environment_catalog.tres"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for pid, spec in PIECES.items():
        h = write_piece(pid, spec)
        print("%-26s %-12s %5.2f m" % (pid, spec[0], h))
    write_catalog()
    print("%d pièces" % len(PIECES))
