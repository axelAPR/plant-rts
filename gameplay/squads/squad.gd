class_name Squad
extends RefCounted
## État de simulation d'une escouade : ses unités, sa formation et son ordre en cours.
## L'escouade est l'unité de commandement : la sélection et les ordres passent par elle.
##
## La formation suit une ancre (point de référence) orientée selon `facing` ; chaque
## unité vise son emplacement autour de l'ancre. Les ordres ne déplacent que l'ancre.

var id: int
var data: SquadData
var team: int
var units: Array[Unit] = []

## Centre de référence de la formation.
var anchor: Vector3
## Vitesse de l'ancre (m/s) au tick courant, transmise aux unités pour qu'elles la suivent.
var anchor_velocity: Vector3 = Vector3.ZERO
## Orientation de la formation (rad), même convention que Unit.yaw.
var facing: float
## Ordre en cours ; null = au repos (les unités gardent leur emplacement).
var order: SquadOrder = null

var _slot_offsets: PackedVector3Array


func _init(p_id: int, p_data: SquadData, p_team: int, p_anchor: Vector3, p_facing: float) -> void:
	id = p_id
	data = p_data
	team = p_team
	anchor = p_anchor
	facing = p_facing
	_slot_offsets = Formation.compute_offsets(data.unit_count, data.formation_columns, data.formation_spacing)


func slot_position(slot: int) -> Vector3:
	return anchor + Basis(Vector3.UP, facing) * _slot_offsets[slot]


## Barycentre réel des unités (différent de l'ancre quand la formation est en mouvement).
func get_center() -> Vector3:
	if units.is_empty():
		return anchor
	var sum := Vector3.ZERO
	for unit in units:
		sum += unit.position
	return sum / units.size()


func get_move_speed() -> float:
	return data.unit_data.move_speed


## Largeur au sol de la formation (m), encombrement des unités compris.
func get_formation_width() -> float:
	var columns := mini(data.formation_columns, units.size())
	return (columns - 1) * data.formation_spacing + 2.0 * data.unit_data.radius


## Écart maximal (m) entre une unité et son emplacement : mesure la cohésion.
func get_formation_error() -> float:
	var error := 0.0
	for unit in units:
		var offset := slot_position(unit.slot_index) - unit.position
		offset.y = 0.0
		error = maxf(error, offset.length())
	return error


## Réattribue les emplacements (après un changement d'orientation ou d'ancre) en
## limitant les croisements entre unités.
func reassign_slots() -> void:
	var positions := PackedVector3Array()
	var slots := PackedVector3Array()
	for i in units.size():
		positions.append(units[i].position)
		slots.append(slot_position(i))
	var assignment := Formation.assign_slots(positions, slots)
	for i in units.size():
		units[i].slot_index = assignment[i]
