# plantRTS — Pisto-pois : animations. À exécuter sur le modèle construit
# (peashooter.blend, ou après build_peashooter()), après prts_lib.py.
#
# Walk : trot sautillant, deux bonds par cycle (balancement gauche puis droite).
# - 24 i/s, 16 images = 0,667 s ; chaque bond (8 images) couvre ~1,2 m à 3,5 m/s ;
# - image 0 = pose de repos exacte : le jeu peut s'arrêter en fin de cycle sans saut ;
# - pièces rigides : racine (bond + écrasement/étirement), tige (inclinaison avant +
#   roulis), tête (retard sur la tige, hochement), feuilles (balayage de jupe).
#
# Convention d'axes (Blender, avant = -Y) : rotation X positive = penche vers l'avant ;
# rotation Y = roulis latéral ; rotation Z = lacet.

WALK_FRAMES = 16


def _walk_hop(side):
    """Un bond (images 0 à 8) ; `side` = +1 ou -1 alterne le balancement."""
    s = side
    return {
        "Peashooter": {  # racine : hauteur du bond, écrasement à l'appel, étirement en poussée
            0: {"loc": (0, 0, 0), "scale": (1, 1, 1)},
            1: {"loc": (0, 0, 0), "scale": (1.07, 1.07, 0.88)},
            3: {"loc": (0, 0, 0.08), "scale": (0.95, 0.95, 1.09)},
            5: {"loc": (0, 0, 0.15), "scale": (1, 1, 1.02)},
            7: {"loc": (0, 0, 0.05), "scale": (0.97, 0.97, 1.05)},
        },
        "Stem": {  # inclinaison avant à la poussée, roulis vers le côté du bond
            0: {"rot": (0, 0, 0)},
            1: {"rot": (4, 3 * s, 0)},
            3: {"rot": (11, 7 * s, 2 * s)},
            5: {"rot": (7, 6 * s, 4 * s)},
            7: {"rot": (3, 2 * s, 2 * s)},
        },
        "Head": {  # suit la tige avec retard : recule à la poussée, hoche à la réception
            0: {"rot": (0, 0, 0)},
            1: {"rot": (6, -1 * s, 0)},
            3: {"rot": (-5, -3 * s, 0)},
            5: {"rot": (1, -4 * s, -3 * s)},
            7: {"rot": (7, -2 * s, -1 * s)},
        },
        "Leaves": {  # la jupe de feuilles tourne légèrement dans le sens du balancement
            0: {"rot": (0, 0, 0)},
            3: {"rot": (0, 0, 4 * s)},
            5: {"rot": (0, 0, 8 * s)},
            7: {"rot": (0, 0, 4 * s)},
        },
    }


def animate_peashooter():
    keys = {}
    for i, side in enumerate((1, -1)):
        for obj, frames in _walk_hop(side).items():
            dst = keys.setdefault(obj, {})
            for f, pose in frames.items():
                dst[i * 8 + f] = pose
    for obj in keys:  # fin de cycle = repos (boucle sans raccord)
        keys[obj][WALK_FRAMES] = keys[obj][0]
    add_animation("Walk", keys)
    scene = bpy.context.scene
    scene.render.fps = 24
    scene.frame_start, scene.frame_end = 0, WALK_FRAMES
