class_name UnitSimulation
extends Node
## Simulation des unités et des escouades, au tick physique fixe.
##
## Ne connaît ni l'affichage ni les entrées : elle expose son état (squads, units),
## que les autres systèmes lisent. Les ordres arrivent par issue_order().
## Mise en pause avec l'arbre de scène (pause tactique).
##
## Contacts entre unités :
## - séparation douce entre toutes les unités voisines ;
## - contournement : une unité en marche passe à côté d'une unité d'une autre escouade ;
## - correction dure (aucun recouvrement) : dans une même escouade, entre ennemis, et
##   entre alliés d'escouades différentes seulement si les deux escouades sont à l'arrêt.
##   Des alliés en mouvement ne se bloquent donc jamais mutuellement ;
## - une unité à l'arrêt ne se laisse pas pousser par un ennemi en mouvement : celui-ci
##   encaisse toute la correction (un ennemi ne force pas le passage).
##
## Escouades superposées : au repos, une unité qui ne se rapproche plus de son
## emplacement (occupé) y renonce et reste sur place (Unit.holding) au lieu de courir
## sans fin ; elle repart dès que l'emplacement se libère.

signal squad_spawned(squad: Squad)
## Un membre a été retiré (mort) ; son escouade le référence encore dans le signal.
signal unit_removed(unit: Unit, squad: Squad)
## L'escouade n'a plus aucun membre : elle est retirée de la simulation.
signal squad_destroyed(squad: Squad)

@export_group("Déplacement")
## Distance (m) en deçà de laquelle une unité ralentit en approchant de son emplacement.
@export var arrive_radius: float = 1.2

@export_group("Évitement")
## Marge (m) ajoutée aux rayons des unités pour la séparation douce.
@export var separation_margin: float = 0.2
## Intensité de la répulsion entre unités trop proches (m/s).
@export var separation_strength: float = 4.0
## Distance (m), au-delà du contact, à partir de laquelle une unité en marche contourne
## une unité d'une autre escouade située devant elle.
@export var avoidance_distance: float = 1.2
## Intensité du contournement latéral (m/s).
@export var avoidance_strength: float = 2.5
## Vitesse (m/s) en dessous de laquelle une unité garde l'orientation de sa formation.
@export var facing_speed_threshold: float = 0.6
## Formation à l'arrêt (ancre immobile) : en deçà de cette distance (m) de sa place,
## une unité s'y replace sans se retourner (pas de côté ou en arrière).
@export var face_slot_distance: float = 1.5

@export_group("Repos")
## Délai (s) sans se rapprocher de son emplacement après lequel une unité au repos y
## renonce et reste sur place.
@export var slot_give_up_time: float = 1.0
## Rapprochement minimal (m) de l'emplacement pour compter comme un progrès.
@export var slot_min_progress: float = 0.05
## Distance (m) à l'emplacement en deçà de laquelle l'unité est considérée en place.
@export var slot_reached_distance: float = 0.15
## Durée (s) minimale sur place avant de retenter un emplacement redevenu libre (évite
## de repartir sans cesse vers un emplacement libre mais inaccessible).
@export var slot_retry_time: float = 3.0

var squads: Array[Squad] = []
var units: Array[Unit] = []

var _squads_by_id: Dictionary[int, Squad] = {}
var _units_by_id: Dictionary[int, Unit] = {}
var _grid := SpatialHashGrid.new(2.0)
var _max_unit_radius: float = 0.0
## Par index d'unité : 1 si son escouade a un ordre en cours (mis à jour à chaque tick).
var _moving := PackedByteArray()
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
		_units_by_id[unit.id] = unit
		_max_unit_radius = maxf(_max_unit_radius, data.unit_data.radius)
	squads.append(squad)
	_squads_by_id[squad.id] = squad
	squad_spawned.emit(squad)
	return squad


func get_squad(squad_id: int) -> Squad:
	return _squads_by_id.get(squad_id)


## Unité vivante d'id `unit_id`, ou null (inconnue ou retirée).
func get_unit(unit_id: int) -> Unit:
	return _units_by_id.get(unit_id)


## Retire un membre (mort). Son emplacement de formation reste libre ; une escouade
## sans membre est retirée à son tour. À appeler entre deux ticks (pas pendant step).
func remove_unit(unit: Unit) -> void:
	if not _units_by_id.has(unit.id):
		return
	unit.alive = false
	_units_by_id.erase(unit.id)
	units.erase(unit)
	var squad := get_squad(unit.squad_id)
	if squad == null:
		return
	squad.units.erase(unit)
	unit_removed.emit(unit, squad)
	if squad.units.is_empty():
		squads.erase(squad)
		_squads_by_id.erase(squad.id)
		squad.order = null
		squad_destroyed.emit(squad)


## Remplace l'ordre en cours d'une escouade.
func issue_order(squad: Squad, order: SquadOrder) -> void:
	squad.order = order
	order.start(squad, self)


func _physics_process(delta: float) -> void:
	step(delta)


## Avance la simulation d'un tick. Appelé au tick physique ; les tests peuvent
## l'appeler directement (physique désactivée) pour simuler vite et de façon reproductible.
func step(delta: float) -> void:
	for unit in units:
		unit.previous_position = unit.position
		unit.previous_yaw = unit.yaw
	_update_orders(delta)
	_update_moving_flags()
	_rebuild_grid()
	_steer_units(delta)
	_resolve_overlaps()
	_update_facing(delta)


func _update_orders(delta: float) -> void:
	for squad in squads:
		squad.anchor_velocity = Vector3.ZERO
		if squad.order != null and squad.order.update(squad, self, delta):
			squad.order = null


func _update_moving_flags() -> void:
	_moving.resize(units.size())
	for i in units.size():
		_moving[i] = 0 if _squads_by_id[units[i].squad_id].is_idle() else 1


func _rebuild_grid() -> void:
	_grid.clear()
	for i in units.size():
		_grid.insert(i, units[i].position)


## Chaque unité suit la vitesse de son ancre et corrige l'écart à son emplacement,
## plus une répulsion douce envers ses voisines (toutes escouades confondues) et, en
## marche, un contournement des unités des autres escouades.
func _steer_units(delta: float) -> void:
	for i in units.size():
		var unit := units[i]
		var squad := _squads_by_id[unit.squad_id]
		var to_slot := squad.slot_position(unit.slot_index) - unit.position
		to_slot.y = 0.0
		var distance := to_slot.length()
		var max_speed := unit.data.move_speed

		var desired := squad.anchor_velocity
		if squad.is_idle():
			_update_hold(unit, squad, distance, delta)
		if distance > 0.02 and not unit.holding:
			desired += to_slot / distance * max_speed * minf(distance / arrive_radius, 1.0)
		desired += _neighbour_forces(i, desired)
		desired = desired.limit_length(max_speed)

		unit.velocity = unit.velocity.move_toward(desired, unit.data.acceleration * delta)
		unit.position += unit.velocity * delta


## Au repos : renonce à un emplacement inaccessible (aucun progrès pendant
## slot_give_up_time), et le reprend dès qu'il est libre.
func _update_hold(unit: Unit, squad: Squad, distance: float, delta: float) -> void:
	if unit.holding:
		unit.slot_stuck_time += delta
		if unit.slot_stuck_time >= slot_retry_time and _is_slot_clear(unit, squad.slot_position(unit.slot_index)):
			unit.release_hold()
		return
	if distance <= slot_reached_distance or distance < unit.slot_best_distance - slot_min_progress:
		unit.slot_best_distance = distance
		unit.slot_stuck_time = 0.0
		return
	unit.slot_stuck_time += delta
	if unit.slot_stuck_time >= slot_give_up_time:
		unit.holding = true
		unit.slot_stuck_time = 0.0


## Aucune unité d'une autre escouade n'occupe l'emplacement (corps compris).
func _is_slot_clear(unit: Unit, slot: Vector3) -> bool:
	for j in _grid.query(slot, unit.data.radius + _max_unit_radius):
		var other := units[j]
		if other.squad_id == unit.squad_id:
			continue
		var offset := slot - other.position
		offset.y = 0.0
		var contact := unit.data.radius + other.data.radius
		if offset.length_squared() < contact * contact:
			return false
	return true


func _neighbour_forces(index: int, desired: Vector3) -> Vector3:
	var unit := units[index]
	var push := Vector3.ZERO
	var heading := Vector3.ZERO
	if _moving[index] == 1 and desired.length_squared() > 0.01:
		heading = desired.normalized()
	var avoiding := heading != Vector3.ZERO
	var reach := separation_margin
	if avoiding:
		reach = maxf(separation_margin, avoidance_distance)
	for j in _grid.query(unit.position, unit.data.radius + _max_unit_radius + reach):
		if j == index:
			continue
		var other := units[j]
		var offset := unit.position - other.position
		offset.y = 0.0
		var contact := unit.data.radius + other.data.radius
		var distance_squared := offset.length_squared()

		var min_distance := contact + separation_margin
		if distance_squared < min_distance * min_distance and not _holds_ground(index, j):
			var distance := sqrt(distance_squared)
			var direction := offset / distance if distance > 0.0001 else _tie_break_direction(unit, other)
			push += direction * (1.0 - distance / min_distance) * separation_strength

		var avoid_range := contact + avoidance_distance
		if avoiding and other.squad_id != unit.squad_id and distance_squared < avoid_range * avoid_range 				and distance_squared > 0.000001:
			push += _avoidance(heading, -offset, contact)
	return push


## Contournement d'un obstacle situé à `to_other` (vecteur vers l'obstacle) : poussée
## latérale, nulle si l'obstacle n'est pas devant. Obstacle décalé d'un côté → on passe
## de l'autre ; droit devant → toujours par la droite du sens de marche, pour que deux
## unités face à face s'écartent dans des sens opposés.
func _avoidance(heading: Vector3, to_other: Vector3, contact: float) -> Vector3:
	var distance := to_other.length()
	var direction := to_other / distance
	var ahead := heading.dot(direction)
	if ahead <= 0.0:
		return Vector3.ZERO
	var right := Vector3(heading.z, 0.0, -heading.x)
	var steer := -right if right.dot(direction) > 0.1 else right
	var closeness := clampf(1.0 - (distance - contact) / avoidance_distance, 0.0, 1.0)
	return steer * ahead * closeness * avoidance_strength


## Correction de position : garantit qu'aucune paire d'unités solides l'une pour
## l'autre (voir _is_solid) ne se chevauche, quelle que soit la force des autres
## comportements.
func _resolve_overlaps() -> void:
	_rebuild_grid()
	for i in units.size():
		var unit := units[i]
		for j in _grid.query(unit.position, unit.data.radius + _max_unit_radius):
			if j <= i:
				continue
			if not _is_solid(i, j):
				continue
			var other := units[j]
			var offset := unit.position - other.position
			offset.y = 0.0
			var min_distance := unit.data.radius + other.data.radius
			var distance := offset.length()
			if distance >= min_distance:
				continue
			var direction := offset / distance if distance > 0.0001 else _tie_break_direction(unit, other)
			var correction := direction * (min_distance - distance)
			var share := 0.5
			if _holds_ground(i, j):
				share = 0.0
			elif _holds_ground(j, i):
				share = 1.0
			unit.position += correction * share
			other.position -= correction * (1.0 - share)


## Correction dure entre deux unités : même escouade, camps ennemis, ou alliés dont
## les deux escouades sont à l'arrêt. Alliés en mouvement : séparation douce seulement.
func _is_solid(i: int, j: int) -> bool:
	var a := units[i]
	var b := units[j]
	if a.squad_id == b.squad_id or a.team != b.team:
		return true
	return _moving[i] == 0 and _moving[j] == 0


## L'unité `i`, à l'arrêt, tient sa position face à l'unité `j`, ennemie en mouvement.
func _holds_ground(i: int, j: int) -> bool:
	return _moving[i] == 0 and _moving[j] == 1 and units[i].team != units[j].team


func _update_facing(delta: float) -> void:
	for unit in units:
		var squad := _squads_by_id[unit.squad_id]
		var target_yaw := squad.slot_yaw(unit.slot_index)
		var flat_velocity := Vector2(unit.velocity.x, unit.velocity.z)
		var to_slot := squad.slot_position(unit.slot_index) - unit.position
		to_slot.y = 0.0
		var settling := squad.anchor_velocity == Vector3.ZERO 				and to_slot.length_squared() < face_slot_distance * face_slot_distance
		var walking := flat_velocity.length() > facing_speed_threshold and not settling
		if walking:
			target_yaw = atan2(flat_velocity.x, flat_velocity.y)
		elif unit.aiming:
			# À l'arrêt, le membre se tourne vers sa cible (combat).
			target_yaw = unit.aim_yaw
		unit.yaw = rotate_toward(unit.yaw, target_yaw, deg_to_rad(unit.data.turn_speed_degrees) * delta)


## Direction déterministe pour séparer deux unités exactement superposées.
func _tie_break_direction(unit: Unit, other: Unit) -> Vector3:
	var angle := float(unit.id * 7919 + other.id) * 0.618
	return Vector3(cos(angle), 0.0, sin(angle))
