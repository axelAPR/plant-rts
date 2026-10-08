# plantRTS — Kit d'environnement : points de jeu (capture, ressources).
# blender -b --python blender/scripts/environment/gameplay.py -- [ids…] [--render]
#
# Règles communes : emprise circulaire de 5 m de rayon ; trois états dans le même
# modèle, objets séparés à afficher ou masquer (State_Neutral, State_Plants,
# State_Zombies) ; mât (Pole) et drapeau (Flag) séparés, pivot à leur base, pour
# animer la prise plus tard. L'état d'un camp se lit de loin par l'anneau coloré.

import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from env_lib import *  # noqa: F401,F403
import bpy
import prts_lib as P
from mathutils import Vector, Matrix, Quaternion

RADIUS = 5.0
DISK_Z = 0.12           # dessus du dallage
SEG = 36
MARKER_R = 4.8
MARKER_ANGLES = (45, 135, 225, 315)
POLE_BASE = 0.42
POLE_HEIGHT = 4.6
FLAG_Z = 3.55           # base du drapeau (pivot), sur le mât


def _platform(bm, mi, pole_at=(0.0, 0.0)):
    """Dalle circulaire à bordure arrondie, socle du mât (au centre par défaut)."""
    inner = 0.75 if pole_at == (0.0, 0.0) else 0.0
    lathe(bm, [(inner, DISK_Z), (4.55, DISK_Z), (4.68, 0.27), (4.92, 0.27), (RADIUS, 0.0)], SEG,
          Matrix.Identity(4), mi)
    lathe(bm, [(0, POLE_BASE), (0.5, POLE_BASE), (0.66, 0.34), (0.75, 0.2), (0.75, DISK_Z - 0.01)], 16,
          Matrix.Translation((pole_at[0], pole_at[1], 0)), mi)
    # Quatre dalles d'accès légèrement surélevées (repères de la grille).
    for a in (0, 90, 180, 270):
        d = Quaternion((0, 0, 1), math.radians(a)) @ Vector((0, -1, 0))
        slab(bm, d * 3.0 + Vector((0, 0, DISK_Z + 0.02)), (1.1, 1.6, 0.06), mi, yaw=a)


def _ring(bm, mi):
    """Anneau de couleur sur le dallage : l'état se lit de loin."""
    lathe(bm, [(3.9, DISK_Z + 0.04), (4.45, DISK_Z + 0.04), (4.5, DISK_Z - 0.005)],
          SEG, Matrix.Identity(4), mi)


def _flag(rig, mi, pivot):
    """Drapeau ondulé (deux faces, épaisseur) le long de +X depuis le mât."""
    bm = rig.part("Flag", pivot, "Pole")
    cols, w, h = 6, 1.5, 0.95
    top, bot = [], []
    for i in range(cols + 1):
        x = pivot.x + 0.06 + w * i / cols
        y = pivot.y + 0.22 * math.sin(i / cols * math.pi * 1.8) * (0.3 + i / cols)
        droop = 0.12 * (i / cols) ** 2
        top.append((Vector((x, y, pivot.z + h - droop)), Vector((x, y, pivot.z + droop * 0.5))))
    verts = []
    for side in (-0.02, 0.02):
        verts.append([(bm.verts.new(a + Vector((0, side, 0))), bm.verts.new(b + Vector((0, side, 0)))) for a, b in top])
    faces = []
    for i in range(cols):
        faces.append(bm.faces.new((verts[0][i][1], verts[0][i + 1][1], verts[0][i + 1][0], verts[0][i][0])))
        faces.append(bm.faces.new((verts[1][i][0], verts[1][i + 1][0], verts[1][i + 1][1], verts[1][i][1])))
        faces.append(bm.faces.new((verts[0][i][0], verts[0][i + 1][0], verts[1][i + 1][0], verts[1][i][0])))
        faces.append(bm.faces.new((verts[1][i][1], verts[1][i + 1][1], verts[0][i + 1][1], verts[0][i][1])))
    faces.append(bm.faces.new((verts[0][-1][0], verts[0][-1][1], verts[1][-1][1], verts[1][-1][0])))
    faces.append(bm.faces.new((verts[1][0][0], verts[1][0][1], verts[0][0][1], verts[0][0][0])))
    for f in faces:
        f.material_index = mi


def _markers_neutral(bm, stone, neutral):
    for a in MARKER_ANGLES:
        p = Quaternion((0, 0, 1), math.radians(a)) @ Vector((MARKER_R, 0, 0))
        lathe(bm, [(0, 0.95), (0.12, 0.95), (0.2, 0.85), (0.2, 0.28), (0.24, 0.24)], 8,
              Matrix.Translation(p), stone)
        ellipsoid(bm, p + Vector((0, 0, 0.98)), (0.16, 0.16, 0.12), neutral, u=8, v=5)


def _markers_plants(bm, green):
    """Grandes pousses feuillues aux quatre repères, fleur de feuilles autour du mât."""
    for a in MARKER_ANGLES:
        p = Quaternion((0, 0, 1), math.radians(a)) @ Vector((MARKER_R, 0, 0.26))
        tube_path(bm, [p, p + Vector((0.06, 0, 0.6)), p + Vector((0, 0.04, 1.25))], [0.09, 0.07, 0.05], 6, green)
        for k, (yaw, L, z) in enumerate(((a + 20, 0.8, 0.55), (a + 200, 0.75, 0.85))):
            mtx = Matrix.Translation(p + Vector((0, 0, z))) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')                 @ Matrix.Rotation(math.radians(25), 4, 'X')
            organic_leaf(bm, L, 0.3, mtx, green, n=3, lift=0.1, droop=0.22, fold=0.06, th=0.04)
    for k in range(5):
        mtx = Matrix.Rotation(math.radians(36 + 72 * k), 4, 'Z') @ Matrix.Translation((0, 0.72, DISK_Z + 0.02))
        organic_leaf(bm, 1.5, 0.55, mtx, green, n=3, lift=0.12, droop=0.1, fold=0.08, th=0.04)


def _markers_zombies(bm, stone, purple):
    """Stèles penchées marquées de violet aux repères, dalles fendues de lueurs violettes
    rayonnant autour du mât."""
    for i, a in enumerate(MARKER_ANGLES):
        p = Quaternion((0, 0, 1), math.radians(a)) @ Vector((MARKER_R, 0, 0.24))
        tilt = 9 * (1 if i % 2 else -1)
        slab(bm, p + Vector((0, 0, 0.55)), (0.7, 0.2, 1.1), stone, yaw=a + 90, pitch=tilt, roll=6, bevel=0.08)
        slab(bm, p + Vector((0, 0, 0.75)), (0.5, 0.24, 0.14), purple, yaw=a + 90, pitch=tilt, roll=6, bevel=0.03)
    for k in range(6):
        a = math.radians(60 * k + 15)
        d = Vector((math.cos(a), math.sin(a), 0))
        # Fissure en zigzag : trois tronçons de plus en plus fins.
        pts = [d * 0.8, d * 1.5 + d.cross(Vector((0, 0, 1))) * 0.2, d * 2.2 - d.cross(Vector((0, 0, 1))) * 0.1,
               d * 3.0 + d.cross(Vector((0, 0, 1))) * 0.15]
        for j in range(3):
            a0, a1 = pts[j], pts[j + 1]
            seg = a1 - a0
            slab(bm, (a0 + a1) / 2 + Vector((0, 0, DISK_Z + 0.015)), (seg.length + 0.08, 0.26 - 0.06 * j, 0.05),
                 purple, yaw=math.degrees(math.atan2(seg.y, seg.x)))


def capture_point():
    """Point stratégique, sans ressource : dallage circulaire, mât et drapeau."""
    model = "capture_point"
    col = start(model)
    rig = Rig(model, col)
    STONE, NEUTRAL, GREEN, PURPLE = (rig.m(n) for n in ("Env_Paving", "Env_Cloth", "Env_PlantTeam", "Env_ZombieTeam"))
    _platform(rig.part("Base", (0, 0, 0)), STONE)
    bm = rig.part("Pole", (0, 0, POLE_BASE))
    cyl(bm, (0, 0, POLE_BASE), (0, 0, POLE_BASE + POLE_HEIGHT), 0.09, 0.07, NEUTRAL, seg=8)
    ellipsoid(bm, (0, 0, POLE_BASE + POLE_HEIGHT + 0.08), (0.15, 0.15, 0.15), NEUTRAL, u=8, v=6)
    _flag(rig, NEUTRAL, Vector((0, 0, FLAG_Z)))
    bm = rig.part("State_Neutral", (0, 0, 0))
    _ring(bm, NEUTRAL)
    _markers_neutral(bm, STONE, NEUTRAL)
    bm = rig.part("State_Plants", (0, 0, 0))
    _ring(bm, GREEN)
    _markers_plants(bm, GREEN)
    bm = rig.part("State_Zombies", (0, 0, 0))
    _ring(bm, PURPLE)
    _markers_zombies(bm, STONE, PURPLE)
    finish(rig, smooth_angle=40.0)
    return {"category": "gameplay", "budget": "building", "footprint": (10.0, 10.0), "render": None,
            "states": ("State_Neutral", "State_Plants", "State_Zombies")}


def render_states(model_id, states):
    """Un rendu de près par état, et un rendu en caméra de jeu (état plantes) avec
    une escouade pour l'échelle."""
    os.makedirs(CAPTURE_DIR, exist_ok=True)
    def show(only):
        for s in states:
            o = bpy.data.objects[s]
            o.hide_render = s != only
            o.hide_viewport = s != only
    for s in states:
        show(s)
        P.preview_render(os.path.join(CAPTURE_DIR, "%s_close_%s.png" % (model_id, s[6:].lower())),
                         target=(0, 0, 1.2), distance=14.0, yaw_deg=-30, pitch_deg=30, lens=40.0, size=(900, 700))
    show("State_Plants")
    pea = scale_collection("_ScalePeashooter",
                           os.path.join(ROOT, "assets", "plants", "peashooter.glb"))
    inst = [(pea, (-1.8 + (i % 3) * 1.8, -7.5 - (i // 3) * 1.8, 0), 180.0) for i in range(6)]
    P.preview_render(os.path.join(CAPTURE_DIR, model_id + "_rts.png"), target=(0, -2.5, 0.5), distance=32.0,
                     yaw_deg=-30, pitch_deg=rts_pitch(32.0), lens=RTS_LENS, size=(960, 540), instances=inst)
    show(None)
    for s in states:
        bpy.data.objects[s].hide_render = False
        bpy.data.objects[s].hide_viewport = False


# ---------------------------------------------------------------- Points de ressource
# Même plateforme que le point de capture ; mât et drapeau sur le bord (la structure
# occupe le centre). Hauteur de la structure selon la ressource (silhouette) :
# principale ≈ 3 m, secondaire ≈ 2 m, tertiaire ≈ 1 m. Anneau à la couleur de la
# ressource du camp (data/factions) ; l'état neutre garde la silhouette sous une bâche.

POLE_AT = (-2.3, 2.3)
STATES = ("State_Neutral", "State_Plants", "State_Zombies")


def _resource_rig(model, plant_mat, zombie_mat):
    col = start(model)
    rig = Rig(model, col)
    M = {"stone": rig.m("Env_Paving"), "cloth": rig.m("Env_Cloth"), "plant": rig.m(plant_mat),
         "zombie": rig.m(zombie_mat)}
    _platform(rig.part("Base", (0, 0, 0)), M["stone"], pole_at=POLE_AT)
    pole = Vector((POLE_AT[0], POLE_AT[1], POLE_BASE))
    bm = rig.part("Pole", pole)
    cyl(bm, pole, pole + Vector((0, 0, POLE_HEIGHT)), 0.09, 0.07, M["cloth"], seg=8)
    ellipsoid(bm, pole + Vector((0, 0, POLE_HEIGHT + 0.08)), (0.15, 0.15, 0.15), M["cloth"], u=8, v=6)
    _flag(rig, M["cloth"], Vector((POLE_AT[0], POLE_AT[1], FLAG_Z)))
    parts = {s: rig.part(s, (0, 0, 0)) for s in STATES}
    _ring(parts["State_Neutral"], M["cloth"])
    _ring(parts["State_Plants"], M["plant"])
    _ring(parts["State_Zombies"], M["zombie"])
    return rig, M, parts


def _tarp(bm, mi, radius, height, seed):
    """Bâche tendue sur la structure (état neutre) : même silhouette, couleur neutre."""
    blob(bm, (0, 0, height * 0.5), (radius, radius, height * 0.5), mi, subdiv=3, noise=0.12, seed=seed,
         flatten_bottom=-0.98)
    for a in (0, 120, 240):                      # cordes et piquets
        d = Quaternion((0, 0, 1), math.radians(a)) @ Vector((1, 0, 0))
        cyl(bm, d * radius * 0.8 + Vector((0, 0, height * 0.5)), d * (radius + 0.6) + Vector((0, 0, DISK_Z)), 0.02,
            0.02, mi, seg=4)


def _info_point():
    return {"category": "gameplay", "budget": "building", "footprint": (10.0, 10.0), "states": STATES}


def resource_point_primary():
    """Ressource principale (Soleil / Cerveaux). Plantes : trois capteurs de soleil en
    corolle autour d'un soleil sur piédestal ; zombies : cuve ouverte débordant de
    cerveaux. Structure ≈ 3 m."""
    rig, M, S = _resource_rig("resource_point_primary", "Env_Sun", "Env_Brain")
    _tarp(S["State_Neutral"], M["cloth"], 1.6, 3.0, 300)
    bm = S["State_Plants"]
    lathe(bm, [(0.7, DISK_Z), (0.6, 0.5), (0.3, 1.4), (0.25, 1.9), (0.0, 1.95)], 10, Matrix.Identity(4), M["cloth"])
    ellipsoid(bm, (0, 0, 2.35), (0.5, 0.5, 0.5), M["plant"], u=12, v=8)
    for k in range(3):                           # capteurs : tige + disque incliné vers le ciel
        a = math.radians(30 + 120 * k)
        d = Vector((math.cos(a), math.sin(a), 0))
        base, top = d * 0.6 + Vector((0, 0, DISK_Z)), d * 1.45 + Vector((0, 0, 2.3))
        cyl(bm, base, top, 0.08, 0.06, M["cloth"], seg=6)
        q = align_z(d * 0.6 + Vector((0, 0, 1)))
        dome(bm, top, 0.75, 0.75, 0.22, M["plant"], seg=12, steps=2, rot=q)
        for r in range(6):                       # pétales autour du capteur
            pa = 2 * math.pi * r / 6
            off = q @ Vector((0.85 * math.cos(pa), 0.85 * math.sin(pa), 0.02))
            ellipsoid(bm, top + off, (0.26, 0.22, 0.05), M["plant"], rot=q @ Quaternion((0, 0, 1), pa), u=5, v=3)
    bm = S["State_Zombies"]
    lathe(bm, [(1.15, DISK_Z), (1.2, 0.3), (1.15, 1.6), (1.25, 1.7), (1.05, 1.72), (1.0, 1.4), (0.0, 1.4)], 14,
          Matrix.Identity(4), M["cloth"])
    for k in range(4):                           # cerclages et pieds de la cuve
        a = math.radians(45 + 90 * k)
        d = Vector((math.cos(a), math.sin(a), 0))
        cyl(bm, d * 1.1 + Vector((0, 0, 0.6)), d * 1.5 + Vector((0, 0, DISK_Z)), 0.07, 0.07, M["cloth"], seg=5)
    rnd = random.Random(310)
    for i in range(6):                           # cerveaux qui débordent
        x, y = rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6)
        blob(bm, (x, y, 1.6 + rnd.uniform(0, 0.5)), (0.42, 0.36, 0.3), M["zombie"], subdiv=2, noise=0.35, seed=320 + i)
    blob(bm, (0.0, 0.0, 2.55), (0.55, 0.45, 0.4), M["zombie"], subdiv=2, noise=0.3, seed=330)
    finish(rig, smooth_angle=45.0)
    return _info_point()


def _gear(bm, center, radius, teeth, thick, axis_q, mi):
    """Roue dentée : disque épais, dents rectangulaires, moyeu."""
    m = Matrix.Translation(Vector(center)) @ axis_q.to_matrix().to_4x4()
    lathe(bm, [(0.0, -thick / 2), (radius, -thick / 2), (radius, thick / 2), (0.0, thick / 2)], teeth * 2, m, mi)
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        p = m @ Vector(((radius + 0.1) * math.cos(a), (radius + 0.1) * math.sin(a), 0))
        q = axis_q @ Quaternion((0, 0, 1), a)
        box(bm, p, (0.22, 0.18, thick), mi, rot=q)
    lathe(bm, [(0.0, thick / 2), (radius * 0.3, thick / 2 + 0.08), (0.0, thick / 2 + 0.1)], 8, m, mi)


def resource_point_secondary():
    """Ressource secondaire (Engrais / Engrenages). Plantes : silo à engrais et sacs ;
    zombies : machine à trois roues dentées. Structure ≈ 2 m."""
    rig, M, S = _resource_rig("resource_point_secondary", "Env_Fertilizer", "Env_Gears")
    _tarp(S["State_Neutral"], M["cloth"], 1.5, 2.0, 340)
    bm = S["State_Plants"]
    lathe(bm, [(0.75, DISK_Z), (0.75, 1.3), (0.55, 1.75), (0.15, 1.95), (0.0, 1.97)], 12,
          Matrix.Translation((0.2, 0.3, 0)), M["plant"])
    for k in range(4):                           # pieds du silo
        a = math.radians(45 + 90 * k)
        d = Vector((math.cos(a), math.sin(a), 0))
        cyl(bm, Vector((0.2, 0.3, 0)) + d * 0.7 + Vector((0, 0, 0.6)), Vector((0.2, 0.3, 0)) + d * 0.95 + Vector((0, 0, DISK_Z)),
            0.05, 0.05, M["cloth"], seg=4)
    rnd = random.Random(350)
    for i, (x, y, z) in enumerate(((-0.9, -0.6, 0.3), (-0.3, -0.95, 0.3), (-0.65, -0.75, 0.62), (0.75, -0.8, 0.3))):
        before = set(bm.verts)
        slab(bm, (x, y, z), (0.7, 0.45, 0.32), M["plant"] if i % 2 else M["cloth"], yaw=rnd.uniform(-30, 30), bevel=0.1)
        jitter([v for v in bm.verts if v not in before], 0.02, seed=360 + i)
    bm = S["State_Zombies"]
    box(bm, (0, 0, 0.45), (1.8, 1.0, 0.7), M["cloth"], bevel=0.06)
    qx = Quaternion((1, 0, 0), math.radians(90))
    _gear(bm, (-0.45, 0.0, 1.35), 0.6, 8, 0.2, qx, M["zombie"])
    _gear(bm, (0.5, -0.05, 1.05), 0.45, 7, 0.2, qx @ Quaternion((0, 0, 1), 0.2), M["zombie"])
    _gear(bm, (0.15, 0.1, 1.85), 0.35, 6, 0.18, qx, M["zombie"])
    cyl(bm, (0.75, 0.3, 0.8), (0.75, 0.3, 2.1), 0.12, 0.1, M["cloth"], seg=6)          # cheminée
    finish(rig, smooth_angle=40.0)
    return _info_point()


def resource_point_tertiary():
    """Ressource tertiaire (Terre / Pesticides). Plantes : butte de terre riche, pots
    et pelle ; zombies : fûts de pesticide et flaque toxique. Structure ≈ 1 m."""
    rig, M, S = _resource_rig("resource_point_tertiary", "Env_Soil", "Env_Pesticide")
    _tarp(S["State_Neutral"], M["cloth"], 1.7, 1.0, 370)
    bm = S["State_Plants"]
    blob(bm, (0, 0, DISK_Z), (1.6, 1.3, 0.75), M["plant"], subdiv=3, noise=0.25, seed=380, flatten_bottom=-0.05)
    for i, (x, y) in enumerate(((1.6, -0.9), (1.9, -0.3), (-1.7, -0.8))):         # pots de terre cuite
        lathe(bm, [(0.0, DISK_Z), (0.18, DISK_Z), (0.25, DISK_Z + 0.35), (0.28, DISK_Z + 0.38), (0.0, DISK_Z + 0.36)], 8,
              Matrix.Translation((x, y, 0)), M["plant"])
    slab(bm, (0.3, -0.2, 1.1), (0.05, 0.05, 1.0), M["cloth"], roll=18, pitch=10)    # pelle plantée
    slab(bm, (0.15, -0.15, 0.55), (0.25, 0.03, 0.32), M["cloth"], roll=18, pitch=10)
    bm = S["State_Zombies"]
    prof = [(0.0, DISK_Z), (0.36, DISK_Z), (0.4, DISK_Z + 0.4), (0.4, DISK_Z + 0.95), (0.0, DISK_Z + 0.95)]
    for x, y in ((-0.5, -0.3), (0.45, -0.45), (0.0, 0.5)):
        lathe(bm, prof, 10, Matrix.Translation((x, y, 0)), M["zombie"])
        for z in (0.35, 0.8):
            lathe(bm, [(0.405, DISK_Z + z - 0.03), (0.42, DISK_Z + z), (0.405, DISK_Z + z + 0.03)], 10,
                  Matrix.Translation((x, y, 0)), M["cloth"])
    lathe(bm, prof, 10, Matrix.Translation((1.3, 0.4, 0.4)) @ Matrix.Rotation(math.radians(90), 4, 'X')
          @ Matrix.Translation((0, 0, -0.5)), M["zombie"])                              # fût renversé
    poly = [(1.1 + 0.9 * math.cos(2 * math.pi * k / 10) * (0.7 + 0.3 * ((k * 7) % 3) / 2),
             -0.6 + 0.6 * math.sin(2 * math.pi * k / 10)) for k in range(10)]
    extrude_xy(bm, poly, DISK_Z, DISK_Z + 0.015, M["zombie"])                        # flaque toxique
    finish(rig, smooth_angle=40.0)
    return _info_point()


BUILDERS = {f.__name__: f for f in (capture_point, resource_point_primary, resource_point_secondary,
                                    resource_point_tertiary)}

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ids = [a for a in argv if not a.startswith("--")] or list(BUILDERS)
    for model_id in ids:
        info = BUILDERS[model_id]()
        rep = check(model_id, info["budget"], info["footprint"])
        rep.update(export(model_id, info["category"]))
        if "--render" in argv:
            render_states(model_id, info["states"])
        print("REPORT", model_id, {k: rep[k] for k in ("triangles", "materials", "footprint", "height", "size",
                                                       "objects", "problems")})
