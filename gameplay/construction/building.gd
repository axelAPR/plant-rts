class_name Building
extends RefCounted
## Bâtiment de la simulation (sans nœud) : identité, camp, position, points de vie,
## état et file de production. Piloté par BuildingSystem, affiché par
## BuildingRenderer (qui ne le modifie jamais).

enum State { CONSTRUCTING, ACTIVE, DESTROYED }

var id: int
var data: BuildingData
var team: int
## Pivot au sol.
var position: Vector3
## Orientation (radians, autour de Y) : l'avant du modèle (+Z) tourné de `yaw`.
var yaw: float
var hp: float
var state: State = State.ACTIVE
## Avancement de la construction (0..1) ; 1 pour un bâtiment posé terminé.
var construction_progress: float = 1.0
var queue: ProductionQueue
## Point de ralliement des escouades produites (au sol).
var rally_point: Vector3


func _init(p_id: int, p_data: BuildingData, p_team: int, p_position: Vector3, p_yaw: float) -> void:
	id = p_id
	data = p_data
	team = p_team
	position = Vector3(p_position.x, 0.0, p_position.z)
	yaw = p_yaw
	hp = p_data.max_hp
	queue = ProductionQueue.new(p_data.queue_capacity)
	rally_point = get_exit_position() + get_forward() * p_data.rally_distance


func is_alive() -> bool:
	return state != State.DESTROYED


func is_active() -> bool:
	return state == State.ACTIVE


## Direction de l'avant (sortie) au sol.
func get_forward() -> Vector3:
	return Basis(Vector3.UP, yaw) * Vector3.BACK


## Point de sortie des escouades produites.
func get_exit_position() -> Vector3:
	return position + Basis(Vector3.UP, yaw) * data.exit_offset


## Demi-côtés de l'emprise au sol, dans le repère de FormationSpace (x, z).
func get_half_extents() -> Vector2:
	return data.footprint_size * 0.5


## Le point (au sol) est-il sur l'emprise du bâtiment ?
func contains_point(point: Vector3) -> bool:
	var local := Basis(Vector3.UP, yaw).inverse() * (point - position)
	var half := get_half_extents()
	return absf(local.x) <= half.x and absf(local.z) <= half.y
