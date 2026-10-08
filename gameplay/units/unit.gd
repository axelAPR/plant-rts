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


func _init(p_id: int, p_data: UnitData, p_team: int, p_position: Vector3, p_yaw: float) -> void:
	id = p_id
	data = p_data
	team = p_team
	position = p_position
	previous_position = p_position
	yaw = p_yaw
	previous_yaw = p_yaw


## Reprend la recherche de l'emplacement (progression remise à zéro).
func release_hold() -> void:
	holding = false
	slot_best_distance = INF
	slot_stuck_time = 0.0
