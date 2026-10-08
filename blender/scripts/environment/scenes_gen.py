# plantRTS — Kit d'environnement : génération des scènes de présentation.
# python blender/scripts/environment/scenes_gen.py      (Python seul, sans Blender)
#
# world/maps/kit_showcase/kit_showcase.tscn : toutes les pièces du catalogue rangées
#   par catégorie (étiquette au-dessus de chacune), les quatre points de jeu dans
#   leurs trois états, une escouade de Pisto-pois, une de Zombies classiques et un
#   Z-Mech pour l'échelle.
# world/maps/kit_demo/kit_demo.tscn : diorama de 80 × 80 m assemblé avec le kit
#   (rue, trois maisons à jardins clôturés, coin de cimetière, point de capture, trois
#   points de ressource). Les raccords suivent les règles du kit : segments de 4 m
#   centrés sur la grille, angles à 3 m du premier segment.
# Coordonnées Godot : X vers la droite, Z vers la caméra, avant des modèles vers +Z.
# Rotation (degrés) autour de Y.

import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from catalog import PIECES  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
UNITS = {"peashooter": "res://assets/plants/peashooter.glb", "browncoat": "res://assets/zombies/browncoat.glb",
         "z_mech": "res://assets/zombies/z_mech.glb"}
STATE_SCRIPT = "res://world/environment/point_state_display.gd"
STATES = ("NEUTRAL", "PLANTS", "ZOMBIES")
STATE_NAMES = {"NEUTRAL": "neutre", "PLANTS": "plantes", "ZOMBIES": "zombies"}


def xform(x, z, yaw=0.0, y=0.0):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    # Godot écrit Transform3D ligne par ligne (base.rows) puis l'origine.
    vals = (c, 0.0, s, 0.0, 1.0, 0.0, -s, 0.0, c, x, y, z)
    return "Transform3D(%s)" % ", ".join(("%.6g" % v) for v in vals)


class Scene:
    """Petit écrivain de .tscn : ressources externes dédupliquées, nœuds à plat."""

    def __init__(self, root_name, ground_size, center=(0.0, 0.0)):
        self.root = root_name
        self.ext = {}
        self.nodes = []
        self.ground_size = ground_size
        self.center = center
        self.names = set()

    def res(self, path, kind="PackedScene"):
        if path not in self.ext:
            self.ext[path] = (kind, "r%d" % len(self.ext))
        return self.ext[path][1]

    def unique(self, name):
        base, k = name, 1
        while name in self.names:
            k += 1
            name = "%s_%d" % (base, k)
        self.names.add(name)
        return name

    def group(self, name):
        self.nodes.append('[node name="%s" type="Node3D" parent="."]' % name)
        self.names.add(name)
        return name

    def piece(self, parent, pid, x, z, yaw=0.0, name=None):
        cat = PIECES[pid][0]
        rid = self.res("res://assets/environment/%s/%s.glb" % (cat, pid))
        n = self.unique(name or pid)
        self.nodes.append('[node name="%s" parent="%s" instance=ExtResource("%s")]\ntransform = %s'
                          % (n, parent, rid, xform(x, z, yaw)))
        return n

    def point(self, parent, pid, x, z, state, yaw=0.0):
        sid = self.res(STATE_SCRIPT, "Script")
        n = self.unique("%s_%s" % (pid, STATE_NAMES[state]))
        self.nodes.append('[node name="%s" type="Node3D" parent="%s"]\ntransform = %s\nscript = ExtResource("%s")\n'
                          'state = %d' % (n, parent, xform(x, z, yaw), sid, STATES.index(state)))
        rid = self.res("res://assets/environment/%s/%s.glb" % (PIECES[pid][0], pid))
        self.nodes.append('[node name="Model" parent="%s/%s" instance=ExtResource("%s")]' % (parent, n, rid))
        return n

    def unit(self, parent, kind, x, z, yaw=0.0):
        rid = self.res(UNITS[kind])
        n = self.unique(kind)
        self.nodes.append('[node name="%s" parent="%s" instance=ExtResource("%s")]\ntransform = %s'
                          % (n, parent, rid, xform(x, z, yaw)))

    def label(self, parent, text, x, z, height, size=64):
        n = self.unique("Label")
        self.nodes.append('[node name="%s" type="Label3D" parent="%s"]\ntransform = %s\nbillboard = 1\n'
                          'no_depth_test = true\npixel_size = 0.01\nfont_size = %d\noutline_size = 12\ntext = "%s"'
                          % (n, parent, xform(x, z, 0, height), size, text))

    def write(self, path, camera_at, camera_bounds):
        cam = self.res("res://camera/rts_camera.tscn")
        gx, gz = self.ground_size
        lines = ['[gd_scene format=3]', '']
        for p, (kind, rid) in self.ext.items():
            lines.append('[ext_resource type="%s" path="%s" id="%s"]' % (kind, p, rid))
        lines += ['', '[sub_resource type="ProceduralSkyMaterial" id="sky_mat"]', '',
                  '[sub_resource type="Sky" id="sky"]', 'sky_material = SubResource("sky_mat")', '',
                  '[sub_resource type="Environment" id="env"]', 'background_mode = 2', 'sky = SubResource("sky")',
                  'ambient_light_source = 3', 'tonemap_mode = 2', '',
                  '[sub_resource type="StandardMaterial3D" id="ground_mat"]', 'albedo_color = Color(0.36, 0.5, 0.27, 1)',
                  '', '[sub_resource type="PlaneMesh" id="ground_mesh"]', 'material = SubResource("ground_mat")',
                  'size = Vector2(%g, %g)' % (gx, gz), '',
                  '[node name="%s" type="Node3D"]' % self.root, '',
                  '[node name="WorldEnvironment" type="WorldEnvironment" parent="."]', 'environment = SubResource("env")', '',
                  '[node name="Sun" type="DirectionalLight3D" parent="."]',
                  'transform = Transform3D(0.866025, -0.383022, 0.321394, 0, 0.642788, 0.766044, -0.5, -0.663414, 0.55667, 0, 20, 0)',
                  'shadow_enabled = true', 'directional_shadow_max_distance = 200.0', '',
                  '[node name="Terrain" type="MeshInstance3D" parent="."]',
                  'transform = %s' % xform(self.center[0], self.center[1], 0, -0.02), 'mesh = SubResource("ground_mesh")', '',
                  '[node name="RTSCamera" parent="." instance=ExtResource("%s")]' % cam,
                  'transform = %s' % xform(camera_at[0], camera_at[1]),
                  'bounds = Rect2(%g, %g, %g, %g)' % camera_bounds, '']
        for node in self.nodes:
            lines += [node, '']
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines))


# ---------------------------------------------------------------- Vitrine

def footprint(pid):
    fp = PIECES[pid][2]
    return (2 * fp, 2 * fp) if isinstance(fp, float) else fp


def showcase():
    order = ("ground", "buildings", "cover_heavy", "cover_light", "vegetation", "props", "gameplay", "borders")
    titles = {"ground": "Routes et sols", "buildings": "Bâtiments", "cover_heavy": "Couvert lourd",
              "cover_light": "Couvert léger", "vegetation": "Végétation", "props": "Petit décor",
              "gameplay": "Points de jeu", "borders": "Bordures"}
    sc = Scene("KitShowcase", (220, 260), (60, 90))
    max_width = 120.0
    gap = 2.0
    z = 0.0
    for cat in order:
        grp = sc.group(cat.title().replace("_", ""))
        items = [p for p in PIECES if PIECES[p][0] == cat]
        if cat == "gameplay":
            items = [(p, s) for p in items for s in STATES]
        else:
            items = [(p, None) for p in items]
        sc.label(grp, titles[cat], -6.0, z + 2.0, 3.0, size=160)
        x, row_depth = 0.0, 0.0
        for pid, state in items:
            w, d = footprint(pid)
            if x + w > max_width:
                z += row_depth + gap + 3.0
                x, row_depth = 0.0, 0.0
            cx, cz = x + w / 2, z + d / 2
            if state:
                sc.point(grp, pid, cx, cz, state)
                name = "%s (%s)" % (PIECES[pid][1], STATE_NAMES[state])
            else:
                sc.piece(grp, pid, cx, cz)
                name = PIECES[pid][1]
            sc.label(grp, name, cx, cz + d / 2 + 0.6, 0.3, size=40)
            x += w + gap
            row_depth = max(row_depth, d)
        z += row_depth + gap + 6.0
    units = sc.group("ScaleUnits")
    for i in range(6):
        sc.unit(units, "peashooter", -10.0 + (i % 3) * 1.8, 6.0 + (i // 3) * 1.8)
    for i in range(8):
        sc.unit(units, "browncoat", -10.0 + (i % 4) * 2.0, 14.0 + (i // 4) * 2.0)
    sc.unit(units, "z_mech", -6.0, 24.0)
    sc.write(os.path.join(ROOT, "world", "maps", "kit_showcase", "kit_showcase.tscn"), (40.0, 20.0),
             (-20.0, -10.0, 170.0, 220.0))
    return z


# ---------------------------------------------------------------- Diorama

def demo():
    sc = Scene("KitDemo", (90, 90))
    # Rue principale (z = 0) : impasse à l'ouest, passage piéton, carrefour en T vers le sud.
    road = sc.group("Road")
    for x in range(-36, 37, 8):
        if x == -36:
            sc.piece(road, "road_end", x, 0, 180)
        elif x == -12:
            sc.piece(road, "road_crosswalk", x, 0)
        elif x == 12:
            sc.piece(road, "road_t", x, 0)
        else:
            sc.piece(road, "road_straight", x, 0)
    sc.piece(road, "road_straight", 12, 8, 90)
    sc.piece(road, "road_straight", 12, 16, 90)
    sc.piece(road, "road_end", 12, 24, -90)
    # Trois maisons au nord, jardins clôturés (clôture avant en z = -6, portillons face
    # aux portes, angles à 3 m du premier segment).
    lots = sc.group("Houses")
    houses = (("house_a", -24, -2.0), ("house_b", -6, 0.0), ("house_two_story", 8, -2.2))
    for pid, cx, door in houses:
        sc.piece(lots, pid, cx, -14)
        sc.piece(lots, "path_straight", cx + door, -8, 90)
        sc.piece(lots, "flowerbed", cx + door + 3.5, -8.0, 90)
    fences = sc.group("Fences")
    gates = {round(cx + door) for _, cx, door in houses}
    for x in range(-30, 15, 4):
        sc.piece(fences, "picket_fence_gate" if x in gates else "picket_fence_straight", x, -6)
    sc.piece(fences, "picket_fence_corner", -33, -6, 180)
    sc.piece(fences, "picket_fence_corner", 17, -6, -90)
    for z in (-9, -13, -17, -21):
        sc.piece(fences, "picket_fence_straight", -33, z, 90)
        sc.piece(fences, "picket_fence_straight", 17, z, 90)
    for z in (-8, -12, -16, -20):
        sc.piece(fences, "picket_fence_straight", -16, z, 90)
        sc.piece(fences, "hedge_straight", 0, z, 90)
    # Jardins : arbres, piscine, balançoire, abri, petit décor.
    garden = sc.group("Gardens")
    sc.piece(garden, "tree_large", -29, -25)
    sc.piece(garden, "swing_set", -21, -24)
    sc.piece(garden, "garden_shed", -10, -24)
    sc.piece(garden, "tree_small", -3, -24)
    sc.piece(garden, "pool", 8, -25)
    sc.piece(garden, "bbq_grill", 14, -22)
    for pid, x, z in (("mailbox", -28, -4.6), ("mailbox", -12, -4.6), ("mailbox", 4, -4.6),
                      ("garden_gnome", -20, -8), ("lawn_flamingo", -12, -8.5), ("bird_bath", 12, -8),
                      ("bush_a", -30, -8), ("bush_b", 14, -8), ("flower_patch_a", -19, -12),
                      ("flower_patch_c", 1.8, -9), ("fire_hydrant", -16, -4.6), ("street_lamp", 0, -4.6),
                      ("street_lamp", -32, -4.6), ("street_lamp", 24, -4.6)):
        sc.piece(garden, pid, x, z)
    # Voitures garées.
    cars = sc.group("Cars")
    sc.piece(cars, "car_sedan", -22, -1.8, 180)
    sc.piece(cars, "pickup_truck", 2, -1.8, 180)
    sc.piece(cars, "car_wreck", 30, 1.8, 10)
    # Bordure nord.
    border = sc.group("Border")
    for x in range(-36, 37, 8):
        sc.piece(border, "border_hedge_straight", x, -38)
    for z in (12, 20, 28, 36):
        sc.piece(border, "border_fence_straight", -39, z, 90)
    # Points de jeu au sud-ouest, protégés par des sacs de sable et des murets.
    points = sc.group("Points")
    sc.point(points, "capture_point", -12, 18, "NEUTRAL")
    sc.point(points, "resource_point_primary", -30, 16, "PLANTS")
    sc.point(points, "resource_point_secondary", -28, 32, "ZOMBIES")
    sc.point(points, "resource_point_tertiary", 0, 32, "NEUTRAL")
    cover = sc.group("Cover")
    for x in (-14, -10):
        sc.piece(cover, "sandbag_straight", x, 11)
    sc.piece(cover, "stone_wall_straight", -19, 18, 90)
    sc.piece(cover, "stone_wall_end", -19, 21, 90)
    sc.piece(cover, "stone_wall_broken", -5, 18, 90)
    for pid, x, z in (("rock_large", -36, 26), ("concrete_barrier", 4, 8), ("crate_stack", -2, 12),
                      ("barrel_group", -22, 9), ("hay_bale", -16, 34), ("tree_large", -20, 28),
                      ("bush_a", 5, 20), ("tall_grass", -34, 8), ("dirt_patch", -4, 24), ("traffic_cone", 7, 6),
                      ("pumpkin_patch", -12, 30), ("log", 4, 26), ("stump", -26, 24)):
        sc.piece(cover, pid, x, z)
    # Coin de cimetière au sud-est : grille en fer forgé, crypte, tombes.
    yard = sc.group("Graveyard")
    sc.piece(yard, "iron_fence_corner", 18, 8, 90)
    for x in (21, 25, 29, 33, 37):
        sc.piece(yard, "iron_fence_gate" if x == 29 else "iron_fence_straight", x, 8)
    for z in (11, 15, 19, 23, 27, 31, 35):
        sc.piece(yard, "iron_fence_straight", 18, z, 90)
    sc.piece(yard, "crypt", 30, 32, 180)
    for i, (pid, x, z) in enumerate((("tombstone_large", 23, 14), ("tombstone_small_a", 26, 14),
                                     ("tombstone_small_b", 34, 14), ("tombstone_small_c", 37, 14),
                                     ("tombstone_small_a", 23, 20), ("tombstone_large", 34, 20),
                                     ("tombstone_small_b", 37, 20), ("tombstone_small_c", 23, 26),
                                     ("tombstone_small_a", 37, 26))):
        sc.piece(yard, pid, x, z, 180)
    for pid, x, z, yaw in (("open_grave", 26, 22, 90), ("coffin", 29, 22, 20), ("bone_pile", 31, 16, 0),
                           ("tree_dead", 22, 34, 0), ("tree_dead", 38, 36, 70)):
        sc.piece(yard, pid, x, z, yaw)
    # Unités pour l'échelle.
    units = sc.group("ScaleUnits")
    for i in range(6):
        sc.unit(units, "peashooter", -14 + (i % 3) * 1.8, 6 + (i // 3) * 1.8)
    for i in range(8):
        sc.unit(units, "browncoat", 25 + (i % 4) * 1.8, 10.5 + (i // 4) * 1.8, 180)
    sc.unit(units, "z_mech", 20, 4.5, 200)
    sc.write(os.path.join(ROOT, "world", "maps", "kit_demo", "kit_demo.tscn"), (0.0, 0.0), (-40.0, -40.0, 80.0, 80.0))


if __name__ == "__main__":
    depth = showcase()
    demo()
    print("Scènes écrites (vitrine : %.0f m de profondeur)" % depth)
