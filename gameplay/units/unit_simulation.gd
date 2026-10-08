class_name UnitSimulation
extends Node
## Simulation des unités et des escouades, au tick physique fixe.
##
## Ne connaît ni l'affichage ni les entrées : elle expose son état (squads, units),
## que les autres systèmes lisent. Les ordres arrivent par issue_order().
## Mise en pause avec l'arbre de scène (pause tactique).

signal squad_spawned(squad: Squad)

@export_group("Déplacement")
## Distance (m) en deçà de laquelle une unité ralentit en approchant de son emplacement.
@export var arrive_radius: float = 1.2

@export_group("Évitement")
## Marge (m) ajoutée aux rayons des unités pour la séparation douce.
@export var separation_margin: float = 0.2
## Intensité de la répulsion entre unités trop proches (m/s).
@export var separation_strength: float = 4.0
## Vitesse (m/s) en dessous de laquelle une unité garde l'orientation de sa formation.
@export var facing_speed_threshold: float = 0.6

var squads: Array[Squad] = []
var units: Array[Unit] = []

var _squads_by_id: Dictionary[int, Squad] = {}
var _grid := SpatialHashGrid.new(2.0)
var _max_unit_radius: float = 0.0
var _next_unit_id: int = 0
var _next_squad_id: int = 0


func spawn_squad(data: SquadData, team: int, position: Vector3, facing: float) -> Squad:
	var squad := Squad.new(_next_squad_id, data, team, position, facing)
	_next_squad_id += 1
	for i in data.unit_count:
		var unit := Unit.new(_next_unit_id, data.unit_data, team, squad.slot_position(i), facing)
		_next_unit_id += 1
		unit.squad_id = squad.id
		unit.slot_index = i
		squad.units.append(unit)
		units.append(unit)
		_max_unit_radius = maxf(_max_unit_radius, data.unit_data.radius)
	squads.append(squad)
	_squads_by_id[squad.id] = squad
	squad_spawned.emit(squad)
	return squad


func get_squad(squad_id: int) -> Squad:
	return _squads_by_id.get(squad_id)


## Remplace l'ordre en cours d'une escouade.
func issue_order(squad: Squad, order: SquadOrder) -> void:
	squad.order = order
	order.start(squad)


func _physics_process(delta: float) -> void:
	for unit in units:
		unit.previous_position = unit.position
		unit.previous_yaw = unit.yaw
	_update_orders(delta)
	_rebuild_grid()
	_steer_units(delta)
	_resolve_overlaps()
	_update_facing(delta)


func _update_orders(delta: float) -> void:
	for squad in squads:
		squad.anchor_velocity = Vector3.ZERO
		if squad.order != null and squad.order.update(squad, delta):
			squad.order = null


func _rebuild_grid() -> void:
	_grid.clear()
	for i in units.size():
		_grid.insert(i, units[i].position)


## Chaque unité suit la vitesse de son ancre et corrige l'écart à son emplacement,
## plus une répulsion douce envers ses voisines (toutes escouades confondues).
func _steer_units(delta: float) -> void:
	for i in units.size():
		var unit := units[i]
		var squad := _squads_by_id[unit.squad_id]
		var to_slot := squad.slot_position(unit.slot_index) - unit.position
		to_slot.y = 0.0
		var distance := to_slot.length()
		var max_speed := unit.data.move_speed

		var desired := squad.anchor_velocity
		if distance > 0.02:
			desired += to_slot / distance * max_speed * minf(distance / arrive_radius, 1.0)
		desired += _separation(i)
		desired = desired.limit_length(max_speed)

		unit.velocity = unit.velocity.move_toward(desired, unit.data.acceleration * delta)
		unit.position += unit.velocity * delta


func _separation(index: int) -> Vector3:
	var unit := units[index]
	var push := Vector3.ZERO
	var search_radius := unit.data.radius + _max_unit_radius + separation_margin
	for j in _grid.query(unit.position, search_radius):
		if j == index:
			continue
		var other := units[j]
		var offset := unit.position - other.position
		offset.y = 0.0
		var min_distance := unit.data.radius + other.data.radius + separation_margin
		var distance_squared := offset.length_squared()
		if distance_squared >= min_distance * min_distance:
			continue
		var distance := sqrt(distance_squared)
		var direction := offset / distance if distance > 0.0001 else _tie_break_direction(unit, other)
		push += direction * (1.0 - distance / min_distance) * separation_strength
	return push


## Correction de position : garantit qu'aucune paire d'unités ne se chevauche,
## quelle que soit la force des autres comportements.
func _resolve_overlaps() -> void:
	_rebuild_grid()
	for i in units.size():
		var unit := units[i]
		for j in _grid.query(unit.position, unit.data.radius + _max_unit_radius):
			if j <= i:
				continue
			var other := units[j]
			var offset := unit.position - other.position
			offset.y = 0.0
			var min_distance := unit.data.radius + other.data.radius
			var distance := offset.length()
			if distance >= min_distance:
				continue
			var direction := offset / distance if distance > 0.0001 else _tie_break_direction(unit, other)
			var correction := direction * (min_distance - distance) * 0.5
			unit.position += correction
			other.position -= correction


func _update_facing(delta: float) -> void:
	for unit in units:
		var target_yaw := _squads_by_id[unit.squad_id].facing
		var flat_velocity := Vector2(unit.velocity.x, unit.velocity.z)
		if flat_velocity.length() > facing_speed_threshold:
			target_yaw = atan2(flat_velocity.x, flat_velocity.y)
		unit.yaw = rotate_toward(unit.yaw, target_yaw, deg_to_rad(unit.data.turn_speed_degrees) * delta)


## Direction déterministe pour séparer deux unités exactement superposées.
func _tie_break_direction(unit: Unit, other: Unit) -> Vector3:
	var angle := float(unit.id * 7919 + other.id) * 0.618
	return Vector3(cos(angle), 0.0, sin(angle))
