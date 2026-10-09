# plantRTS — Carte « Banlieue » (world/maps/suburb/).
# blender -b --python blender/scripts/environment/map_suburb.py
# (Blender sert seulement pour numpy ; aucun objet Blender n'est créé.)
#
# Carte 1 contre 1 de 320 × 320 m (bornes de la caméra), sans symétrie : plantes au
# sud (+Z), zombies au nord (-Z), comme le menu DEV. Quartiers :
#   - sud-ouest : lotissement des plantes (rue z = 60, impasse x = -44) ;
#   - sud : base des plantes (serres, potager, ressource principale) ;
#   - sud-est : ferme et verger (ressource secondaire neutre) ;
#   - ouest : forêt avec une clairière (ressource tertiaire) ;
#   - centre : parc (point de capture) au sud du boulevard, terrain vague au nord ;
#   - est : commerces et parking (second point de capture) le long du boulevard ;
#   - nord-est : casse automobile (ressource tertiaire) et base des zombies
#     (cimetière, cryptes, ressource principale) ;
#   - nord : lotissement des zombies (rue z = -60) et vieux parc abandonné
#     (ressource secondaire).
# Routes sur une grille de 8 m : chaque case choisit sa tuile (droite, T, croisement,
# impasse) d'après ses voisines. Les pièces sont posées avec un contrôle d'emprise
# (aucun chevauchement) ; les maisons sont alignées sur les rues, les jardins, la
# forêt et le petit décor sont tirés au hasard (graine fixe : carte reproductible).
#
# Écrit world/maps/suburb/suburb.tscn (décor, sol, ciel, systèmes de jeu repris de la
# carte de test) et world/maps/suburb/suburb_splat.png (mélange des sols : R herbe
# sèche, G chemin, B herbe morte, A sol corrompu ; 2 px/m).
# Coordonnées Godot : X vers l'est, Z vers le sud ; avant des modèles vers +Z.

import os, random, struct, sys, zlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from catalog import PIECES  # noqa: E402
from scenes_gen import Scene, xform  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT_DIR = os.path.join(ROOT, "world", "maps", "suburb")
RES_DIR = "res://world/maps/suburb/"

HALF = 160.0           # zone jouable : -160..160 m
TERRAIN = 460.0        # sol visible : -230..230 m
SPLAT_PX_PER_M = 2
SEED = 2026

# ---------------------------------------------------------------- Points de jeu

POINTS = [
    ("capture_point", -44.0, 30.0, "NEUTRAL"),              # parc central
    ("capture_point", 112.0, 24.0, "NEUTRAL"),              # parking des commerces
    ("resource_point_primary", 36.0, 124.0, "PLANTS"),      # base des plantes
    ("resource_point_primary", 64.0, -122.0, "ZOMBIES"),    # base des zombies
    ("resource_point_secondary", -112.0, 104.0, "NEUTRAL"), # jardins du sud-ouest
    ("resource_point_secondary", 132.0, 76.0, "NEUTRAL"),   # ferme
    ("resource_point_secondary", -40.0, -108.0, "NEUTRAL"), # vieux parc
    ("resource_point_tertiary", -134.0, -28.0, "NEUTRAL"),  # clairière
    ("resource_point_tertiary", 128.0, -36.0, "NEUTRAL"),   # casse
]
POINT_CLEARANCE = 6.5  # demi-côté gardé libre autour d'un point (disque de 5 m)

# ---------------------------------------------------------------- Routes (grille 8 m)

# Polylignes de centres de cases (multiples de 8 + 4), parcourues case par case.
ROADS = [
    [(-148, 4), (148, 4)],          # boulevard est-ouest
    [(-84, -100), (-84, 92)],       # route ouest
    [(-4, -60), (-4, 60)],          # rue centrale
    [(76, -92), (76, 92)],          # route est
    [(-132, 60), (76, 60)],         # rue des plantes
    [(-84, -60), (140, -60)],       # rue des zombies
    [(-44, 60), (-44, 100)],        # impasse des plantes
    [(36, -60), (36, -92)],         # impasse des zombies
]
CROSSWALKS = {(-36, 4), (-52, 4), (108, 4), (-12, 60), (-4, -52)}


def road_cells():
    cells = set()
    for poly in ROADS:
        for (ax, az), (bx, bz) in zip(poly, poly[1:]):
            n = int(max(abs(bx - ax), abs(bz - az)) / 8)
            for k in range(n + 1):
                cells.add((ax + (bx - ax) * k // n, az + (bz - az) * k // n))
    return cells


def road_tiles(cells):
    """Tuile et rotation de chaque case d'après ses voisines (N = -Z)."""
    tiles = []
    for x, z in sorted(cells):
        n, s, e, w = (x, z - 8) in cells, (x, z + 8) in cells, (x + 8, z) in cells, (x - 8, z) in cells
        count = n + s + e + w
        if count == 4:
            tiles.append(("road_cross", x, z, 0))
        elif count == 3:
            yaw = 0 if not n else 180 if not s else 90 if not w else -90
            tiles.append(("road_t", x, z, yaw))
        elif count == 2 and e and w:
            tiles.append(("road_crosswalk" if (x, z) in CROSSWALKS else "road_straight", x, z, 0))
        elif count == 2 and n and s:
            tiles.append(("road_crosswalk" if (x, z) in CROSSWALKS else "road_straight", x, z, 90))
        elif count == 1:
            yaw = 0 if w else 180 if e else -90 if n else 90
            tiles.append(("road_end", x, z, yaw))
        else:
            raise ValueError("case de route sans tuile possible (virage ?) : %s" % ((x, z),))
    return tiles


# ---------------------------------------------------------------- Emprises

def footprint_rect(pid, x, z, yaw, margin=0.0):
    fp = PIECES[pid][2]
    w, d = (2 * fp, 2 * fp) if isinstance(fp, float) else fp
    q = round(yaw / 90.0) * 90
    if abs(yaw - q) > 1:
        w = d = max(w, d) * 1.15
    elif q % 180:
        w, d = d, w
    return (x - w / 2 - margin, x + w / 2 + margin, z - d / 2 - margin, z + d / 2 + margin)


class Layout:
    """Pièces posées et emprises occupées (rectangles alignés sur les axes)."""

    def __init__(self):
        self.items = []
        self.rects = []
        self.rejected = []

    def free(self, rect):
        x0, x1, z0, z1 = rect
        if x0 < -HALF + 2 or x1 > HALF - 2 or z0 < -HALF + 2 or z1 > HALF - 2:
            return False
        for a0, a1, b0, b1 in self.rects:
            if x0 < a1 - 0.05 and x1 > a0 + 0.05 and z0 < b1 - 0.05 and z1 > b0 + 0.05:
                return False
        return True

    def reserve(self, rect):
        self.rects.append(rect)

    def put(self, group, pid, x, z, yaw=0.0, check=True, margin=0.0, report=True):
        rect = footprint_rect(pid, x, z, yaw)
        if check and not self.free(footprint_rect(pid, x, z, yaw, margin)):
            if report:
                self.rejected.append("%s (%s) en (%.1f, %.1f)" % (pid, group, x, z))
            return False
        self.items.append((group, pid, round(x, 2), round(z, 2), round(yaw, 1)))
        if PIECES[pid][0] != "ground":
            self.reserve(rect)
        return True


# ---------------------------------------------------------------- Thèmes

DOORS = {"house_a": -2.0, "house_b": 0.0, "house_two_story": -2.2, "house_haunted": -1.6}
THEMES = {
    "plants": {
        "houses": ["house_a", "house_b", "house_two_story", "house_a", "house_b"],
        "fence": ["picket_fence_straight"], "gate": "picket_fence_gate", "fence_chance": 0.85,
        "front": ["bush_a", "bush_b", "flower_patch_a", "flower_patch_b", "flower_patch_c", "garden_gnome",
                  "lawn_flamingo", "bird_bath", "planter_box"],
        "back": ["tree_large", "tree_small", "pool", "swing_set", "garden_shed", "bbq_grill", "picnic_table",
                 "doghouse", "lawn_mower", "garden_hose", "tree_large", "bush_a", "flower_patch_b"],
        "street": ["car_sedan", "pickup_truck", "car_sedan"],
    },
    "zombies": {
        "houses": ["house_haunted", "house_b", "house_haunted", "house_two_story", "house_haunted"],
        "fence": ["picket_fence_broken", "picket_fence_straight", "picket_fence_broken"],
        "gate": "picket_fence_gate", "fence_chance": 0.7,
        "front": ["tall_grass", "bone_pile", "tombstone_small_a", "tombstone_small_b", "tombstone_small_c",
                  "bucket", "tall_grass"],
        "back": ["tree_dead", "stump", "pool", "swing_set", "garden_shed", "open_grave", "coffin", "car_wreck",
                 "trash_cans", "barrel_group", "pumpkin_patch", "tree_dead", "tall_grass"],
        "street": ["car_wreck", "car_sedan", "car_wreck"],
    },
    "shops": {
        "houses": ["corner_shop", "garage", "corner_shop", "garage", "corner_shop"],
        "fence": [], "gate": None, "fence_chance": 0.0,
        "front": ["trash_cans", "road_sign", "fire_hydrant", "street_lamp"],
        "back": ["dumpster", "crate_stack", "barrel_group", "trash_cans", "pickup_truck", "car_sedan"],
        "street": ["car_sedan", "pickup_truck", "car_sedan"],
    },
}


def frame(axis, c0, side, u, v):
    """Repère d'une rangée : u le long de la rue, v en s'éloignant de la rue (côté
    `side` = ±1). Renvoie (x, z) monde."""
    return (u, c0 + side * v) if axis == "x" else (c0 + side * v, u)


def facing(axis, side):
    """Rotation d'une façade tournée vers la rue."""
    if axis == "x":
        return 180 if side > 0 else 0
    return -90 if side > 0 else 90


def door_sign(axis, side):
    """Sens, le long de u, de l'axe X du modèle une fois tourné vers la rue."""
    return {180: -1, 0: 1, -90: 1, 90: -1}[facing(axis, side)]


def house_row(L, rnd, group, theme, axis, c0, side, u_from, u_to, parked=0.3):
    """Rangée de maisons le long d'une rue (axe `axis` = "x" pour une rue est-ouest
    à z = c0, "z" pour une rue nord-sud à x = c0), côté `side` (±1)."""
    t = THEMES[theme]
    yaw = facing(axis, side)
    along = 0 if axis == "x" else 90          # pièce posée le long de la rue
    across = 90 - along                        # allée perpendiculaire à la rue
    u = u_from + rnd.uniform(0, 4)
    while u < u_to:
        pid = rnd.choice(t["houses"])
        w = PIECES[pid][2][0]
        hu = u + w / 2
        door = DOORS.get(pid)
        dw = hu
        if door is not None:
            dw = hu + door_sign(axis, side) * door
            snapped = round((dw - 2) / 4) * 4 + 2     # portail sur la grille des piquets
            hu += snapped - dw
            dw = snapped
        lot = [frame(axis, c0, side, a, b) for a, b in ((hu - w / 2 - 1, 5), (hu + w / 2 + 1, 28))]
        rect = (min(p[0] for p in lot), max(p[0] for p in lot), min(p[1] for p in lot), max(p[1] for p in lot))
        if hu + w / 2 > u_to or not L.free(rect):
            u += 4
            continue
        hx, hz = frame(axis, c0, side, hu, 14)
        L.put(group, pid, hx, hz, yaw)
        if door is not None and rnd.random() < t["fence_chance"]:
            for k in (-4, 0, 4):
                fid = t["gate"] if k == 0 else rnd.choice(t["fence"])
                fx, fz = frame(axis, c0, side, dw + k, 6)
                L.put(group, fid, fx, fz, along, report=False)
        if door is not None:
            px, pz = frame(axis, c0, side, dw, 8.5)
            L.put(group, "path_straight", px, pz, across, check=False)
            mx, mz = frame(axis, c0, side, dw + 2, 3.6)
            L.put(group, "mailbox", mx, mz, yaw, check=False)
        for _ in range(rnd.randint(1, 2)):
            fu = hu + rnd.choice((-1, 1)) * rnd.uniform(2.0, w / 2 - 0.5)
            fx, fz = frame(axis, c0, side, fu, 8.8)
            L.put(group, rnd.choice(t["front"]), fx, fz, rnd.uniform(0, 360) if theme != "shops" else yaw,
                  report=False)
        for _ in range(rnd.randint(2, 4)):
            bu = hu + rnd.uniform(-w / 2, w / 2)
            bx, bz = frame(axis, c0, side, bu, rnd.uniform(21, 26))
            L.put(group, rnd.choice(t["back"]), bx, bz, rnd.choice((0, 90, 180, 270)), margin=0.5, report=False)
        if rnd.random() < parked:
            cx, cz = frame(axis, c0, side, hu + rnd.uniform(-3, 3), 1.8)
            L.put(group, rnd.choice(t["street"]), cx, cz, along + rnd.choice((0, 180)), check=False)
        u = hu + w / 2 + rnd.uniform(3, 8)


# ---------------------------------------------------------------- Quartiers

def iron_enclosure(L, group, x0, x1, z0, z1, gate_x=None):
    """Grille en fer forgé rectangulaire, coins en (x0, z0)…(x1, z1) ; segments de 4 m
    centrés à 3 m des coins (règle du kit). Portail au sud (z1) en x = gate_x."""
    for x in range(int(x0) + 3, int(x1) - 2, 4):
        L.put(group, "iron_fence_gate" if x == gate_x else "iron_fence_straight", x, z1, 0)
        L.put(group, "iron_fence_straight", x, z0, 0)
    for z in range(int(z0) + 3, int(z1) - 2, 4):
        L.put(group, "iron_fence_straight", x0, z, 90)
        L.put(group, "iron_fence_straight", x1, z, 90)
    L.put(group, "iron_fence_corner", x0, z1, 180)
    L.put(group, "iron_fence_corner", x1, z1, -90)
    L.put(group, "iron_fence_corner", x0, z0, 90)
    L.put(group, "iron_fence_corner", x1, z0, 0)


def place_all(L, group, items):
    for pid, x, z, yaw in items:
        L.put(group, pid, x, z, yaw)


def landmarks(L):
    # Base des plantes : serres, potager, massifs, muret.
    place_all(L, "BasePlants", [("greenhouse", x, 118, 180) for x in (50, 56, 62, 68)]
              + [("planter_box", x, 112.5, 0) for x in (50, 56, 62, 68)]
              + [("garden_shed", 76, 132, 180), ("garden_shed", 14, 140, 90), ("hay_bale", 22, 112, 0),
                 ("hay_bale", 20, 115, 25), ("wheelbarrow", 26, 136, 120), ("lawn_mower", 46, 136, 200),
                 ("flowerbed", 8, 120, 90), ("flowerbed", 8, 126, 90), ("flowerbed", 8, 132, 90),
                 ("stone_wall_straight", 34, 134, 0), ("stone_wall_end", 31, 134, 0),
                 ("stone_wall_end", 37, 134, 180), ("garden_bench", 42, 140, 180), ("bird_bath", 30, 142, 0),
                 ("picnic_table", 60, 140, 15), ("sandbag_straight", 24, 122, 90)])
    # Base des zombies : grand cimetière, cryptes, tombes.
    iron_enclosure(L, "BaseZombies", 87, 129, -149, -111, gate_x=106)
    tombs = ("tombstone_large", "tombstone_small_a", "tombstone_small_b", "tombstone_small_c")
    place_all(L, "BaseZombies", [("crypt", 98, -138, 0), ("crypt", 118, -138, 0), ("crypt", 52, -136, 0)]
              + [(tombs[(i + j) % 4], x, z, 0) for i, x in enumerate(range(92, 126, 4))
                 for j, z in enumerate((-126, -120)) if x not in (106, 110)]
              + [("open_grave", 108, -131, 0), ("open_grave", 92, -132, 0), ("coffin", 111, -133, 30),
                 ("bone_pile", 104, -144, 0), ("tree_dead", 91, -145, 0), ("tree_dead", 125, -115, 90),
                 ("tree_dead", 125, -145, 200), ("pumpkin_patch", 72, -140, 0), ("pumpkin_patch", 40, -146, 30),
                 ("barrel_group", 50, -112, 0), ("crate_stack", 54, -110, 20), ("car_wreck", 80, -104, 20),
                 ("tombstone_large", 46, -128, 0), ("concrete_barrier", 70, -112, 0),
                 ("concrete_barrier", 58, -132, 90)])
    # Parc central (point de capture en (-44, 30)).
    place_all(L, "Park", [
        ("sandbag_straight", -48.5, 22, 0), ("sandbag_straight", -39.5, 22, 0), ("sandbag_straight", -44, 39, 0),
        ("stone_wall_broken", -54, 30, 90), ("stone_wall_straight", -34, 33, 90), ("stone_wall_end", -34, 36, 90),
        ("tree_large", -64, 16, 0), ("tree_large", -70, 30, 30), ("tree_large", -60, 46, 0),
        ("tree_large", -24, 18, 60), ("tree_large", -18, 42, 0), ("tree_large", -30, 50, 0),
        ("tree_small", -54, 50, 0), ("tree_small", -14, 26, 0), ("tree_small", -74, 46, 0),
        ("garden_bench", -47, 46, 0), ("garden_bench", -41, 46, 0), ("garden_bench", -60, 26, 90),
        ("street_lamp", -50, 44, 0), ("street_lamp", -38, 44, 0), ("street_lamp", -44, 14, 0),
        ("bird_bath", -30, 26, 0), ("picnic_table", -66, 38, 20), ("picnic_table", -22, 32, 70),
        ("trash_cans", -36, 48, 0), ("flower_patch_a", -56, 38, 0), ("flower_patch_c", -26, 40, 0),
        ("flower_patch_b", -50, 12, 0), ("bush_b", -74, 20, 0), ("bush_a", -16, 50, 0),
        ("hedge_straight", -70, 54, 0), ("hedge_straight", -66, 54, 0),
        ("hedge_straight", -22, 54, 0), ("hedge_straight", -18, 54, 0), ("swing_set", -68, 12, 0)])
    # Terrain vague au nord du boulevard : ligne de front.
    place_all(L, "Wasteland", [
        ("sandbag_straight", -60, -8, 0), ("sandbag_curve", -54, -10, 0), ("sandbag_straight", -26, -10, 15),
        ("stone_wall_broken", -40, -18, 0), ("stone_wall_broken", -70, -30, 90), ("car_wreck", -48, -30, 40),
        ("car_wreck", -16, -36, 110), ("rock_large", -32, -40, 0), ("rock_large", -64, -46, 30),
        ("concrete_barrier", -20, -22, 90), ("concrete_barrier", -76, -14, 0), ("log", -56, -22, 20),
        ("stump", -36, -28, 0), ("tree_dead", -24, -48, 0), ("tree_dead", -74, -40, 60), ("hay_bale", -46, -44, 0),
        ("traffic_cone", -12, -14, 0), ("traffic_cone", -12, -18, 0), ("barrel_group", -66, -20, 0)])
    # Parking des commerces (point de capture en (112, 24)).
    place_all(L, "Parking", [
        ("car_sedan", 98, 16, 90), ("car_sedan", 102, 16, 90), ("pickup_truck", 124, 15, 90),
        ("car_sedan", 128, 16, 90), ("car_wreck", 100, 34, 70), ("concrete_barrier", 106, 34, 0),
        ("concrete_barrier", 118, 34, 0), ("dumpster", 136, 30, 0), ("dumpster", 138, 33, 90),
        ("crate_stack", 92, 30, 0), ("traffic_cone", 112, 13, 0), ("traffic_cone", 116, 13, 0),
        ("street_lamp", 94, 22, 90), ("street_lamp", 132, 22, -90), ("road_sign", 86, 10, 180),
        ("trash_cans", 134, 12, 0)])
    # Casse automobile (ressource tertiaire en (128, -36)).
    place_all(L, "Junkyard", [
        ("car_wreck", 114, -30, 0), ("car_wreck", 114, -34, 10), ("car_wreck", 142, -42, 80),
        ("car_wreck", 140, -26, 120), ("car_wreck", 120, -48, 45), ("car_wreck", 98, -40, 90),
        ("car_wreck", 150, -80, 30), ("car_wreck", 132, -84, 0), ("dumpster", 146, -32, 0),
        ("dumpster", 104, -24, 90), ("crate_stack", 136, -48, 0), ("crate_stack", 108, -46, 30),
        ("barrel_group", 122, -22, 0), ("barrel_group", 150, -50, 0), ("concrete_barrier", 128, -26, 0),
        ("concrete_barrier", 120, -40, 90), ("concrete_barrier", 136, -36, 90), ("traffic_cone", 100, -30, 0),
        ("tree_dead", 152, -22, 0), ("tree_dead", 96, -84, 30), ("trash_cans", 104, -78, 0),
        ("pickup_truck", 140, -94, 20), ("car_wreck", 116, -92, 160)])
    # Ferme et verger (ressource secondaire en (132, 76)).
    place_all(L, "Farm", [
        ("greenhouse", 148, 96, 90), ("garden_shed", 148, 108, 90), ("wheelbarrow", 120, 70, 30),
        ("hay_bale", 118, 84, 0), ("hay_bale", 120, 87, 30), ("hay_bale", 146, 66, 0), ("hay_bale", 144, 70, 0),
        ("pickup_truck", 140, 90, 70)])
    for x in range(96, 141, 8):                    # verger
        for z in (124, 132, 140, 148):
            L.put("Farm", "tree_small", x + (z % 16) / 4, z, 0, report=False)
    for x in range(94, 115, 4):                    # champ de fleurs
        for z in (98, 104, 110):
            L.put("Farm", ("flower_patch_a", "flower_patch_b", "flower_patch_c")[(x // 4 + z) % 3], x, z, 0,
                  report=False)
    for x in range(94, 115, 4):                    # clôture du champ
        L.put("Farm", "picket_fence_straight", x, 94, 0, report=False)
        L.put("Farm", "picket_fence_straight", x, 115, 0, report=False)
    # Vieux parc abandonné (ressource secondaire en (-40, -108)).
    place_all(L, "OldPark", [
        ("swing_set", -24, -98, 0), ("picnic_table", -56, -96, 30), ("garden_bench", -30, -120, 180),
        ("tree_dead", -60, -118, 0), ("tree_dead", -20, -124, 70), ("tree_dead", -52, -132, 0),
        ("tombstone_small_b", -32, -94, 0), ("tombstone_large", -66, -104, 0), ("pumpkin_patch", -16, -110, 0),
        ("stone_wall_broken", -48, -96, 0), ("picket_fence_broken", -62, -90, 0),
        ("picket_fence_broken", -58, -90, 0), ("bird_bath", -44, -126, 0), ("street_lamp", -34, -100, 0),
        ("open_grave", -28, -112, 0)])
    # Clairière de la forêt (ressource tertiaire en (-134, -28)).
    place_all(L, "Clearing", [
        ("rock_large", -144, -20, 0), ("rock_large", -124, -38, 50), ("log", -126, -18, 30),
        ("log", -142, -38, 100), ("stump", -134, -16, 0), ("stump", -146, -30, 0), ("hay_bale", -122, -28, 0)])
    # Jardins du sud-ouest (ressource secondaire en (-112, 104)).
    place_all(L, "Gardens", [
        ("hedge_straight", -122, 96, 90), ("hedge_straight", -122, 112, 90), ("hedge_straight", -102, 96, 90),
        ("hedge_straight", -102, 112, 90), ("flowerbed", -112, 116, 0), ("flowerbed", -112, 92, 0),
        ("greenhouse", -130, 110, 0), ("garden_shed", -94, 116, 0), ("bird_bath", -118, 120, 0),
        ("planter_box", -106, 120, 0)])


def scatter(L, rnd, group, rect, pieces, count, margin=1.0):
    """Pose jusqu'à `count` pièces tirées dans `pieces` (liste pondérée par
    répétition) dans le rectangle, sans chevauchement."""
    x0, x1, z0, z1 = rect
    placed = 0
    for _ in range(count * 6):
        if placed >= count:
            break
        if L.put(group, rnd.choice(pieces), rnd.uniform(x0, x1), rnd.uniform(z0, z1), rnd.uniform(0, 360),
                 margin=margin, report=False):
            placed += 1
    return placed


def vegetation(L, rnd):
    green = ["tree_large"] * 5 + ["tree_small"] * 2 + ["bush_a", "bush_b"]
    dead = ["tree_dead"] * 4 + ["stump", "tall_grass", "tree_large"]
    # Forêt de l'ouest : verte au sud, morte au nord.
    scatter(L, rnd, "Forest", (-156, -94, -10, 48), green + ["log"], 110, margin=0.3)
    scatter(L, rnd, "Forest", (-156, -94, -112, -10), dead + ["tree_large"] * 2 + ["log", "rock_large"], 110,
            margin=0.3)
    # Bosquets et petit décor par moitié de carte.
    scatter(L, rnd, "WildPlants", (-156, 156, 20, 156), green + ["flower_patch_a", "flower_patch_b", "tall_grass"], 170)
    scatter(L, rnd, "WildZombies", (-156, 156, -156, -16), dead + ["tombstone_small_a", "bone_pile", "tall_grass"], 170)
    scatter(L, rnd, "WildMiddle", (-156, 156, -20, 20), ["tall_grass", "rock_large", "stump", "bush_a", "tree_small"],
            50)


# ---------------------------------------------------------------- Bordure et horizon

def border(L):
    for k in range(-154, 155, 8):
        L.put("Border", "border_hedge_straight", k, 159, 0, check=False)
        L.put("Border", "border_fence_straight", k, -159, 0, check=False)
        side = "border_hedge_straight" if k > 0 else "border_fence_straight"
        L.put("Border", side, -159, k, 90, check=False)
        L.put("Border", side, 159, k, 90, check=False)
    for x, z, yaw in ((159, -159, 0), (-159, -159, 90), (-159, 159, 180), (159, 159, -90)):
        L.put("Border", "border_hedge_corner", x, z, yaw, check=False)


def horizon_trees(L, rnd):
    """Deux couronnes d'arbres hors de la zone jouable."""
    for dist, step in ((167.0, 9.0), (179.0, 13.0)):
        perimeter = 8 * dist
        n = int(perimeter / step)
        for i in range(n):
            t = (i + rnd.uniform(-0.3, 0.3)) / n * perimeter
            side, u = int(t // (2 * dist)), t % (2 * dist) - dist
            x, z = [(u, -dist), (dist, u), (-u, dist), (-dist, -u)][side]
            x += rnd.uniform(-2.5, 2.5)
            z += rnd.uniform(-2.5, 2.5)
            if z < -20:
                pid = "tree_dead" if rnd.random() < 0.8 else "tree_large"
            elif z > 20:
                pid = "tree_large" if rnd.random() < 0.75 else "tree_small"
            else:
                pid = rnd.choice(("tree_large", "tree_dead"))
            L.put("Horizon", pid, x, z, rnd.uniform(0, 360), check=False)


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


def rect_weight(xs, zs, rect, edge, soft=4.0):
    """Poids d'un rectangle (1 à l'intérieur), bord décalé par `edge` et adouci."""
    x0, x1, z0, z1 = rect
    inside = np.minimum(np.minimum(xs - x0, x1 - xs), np.minimum(zs - z0, z1 - zs))
    return np.clip((inside + edge) / soft, 0, 1)


# Chemins de terre (polylignes, largeur en m).
PATHS = [
    ([(-44, 8), (-44, 24)], 3.0), ([(-80, 30), (-50, 30)], 2.6), ([(-38, 30), (-8, 30)], 2.6),
    ([(-44, 36), (-44, 56)], 2.6),                                        # parc
    ([(-4, 64), (10, 100), (30, 118)], 3.2), ([(40, 128), (60, 140), (76, 132)], 2.6),
    ([(36, 64), (36, 118)], 3.0), ([(46, 112), (72, 112)], 2.4),           # base des plantes
    ([(80, 76), (126, 76)], 3.0), ([(132, 82), (132, 120)], 2.6),         # ferme
    ([(80, 24), (106, 24)], 3.0),                                         # parking
    ([(80, -36), (122, -36)], 3.4), ([(128, -42), (128, -56)], 3.0),      # casse
    ([(64, -116), (64, -64)], 3.0), ([(70, -122), (106, -112)], 2.6),    # base des zombies
    ([(-40, -102), (-40, -64)], 2.8), ([(-46, -108), (-80, -112)], 2.2),  # vieux parc
    ([(-88, -28), (-128, -28)], 2.6),                                     # clairière
    ([(-106, 104), (-88, 100)], 2.6), ([(-112, 98), (-112, 64)], 2.4),    # jardins
    ([(-60, -4), (-30, -26), (-10, -50)], 2.2),                           # terrain vague
]
FARM_ROWS = (90, 116, 96, 112)       # rangs de terre du champ (x0, x1, z0, z1)


def splat_map():
    n = int(TERRAIN * SPLAT_PX_PER_M)
    coords = -TERRAIN / 2 + (np.arange(n) + 0.5) / SPLAT_PX_PER_M
    xs, zs = np.meshgrid(coords, coords)            # ligne = z croissant (v de l'UV)
    noise_a = fbm(xs, zs, 40.0, 11)
    noise_b = fbm(xs, zs, 9.0, 23)
    noise_c = fbm(xs, zs, 18.0, 37)
    edge = (noise_b - 0.5) * 1.4

    # B : herbe morte au nord, frontière très irrégulière.
    dead = np.clip((-14.0 - zs + (noise_a - 0.5) * 70.0) / 8.0, 0, 1)

    # R : herbe sèche (terrain vague, ferme, casse, clairière, taches éparses).
    dry = np.clip((noise_b * 0.9 + np.exp(-(zs / 40.0) ** 2) * 0.3 - 0.72) * 5.0, 0, 1)
    for rect in ((-82, -6, -56, -2), (86, 156, 64, 156), (92, 158, -100, -18), (-150, -118, -44, -12)):
        dry = np.maximum(dry, rect_weight(xs, zs, rect, (noise_a - 0.5) * 34.0 + (noise_b - 0.5) * 10.0, 6.0))

    # A : sol corrompu (base zombie, cimetière, taches du vieux parc).
    corrupt = np.clip((-zs - 112.0) / 10.0 + (noise_c - 0.5) * 2.4, 0, 1) * (xs > 20)
    corrupt = np.maximum(corrupt, rect_weight(xs, zs, (86, 130, -150, -110), (noise_b - 0.5) * 3.0, 2.0))
    corrupt = np.maximum(corrupt, np.clip((16.0 - np.hypot(xs - 64, zs + 122)) / 5.0, 0, 1))
    corrupt = np.maximum(corrupt, np.clip((noise_c - 0.74) * 8.0, 0, 1) * (zs < -70))

    # G : chemins, anneaux autour des points, casse en terre battue, rangs du champ.
    path = np.zeros_like(xs)
    for poly, width in PATHS:
        for a, b in zip(poly, poly[1:]):
            d = segment_distance(xs, zs, a, b)
            path = np.maximum(path, np.clip((width / 2 - d + edge) / 0.6 + 0.5, 0, 1))
    for _, px, pz, _ in POINTS:
        d = np.hypot(xs - px, zs - pz)
        path = np.maximum(path, np.clip((7.5 - d + edge * 1.5) / 1.2, 0, 1))
    path = np.maximum(path, rect_weight(xs, zs, (96, 154, -56, -20),
                                        (noise_a - 0.5) * 24.0 + (noise_b - 0.5) * 8.0 - 4.0, 3.0))
    x0, x1, z0, z1 = FARM_ROWS
    rows = (np.abs(((zs - z0) % 6.0) - 3.0) < 1.1) & (xs > x0) & (xs < x1) & (zs > z0) & (zs < z1)
    path = np.maximum(path, rows * 0.85)
    path = np.maximum(path, rect_weight(xs, zs, (44, 74, 108, 122), edge * 2.0, 2.0))

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


def write_scene(sc, path, camera_at):
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
    for _, name in GROUND_TEXTURES:
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
              'transform = %s' % xform(*camera_at),
              'bounds = Rect2(%g, %g, %g, %g)' % (-HALF, -HALF, 2 * HALF, 2 * HALF), '']
    for node in sc.nodes:
        lines += [node, '']
    lines.append(systems_nodes())
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def build():
    rnd = random.Random(SEED)
    L = Layout()
    for pid, x, z, yaw in road_tiles(road_cells()):
        L.put("Roads", pid, x, z, yaw, check=False)
        L.reserve((x - 4, x + 4, z - 4, z + 4))
    for _, x, z, _ in POINTS:
        L.reserve((x - POINT_CLEARANCE, x + POINT_CLEARANCE, z - POINT_CLEARANCE, z + POINT_CLEARANCE))
    landmarks(L)
    hand_rejected = list(L.rejected)
    # Lotissements et commerces le long des rues (u = coordonnée le long de la rue).
    for group, theme, axis, c0, side, u0, u1 in (
            ("LotsPlants", "plants", "x", 60, 1, -128, -8), ("LotsPlants", "plants", "x", 60, -1, -128, -8),
            ("LotsPlants", "plants", "z", -44, 1, 64, 104), ("LotsPlants", "plants", "z", -44, -1, 64, 104),
            ("LotsPlants", "plants", "x", 60, 1, 0, 72), ("LotsPlants", "plants", "z", 76, 1, 30, 56),
            ("LotsPlants", "plants", "z", -84, -1, 10, 56),
            ("LotsZombies", "zombies", "x", -60, -1, -80, 140), ("LotsZombies", "zombies", "x", -60, 1, -80, 72),
            ("LotsZombies", "zombies", "z", 36, 1, -96, -64), ("LotsZombies", "zombies", "z", 36, -1, -96, -64),
            ("LotsZombies", "zombies", "z", -84, -1, -100, -64),
            ("Shops", "shops", "x", 4, -1, 0, 72), ("Shops", "shops", "x", 4, 1, 0, 72),
            ("Shops", "shops", "x", 4, -1, 84, 146)):
        house_row(L, rnd, group, theme, axis, c0, side, u0, u1)
    vegetation(L, rnd)
    border(L)
    horizon_trees(L, rnd)

    sc = Scene("Suburb", (TERRAIN, TERRAIN))
    groups = {}
    for group, pid, x, z, yaw in L.items:
        if group not in groups:
            groups[group] = sc.group(group)
        sc.piece(groups[group], pid, x, z, yaw)
    pts = sc.group("Points")
    for pid, x, z, state in POINTS:
        sc.point(pts, pid, x, z, state)

    os.makedirs(OUT_DIR, exist_ok=True)
    write_png(os.path.join(OUT_DIR, "suburb_splat.png"), splat_map())
    write_scene(sc, os.path.join(OUT_DIR, "suburb.tscn"), (20, 104))
    counts = {}
    for group, *_ in L.items:
        counts[group] = counts.get(group, 0) + 1
    print("Carte écrite : %d pièces, %d points" % (len(L.items), len(POINTS)))
    print("  " + ", ".join("%s %d" % kv for kv in counts.items()))
    for r in hand_rejected:
        print("  REFUSÉ (placement manuel)", r)


if __name__ == "__main__":
    build()
