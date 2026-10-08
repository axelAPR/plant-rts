class_name UnitData
extends Resource
## Définition d'un type d'unité (plante, zombie…), partagée par toutes ses instances.

@export_group("Identité")
@export var id: StringName = &""
@export var display_name: String = ""
## Faction (plantes, zombies…) : noms et couleurs des ressources de son coût.
@export var faction: FactionData

@export_group("Représentation")
## Scène visuelle (modèle importé) : pivot au sol, orientée vers +Z (Vector3.MODEL_FRONT).
@export var visual_scene: PackedScene
## Modèle local prioritaire, utilisé à la place de `visual_scene` s'il existe sur la
## machine : contenus non publiés (ex. modèles issus de Garden Warfare 2, dans des
## dossiers ignorés par Git). Absent (dépôt cloné) → `visual_scene`.
@export_file("*.glb", "*.gltf", "*.tscn", "*.scn") var local_visual_path: String = ""

@export_group("Déplacement")
## Vitesse maximale (m/s).
@export var move_speed: float = 3.5
## Accélération (m/s²).
@export var acceleration: float = 14.0
## Vitesse de rotation (degrés/s).
@export var turn_speed_degrees: float = 540.0
## Rayon du corps (m) : tronc, pieds — ni bras, ni armes, ni feuilles. Sert aux
## collisions et à l'évitement entre unités.
@export var radius: float = 0.35
## Rayon de l'emprise visuelle complète (m), armes et feuilles comprises : anneau de
## sélection, clic, et emprise des formations pour réserver les destinations.
@export var footprint_radius: float = 0.55


@export_group("Combat")
## Points de vie d'un membre (HP individuels : chaque membre d'une escouade a les siens).
@export var member_hp: float = 100.0
## Dégâts infligés par UN tir réussi d'UN membre (pas un DPS).
@export var damage_per_shot: float = 0.0
## Probabilité (0 à 1) qu'un tir arrivé sur sa cible la touche, tirée pour chaque tir.
@export_range(0.0, 1.0) var accuracy: float = 1.0:
	set(value):
		accuracy = clampf(value, 0.0, 1.0)
## Délai (s) entre deux tirs d'un même membre.
@export var attack_cooldown: float = 1.0
## Portée (m), mesurée jusqu'au bord du corps de la cible. 0 = n'attaque pas.
@export var attack_range: float = 0.0
## Projectile tiré ; null = attaque de mêlée (sans projectile).
@export var projectile: ProjectileData
## Vitesse (m/s) des projectiles de cette unité.
@export var projectile_speed: float = 30.0
## Hauteur (m) de départ des projectiles (bouche du canon, environ).
@export var muzzle_height: float = 0.9
## Hauteur (m) du volume touchable (cylindre de rayon `radius`).
@export var hit_height: float = 1.5


## Peut attaquer : portée et dégâts définis.
func can_attack() -> bool:
	return attack_range > 0.0 and damage_per_shot > 0.0


func is_melee() -> bool:
	return projectile == null


## Scène à afficher : le modèle local s'il est présent, sinon le modèle publié.
func get_visual_scene() -> PackedScene:
	if not local_visual_path.is_empty() and ResourceLoader.exists(local_visual_path):
		var local := load(local_visual_path) as PackedScene
		if local != null:
			return local
	return visual_scene
