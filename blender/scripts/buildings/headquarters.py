# plantRTS — Quartiers généraux (bâtiments de jeu) : Arbre de Vie (plantes) et
# Tombeau monumental (zombies).
# blender -b --python blender/scripts/buildings/headquarters.py -- [ids…] [--render=<dossier>]
#
# Même langage que le kit de décor (env_lib : matériaux texturés Env_*, UV en mètres,
# pièces rigides) ; budget propre aux QG (bâtiments uniques et centraux) : ≤ 10 000
# triangles et ≤ 8 matériaux. Pivot au sol au centre de l'emprise (14 × 14 m), entrée
# vers -Y (→ +Z dans Godot : sortie des escouades). Les effets (lueurs, particules)
# sont ajoutés dans les scènes Godot (assets/buildings/<id>.tscn).
# Écrit blender/buildings/<id>.blend, assets/buildings/<id>.glb et le portrait du HUD
# assets/buildings/<id>_portrait.png.

import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import bmesh
from mathutils import Matrix, Vector
import env_lib as E
from env_lib import *  # noqa: F401,F403
import prts_lib as P

BUDGET = 10000
MAX_MATERIALS = 8
FOOTPRINT = (14.0, 14.0)


def _two_tone(verts, center, radii, light, dark, band=-0.3):
    """Feuillage : faces claires au-dessus de la ligne `band`, sombres dessous."""
    for f in {f for v in verts for f in v.link_faces}:
        rel = (f.calc_center_median().z - center[2]) / radii[2]
        f.material_index = light if rel > band else dark


def _bloom(bm, center, normal, size, petal, heart):
    """Fleur-soleil posée sur le feuillage : couronne de pétales et cœur bombé."""
    n = Vector(normal).normalized()
    m = Matrix.Translation(Vector(center)) @ P.align_z(n).to_matrix().to_4x4()
    lathe(bm, [(0.0, -0.05 * size), (1.0 * size, 0.0), (0.0, 0.08 * size)], 14, m, petal, ridge=0.55)
    ellipsoid(bm, Vector(center) + n * 0.12 * size, (0.42 * size, 0.42 * size, 0.2 * size), heart,
              rot=P.align_z(n), u=10, v=5)


# ---------------------------------------------------------------- Arbre de Vie

def tree_of_life():
    """Arbre de Vie : tronc colossal vrillé parcouru de veines de sève lumineuses,
    racines-contreforts, porte en arche éclairée, jupe de feuilles géantes, couronne
    en masses deux tons ornée de fleurs-soleils, lianes. Emprise 14 × 14 m,
    hauteur ≈ 16 m (dessous de la couronne vers 7,5 m : unités visibles dessous)."""
    model = "tree_of_life"
    col = start(model)
    rig = Rig(model, col)
    BARK, LEAF, DARK = rig.m("Env_Bark"), rig.m("Env_Foliage"), rig.m("Env_FoliageDark")
    MOSS, SAP = rig.m("Env_Moss"), rig.m("Env_Sun")
    YELLOW, ORANGE = rig.m("Env_Paint:yellow"), rig.m("Env_Paint:orange")
    bm = rig.part("Tree", (0, 0, 0))
    rnd = random.Random(7)

    # Tronc : vrillé, très évasé au pied, se divise en charpentières vers 7 m.
    trunk = [(0.0, 0.25, 0.0), (0.1, 0.3, 1.5), (0.25, 0.2, 3.5), (0.0, 0.0, 5.5), (-0.2, 0.1, 7.0)]
    tube_path(bm, trunk, [2.6, 2.05, 1.75, 1.55, 1.3], 16, BARK, cap_start=False)
    # Côtes d'écorce torsadées et veines de sève lumineuses entre elles.
    for k in range(6):
        a0 = math.radians(60 * k + 20)
        for vein in (False, True):
            off = 0.5 if vein else 0.0
            pts, rad = [], []
            for i in range(7):
                t = i / 6
                a = a0 + off + t * 1.1
                r = (2.5 if not vein else 2.35) - t * 1.15
                pts.append((math.cos(a) * r, 0.25 + math.sin(a) * r, 0.2 + t * 6.6))
                rad.append((0.36 - t * 0.18) if not vein else 0.11)
            ang = math.degrees(a0 + off) % 360
            if 230 < ang < 310:                                 # porte dégagée (-Y)
                continue
            tube_path(bm, pts, rad, 5 if vein else 6, SAP if vein else BARK)
    # Racines-contreforts : sept bras qui plongent dans le sol, la porte (-Y) dégagée.
    for k, deg in enumerate((-30, 15, 60, 105, 150, 195, 240)):
        a = math.radians(deg + rnd.uniform(-8, 8))
        d = Vector((math.cos(a), math.sin(a), 0.0))
        length = rnd.uniform(5.3, 5.9)
        pts = [d * 1.4 + Vector((0, 0.25, 2.2)), d * 2.9 + Vector((0, 0.25, 1.4)),
               d * (length - 1.6) + Vector((0, 0.25, 0.45)), d * length + Vector((0, 0.25, -0.15))]
        tube_path(bm, pts, [0.95, 0.75, 0.42, 0.2], 9, BARK, cap_start=False)
        if k % 2 == 0:                                       # bulbe de sève lumineux
            p = d * (length - 2.4) + Vector((0, 0.25, 0.75))
            blob(bm, p, (0.36, 0.36, 0.45), SAP, subdiv=2, noise=0.1, seed=40 + k)
    # Porte en arche en relief : intérieur de sève lumineuse, bourrelet d'écorce.
    ellipsoid(bm, (0.0, -1.95, 0.0), (1.3, 0.6, 3.1), SAP, u=16, v=10)
    arch = [(math.cos(math.radians(t)) * 1.55, -2.5 + 0.2 * math.sin(math.radians(t)),
             math.sin(math.radians(t)) * 3.4) for t in range(0, 181, 12)]
    tube_path(bm, arch, [0.42] * len(arch), 8, BARK)
    blob(bm, (0.0, -3.2, 0.0), (2.0, 1.0, 0.25), MOSS, subdiv=2, noise=0.15, seed=3, flatten_bottom=0.0)
    # Jupe de feuilles géantes au pied (identité végétale, lisible de haut).
    for k, deg in enumerate((-10, 40, 85, 130, 175, 215)):
        a = math.radians(deg)
        base = Vector((math.cos(a) * 2.6, math.sin(a) * 2.6 + 0.25, 0.25))
        m = Matrix.Translation(base) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Rotation(math.radians(-12), 4, 'Y')
        organic_leaf(bm, 2.9, 1.4, m, LEAF if k % 2 else DARK, n=6, lift=0.5, droop=0.6, fold=0.25)
    # Charpentières vers la couronne.
    for end in ((3.2, -1.2, 10.0), (-3.4, 0.9, 10.2), (0.6, 3.3, 10.6), (-0.8, -2.6, 11.0), (2.4, 2.4, 11.4)):
        mid = (end[0] * 0.45, end[1] * 0.45 + 0.1, 8.6)
        tube_path(bm, [(-0.2, 0.1, 6.6), mid, end], [1.0, 0.7, 0.42], 9, BARK)
    # Couronne : grandes masses (lisibles de loin), dessous à plus de 7 m.
    masses = (((0.0, 0.3, 12.3), (5.0, 4.8, 3.2), 3), ((3.6, -1.6, 10.6), (3.0, 2.8, 2.3), 3),
              ((-3.6, 1.2, 10.8), (2.85, 2.8, 2.3), 3), ((1.2, 3.8, 11.0), (2.8, 2.5, 2.2), 3),
              ((-1.6, -3.4, 11.3), (2.6, 2.4, 2.1), 3), ((-3.0, -1.8, 13.2), (2.2, 2.1, 1.7), 2),
              ((2.6, 2.0, 13.6), (2.4, 2.2, 1.8), 2), ((0.4, -0.4, 15.0), (2.4, 2.3, 1.4), 2))
    for i, (c, r, sub) in enumerate(masses):
        verts = blob(bm, c, r, LEAF, subdiv=sub, noise=0.22, seed=10 + i)
        _two_tone(verts, c, r, LEAF, DARK, band=-0.35 if sub >= 3 else -0.5)
    # Fleurs-soleils sur la couronne (identité des plantes, lisibles en vue RTS).
    for c, n, s in (((0.0, -4.3, 12.6), (0, -1, 0.35), 1.7), ((4.7, -2.4, 11.4), (1, -0.6, 0.3), 1.4),
                    ((-4.9, -0.4, 11.8), (-1, -0.3, 0.3), 1.4), ((2.2, 4.3, 13.0), (0.4, 1, 0.5), 1.3),
                    ((-2.0, 2.7, 15.0), (-0.3, 0.5, 1), 1.3), ((1.6, -1.8, 16.0), (0.3, -0.4, 1), 1.4),
                    ((5.0, 1.6, 12.4), (1, 0.4, 0.3), 1.2), ((-3.2, -3.6, 13.6), (-0.5, -0.7, 0.6), 1.2)):
        _bloom(bm, c, n, s, YELLOW, ORANGE)
    # Lianes qui pendent de la couronne, terminées par une touffe de feuilles.
    for k in range(9):
        a = math.radians(40 * k + rnd.uniform(-10, 10))
        top = Vector((math.cos(a) * 4.6, math.sin(a) * 4.4 + 0.3, 9.6))
        if top.y < -3.0 and abs(top.x) < 2.2:
            continue
        drop = rnd.uniform(2.0, 3.4)
        pts = [top, top + Vector((0.15, 0.1, -drop * 0.5)), top + Vector((0.05, 0.25, -drop))]
        tube_path(bm, pts, [0.1, 0.08, 0.05], 5, LEAF)
        verts = blob(bm, pts[-1], (0.42, 0.42, 0.36), LEAF, subdiv=2, noise=0.3, seed=60 + k)
        _two_tone(verts, pts[-1], (0.42, 0.42, 0.36), LEAF, DARK, band=-0.2)
    # Mousse au pied du tronc.
    for k in range(5):
        a = math.radians(72 * k + 50)
        blob(bm, (math.cos(a) * 2.6, math.sin(a) * 2.6 + 0.25, 0.25), (1.0, 0.9, 0.45), MOSS, subdiv=2,
             noise=0.25, seed=80 + k, flatten_bottom=-0.5)
    finish(rig, smooth_angle=60.0)
    return {"target_z": 7.5, "distance": 34.0}


# ---------------------------------------------------------------- Tombeau monumental

def zombie_tomb():
    """Tombeau monumental : socle à degrés, mausolée fissuré de lueurs vertes, portique
    à colonnes et fronton au cerveau lumineux, grande porte de fer entrouverte sur une
    lueur verte, toit pyramidal violet et obélisque, pinacles d'angle à flammes vertes,
    antenne de commandement, étendards, braseros, sacs de sable, tombes.
    Emprise 14 × 14 m, hauteur ≈ 15 m."""
    model = "zombie_tomb"
    col = start(model)
    rig = Rig(model, col)
    SLAB, WALL, ROOF = rig.m("Env_CryptSlab"), rig.m("Env_StoneWall"), rig.m("Env_RoofPurple")
    IRON, BRAIN, GLOW = rig.m("Env_RustyIron"), rig.m("Env_Brain"), rig.m("Env_Pesticide")
    CLOTH, BURLAP = rig.m("Env_ZombieTeam"), rig.m("Env_Burlap")
    bm = rig.part("Tomb", (0, 0, 0))
    rnd = random.Random(13)

    # Socle à trois degrés.
    z = 0.0
    for size, h in ((13.6, 0.35), (12.2, 0.35), (10.8, 0.4)):
        box(bm, (0, 0.3, z + h / 2), (size, size - 0.6, h), SLAB, bevel=0.05)
        z += h
    base = z
    # Escalier d'entrée sur le devant.
    for i in range(3):
        box(bm, (0, -6.2 + i * 0.55, 0.18 + i * 0.36), (4.6, 0.6, 0.36 + i * 0.72), SLAB, bevel=0.04)
    # Corps du mausolée (sans dessus : toit posé dessus).
    hx, hy, top = 3.9, 3.6, base + 5.6
    cy = 0.8
    before = set(bm.faces)
    box(bm, (0, cy, (base + top) / 2), (2 * hx, 2 * hy, top - base), WALL)
    bm.normal_update()
    bmesh.ops.delete(bm, geom=[f for f in set(bm.faces) - before if f.normal.z > 0.9], context='FACES_ONLY')
    # Pilastres d'angle, corniche.
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(bm, (sx * hx, cy + sy * hy, (base + top) / 2), (0.8, 0.8, top - base), SLAB, bevel=0.05)
    box(bm, (0, cy, top + 0.2), (2 * hx + 1.0, 2 * hy + 1.0, 0.4), SLAB, bevel=0.06)
    # Toit pyramidal (silhouette), obélisque et orbe vert.
    lathe(bm, [(0, 0), (6.2, 0), (0, 4.2)], 4,
          Matrix.Translation((0, cy, top + 0.4)) @ Matrix.Rotation(math.radians(45), 4, 'Z'), ROOF)
    t = top + 3.4
    lathe(bm, [(0, 0), (0.8, 0), (0.8, 0.35), (0.55, 0.5), (0.36, 3.0), (0.0, 3.7)], 4,
          Matrix.Translation((0, cy, t)) @ Matrix.Rotation(math.radians(45), 4, 'Z'), SLAB)
    blob(bm, (0, cy, t + 3.95), (0.45, 0.45, 0.45), GLOW, subdiv=2, noise=0.05, seed=5)
    # Pinacles d'angle sur le socle, flammes vertes.
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = (sx * 5.7, 0.3 + sy * 5.6, base)
            lathe(bm, [(0, 0), (0.55, 0), (0.55, 0.3), (0.35, 0.45), (0.25, 2.6), (0.0, 3.1)], 4,
                  Matrix.Translation(p) @ Matrix.Rotation(math.radians(45), 4, 'Z'), SLAB)
            blob(bm, (p[0], p[1], base + 3.35), (0.3, 0.3, 0.45), GLOW, subdiv=1, noise=0.3, seed=9 + sx + 3 * sy)
    # Antenne de commandement (mât et paraboles) sur le toit.
    cyl(bm, (2.6, cy + 2.4, top + 0.4), (2.6, cy + 2.4, top + 5.0), 0.09, 0.05, IRON, seg=6)
    for zz, rr in ((top + 2.6, 0.75), (top + 3.9, 0.55)):
        lathe(bm, [(0, 0), (rr, 0.22), (rr, 0.28), (0, 0.06)], 10,
              Matrix.Translation((2.85, cy + 2.4, zz)) @ Matrix.Rotation(math.radians(-70), 4, 'Y'), IRON)
    blob(bm, (2.6, cy + 2.4, top + 5.1), (0.15, 0.15, 0.15), GLOW, subdiv=1, noise=0.0, seed=6)
    # Portique : quatre colonnes, entablement, fronton au cerveau.
    py = -hy + cy - 1.7
    for x in (-3.0, -1.6, 1.6, 3.0):
        lathe(bm, [(0, 0), (0.55, 0), (0.55, 0.3), (0.38, 0.45), (0.34, 4.9), (0.5, 5.1), (0.55, 5.3), (0, 5.3)],
              12, Matrix.Translation((x, py, base)), SLAB)
    ent = base + 5.3
    box(bm, (0, py + 0.4, ent + 0.3), (7.6, 2.4, 0.6), SLAB, bevel=0.05)
    ped_y = py + 0.4
    prism(bm, [(-3.9, ent + 0.6), (3.9, ent + 0.6), (0, ent + 2.6)], 2.0, Matrix.Translation((0, ped_y, 0)), WALL)
    front = ped_y - 1.0                                         # face avant du fronton
    for s in (-1, 1):                                           # rampants
        slab(bm, (s * 1.95, front - 0.12, ent + 1.62), (4.4, 0.3, 0.24), SLAB, roll=s * 27.0)
    # Cerveau sculpté lumineux devant le fronton, inscription sur l'entablement.
    bc = Vector((0, front - 0.25, ent + 1.4))
    for i, (dx, dz, r) in enumerate(((-0.38, 0.05, 0.46), (0.38, 0.05, 0.46), (-0.22, 0.32, 0.4), (0.22, 0.32, 0.4),
                                      (0.0, -0.12, 0.42))):
        blob(bm, bc + Vector((dx, 0, dz)), (r, 0.32, r * 0.85), BRAIN, subdiv=2, noise=0.25, seed=20 + i)
    text_mesh(bm, "ZOMBIES", Matrix.Translation((0, py + 0.4 - 1.2 - 0.04, ent + 0.3)), 0.48, 0.06, IRON)
    # Porte monumentale : chambranle, lueur verte, battants de fer entrouverts.
    door_y = -hy + cy - 0.02
    box(bm, (0, door_y - 0.2, base + 4.35), (3.8, 0.45, 0.5), SLAB)
    for sx in (-1, 1):
        box(bm, (sx * 1.65, door_y - 0.2, base + 2.1), (0.5, 0.45, 4.2), SLAB)
    box(bm, (0, door_y + 0.15, base + 2.05), (2.8, 0.1, 4.1), GLOW)
    slab(bm, (-1.0, door_y - 0.6, base + 2.0), (1.45, 0.14, 3.9), IRON, yaw=-38)
    slab(bm, (0.95, door_y - 0.32, base + 2.0), (1.45, 0.14, 3.9), IRON, yaw=12)
    # Fissures lumineuses sur les murs.
    for k in range(9):
        side = rnd.choice(((1, 0), (-1, 0), (0, 1)))
        if side[0]:
            x, y = side[0] * (hx + 0.02), cy + rnd.uniform(-hy + 0.8, hy - 0.8)
        else:
            x, y = rnd.uniform(-hx + 0.8, hx - 0.8), cy + hy + 0.02
        zz = rnd.uniform(base + 1.0, top - 1.0)
        for s in range(3):
            length = rnd.uniform(0.5, 1.0)
            slab(bm, (x, y, zz - s * 0.6), (0.07 if side[0] else length, length if side[0] else 0.07, 0.07), GLOW,
                 roll=rnd.uniform(-40, 40) if side[0] else 0.0, pitch=0.0 if side[0] else rnd.uniform(-40, 40))
    # Braseros à lueur verte de part et d'autre de l'escalier.
    for sx in (-1, 1):
        x = sx * 3.3
        lathe(bm, [(0, 0), (0.45, 0), (0.25, 0.25), (0.2, 1.0), (0.6, 1.25), (0.75, 1.55), (0, 1.45)], 10,
              Matrix.Translation((x, -5.5, base - 0.75)), IRON)
        blob(bm, (x, -5.5, base + 0.95), (0.5, 0.5, 0.35), GLOW, subdiv=2, noise=0.3, seed=30 + sx)
    # Sacs de sable : murets de part et d'autre de l'entrée (poste de commandement).
    for sx in (-1, 1):
        for i in range(3):
            for row in range(2):
                c = (sx * (4.6 + i * 0.8 - row * 0.4), -5.75, 0.95 + row * 0.36)
                blob(bm, c, (0.44, 0.3, 0.19), BURLAP, subdiv=2, noise=0.12, seed=40 + i + row * 7 + (sx > 0) * 20,
                     flatten_bottom=-0.6)
    # Étendards zombies sur la façade et le long des flancs.
    for sx in (-1, 1):
        box(bm, (sx * 2.35, door_y - 0.1, base + 3.6), (1.1, 0.06, 3.0), CLOTH)
        box(bm, (sx * 2.35, door_y - 0.12, base + 5.15), (1.3, 0.1, 0.12), IRON)
        box(bm, (sx * (hx + 0.06), cy, base + 3.3), (0.06, 1.3, 3.4), CLOTH)
    # Tombes sur le socle.
    for x, y in ((-4.8, 2.6), (-4.6, 4.4), (4.7, 2.2), (4.9, 4.2), (-2.4, 5.6), (2.2, 5.7)):
        slab(bm, (x, y, base + 0.55), (0.75, 0.22, 1.1), SLAB, yaw=rnd.uniform(-12, 12), roll=rnd.uniform(-6, 6))
    finish(rig, smooth_angle=35.0)
    return {"target_z": 5.5, "distance": 32.0}


BUILDERS = {"tree_of_life": tree_of_life, "zombie_tomb": zombie_tomb}


def build(model_id, render_dir=None):
    info = BUILDERS[model_id]()
    E.BUDGET["headquarters"] = BUDGET
    E.MAX_MATERIALS = MAX_MATERIALS
    rep = check(model_id, "headquarters", FOOTPRINT)
    blend = os.path.join(E.ROOT, "blender", "buildings", model_id + ".blend")
    glb = os.path.join(E.ROOT, "assets", "buildings", model_id + ".glb")
    if render_dir:
        os.makedirs(render_dir, exist_ok=True)
        for tag, yaw, pitch, dist in (("front", -25.0, 16.0, 1.0), ("back", 150.0, 20.0, 1.0), ("rts", -20.0, 50.0, 1.6)):
            P.preview_render(os.path.join(render_dir, "%s_%s.png" % (model_id, tag)), target=(0, 0, info["target_z"]),
                             distance=info["distance"] * dist, yaw_deg=yaw, pitch_deg=pitch, size=(900, 900))
    # Portrait du HUD (rendu de notre propre modèle : publiable).
    P.preview_render(os.path.join(E.ROOT, "assets", "buildings", model_id + "_portrait.png"),
                     target=(0, 0, info["target_z"] * 0.95), distance=info["distance"] * 0.95, yaw_deg=-28.0,
                     pitch_deg=14.0, size=(256, 256))
    P.save_and_export(model_id, blend, glb)
    print("REPORT", model_id, {k: rep[k] for k in ("triangles", "materials", "height", "problems")})


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ids = [a for a in argv if not a.startswith("--")] or list(BUILDERS)
    render = next((a.split("=", 1)[1] for a in argv if a.startswith("--render=")), None)
    for model_id in ids:
        build(model_id, render)
