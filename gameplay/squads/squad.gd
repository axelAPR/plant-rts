class_name Squad
extends RefCounted
## État de simulation d'une escouade : ses unités, sa formation et son ordre en cours.
## L'escouade est l'unité de commandement : la sélection et les ordres passent par elle.
##
## La formation suit une ancre (point de référence) orientée selon `facing` ; chaque
## unité vise son emplacement autour de l'ancre. Les ordres ne déplacent que l'ancre.
## La forme est organique (Formation.compute_organic_offsets) : chaque escouade a sa
## variante, et en tire une nouvelle à chaque déplacement (vary_formation).

## Écart minimal (m) entre deux corps voisins d'une formation organique.
const MIN_SLOT_GAP := 0.3

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
var _slot_yaws: PackedFloat32Array
## Numéro de la variante de forme en cours (graine déterministe avec l'id).
var _variant: int = 0


func _init(p_id: int, p_data: SquadData, p_team: int, p_anchor: Vector3, p_facing: float) -> void:
	id = p_id
	data = p_data
	team = p_team
	anchor = p_anchor
	facing = p_facing
	_build_formation()


func slot_position(slot: int) -> Vector3:
	return slot_position_from(anchor, facing, slot)


## Position de l'emplacement si la formation était centrée sur `center` et orientée
## selon `p_facing` (ex. : places finales à la destination d'un ordre).
func slot_position_from(center: Vector3, p_facing: float, slot: int) -> Vector3:
	return center + Basis(Vector3.UP, p_facing) * _slot_offsets[slot]


## Orientation (rad) de l'unité au repos sur cet emplacement.
func slot_yaw(slot: int) -> float:
	return facing + _slot_yaws[slot]


## Tire une nouvelle variante de la forme (même allure, autre disposition).
func vary_formation() -> void:
	_variant += 1
	_build_formation()


func _build_formation() -> void:
	var seed := hash(Vector2i(id, _variant))
	var min_distance := maxf(2.0 * data.unit_data.radius + MIN_SLOT_GAP,
			data.formation_spacing * (1.0 - data.formation_irregularity))
	_slot_offsets = Formation.compute_organic_offsets(data.unit_count, data.formation_columns,
			data.formation_spacing, data.formation_irregularity, min_distance, seed)
	_slot_yaws = Formation.compute_slot_yaws(data.unit_count, data.formation_yaw_jitter_degrees, seed + 1)


## Barycentre réel des unités (différent de l'ancre quand la formation est en mouvement).
func get_center() -> Vector3:
	if units.is_empty():
		return anchor
	var sum := Vector3.ZERO
	for unit in units:
		sum += unit.position
	return sum / units.size()


## Vitesse (m/s) de l'unité la plus rapide de l'escouade.
func get_max_unit_speed() -> float:
	var fastest := 0.0
	for unit in units:
		fastest = maxf(fastest, unit.velocity.length())
	return fastest


func get_move_speed() -> float:
	return data.unit_data.move_speed


## Largeur au sol de la formation (m), emprise visuelle des unités comprise.
func get_formation_width() -> float:
	return get_footprint_half_extents().x * 2.0


## Demi-dimensions (m) de l'emprise au sol de la formation, emprise visuelle des unités
## comprise : x = demi-largeur, y = demi-profondeur (repère de la formation). Borne
## valable pour toutes les variantes organiques (grille + irrégularité maximale).
func get_footprint_half_extents() -> Vector2:
	return footprint_half_extents(data, units.size())


static func footprint_half_extents(p_data: SquadData, count: int) -> Vector2:
	var n := maxi(count, 1)
	var columns := clampi(p_data.formation_columns, 1, n)
	var rows := ceili(float(n) / columns)
	var margin := p_data.unit_data.footprint_radius
	if n > 1:
		margin += p_data.formation_spacing * p_data.formation_irregularity
	return Vector2((columns - 1) * p_data.formation_spacing * 0.5 + margin,
			(rows - 1) * p_data.formation_spacing * 0.5 + margin)


## Au repos : aucun ordre en cours.
func is_idle() -> bool:
	return order == null


## Position que l'escouade réserve : la destination de son ordre en cours, ou son ancre
## au repos. Les autres ordres choisissent leurs destinations hors de cette emprise.
func get_reserved_position() -> Vector3:
	return anchor if order == null else order.reserved_position(self)


func get_reserved_facing() -> float:
	return facing if order == null else order.reserved_facing(self)


## Écart maximal (m) entre une unité et son emplacement : mesure la cohésion.
func get_formation_error() -> float:
	var error := 0.0
	for unit in units:
		var offset := slot_position(unit.slot_index) - unit.position
		offset.y = 0.0
		error = maxf(error, offset.length())
	return error


## Réattribue les emplacements (après un changement d'orientation, d'ancre ou de forme)
## en limitant les croisements entre unités. Les unités reprennent la recherche de leur
## emplacement (voir Unit.holding).
func reassign_slots() -> void:
	for unit in units:
		unit.release_hold()
	var positions := PackedVector3Array()
	var slots := PackedVector3Array()
	for i in units.size():
		positions.append(units[i].position)
		slots.append(slot_position(i))
	var assignment := Formation.assign_slots(positions, slots)
	for i in units.size():
		units[i].slot_index = assignment[i]
