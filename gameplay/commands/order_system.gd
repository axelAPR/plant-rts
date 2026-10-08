class_name OrderSystem
extends Node
## Transforme une intention (du joueur ou de l'IA) en ordres d'escouade.
##
## Un ordre de groupe donne à chaque escouade sa propre destination : les escouades
## se placent côte à côte, sur plusieurs rangs dès que la ligne dépasserait
## `max_line_width`. Les escouades peuvent être superposées à d'autres, sauf si
## `move_settings.avoid_occupied_destinations` : chaque destination prend alors
## l'emplacement libre le plus proche (voir FormationSpace).

@export var simulation: UnitSimulation
## Réglages transmis aux ordres de déplacement (blocage, délais, destinations).
@export var move_settings: MoveOrderSettings = MoveOrderSettings.new()

@export_group("Ordres de groupe")
## Espace (m) laissé entre deux escouades voisines d'un même rang.
@export var squad_gap: float = 2.0
## Espace (m) laissé entre deux rangs.
@export var row_gap: float = 2.0
## Largeur (m) maximale d'un rang ; au-delà, les escouades forment un rang de plus.
@export var max_line_width: float = 40.0
## En deçà de cette distance (m), un ordre de déplacement garde l'orientation actuelle.
@export var min_turn_distance: float = 1.0


func issue_move(squads: Array[Squad], target: Vector3) -> void:
	if squads.is_empty():
		return
	target.y = 0.0

	var group_center := Vector3.ZERO
	for squad in squads:
		group_center += squad.get_center()
	group_center /= squads.size()

	var direction := target - group_center
	direction.y = 0.0
	var facing := squads[0].facing
	if direction.length() > min_turn_distance:
		facing = atan2(direction.x, direction.z)
	var basis := Basis(Vector3.UP, facing)
	var lateral := basis * Vector3.RIGHT
	var forward := basis * Vector3.MODEL_FRONT

	var space := FormationSpace.new(move_settings.reservation_margin)
	if move_settings.avoid_occupied_destinations:
		space = FormationSpace.from_simulation(simulation, move_settings.reservation_margin, squads)
	for placement in _layout_rows(squads, lateral, forward):
		var squad: Squad = placement[0]
		var offset: Vector2 = placement[1]
		var half := squad.get_footprint_half_extents()
		var destination := space.find_free(target + lateral * offset.x + forward * offset.y, half, facing,
				move_settings.free_search_radius, move_settings.free_search_step, -forward)
		space.add(destination, half, facing)
		simulation.issue_order(squad, MoveOrder.new(destination, facing, move_settings))


## Attaque : chaque escouade s'approche de `target` et la prend pour cible. Les
## escouades du même camp que la cible sont ignorées.
func issue_attack(squads: Array[Squad], target: Squad) -> void:
	for squad in squads:
		if target != null and squad.team != target.team and squad.data.unit_data.can_attack():
			simulation.issue_order(squad, AttackOrder.new(target.id))


func issue_stop(squads: Array[Squad]) -> void:
	for squad in squads:
		simulation.issue_order(squad, StopOrder.new())


## Disposition du groupe en rangs : renvoie [escouade, décalage] dans l'ordre de
## placement (premier rang d'abord), décalage = (latéral, avant) par rapport à la cible.
## Les escouades les plus avancées vers la cible forment le premier rang ; dans un rang,
## elles sont triées selon leur position latérale actuelle (trajectoires sans croisement).
## Le bloc de rangs est centré sur la cible.
func _layout_rows(squads: Array[Squad], lateral: Vector3, forward: Vector3) -> Array[Array]:
	var by_depth: Array[Squad] = squads.duplicate()
	by_depth.sort_custom(func(a: Squad, b: Squad) -> bool:
		return a.get_center().dot(forward) > b.get_center().dot(forward))

	var rows: Array[Array] = []
	var row_widths: Array[float] = []
	for squad in by_depth:
		var width := squad.get_footprint_half_extents().x * 2.0
		if rows.is_empty() or row_widths[-1] + squad_gap + width > max_line_width:
			rows.append([])
			row_widths.append(-squad_gap)
		rows[-1].append(squad)
		row_widths[-1] += squad_gap + width

	var row_depths: Array[float] = []
	var total_depth := row_gap * (rows.size() - 1)
	for row in rows:
		var depth := 0.0
		for squad: Squad in row:
			depth = maxf(depth, squad.get_footprint_half_extents().y * 2.0)
		row_depths.append(depth)
		total_depth += depth

	var placements: Array[Array] = []
	var front := total_depth * 0.5
	for r in rows.size():
		var row: Array = rows[r]
		row.sort_custom(func(a: Squad, b: Squad) -> bool:
			return a.get_center().dot(lateral) < b.get_center().dot(lateral))
		var row_center := front - row_depths[r] * 0.5
		front -= row_depths[r] + row_gap
		var cursor := -row_widths[r] * 0.5
		for squad: Squad in row:
			var width := squad.get_footprint_half_extents().x * 2.0
			placements.append([squad, Vector2(cursor + width * 0.5, row_center)])
			cursor += width + squad_gap
	return placements
