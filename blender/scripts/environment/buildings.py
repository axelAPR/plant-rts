# plantRTS — Kit d'environnement : bâtiments de décor (bloquants).
# blender -b --python blender/scripts/environment/buildings.py -- [ids…] [--render]
#
# Maisons basses de banlieue : murs de 2,8 m par niveau sur un soubassement de 0,35 m,
# toit à deux pans (faîtage ≈ 5,2 m de plain-pied, ≤ 8 m à étage), porte de 2,3 m
# (plus haute qu'un zombie, 2,04 m). Façade principale vers -Y. Pas d'intérieur :
# volumes pleins, vitres opaques ; dessous et faces cachées supprimés.
# Matériaux texturés (env_lib.TEXTURES) ; l'atlas Env_Trim regroupe boiseries
# blanches (« :white »), rouges (« :red »), bois naturel (« :wood ») et vitres (« :glass »).
# Les maisons sont décrites par des paramètres (_house) : couleurs, niveaux, porche,
# lucarne, cheminée, délabrement.

import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from env_lib import *  # noqa: F401,F403
import bmesh
from mathutils import Vector, Matrix, Quaternion

PLINTH = 0.35           # soubassement
STORY = 2.8             # hauteur d'un niveau
DOOR_W, DOOR_H = 1.1, 2.3


class Facade:
    """Repère d'un mur : `u` le long du mur, `out` vers l'extérieur, `z` en hauteur.
    `yaw` (degrés) : 0 = façade avant (-Y), 180 = arrière, 90 = côté +X, -90 = côté -X.
    `depth` : distance du centre du bâtiment au plan du mur."""

    def __init__(self, yaw, depth, center=(0.0, 0.0)):
        self.yaw = yaw
        self.depth = depth
        self.center = Vector((center[0], center[1], 0.0))
        self.rot = Quaternion((0, 0, 1), math.radians(yaw))

    def p(self, u, out, z):
        return self.center + self.rot @ Vector((u, -(self.depth + out), z))

    def slab(self, bm, u, out, z, w, t, h, mi, pitch=0.0, roll=0.0, bevel=0.0):
        """Boîte dans le repère du mur : largeur `w` (le long), épaisseur `t`, hauteur `h`."""
        slab(bm, self.p(u, out, z), (w, t, h), mi, yaw=self.yaw, pitch=pitch, roll=roll, bevel=bevel)


def facades(hx, hy, center=(0.0, 0.0)):
    return {"front": Facade(0, hy, center), "back": Facade(180, hy, center),
            "right": Facade(90, hx, center), "left": Facade(-90, hx, center)}


def _window(bm, f, u, z, M, w=1.1, h=1.3, shutters=True, sill=True, boarded=False, rnd=None):
    """Fenêtre : vitre, cadre saillant à corniche, croisillons, appui ; volets.
    `boarded` : planches clouées en travers, volets de travers (maison abandonnée)."""
    f.slab(bm, u, 0.03, z, w, 0.04, h, M["glass"])
    t = 0.12
    f.slab(bm, u, 0.08, z + h / 2 + t / 2 - 0.02, w + 2 * t, 0.1, t, M["white"])          # linteau
    f.slab(bm, u, 0.1, z + h / 2 + t + 0.02, w + 2 * t + 0.14, 0.14, 0.07, M["white"])     # corniche
    if sill:
        f.slab(bm, u, 0.12, z - h / 2 - 0.05, w + 2 * t + 0.12, 0.18, 0.09, M["white"])  # appui
    for s in (-1, 1):
        f.slab(bm, u + s * (w / 2 + t / 2 - 0.02), 0.08, z, t, 0.1, h + 0.04, M["white"])
    if boarded:
        for k, ang in enumerate((-24, 18, -8)):
            f.slab(bm, u, 0.12 + 0.02 * k, z + 0.3 * (k - 1), w + 0.3, 0.04, 0.16, M["wood"], roll=ang)
    else:
        f.slab(bm, u, 0.065, z, 0.06, 0.04, h, M["white"])                              # croisillons
        f.slab(bm, u, 0.065, z + 0.1, w, 0.04, 0.06, M["white"])
    if shutters:
        for s in (-1, 1):
            su = u + s * (w / 2 + t + 0.26)
            tilt = rnd.uniform(-14, 14) if (boarded and rnd) else 0.0
            f.slab(bm, su, 0.05, z - abs(tilt) * 0.01, 0.44, 0.05, h + 0.1, M["accent"], roll=tilt, bevel=0.015)


def _door(bm, f, u, M, z0=PLINTH):
    z = z0 + DOOR_H / 2
    f.slab(bm, u, 0.04, z, DOOR_W, 0.06, DOOR_H, M["accent"], bevel=0.02)
    for dz in (0.45, -0.5):      # panneaux en relief
        f.slab(bm, u, 0.075, z + dz, DOOR_W - 0.34, 0.03, 0.7, M["accent"], bevel=0.015)
    f.slab(bm, u, 0.075, z + 0.92, DOOR_W - 0.4, 0.03, 0.26, M["glass"])
    f.slab(bm, u + 0.38, 0.1, z - 0.08, 0.08, 0.08, 0.08, M["white"], bevel=0.02)   # poignée
    t = 0.14
    f.slab(bm, u, 0.08, z + DOOR_H / 2 + t / 2, DOOR_W + 2 * t, 0.12, t, M["white"])
    for s in (-1, 1):
        f.slab(bm, u + s * (DOOR_W / 2 + t / 2), 0.08, z, t, 0.12, DOOR_H, M["white"])


def _gable_roof(bm, half_x, half_y, pitch, wall_top, M, overhang=0.45, rake=0.35, center=(0.0, 0.0),
                gutters=True, holes=(), rnd=None):
    """Toit à deux pans (faîtage le long de X), tuiles texturées : couverture épaisse,
    faîtière, bandeaux, planches de rive, gouttières. `holes` : [(pan, x0, x1)] parties
    de couverture manquantes (chevrons apparents). Renvoie (faîtage, égout, débord)."""
    cx, cy = center
    t = math.tan(math.radians(pitch))
    ridge_z = wall_top + half_y * t
    run = half_y + overhang
    slope = run / math.cos(math.radians(pitch))
    length = 2 * (half_x + rake)
    eave_z = wall_top - overhang * t
    for s in (-1, 1):                       # s = -1 : pan avant
        ang = -s * pitch
        q = Quaternion((1, 0, 0), math.radians(ang))
        up = q @ Vector((0, 0, 1))
        mid = Vector((cx, cy + s * run / 2, (eave_z + ridge_z) / 2)) + up * 0.1
        # Couverture, découpée autour des trous éventuels.
        spans = [(-length / 2, length / 2)]
        for pan, h0, h1 in holes:
            if pan == s:
                spans = [(a, h0) for a, b in spans if a < h0] + [(h1, b) for a, b in spans if b > h1]
                for k in range(4):           # chevrons visibles dans le trou
                    x = h0 + (h1 - h0) * (k + 0.5) / 4
                    slab(bm, mid + Vector((x, 0, 0)) - up * 0.05, (0.1, slope, 0.12), M["wood"], pitch=ang)
        for a, b in spans:
            slab(bm, mid + Vector(((a + b) / 2, 0, 0)), (b - a, slope + 0.05, 0.2), M["roof"], pitch=ang,
                 roll=rnd.uniform(-2, 2) if (rnd and holes) else 0.0)
        slab(bm, (cx, cy + s * (run - 0.02), eave_z - 0.05), (length, 0.08, 0.24), M["white"])   # bandeau
        if gutters:
            slab(bm, (cx, cy + s * (run + 0.08), eave_z - 0.1), (length, 0.14, 0.12), M["white"])
    cyl(bm, (cx - length / 2 - 0.02, cy, ridge_z + 0.2), (cx + length / 2 + 0.02, cy, ridge_z + 0.2 - (0.25 if holes else 0)),
        0.17, 0.17, M["roof"], seg=8)
    for x in (-length / 2, length / 2):
        for s in (-1, 1):
            a = Vector((cx + x, cy + s * run, eave_z))
            b = Vector((cx + x, cy, ridge_z + 0.1))
            slab(bm, (a + b) / 2 + Vector((0, 0, 0.08)), (0.09, (b - a).length + 0.12, 0.28), M["white"],
                 pitch=-s * pitch)
    return ridge_z, eave_z, run


def _gables(bm, hx, hy, wall_top, pitch, M, F, vent=True):
    rise = hy * math.tan(math.radians(pitch))
    for x, f in ((hx, F["right"]), (-hx, F["left"])):
        mtx = Matrix.Translation((x, 0, 0)) @ Matrix.Rotation(math.radians(90), 4, 'Z')
        prism(bm, [(-hy, wall_top - 0.05), (hy, wall_top - 0.05), (0, wall_top + rise)], 0.12, mtx, M["walls"])
        if vent:
            c, d = f.p(0, 0.06, wall_top + rise * 0.4), f.p(0, 0.14, wall_top + rise * 0.4)
            cyl(bm, c, d, 0.36, 0.36, M["white"], seg=10)
            cyl(bm, d, d + (d - c) * 0.25, 0.26, 0.26, M["glass"], seg=10)


def _downspout(bm, x, y_wall, y_gutter, eave_z, M):
    """Descente d'eau pluviale : col de cygne depuis la gouttière, tuyau le long du
    mur, coude au pied."""
    top = Vector((x, y_wall, eave_z - 0.55))
    cyl(bm, (x, y_gutter, eave_z - 0.12), top, 0.055, 0.055, M["white"], seg=6)
    cyl(bm, top, (x, y_wall, 0.1), 0.055, 0.055, M["white"], seg=6)
    cyl(bm, (x, y_wall, 0.1), (x, y_wall + math.copysign(0.3, y_wall), 0.03), 0.06, 0.06, M["white"], seg=6)


def _dormer(bm, x, hy, wall_top, pitch, M):
    """Lucarne sur le pan avant : petit volume à pignon, fenêtre carrée."""
    y_front, y_back = -(hy - 0.85), -0.4
    t = math.tan(math.radians(pitch))
    z0 = wall_top + (hy - abs(y_front)) * t - 0.25
    z1 = z0 + 1.1
    w = 1.5
    box(bm, (x, (y_front + y_back) / 2, (z0 + z1) / 2), (w, y_back - y_front, z1 - z0), M["walls"])
    prism(bm, [(-w / 2, z1), (w / 2, z1), (0, z1 + 0.55)], 0.1, Matrix.Translation((x, y_front + 0.04, 0)),
          M["walls"])
    for s in (-1, 1):
        slab(bm, (x + s * 0.47, (y_front + y_back) / 2 - 0.12, z1 + 0.3), (1.02, y_back - y_front + 0.5, 0.12),
             M["roof"], roll=s * 32)
    zc = (z0 + z1) / 2 + 0.05

    def part(u, out, z, ww, tt, hh, mi):
        slab(bm, Vector((x + u, y_front - out, z)), (ww, tt, hh), mi)
    part(0, 0.03, zc, 0.7, 0.04, 0.6, M["glass"])
    for s in (-1, 1):
        part(s * 0.4, 0.07, zc, 0.1, 0.1, 0.8, M["white"])
        part(0, 0.07, zc + s * 0.37, 0.9, 0.1, 0.1, M["white"])
    part(0, 0.06, zc, 0.05, 0.04, 0.6, M["white"])


def _walls(bm, hx, hy, wall_top, M, center=(0.0, 0.0)):
    """Soubassement en brique et murs pleins (dessus, caché sous le toit, supprimé)."""
    cx, cy = center
    box(bm, (cx, cy, PLINTH / 2), (2 * hx + 0.2, 2 * hy + 0.2, PLINTH), M["brick"], bevel=0.03)
    before = set(bm.faces)
    box(bm, (cx, cy, (PLINTH + wall_top) / 2), (2 * hx, 2 * hy, wall_top - PLINTH), M["walls"])
    bm.normal_update()
    bmesh.ops.delete(bm, geom=[f for f in set(bm.faces) - before if f.normal.z > 0.9], context='FACES_ONLY')
    for x in (-hx, hx):
        for y in (-hy, hy):
            box(bm, (cx + x, cy + y, (PLINTH + wall_top) / 2), (0.22, 0.22, wall_top - PLINTH), M["white"], bevel=0.02)


def _house(model, mats, hx=4.0, hy=3.0, stories=1, pitch=33.0, door_u=-2.0, windows=None, porch="canopy",
           dormer=None, chimney=(2.6, 1.3), downspouts=True, decay=False, seed=42, vents=True):
    """Maison paramétrée. `mats` : {walls, roof, brick, accent, trim} (noms de matériaux) ;
    `windows` : {façade: [u…]} pour chaque niveau ; `porch` : 'canopy' (auvent sur
    poteaux) ou 'veranda' (galerie sur toute la façade) ; `decay` : maison abandonnée."""
    col = start(model)
    rig = Rig(model, col)
    rnd = random.Random(seed)
    M = {"walls": rig.m(mats["walls"]), "roof": rig.m(mats["roof"]), "brick": rig.m(mats["brick"]),
         "white": rig.m(mats.get("trim", "Env_Trim:white")), "accent": rig.m(mats.get("accent", "Env_Trim:red")),
         "glass": rig.m("Env_Trim:glass"), "wood": rig.m("Env_Trim:wood")}
    bm = rig.part("House", (0, 0, 0))
    wall_top = PLINTH + STORY * stories
    F = facades(hx, hy)
    _walls(bm, hx, hy, wall_top, M)
    for f, length in ((F["front"], 2 * hx), (F["back"], 2 * hx), (F["right"], 2 * hy), (F["left"], 2 * hy)):
        f.slab(bm, 0, 0.03, wall_top - 0.12, length, 0.06, 0.22, M["white"])            # frise haute
        for k in range(1, stories):
            f.slab(bm, 0, 0.04, PLINTH + STORY * k, length, 0.08, 0.16, M["white"])     # bandeau d'étage
    _gables(bm, hx, hy, wall_top, pitch, M, F, vent=vents)
    _door(bm, F["front"], door_u, M)
    windows = windows or {"front": (0.75, 2.75), "back": (-2.2, 1.6), "right": (0.0,), "left": (0.6,)}
    for k in range(stories):
        z = PLINTH + STORY * k + 1.55
        for name, us in windows.items():
            for u in us:
                if k == 0 and name == "front" and abs(u - door_u) < 1.2:
                    continue
                _window(bm, F[name], u, z, M, shutters=k == 0, boarded=decay and rnd.random() < 0.6, rnd=rnd)
        if k > 0:
            _window(bm, F["front"], door_u, z, M, shutters=False, boarded=decay, rnd=rnd)
    # Perron en brique, porche.
    for (d, h) in ((0.95, PLINTH * 0.5), (0.6, PLINTH)):
        box(bm, (door_u, -hy - d / 2, h / 2 - 0.02), (2.0, d, h - 0.04), M["brick"])
        box(bm, (door_u, -hy - d / 2, h - 0.02), (2.06, d + 0.04, 0.05), M["white"])
    canopy_z = PLINTH + DOOR_H + 0.35
    if porch == "canopy":
        for s in (-1, 1):
            roll = s * 28 + (rnd.uniform(-10, 10) if decay else 0)
            slab(bm, (door_u + s * 0.52, -hy - 0.46, canopy_z + 0.3), (1.12, 1.0, 0.12), M["roof"], roll=roll,
                 bevel=0.02)
            box(bm, (door_u + s * 0.85, -hy - 0.82, (PLINTH + canopy_z) / 2), (0.13, 0.13, canopy_z - PLINTH),
                M["white"], bevel=0.02)
        slab(bm, (door_u, -hy - 0.46, canopy_z), (1.95, 0.95, 0.14), M["white"])
        prism(bm, [(-0.95, canopy_z + 0.07), (0.95, canopy_z + 0.07), (0, canopy_z + 0.55)], 0.06,
              Matrix.Translation((door_u, -hy - 0.94, 0)), M["white"])
    elif porch == "veranda":
        depth = 0.85
        box(bm, (0, -hy - depth / 2, PLINTH / 2), (2 * hx - 0.6, depth, PLINTH), M["wood"])
        slab(bm, (0, -hy - depth / 2 + 0.05, canopy_z + 0.12), (2 * hx - 0.3, depth + 0.2, 0.12), M["roof"],
             pitch=14 if not decay else 18, roll=4 if decay else 0)
        for i in range(5):
            x = -hx + 0.5 + i * (2 * hx - 1.0) / 4
            if decay and i == 3:
                continue                       # poteau manquant
            box(bm, (x, -hy - depth + 0.12, (PLINTH + canopy_z) / 2), (0.14, 0.14, canopy_z - PLINTH),
                M["white"], bevel=0.02)
        for x0, x1 in ((-hx + 0.5, door_u - 0.7), (door_u + 0.7, hx - 0.5)):
            box(bm, ((x0 + x1) / 2, -hy - depth + 0.12, PLINTH + 0.75), (x1 - x0, 0.08, 0.08), M["white"])
    # Toit, descentes d'eau, lucarne, cheminée.
    holes = ((-1, -1.6, 0.4),) if decay else ()
    ridge_z, eave_z, run = _gable_roof(bm, hx, hy, pitch, wall_top, M, holes=holes, rnd=rnd,
                                       gutters=not decay)
    if downspouts and not decay:
        for x in (-hx + 0.3, hx - 0.3):
            for s in (-1, 1):
                _downspout(bm, x, s * (hy + 0.1), s * (run + 0.08), eave_z, M)
    if dormer is not None:
        _dormer(bm, dormer, hy, wall_top, pitch, M)
    if chimney is not None:
        cx, cy = chimney
        top = ridge_z + 0.55
        lean = 6.0 if decay else 0.0
        base_z = wall_top + (hy - abs(cy)) * math.tan(math.radians(pitch)) - 0.4
        slab(bm, (cx, cy, (base_z + top) / 2), (0.74, 0.74, top - base_z), M["brick"], roll=lean, bevel=0.03)
        slab(bm, (cx + math.sin(math.radians(lean)) * (top - base_z) / 2, cy, top), (0.92, 0.92, 0.14), M["white"],
             roll=lean, bevel=0.03)
    if decay:
        # Planches arrachées au pied des murs, gouttière tombée.
        for i in range(3):
            slab(bm, (rnd.uniform(-hx + 1.5, hx - 1.5), -hy - 0.55, 0.03), (1.2, 0.18, 0.05), M["wood"],
                 yaw=rnd.uniform(-12, 12))
        slab(bm, (hx - 1.0, -run - 0.2, 0.9), (2.4, 0.14, 0.12), M["white"], roll=35)
    finish(rig, smooth_angle=30.0)
    return rig


def _info(footprint, render=None):
    return {"category": "buildings", "budget": "building", "footprint": footprint,
            "render": render or {"target_z": 2.4, "close_distance": 17.0, "squad_offset": (-1.0, -7.0),
                                 "rts_distance": 32.0, "close_pitch": 16.0}}


def house_a():
    """Petite maison de plain-pied, bardage bleu-vert, toit de tuiles, porte rouge sous
    auvent, lucarne. Corps 8 × 6 m, emprise 10 × 8 m."""
    _house("house_a", {"walls": "Env_Siding", "roof": "Env_RoofTiles", "brick": "Env_Brick"}, dormer=1.75)
    return _info((10.0, 8.0))


def house_b():
    """Maison de plain-pied à galerie : bardage jaune, toit d'ardoise, porte et volets
    en bois naturel. Corps 8 × 6 m, emprise 10 × 8 m."""
    _house("house_b", {"walls": "Env_SidingYellow", "roof": "Env_RoofSlate", "brick": "Env_BrickGrey",
                       "accent": "Env_Trim:wood"},
           door_u=0.0, porch="veranda", windows={"front": (-2.4, 2.4), "back": (-2.0, 2.0), "right": (-1.0, 1.0),
                                                  "left": (0.0,)}, chimney=(-2.6, 1.2), pitch=30.0, seed=7)
    return _info((10.0, 8.0))


def house_two_story():
    """Maison à étage : crépi menthe, toit brun, auvent ; faîtage < 8 m. Corps 8 × 6 m,
    emprise 10 × 8 m."""
    _house("house_two_story", {"walls": "Env_PlasterMint", "roof": "Env_RoofBrown", "brick": "Env_Brick",
                               "accent": "Env_Trim:wood"},
           stories=2, pitch=25.0, door_u=-2.2, windows={"front": (0.4, 2.6), "back": (-2.0, 1.8), "right": (0.0,),
                                                         "left": (0.0,)}, chimney=(2.4, 1.0), seed=11,
           downspouts=False, vents=False)
    return _info((10.0, 8.0), {"target_z": 3.4, "close_distance": 20.0, "squad_offset": (-1.0, -7.0),
                               "rts_distance": 34.0, "close_pitch": 16.0})


def house_haunted():
    """Maison abandonnée (côté zombies) : bardage pourri, toit troué aux chevrons
    apparents, fenêtres condamnées, volets de travers, galerie affaissée, cheminée
    penchée. Corps 8 × 6 m, emprise 10 × 8 m."""
    _house("house_haunted", {"walls": "Env_SidingRotten", "roof": "Env_RoofRotten", "brick": "Env_BrickGrey",
                             "accent": "Env_Trim:red", "trim": "Env_Trim:wood"},
           porch="veranda", door_u=-1.6, dormer=1.9, decay=True, chimney=(-2.4, 1.2), seed=13)
    return _info((10.0, 8.0))


def garage():
    """Garage individuel : crépi gris, porte basculante métallique à lames, toit vert.
    Corps 4,4 × 6 m, emprise 6 × 8 m."""
    model = "garage"
    col = start(model)
    rig = Rig(model, col)
    M = {"walls": rig.m("Env_PlasterGrey"), "roof": rig.m("Env_RoofGreen"), "brick": rig.m("Env_PlasterGrey"),
         "white": rig.m("Env_Trim:white"), "glass": rig.m("Env_Trim:glass"), "wood": rig.m("Env_Trim:wood"),
         "metal": rig.m("Env_Metal")}
    bm = rig.part("Garage", (0, 0, 0))
    hx, hy, wall_top = 2.2, 3.0, PLINTH + 2.6
    F = facades(hx, hy)
    _walls(bm, hx, hy, wall_top, M)
    _gables(bm, hx, hy, wall_top, 22.0, M, F, vent=False)
    # Porte basculante : lames horizontales, encadrement, poignée.
    for i in range(6):
        F["front"].slab(bm, 0, 0.04 + 0.01 * (i % 2), PLINTH + 0.2 + i * 0.36, 3.2, 0.06, 0.34, M["metal"])
    F["front"].slab(bm, 0, 0.09, PLINTH + 2.3, 3.5, 0.12, 0.14, M["white"])
    for s in (-1, 1):
        F["front"].slab(bm, s * 1.68, 0.09, PLINTH + 1.15, 0.14, 0.12, 2.3, M["white"])
    F["front"].slab(bm, 0, 0.1, PLINTH + 0.6, 0.4, 0.06, 0.08, M["white"])
    _window(bm, F["right"], 0.0, PLINTH + 1.6, M, w=0.9, h=0.8, shutters=False)
    _window(bm, F["back"], 0.8, PLINTH + 1.6, M, w=0.9, h=0.8, shutters=False)
    # Petite porte de service côté gauche.
    F["left"].slab(bm, -1.2, 0.04, PLINTH + 1.05, 0.9, 0.06, 2.1, M["wood"], bevel=0.02)
    # Toit à deux pans le long de Y (faîtage perpendiculaire à la porte).
    t = math.tan(math.radians(22.0))
    ridge = wall_top + hx * t
    for s in (-1, 1):
        run_x = hx + 0.4
        slope = run_x / math.cos(math.radians(22.0))
        up = Quaternion((0, 1, 0), math.radians(s * 22.0)) @ Vector((0, 0, 1))
        mid = Vector((s * run_x / 2, 0, (wall_top - 0.4 * t + ridge) / 2)) + up * 0.1
        slab(bm, mid, (slope + 0.05, 2 * hy + 0.7, 0.2), M["roof"], roll=s * 22.0)
    cyl(bm, (0, -hy - 0.37, ridge + 0.2), (0, hy + 0.37, ridge + 0.2), 0.15, 0.15, M["roof"], seg=8)
    # Pignons avant/arrière (le faîtage est le long de Y).
    for y in (-hy, hy):
        prism(bm, [(-hx, wall_top - 0.05), (hx, wall_top - 0.05), (0, ridge)], 0.12, Matrix.Translation((0, y, 0)),
              M["walls"])
    finish(rig, smooth_angle=30.0)
    return _info((6.0, 8.0), {"target_z": 1.8, "close_distance": 13.0, "squad_offset": (-1.0, -6.0),
                              "rts_distance": 28.0, "close_pitch": 16.0})


def garden_shed():
    """Abri de jardin en planches, porte à écharpe en Z, petite fenêtre, toit brun.
    Corps 2,6 × 2,2 m, emprise 4 × 4 m."""
    model = "garden_shed"
    col = start(model)
    rig = Rig(model, col)
    M = {"walls": rig.m("Env_WoodPlanks"), "roof": rig.m("Env_RoofBrown"), "brick": rig.m("Env_WoodPlanks"),
         "white": rig.m("Env_Trim:white"), "glass": rig.m("Env_Trim:glass"), "wood": rig.m("Env_Trim:wood"),
         "accent": rig.m("Env_Trim:red")}
    bm = rig.part("Shed", (0, 0, 0))
    hx, hy = 1.3, 1.1
    wall_top = 0.15 + 2.1
    F = facades(hx, hy)
    box(bm, (0, 0, 0.075), (2 * hx + 0.1, 2 * hy + 0.1, 0.15), M["wood"])
    before = set(bm.faces)
    box(bm, (0, 0, (0.15 + wall_top) / 2), (2 * hx, 2 * hy, wall_top - 0.15), M["walls"])
    bm.normal_update()
    bmesh.ops.delete(bm, geom=[f for f in set(bm.faces) - before if f.normal.z > 0.9], context='FACES_ONLY')
    for x in (-hx, hx):
        for y in (-hy, hy):
            box(bm, (x, y, (0.15 + wall_top) / 2), (0.14, 0.14, wall_top - 0.15), M["white"])
    f = F["front"]
    f.slab(bm, -0.35, 0.04, 0.15 + 0.95, 0.9, 0.06, 1.9, M["accent"], bevel=0.02)
    for z in (0.45, 1.75):
        f.slab(bm, -0.35, 0.08, z, 0.9, 0.04, 0.12, M["white"])
    f.slab(bm, -0.35, 0.08, 1.1, 0.12, 0.04, 1.45, M["white"], roll=-35)
    _window(bm, f, 0.75, 1.45, M, w=0.5, h=0.5, shutters=False)
    _gables(bm, hx, hy, wall_top, 30.0, M, F, vent=False)
    _gable_roof(bm, hx, hy, 30.0, wall_top, M, overhang=0.25, rake=0.2, gutters=False)
    # Outils appuyés contre le mur : pelle et râteau.
    for x, ang in ((1.0, 12), (1.15, 18)):
        slab(bm, (x, -hy - 0.12, 0.75), (0.05, 0.05, 1.5), M["wood"], pitch=-ang)
    finish(rig, smooth_angle=30.0)
    return {"category": "buildings", "budget": "building", "footprint": (4.0, 4.0),
            "render": {"target_z": 1.3, "close_distance": 8.0, "squad_offset": (0.0, -4.0), "rts_distance": 22.0}}


def greenhouse():
    """Serre : muret de brique, armature blanche, vitrage, toit vitré à deux pans,
    plantes visibles derrière les vitres basses. Emprise 4 × 6 m."""
    model = "greenhouse"
    col = start(model)
    rig = Rig(model, col)
    BRICK, WHITE, GLASS, LEAF = (rig.m(n) for n in ("Env_Brick", "Env_Trim:white", "Env_Trim:glass", "Env_Hedge"))
    bm = rig.part("Greenhouse", (0, 0, 0))
    hx, hy, low, wall_top = 1.7, 2.7, 0.6, 2.2
    box(bm, (0, 0, low / 2), (2 * hx, 2 * hy, low), BRICK, bevel=0.02)
    before = set(bm.faces)
    box(bm, (0, 0, (low + wall_top) / 2), (2 * hx - 0.1, 2 * hy - 0.1, wall_top - low), GLASS)
    bm.normal_update()
    bmesh.ops.delete(bm, geom=[f for f in set(bm.faces) - before if f.normal.z > 0.9], context='FACES_ONLY')
    ridge = wall_top + hx * math.tan(math.radians(32))
    for y in (-hy + 0.05, hy - 0.05):
        prism(bm, [(-hx + 0.05, wall_top), (hx - 0.05, wall_top), (0, ridge)], 0.06, Matrix.Translation((0, y, 0)), GLASS)
    for s in (-1, 1):
        run = hx + 0.05
        mid = Vector((s * run / 2, 0, (wall_top + ridge) / 2))
        slab(bm, mid, (run / math.cos(math.radians(32)) + 0.04, 2 * hy, 0.05), GLASS, roll=s * 32)
    # Armature : montants, traverses, chevrons, faîtage.
    for i in range(5):
        y = -hy + i * (2 * hy) / 4
        for s in (-1, 1):
            box(bm, (s * hx, y, (low + wall_top) / 2), (0.08, 0.08, wall_top - low), WHITE)
            a, b = Vector((s * hx, y, wall_top)), Vector((0, y, ridge))
            box(bm, (a + b) / 2 + Vector((0, 0, 0.04)), (0.07, 0.07, (b - a).length), WHITE, rot=align_z(b - a))
    for s in (-1, 1):
        box(bm, (s * hx, 0, wall_top), (0.1, 2 * hy, 0.08), WHITE)
        box(bm, (s * hx, 0, low + 0.04), (0.1, 2 * hy, 0.08), WHITE)
    box(bm, (0, 0, ridge + 0.04), (0.12, 2 * hy + 0.1, 0.1), WHITE)
    # Porte vitrée à l'avant.
    box(bm, (0, -hy - 0.03, (low + 2.05) / 2 - 0.25), (0.9, 0.06, 2.05 - low + 0.5), WHITE)
    box(bm, (0, -hy - 0.07, 1.1), (0.7, 0.04, 1.4), GLASS)
    # Plantes en pot à l'intérieur, dépassant du muret.
    rnd = random.Random(21)
    for i in range(6):
        x, y = rnd.choice((-1, 1)) * (hx - 0.45), -hy + 0.6 + i * 0.8
        blob(bm, (x, y, low + 0.3), (0.35, 0.32, 0.3), LEAF, subdiv=2, noise=0.25, seed=30 + i)
    finish(rig, smooth_angle=30.0)
    return {"category": "buildings", "budget": "building", "footprint": (4.0, 6.0),
            "render": {"target_z": 1.4, "close_distance": 10.0, "squad_offset": (0.0, -5.0), "rts_distance": 24.0}}


def crypt():
    """Crypte (côté zombies) : caveau de pierre à fronton et colonnes, porte de fer
    rouillé entrouverte, marches usées, mousse. Emprise 6 × 6 m."""
    model = "crypt"
    col = start(model)
    rig = Rig(model, col)
    WALL, SLAB, IRON, MOSS = (rig.m(n) for n in ("Env_StoneWall", "Env_CryptSlab", "Env_RustyIron", "Env_Moss"))
    bm = rig.part("Crypt", (0, 0, 0))
    rnd = random.Random(31)
    hx, hy = 2.0, 2.2
    box(bm, (0, 0.2, 0.2), (2 * hx + 0.6, 2 * hy + 0.4, 0.4), SLAB, bevel=0.04)          # socle
    for i, (d, h) in enumerate(((0.5, 0.13), (0.35, 0.26))):                             # marches
        box(bm, (0, -hy - 0.25 - d / 2 + 0.35, h / 2), (2.0, d, h), SLAB, bevel=0.03)
    before = set(bm.faces)
    box(bm, (0, 0.3, 0.4 + 1.5), (2 * hx, 2 * hy - 0.2, 3.0), WALL)
    bm.normal_update()
    bmesh.ops.delete(bm, geom=[f for f in set(bm.faces) - before if f.normal.z > 0.9], context='FACES_ONLY')
    top = 3.4
    box(bm, (0, 0.2, top + 0.12), (2 * hx + 0.4, 2 * hy + 0.2, 0.24), SLAB, bevel=0.04)  # entablement
    prism(bm, [(-hx - 0.2, top + 0.24), (hx + 0.2, top + 0.24), (0, top + 1.25)], 0.4,
          Matrix.Translation((0, -hy + 0.05, 0)), SLAB)                                   # fronton
    slab(bm, (0, 0.4, top + 0.6), (2 * hx + 0.2, 2 * hy - 0.4, 0.5), WALL)                # toit
    # Colonnes de part et d'autre de la porte.
    for s in (-1, 1):
        x = s * 1.35
        lathe(bm, [(0, 0.4), (0.3, 0.4), (0.3, 0.55), (0.22, 0.65), (0.2, 3.2), (0.3, 3.3), (0.3, top), (0, top)],
              10, Matrix.Translation((x, -hy - 0.15, 0)), SLAB)
    # Porte de fer rouillé entrouverte, linteau gravé.
    box(bm, (0, -hy - 0.02, 0.4 + 1.2), (1.5, 0.12, 2.4), SLAB)
    slab(bm, (-0.35, -hy - 0.25, 0.4 + 1.1), (0.7, 0.08, 2.1), IRON, yaw=-28)
    slab(bm, (0.36, -hy - 0.1, 0.4 + 1.1), (0.7, 0.08, 2.1), IRON)
    for k in range(4):
        slab(bm, (0.36, -hy - 0.15, 0.4 + 0.3 + k * 0.5), (0.72, 0.04, 0.06), IRON)
    text_mesh(bm, "R.I.P.", Matrix.Translation((0, -hy - 0.2, top - 0.25)), 0.32, 0.04, IRON)
    # Mousse et lierre sur les arêtes.
    for c, r in (((-hx, -hy + 0.3, 3.3), (0.35, 0.3, 0.2)), ((hx, -hy + 0.4, 0.7), (0.3, 0.3, 0.35)),
                 ((hx - 0.2, hy, 2.8), (0.4, 0.25, 0.3)), ((-hx - 0.1, hy - 0.5, 0.5), (0.35, 0.3, 0.3))):
        blob(bm, c, r, MOSS, subdiv=2, noise=0.3, seed=rnd.randint(0, 99))
    finish(rig, smooth_angle=35.0)
    return {"category": "buildings", "budget": "building", "footprint": (6.0, 6.0),
            "render": {"target_z": 2.0, "close_distance": 13.0, "squad_offset": (0.0, -6.0), "zombies": True,
                       "rts_distance": 28.0}}


def corner_shop():
    """Épicerie de quartier : façade de brique, grandes vitrines, store rayé, enseigne,
    toit plat à acrotère, climatiseur. Corps 8 × 7 m, emprise 10 × 10 m."""
    model = "corner_shop"
    col = start(model)
    rig = Rig(model, col)
    M = {"walls": rig.m("Env_Brick"), "white": rig.m("Env_Trim:white"), "glass": rig.m("Env_Trim:glass"),
         "red": rig.m("Env_Paint:red"), "paper": rig.m("Env_Paint:white"), "yellow": rig.m("Env_Paint:yellow"),
         "metal": rig.m("Env_Metal")}
    bm = rig.part("Shop", (0, 0, 0))
    hx, hy, top = 4.0, 3.5, 4.2
    F = facades(hx, hy, (0.0, 0.5))
    before = set(bm.faces)
    box(bm, (0, 0.5, top / 2), (2 * hx, 2 * hy, top), M["walls"])
    bm.normal_update()
    bmesh.ops.delete(bm, geom=[f for f in set(bm.faces) - before if f.normal.z > 0.9], context='FACES_ONLY')
    # Toit plat (gravillons = métal) entouré d'un acrotère blanc.
    box(bm, (0, 0.5, top - 0.05), (2 * hx - 0.1, 2 * hy - 0.1, 0.1), M["metal"])
    for f, length in ((F["front"], 2 * hx + 0.3), (F["back"], 2 * hx + 0.3), (F["right"], 2 * hy), (F["left"], 2 * hy)):
        f.slab(bm, 0, 0.05, top + 0.2, length, 0.25, 0.4, M["white"])
        f.slab(bm, 0, 0.05, 0.15, length, 0.1, 0.3, M["white"])
    # Vitrines et porte vitrée.
    front = F["front"]
    for u in (-2.4, 2.4):
        front.slab(bm, u, 0.03, 1.55, 2.4, 0.04, 2.0, M["glass"])
        for du in (-1.25, 0.0, 1.25):
            front.slab(bm, u + du, 0.08, 1.55, 0.1, 0.1, 2.1, M["white"])
        front.slab(bm, u, 0.12, 0.5, 2.7, 0.2, 0.1, M["white"])
        front.slab(bm, u, 0.08, 2.6, 2.6, 0.1, 0.1, M["white"])
    front.slab(bm, 0, 0.03, 1.25, 1.2, 0.04, 2.3, M["glass"])
    for du in (-0.65, 0.65):
        front.slab(bm, du, 0.08, 1.25, 0.12, 0.1, 2.5, M["white"])
    front.slab(bm, 0, 0.08, 2.45, 1.4, 0.1, 0.12, M["white"])
    # Store rayé rouge et blanc, incliné, sur toute la façade.
    stripes = 12
    for i in range(stripes):
        x = -hx + (i + 0.5) * (2 * hx / stripes)
        slab(bm, (x, 0.5 - hy - 0.65, 3.05), (2 * hx / stripes + 0.005, 1.4, 0.06), M["red"] if i % 2 else M["paper"],
             pitch=-22)
    box(bm, (0, 0.5 - hy - 1.3, 2.78), (2 * hx, 0.06, 0.25), M["red"])
    # Enseigne.
    front.slab(bm, 0, 0.1, 3.7, 4.6, 0.12, 0.7, M["yellow"], bevel=0.03)
    text_mesh(bm, "ÉPICERIE", Matrix.Translation(front.p(0, 0.19, 3.62)), 0.48, 0.05, M["red"])
    # Fenêtres latérales et arrière, climatiseur et porte de service.
    for f, us in ((F["right"], (-1.5, 1.5)), (F["left"], (0.0,)), (F["back"], (2.0,))):
        for u in us:
            _window(bm, f, u, 2.0, {"glass": M["glass"], "white": M["white"], "accent": M["red"],
                                    "wood": M["white"]}, shutters=False)
    box(bm, (1.5, 0.5 + 1.0, top + 0.35), (1.2, 0.9, 0.7), M["metal"], bevel=0.04)
    F["back"].slab(bm, -1.8, 0.04, 1.1, 1.0, 0.06, 2.2, M["metal"])
    finish(rig, smooth_angle=30.0)
    return {"category": "buildings", "budget": "building", "footprint": (10.0, 10.0),
            "render": {"target_z": 2.2, "close_distance": 17.0, "squad_offset": (0.0, -8.0), "rts_distance": 32.0}}


BUILDERS = {f.__name__: f for f in (house_a, house_b, house_two_story, house_haunted, garage, garden_shed,
                                    greenhouse, crypt, corner_shop)}

if __name__ == "__main__":
    run(BUILDERS)
