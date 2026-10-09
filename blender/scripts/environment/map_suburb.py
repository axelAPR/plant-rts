# plantRTS — Première carte complète : « Banlieue » (world/maps/suburb/).
# blender -b --python blender/scripts/environment/map_suburb.py
# (Blender sert seulement pour numpy ; aucun objet Blender n'est créé.)
#
# Carte 1 contre 1 de 160 × 160 m (bornes de la caméra), symétrique par rapport au
# centre (x, z) → (-x, -z) : plantes au sud (+Z), zombies au nord (-Z), comme le
# menu DEV. Deux rues est-ouest (z = ±20) et deux avenues nord-sud (x = ±36) ; une
# rangée de maisons de chaque côté ; parc central avec le point de capture ; deux
# terrains vagues avec les points de ressource tertiaire ; base de chaque camp avec
# sa ressource principale et un point de ressource secondaire ; bordure (haie au sud,
# palissade au nord) et une couronne d'arbres hors jeu qui ferme l'horizon.
#
# Écrit world/maps/suburb/suburb.tscn (décor, sol, ciel, systèmes de jeu repris de la
# carte de test) et world/maps/suburb/suburb_splat.png (mélange des sols : R herbe
# sèche, G chemin, B herbe morte, A sol corrompu ; 2 px/m sur 300 × 300 m).
# Coordonnées Godot : X vers l'est, Z vers le sud ; avant des modèles vers +Z.

import math, os, random, struct, sys, zlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from catalog import PIECES  # noqa: E402
from scenes_gen import Scene, xform  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT_DIR = os.path.join(ROOT, "world", "maps", "suburb")
RES_DIR = "res://world/maps/suburb/"

HALF = 80.0            # zone jouable : -80..80 m
TERRAIN = 300.0        # sol visible : -150..150 m
SPLAT_PX_PER_M = 2

# ---------------------------------------------------------------- Disposition

# Points de jeu côté plantes (le côté zombies est le symétrique).
POINTS_SOUTH = [("resource_point_primary", -18.0, 64.0, "PLANTS"),
                ("resource_point_secondary", 54.0, 64.0, "NEUTRAL")]
# Points partagés (placés une fois).
POINTS_SHARED = [("capture_point", 0.0, 0.0, "NEUTRAL"),
                 ("resource_point_tertiary", 56.0, 0.0, "NEUTRAL"),
                 ("resource_point_tertiary", -56.0, 0.0, "NEUTRAL")]

# Maisons du côté plantes : (id, x, décalage de la porte dans le modèle). Façade vers
# la rue (z = 20), donc rotation de 180° : porte en x - décalage.
HOUSES_SOUTH = [("house_b", -62, 0.0), ("house_a", -48, -2.0), ("house_two_story", -24, -2.2),
                ("house_a", -12, -2.0), ("house_b", 10, 0.0), ("house_two_story", 24, -2.2),
                ("corner_shop", 46, None), ("house_a", 60, -2.0)]
HOUSE_Z = 34.0
FENCE_Z = 26.0
# Clôtures avant : blocs (premier, dernier centre de segment ; pas de 4 m).
FENCE_BLOCKS = [(-66, -46), (-30, -6), (6, 30), (54, 66)]

# Variante zombie des pièces des lotissements (symétrique du côté plantes).
ZOMBIE_LOTS = {"house_a": "house_haunted", "tree_large": "tree_dead", "tree_small": "stump",
               "car_sedan": "car_wreck", "pickup_truck": "car_wreck", "bush_a": "tall_grass",
               "bush_b": "tall_grass", "flowerbed": "tall_grass", "flower_patch_a": "bone_pile",
               "flower_patch_b": "tall_grass", "flower_patch_c": "bone_pile",
               "garden_gnome": "tombstone_small_c", "lawn_flamingo": "bone_pile",
               "bird_bath": "tombstone_small_a", "lawn_mower": "wheelbarrow", "garden_hose": "bucket",
               "hedge_straight": "iron_fence_straight"}
# Moitié nord du parc : fleurs fanées.
ZOMBIE_PARK = {"flower_patch_a": "tall_grass", "flower_patch_c": "tall_grass", "bush_b": "bush_a"}


def lots_south():
    """Lotissements du côté plantes : maisons, clôtures, allées, jardins, rue."""
    items = []
    gates = set()
    for pid, x, door in HOUSES_SOUTH:
        items.append((pid, x, HOUSE_Z, 180))
        if door is None:
            continue
        gate = int(round((x - door) / 2.0)) * 2
        gates.add(gate)
        items.append(("path_straight", gate, 28.5, 90))
        items.append(("flowerbed", gate + 3.5, 28.5, 90))
        items.append(("mailbox", gate + 2.0, 23.6, 180))
    for first, last in FENCE_BLOCKS:
        for x in range(first, last + 1, 4):
            items.append(("picket_fence_gate" if x in gates else "picket_fence_straight", x, FENCE_Z, 0))
    # Jardins de devant.
    items += [("bush_a", -65.5, 28.6, 0), ("garden_gnome", -55, 29, 160), ("lawn_flamingo", -51, 29, 200),
              ("bush_a", -28, 28.6, 0), ("flower_patch_b", -25, 28.8, 0), ("bird_bath", -15, 28.8, 0),
              ("flower_patch_a", 6, 28.8, 0), ("bush_a", 17, 28.6, 0), ("flower_patch_c", 21, 28.8, 0),
              ("garden_gnome", 23, 29, 200), ("bush_b", 57, 28.6, 0), ("flower_patch_b", 59, 28.8, 0)]
    # Jardins de derrière (z 40..50) et haies mitoyennes.
    items += [("tree_large", -66, 45, 0), ("swing_set", -60, 43, 0), ("garden_shed", -47, 45, 180),
              ("tree_small", -42, 48, 0), ("pool", -25, 44, 0), ("bbq_grill", -21, 48, 30),
              ("tree_large", -11, 45, 0), ("doghouse", -6, 41, 200), ("lawn_mower", 7, 41, 70),
              ("picnic_table", 10, 45, 0), ("tree_large", 12, 48, 0), ("pool", 24, 44, 0),
              ("tree_small", 29, 48, 0), ("dumpster", 44, 41, 0), ("crate_stack", 47, 41.5, 15),
              ("barrel_group", 49.5, 43.5, 0), ("garden_hose", 57, 41, 0), ("tree_large", 63, 45, 0)]
    for z in (41, 45):
        items += [("hedge_straight", -18, z, 90), ("hedge_straight", 17, z, 90)]
    # Trottoir : lampadaires, bouche d'incendie, panneau ; voitures garées.
    items += [("street_lamp", -55, 23.6, 180), ("street_lamp", -18, 23.6, 180), ("street_lamp", 17, 23.6, 180),
              ("street_lamp", 53, 23.6, 180), ("fire_hydrant", -30.5, 23.6, 0), ("road_sign", 31, 23.6, 180),
              ("car_sedan", -52, 21.8, 180), ("pickup_truck", 18, 21.8, 0), ("car_sedan", 60, 21.8, 0),
              ("tree_small", -41, 40, 0), ("tree_small", 31, 40, 0), ("trash_cans", 41, 26, 0)]
    return items


def park_south():
    """Moitié sud du parc central (le point de capture est au centre)."""
    return [("sandbag_straight", -4.5, 8, 0), ("sandbag_straight", 4.5, 8, 0),
            ("stone_wall_broken", -10, 3, 90), ("stone_wall_straight", 9, 7, 45),
            ("tree_large", -20, 8, 0), ("tree_large", -26, 12, 30), ("tree_large", 14, 11, 60),
            ("tree_large", 25, 5, 0), ("tree_small", -8, 13, 0), ("tree_small", 29, 12, 0),
            ("garden_bench", -3, 11.5, 90), ("garden_bench", 3, 11.5, -90),
            ("street_lamp", -3, 14.8, 0), ("street_lamp", 3, 14.8, 0), ("trash_cans", -5.5, 14.8, 0),
            ("bird_bath", -18, 3, 0), ("picnic_table", 20, 10, 20), ("flower_patch_a", -14, 6, 0),
            ("flower_patch_c", 16, 3, 0), ("bush_a", -29, 4, 0), ("bush_b", -24, 15, 0),
            ("hedge_straight", -18, 15, 0), ("hedge_straight", -14, 15, 0),
            ("hedge_straight", 18, 15, 0), ("hedge_straight", 22, 15, 0)]


def field_east():
    """Terrain vague à l'est (point de ressource tertiaire en (56, 0)) ; l'ouest est
    son symétrique."""
    return [("rock_large", 46, 9, 0), ("rock_large", 63, -10, 40), ("car_wreck", 50, -8, 25),
            ("car_wreck", 65, 7, -70), ("concrete_barrier", 56, 8.5, 0), ("concrete_barrier", 56, -8.5, 0),
            ("hay_bale", 47, -3, 0), ("log", 60, 13, 10), ("stump", 44, -13, 0), ("tree_large", 67, 13, 0),
            ("tree_dead", 68, -13, 0), ("tall_grass", 52, 13, 0), ("tall_grass", 68, -4, 0),
            ("tall_grass", 42, 4, 0), ("traffic_cone", 41, -10, 0), ("traffic_cone", 42, -7.5, 30)]


def base_plants():
    """Base des plantes (sud) : serres, potager, massifs, arbres."""
    return [("greenhouse", 6, 62, 180), ("greenhouse", 12, 62, 180), ("greenhouse", 18, 62, 180),
            ("garden_shed", 26, 66, 180), ("planter_box", 6, 56.5, 0), ("planter_box", 12, 56.5, 0),
            ("planter_box", 18, 56.5, 0), ("hay_bale", -6, 60, 0), ("hay_bale", -8, 62, 20),
            ("wheelbarrow", -4, 66, 120), ("lawn_mower", -12, 56, 200),
            ("flowerbed", -32, 60, 0), ("flowerbed", -32, 64, 0), ("flowerbed", -32, 68, 0),
            ("flower_patch_a", -26, 56, 0), ("flower_patch_b", -10, 72, 0), ("flower_patch_c", 30, 58, 0),
            ("flower_patch_a", 40, 70, 0), ("flower_patch_b", -40, 57, 0),
            ("tree_large", -62, 60, 0), ("tree_large", -50, 70, 40), ("tree_large", -66, 72, 0),
            ("tree_large", 30, 74, 0), ("tree_large", 64, 74, 0), ("tree_large", 44, 57, 0),
            ("tree_small", -44, 64, 0), ("tree_small", -8, 75, 0), ("tree_small", 20, 72, 0),
            ("tree_small", 70, 58, 0), ("bush_b", -36, 72, 0), ("bush_a", 2, 74, 0), ("bush_a", 62, 56, 0),
            ("bush_b", -58, 55, 0), ("tall_grass", -70, 64, 0), ("tall_grass", 72, 66, 0),
            ("bird_bath", -26, 70, 0), ("garden_bench", -24, 74, 180), ("picnic_table", 36, 66, 0),
            ("stone_wall_straight", -18, 71, 0), ("stone_wall_end", -21, 71, 0), ("stone_wall_end", -15, 71, 180)]


def base_zombies():
    """Base des zombies (nord) : cimetière clôturé, crypte, tombes, arbres morts."""
    items = []
    # Cimetière : grille en fer forgé de x -33..-3, z -74..-56, portail au sud.
    for x in range(-30, -5, 4):
        items.append(("iron_fence_gate" if x == -18 else "iron_fence_straight", x, -56, 0))
        items.append(("iron_fence_straight", x, -74, 0))
    for z in (-59, -63, -67, -71):
        items += [("iron_fence_straight", -33, z, 90), ("iron_fence_straight", -3, z, 90)]
    items += [("iron_fence_corner", -33, -56, 180), ("iron_fence_corner", -3, -56, -90),
              ("iron_fence_corner", -33, -74, 90), ("iron_fence_corner", -3, -74, 0)]
    items += [("crypt", -18, -69, 0), ("tombstone_large", -29, -60, 0), ("tombstone_small_a", -25, -60, 0),
              ("tombstone_small_b", -11, -60, 0), ("tombstone_large", -7, -60, 0),
              ("tombstone_small_c", -29, -64, 0), ("tombstone_large", -25, -64, 0),
              ("tombstone_small_a", -11, -64, 0), ("tombstone_small_b", -7, -64, 0),
              ("open_grave", -27, -69, 0), ("coffin", -24, -70, 30), ("bone_pile", -10, -70, 0),
              ("tree_dead", -30, -71, 0), ("tree_dead", -6, -71, 120)]
    # Autour : arbres morts, citrouilles, épaves, débris.
    items += [("barrel_group", 8, -58, 0), ("crate_stack", 10, -61, 20), ("car_wreck", 30, -58, 20),
              ("trash_cans", 26, -55, 0), ("pumpkin_patch", 28, -70, 0), ("pumpkin_patch", 46, -74, 30),
              ("bone_pile", 34, -66, 0), ("open_grave", 60, -70, 0), ("concrete_barrier", 6, -70, 90),
              ("tree_dead", 40, -64, 0), ("tree_dead", 60, -58, 60), ("tree_dead", 66, -72, 0),
              ("tree_dead", -46, -70, 200), ("tree_dead", -66, -60, 0), ("stump", 50, -72, 0),
              ("log", -44, -58, 70), ("tall_grass", -60, -74, 0), ("tall_grass", 70, -62, 0),
              ("tall_grass", 46, -56, 0), ("tombstone_small_c", -40, -66, 0), ("tombstone_small_b", -62, -68, 0),
              ("tombstone_large", 20, -74, 0), ("dumpster", 64, -64, 0)]
    return items


def mirror(items, swap=None):
    swap = swap or {}
    return [(swap.get(pid, pid), -x, -z, yaw + 180) for pid, x, z, yaw in items]


# ---------------------------------------------------------------- Routes

def roads():
    items = []
    for z in (20, -20):
        for x in range(-68, 69, 8):
            if x == -68:
                items.append(("road_end", x, z, 180))
            elif x == 68:
                items.append(("road_end", x, z, 0))
            elif x in (-36, 36):
                items.append(("road_cross", x, z, 0))
            elif x == 0:
                items.append(("road_crosswalk", x, z, 0))
            else:
                items.append(("road_straight", x, z, 0))
    for x in (-36, 36):
        for z in (-12, -4, 4, 12, 28, 36, 44, -28, -36, -44):
            items.append(("road_straight", x, z, 90))
        items.append(("road_end", x, 52, -90))
        items.append(("road_end", x, -52, 90))
    return items


# ---------------------------------------------------------------- Bordure et horizon

def border():
    items = []
    for k in range(-74, 75, 8):
        items.append(("border_hedge_straight", k, 79, 0))
        items.append(("border_fence_straight", k, -79, 0))
        side = "border_hedge_straight" if k > 0 else "border_fence_straight"
        items.append((side, -79, k, 90))
        items.append((side, 79, k, 90))
    items += [("border_hedge_corner", 79, -79, 0), ("border_hedge_corner", -79, -79, 90),
              ("border_hedge_corner", -79, 79, 180), ("border_hedge_corner", 79, 79, -90)]
    return items


def horizon_trees():
    """Deux couronnes d'arbres hors de la zone jouable (déterministes)."""
    rnd = random.Random(7)
    items = []
    for dist, step in ((87.0, 9.0), (98.0, 13.0)):
        perimeter = 8 * dist
        n = int(perimeter / step)
        for i in range(n):
            t = (i + rnd.uniform(-0.3, 0.3)) / n * perimeter
            side, u = int(t // (2 * dist)), t % (2 * dist) - dist
            x, z = [(u, -dist), (dist, u), (-u, dist), (-dist, -u)][side]
            x += rnd.uniform(-2.5, 2.5)
            z += rnd.uniform(-2.5, 2.5)
            if z < -8:
                pid = "tree_dead"
            elif z > 8:
                pid = "tree_large" if rnd.random() < 0.7 else "tree_small"
            else:
                pid = rnd.choice(("tree_large", "tree_dead"))
            items.append((pid, round(x, 2), round(z, 2), rnd.uniform(0, 360)))
    return items


# ---------------------------------------------------------------- Carte des sols

def value_noise(xs, zs, cell, seed):
    """Bruit de valeur lissé (une octave) aux positions (xs, zs) en m."""
    rnd = np.random.default_rng(seed)
    n = int(TERRAIN / cell) + 3
    grid = rnd.random((n, n))
    gx = (xs + TERRAIN / 2) / cell
    gz = (zs + TERRAIN / 2) / cell
    ix, iz = np.floor(gx).astype(int), np.floor(gz).astype(int)
    fx, fz = gx - ix, gz - iz
    fx, fz = fx * fx * (3 - 2 * fx), fz * fz * (3 - 2 * fz)
    a = grid[iz, ix] * (1 - fx) + grid[iz, ix + 1] * fx
    b = grid[iz + 1, ix] * (1 - fx) + grid[iz + 1, ix + 1] * fx
    return a * (1 - fz) + b * fz


def fbm(xs, zs, cell, seed, octaves=3):
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total = total + value_noise(xs, zs, cell / (2 ** o), seed + o) * amp
        norm += amp
        amp *= 0.5
    return total / norm


def segment_distance(xs, zs, a, b):
    (ax, az), (bx, bz) = a, b
    dx, dz = bx - ax, bz - az
    t = np.clip(((xs - ax) * dx + (zs - az) * dz) / max(dx * dx + dz * dz, 1e-9), 0, 1)
    return np.hypot(xs - (ax + t * dx), zs - (az + t * dz))


# Chemins de terre côté plantes (polylignes, largeur en m) ; le nord est symétrique.
PATHS_SOUTH = [
    ([(0, 24), (0, 56), (-12, 62)], 3.2),          # allée centrale vers la ressource principale
    ([(0, 56), (6, 58), (20, 58)], 2.6),           # vers les serres
    ([(0, 16), (0, 5)], 3.0),                      # parc : rue → point de capture
    ([(-32, 0), (-5, 0)], 2.6),                    # parc : avenue → point de capture
    ([(40, 1), (51, 0)], 2.8),                     # terrain vague → ressource tertiaire
    ([(36, 56), (42, 60), (49, 63)], 2.8),         # avenue → ressource secondaire
    ([(-55, 24), (-55, 40), (-54, 56), (-30, 62)], 2.4),
    ([(52.5, 24), (52.5, 40), (54, 59)], 2.4),
]


def splat_map():
    n = int(TERRAIN * SPLAT_PX_PER_M)
    coords = -TERRAIN / 2 + (np.arange(n) + 0.5) / SPLAT_PX_PER_M
    xs, zs = np.meshgrid(coords, coords)            # ligne = z croissant (v de l'UV)
    noise_a = fbm(xs, zs, 28.0, 11)
    noise_b = fbm(xs, zs, 9.0, 23)
    noise_c = fbm(xs, zs, 16.0, 37)

    # B : herbe morte au nord, frontière irrégulière un peu au sud du centre.
    dead = np.clip((2.0 - zs + (noise_a - 0.5) * 30.0) / 6.0, 0, 1)

    # R : herbe sèche dans la bande centrale et les terrains vagues, taches ailleurs.
    band = np.exp(-(zs / 24.0) ** 2)
    fields = np.clip((np.minimum(np.abs(xs) - 40.0, 18.0 - np.abs(zs)) + (noise_a - 0.5) * 16.0) / 4.0, 0, 1)
    dry = np.clip((noise_b * 0.9 + band * 0.45 + fields * 0.35 - 0.78) * 5.0, 0, 1)

    # A : sol corrompu autour de la base zombie, du cimetière et en taches au nord.
    corrupt = np.clip((-zs - 58.0) / 8.0 + (noise_c - 0.5) * 2.2, 0, 1)
    graveyard = (xs > -34) & (xs < -2) & (zs > -75) & (zs < -55)
    corrupt = np.maximum(corrupt, graveyard * np.clip(0.8 + noise_b, 0, 1))
    corrupt = np.maximum(corrupt, np.clip((14.0 - np.hypot(xs - 18, zs + 64)) / 5.0, 0, 1))
    corrupt = np.maximum(corrupt, np.clip((noise_c - 0.76) * 8.0, 0, 1) * (zs < -30))
    corrupt *= np.clip((-zs - 10.0) / 10.0, 0, 1)

    # G : chemins, anneaux autour des points, terre battue des bases.
    path = np.zeros_like(xs)
    edge = (noise_b - 0.5) * 1.4
    for poly, width in PATHS_SOUTH:
        for sign in (1, -1):
            pts = [(sign * x, sign * z) for x, z in poly]
            for a, b in zip(pts, pts[1:]):
                d = segment_distance(xs, zs, a, b)
                path = np.maximum(path, np.clip((width / 2 - d + edge) / 0.6 + 0.5, 0, 1))
    points = [(x, z) for _, x, z, _ in POINTS_SOUTH] + [(-x, -z) for _, x, z, _ in POINTS_SOUTH]
    points += [(x, z) for _, x, z, _ in POINTS_SHARED]
    for px, pz in points:
        d = np.hypot(xs - px, zs - pz)
        path = np.maximum(path, np.clip((7.5 - d + edge * 1.5) / 1.2, 0, 1))
    for cx, cz, rx, rz in ((12, 60, 10, 6), (-12, -60, 0, 0)):
        if rx:
            d = np.maximum(np.abs(xs - cx) / rx, np.abs(zs - cz) / rz)
            path = np.maximum(path, np.clip((1.0 - d) * 4.0 + edge, 0, 1))

    rgba = np.stack([dry, path, dead, corrupt], axis=-1)
    return (np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8)


def write_png(path, rgba):
    h, w, _ = rgba.shape
    raw = b"".join(b"\x00" + rgba[y].tobytes() for y in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------- Scène

GROUND_TEXTURES = (("grass_texture", "grass"), ("dry_texture", "grass_dry"), ("path_texture", "dirt_path"),
                   ("dead_texture", "grass_dead"), ("corrupted_texture", "corrupted"))

# Systèmes de jeu, repris de world/maps/test_map/test_map.tscn (mêmes liaisons).
SYSTEMS_EXT = [
    ("Script", "res://data/units/squad_data.gd", "sys_squad_data"),
    ("Script", "res://data/factions/faction_data.gd", "sys_faction_data"),
    ("Script", "res://gameplay/units/unit_simulation.gd", "sys_sim"),
    ("Script", "res://gameplay/commands/order_system.gd", "sys_orders"),
    ("Script", "res://player/selection_controller.gd", "sys_selection"),
    ("Script", "res://player/command_controller.gd", "sys_commands"),
    ("Script", "res://gameplay/units/unit_renderer.gd", "sys_renderer"),
    ("Script", "res://gameplay/combat/combat_system.gd", "sys_combat"),
    ("Script", "res://gameplay/combat/projectile_renderer.gd", "sys_projectiles"),
    ("Script", "res://gameplay/economy/production_system.gd", "sys_production"),
    ("Script", "res://gameplay/economy/economy.gd", "sys_economy"),
    ("Script", "res://ui/selection_box.gd", "sys_box"),
    ("Script", "res://ui/dev_menu.gd", "sys_dev_menu"),
    ("Script", "res://ui/resource_bar.gd", "sys_resource_bar"),
    ("Script", "res://ui/unit_info_panel.gd", "sys_info"),
    ("Resource", "res://data/factions/plants.tres", "sys_plants"),
    ("Resource", "res://data/factions/zombies.tres", "sys_zombies"),
]
PLANT_SQUADS = ("peashooter", "sunflower", "kernel_corn", "cactus", "rose", "chomper", "citron", "torchwood")
ZOMBIE_SQUADS = ("browncoat", "foot_soldier", "engineer", "scientist", "imp", "deadbeard", "all_star",
                 "super_brainz", "action_hero_80s", "z_mech")

FULL_RECT = 'layout_mode = 3\nanchors_preset = 15\nanchor_right = 1.0\nanchor_bottom = 1.0\n' \
            'grow_horizontal = 2\ngrow_vertical = 2\nmouse_filter = 2'


def systems_nodes():
    squads = lambda ids: ", ".join('ExtResource("sq_%s")' % i for i in ids)  # noqa: E731
    return """[node name="UnitSimulation" type="Node" parent="."]
script = ExtResource("sys_sim")

[node name="OrderSystem" type="Node" parent="." node_paths=PackedStringArray("simulation")]
script = ExtResource("sys_orders")
simulation = NodePath("../UnitSimulation")

[node name="SelectionController" type="Node" parent="." node_paths=PackedStringArray("simulation", "camera_rig", "selection_box")]
script = ExtResource("sys_selection")
simulation = NodePath("../UnitSimulation")
camera_rig = NodePath("../RTSCamera")
selection_box = NodePath("../HUD/SelectionBox")
team = -1

[node name="CommandController" type="Node" parent="." node_paths=PackedStringArray("selection", "order_system", "camera_rig")]
script = ExtResource("sys_commands")
selection = NodePath("../SelectionController")
order_system = NodePath("../OrderSystem")
camera_rig = NodePath("../RTSCamera")

[node name="UnitRenderer" type="Node3D" parent="." node_paths=PackedStringArray("simulation", "selection")]
script = ExtResource("sys_renderer")
simulation = NodePath("../UnitSimulation")
selection = NodePath("../SelectionController")

[node name="CombatSystem" type="Node" parent="." node_paths=PackedStringArray("simulation")]
script = ExtResource("sys_combat")
simulation = NodePath("../UnitSimulation")

[node name="ProjectileRenderer" type="MultiMeshInstance3D" parent="." node_paths=PackedStringArray("combat")]
script = ExtResource("sys_projectiles")
combat = NodePath("../CombatSystem")

[node name="ProductionSystem" type="Node" parent="." node_paths=PackedStringArray("economy", "simulation")]
script = ExtResource("sys_production")
economy = NodePath("../Economy")
simulation = NodePath("../UnitSimulation")

[node name="Economy" type="Node" parent="."]
script = ExtResource("sys_economy")
factions = Array[ExtResource("sys_faction_data")]([ExtResource("sys_plants"), ExtResource("sys_zombies")])

[node name="HUD" type="CanvasLayer" parent="."]

[node name="SelectionBox" type="Control" parent="HUD"]
%(rect)s
script = ExtResource("sys_box")

[node name="DevMenu" type="Control" parent="HUD" node_paths=PackedStringArray("simulation", "camera_rig")]
%(rect)s
script = ExtResource("sys_dev_menu")
simulation = NodePath("../../UnitSimulation")
camera_rig = NodePath("../../RTSCamera")
plant_squads = Array[ExtResource("sys_squad_data")]([%(plants)s])
zombie_squads = Array[ExtResource("sys_squad_data")]([%(zombies)s])

[node name="ResourceBar" type="Control" parent="HUD" node_paths=PackedStringArray("economy")]
%(rect)s
script = ExtResource("sys_resource_bar")
economy = NodePath("../../Economy")
teams = Array[int]([0, 1])

[node name="UnitInfoPanel" type="Control" parent="HUD" node_paths=PackedStringArray("selection")]
%(rect)s
script = ExtResource("sys_info")
selection = NodePath("../../SelectionController")
""" % {"rect": FULL_RECT, "plants": squads(PLANT_SQUADS), "zombies": squads(ZOMBIE_SQUADS)}


def write_scene(sc, path):
    cam = sc.res("res://camera/rts_camera.tscn")
    lines = ['[gd_scene format=3]', '']
    for p, (kind, rid) in sc.ext.items():
        lines.append('[ext_resource type="%s" path="%s" id="%s"]' % (kind, p, rid))
    for kind, p, rid in SYSTEMS_EXT:
        lines.append('[ext_resource type="%s" path="%s" id="%s"]' % (kind, p, rid))
    for sid in PLANT_SQUADS + ZOMBIE_SQUADS:
        lines.append('[ext_resource type="Resource" path="res://data/units/%s_squad.tres" id="sq_%s"]' % (sid, sid))
    lines += ['[ext_resource type="Shader" path="res://assets/shaders/stylized_sky.gdshader" id="sky_shader"]',
              '[ext_resource type="Shader" path="res://assets/shaders/terrain_splat.gdshader" id="ground_shader"]',
              '[ext_resource type="Texture2D" path="%ssuburb_splat.png" id="ground_splat"]' % RES_DIR]
    for param, name in GROUND_TEXTURES:
        lines.append('[ext_resource type="Texture2D" path="res://assets/textures/ground/%s.png" id="tex_%s"]'
                     % (name, name))
    half_t = TERRAIN / 2
    lines += ['',
              '[sub_resource type="FastNoiseLite" id="cloud_noise"]', 'frequency = 0.004', 'fractal_octaves = 4', '',
              '[sub_resource type="FastNoiseLite" id="macro_noise"]', 'seed = 5', 'frequency = 0.012',
              'fractal_octaves = 2', '',
              '[sub_resource type="NoiseTexture2D" id="macro_texture"]', 'width = 256', 'height = 256',
              'seamless = true', 'normalize = true', 'noise = SubResource("macro_noise")', '',
              '[sub_resource type="NoiseTexture2D" id="cloud_texture"]', 'width = 512', 'height = 512',
              'seamless = true', 'noise = SubResource("cloud_noise")', '',
              '[sub_resource type="ShaderMaterial" id="sky_material"]', 'shader = ExtResource("sky_shader")',
              'shader_parameter/cloud_noise = SubResource("cloud_texture")', '',
              '[sub_resource type="Sky" id="sky"]', 'sky_material = SubResource("sky_material")', '',
              '[sub_resource type="Environment" id="environment"]', 'background_mode = 2', 'sky = SubResource("sky")',
              'ambient_light_source = 3', 'ambient_light_energy = 1.1', 'tonemap_mode = 2',
              'fog_enabled = true', 'fog_light_color = Color(0.66, 0.84, 0.95, 1)', 'fog_density = 0.0008',
              'fog_sky_affect = 0.0', '',
              '[sub_resource type="ShaderMaterial" id="ground_material"]', 'shader = ExtResource("ground_shader")',
              'shader_parameter/splat_map = ExtResource("ground_splat")',
              'shader_parameter/macro_noise = SubResource("macro_texture")']
    for param, name in GROUND_TEXTURES:
        lines.append('shader_parameter/%s = ExtResource("tex_%s")' % (param, name))
    lines += ['shader_parameter/map_origin = Vector2(%g, %g)' % (-half_t, -half_t),
              'shader_parameter/map_size = Vector2(%g, %g)' % (TERRAIN, TERRAIN), '',
              '[sub_resource type="PlaneMesh" id="ground_mesh"]', 'material = SubResource("ground_material")',
              'size = Vector2(%g, %g)' % (TERRAIN, TERRAIN), '',
              '[sub_resource type="BoxShape3D" id="ground_shape"]', 'size = Vector3(%g, 1, %g)' % (TERRAIN, TERRAIN), '',
              '[node name="%s" type="Node3D"]' % sc.root, '',
              '[node name="WorldEnvironment" type="WorldEnvironment" parent="."]', 'environment = SubResource("environment")', '',
              '[node name="Sun" type="DirectionalLight3D" parent="."]',
              'transform = Transform3D(0.866025, -0.383022, 0.321394, 0, 0.642788, 0.766044, -0.5, -0.663414, 0.55667, 0, 20, 0)',
              'light_color = Color(1, 0.97, 0.9, 1)', 'shadow_enabled = true', 'directional_shadow_max_distance = 150.0', '',
              '[node name="Ground" type="StaticBody3D" parent="."]', '',
              '[node name="Mesh" type="MeshInstance3D" parent="Ground"]',
              'transform = %s' % xform(0, 0, 0, -0.02), 'mesh = SubResource("ground_mesh")', '',
              '[node name="Collision" type="CollisionShape3D" parent="Ground"]',
              'transform = %s' % xform(0, 0, 0, -0.5), 'shape = SubResource("ground_shape")', '',
              '[node name="RTSCamera" parent="." instance=ExtResource("%s")]' % cam,
              'transform = %s' % xform(0, 40),
              'bounds = Rect2(%g, %g, %g, %g)' % (-HALF, -HALF, 2 * HALF, 2 * HALF), '']
    for node in sc.nodes:
        lines += [node, '']
    lines.append(systems_nodes())
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def check_overlaps(groups):
    """Signale les emprises qui se chevauchent (rectangles alignés, rotation par pas de
    90° ; les autres rotations prennent le carré englobant). Bordure et horizon exclus."""
    boxes = []
    for name, items in groups:
        for pid, x, z, yaw in items:
            fp = PIECES[pid][2]
            w, d = (2 * fp, 2 * fp) if isinstance(fp, float) else fp
            q = round(yaw / 90.0) * 90
            if abs(yaw - q) > 1:
                w = d = max(w, d)
            elif q % 180:
                w, d = d, w
            boxes.append((pid, name, x - w / 2, x + w / 2, z - d / 2, z + d / 2))
    problems = []
    ground = {p for p in PIECES if PIECES[p][0] == "ground"}
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if a[0] in ground or b[0] in ground:
                continue
            ox = min(a[3], b[3]) - max(a[2], b[2])
            oz = min(a[5], b[5]) - max(a[4], b[4])
            if ox > 0.3 and oz > 0.3:
                problems.append("%s (%s) / %s (%s) : %.1f × %.1f m" % (a[0], a[1], b[0], b[1], ox, oz))
    return problems


def build():
    sc = Scene("Suburb", (TERRAIN, TERRAIN))
    groups = [
        ("Roads", roads()),
        ("LotsPlants", lots_south()),
        ("LotsZombies", mirror(lots_south(), ZOMBIE_LOTS)),
        ("Park", park_south() + mirror(park_south(), ZOMBIE_PARK)),
        ("Fields", field_east() + mirror(field_east())),
        ("BasePlants", base_plants()),
        ("BaseZombies", base_zombies()),
    ]
    decor_groups = list(groups)
    groups += [("Border", border()), ("Horizon", horizon_trees())]
    for name, items in groups:
        grp = sc.group(name)
        for pid, x, z, yaw in items:
            sc.piece(grp, pid, x, z, yaw)
    points = sc.group("Points")
    for pid, x, z, state in POINTS_SOUTH:
        sc.point(points, pid, x, z, state)
        sc.point(points, pid, -x, -z, {"PLANTS": "ZOMBIES"}.get(state, state), 180)
    for pid, x, z, state in POINTS_SHARED:
        sc.point(points, pid, x, z, state)
    point_items = [(pid, x, z, 0) for pid, x, z, _ in POINTS_SOUTH + POINTS_SHARED]
    point_items += [(pid, -x, -z, 0) for pid, x, z, _ in POINTS_SOUTH]

    os.makedirs(OUT_DIR, exist_ok=True)
    write_png(os.path.join(OUT_DIR, "suburb_splat.png"), splat_map())
    write_scene(sc, os.path.join(OUT_DIR, "suburb.tscn"))
    count = sum(len(items) for _, items in groups)
    print("Carte écrite : %d pièces de décor, %d points" % (count, len(point_items)))
    for problem in check_overlaps(decor_groups + [("Points", point_items)]):
        print("  CHEVAUCHEMENT", problem)


if __name__ == "__main__":
    build()
