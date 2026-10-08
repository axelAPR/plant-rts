class_name Unit
extends RefCounted
## État de simulation d'une unité. Aucune dépendance aux nœuds : la représentation
## visuelle lit cet état sans jamais le modifier.

var id: int
var data: UnitData
## Camp de l'unité (0 = joueur) ; générique pour les plantes comme pour les zombies.
var team: int
## Identifiant de l'escouade. Pas de référence directe : Squad référence déjà ses
## unités, et un cycle entre RefCounted ne serait jamais libéré.
var squad_id: int = -1
## Index de l'emplacement occupé dans la formation de l'escouade.
var slot_index: int = 0
## Au repos, l'unité a renoncé à rejoindre son emplacement (occupé par d'autres
## unités) : elle reste où elle est au lieu de courir sur place. Levé dès que
## l'emplacement se libère ou qu'un nouvel ordre réattribue les emplacements.
var holding: bool = false
## Plus petite distance (m) à l'emplacement atteinte depuis le dernier progrès.
var slot_best_distance: float = INF
## Temps (s) écoulé sans se rapprocher de l'emplacement, ou passé sur place une fois
## l'emplacement abandonné.
var slot_stuck_time: float = 0.0

var position: Vector3
var velocity: Vector3 = Vector3.ZERO
## Orientation (rad) autour de Y ; 0 = regarde vers +Z (Vector3.MODEL_FRONT).
var yaw: float

## État au tick précédent, pour interpoler l'affichage entre deux ticks physiques.
var previous_position: Vector3
var previous_yaw: float

## Combat (voir CombatSystem). Points de vie propres au membre.
var health: float
## Mort : le membre ne tire plus, ne compte plus et est retiré de la simulation.
var alive: bool = true
## Temps (s) restant avant que le membre puisse tirer à nouveau.
var attack_cooldown_left: float = 0.0
## Cible actuelle (id d'unité, -1 = aucune). Un id plutôt qu'une référence : deux
## unités qui se ciblent mutuellement formeraient un cycle jamais libéré.
var target_id: int = -1
## Délai (s) avant de rechercher une nouvelle cible.
var retarget_time_left: float = 0.0
## Orientation (rad) vers la cible ; utilisée à l'arrêt quand `aiming`.
var aim_yaw: float = 0.0
var aiming: bool = false


func _init(p_id: int, p_data: UnitData, p_team: int, p_position: Vector3, p_yaw: float) -> void:
	id = p_id
	data = p_data
	team = p_team
	position = p_position
	previous_position = p_position
	yaw = p_yaw
	previous_yaw = p_yaw
	health = p_data.member_hp


## Reprend la recherche de l'emplacement (progression remise à zéro).
func release_hold() -> void:
	holding = false
	slot_best_distance = INF
	slot_stuck_time = 0.0
