class_name BuildingSystem
extends Node
## Bâtiments de la partie (simulation sans nœud, avancée au tick physique → mise en
## pause avec le jeu) : ajout, points de vie et destruction, files de production,
## préparation de la construction par les unités constructrices.
##
## Production (réutilise ProductionSystem) : à la mise en file, coût et population
## sont réservés (tout ou rien) ; à la fin du temps de production, l'escouade
## apparaît sur un emplacement libre devant la sortie puis rejoint le point de
## ralliement. Sortie encombrée → l'escouade attend (état WAITING_FOR_EXIT) au lieu
## d'apparaître dans le bâtiment. Annulation → remboursement intégral.
##
## Bâtiments de départ : nœuds BuildingSpawn enfants de ce nœud.

enum QueueResult { OK, NOT_ACTIVE, NOT_PRODUCIBLE, QUEUE_FULL, NOT_ENOUGH_PRIMARY, NOT_ENOUGH_SECONDARY,
	NOT_ENOUGH_TERTIARY, NOT_ENOUGH_POPULATION, INVALID }
enum PlacementResult { OK, OUT_OF_BOUNDS, BLOCKED_BY_BUILDING, BLOCKED_BY_UNITS }

signal building_added(building: Building)
signal building_destroyed(building: Building)
## File de production modifiée (ajout, annulation, fin, attente).
signal queue_changed(building: Building)
signal production_completed(building: Building, squad: Squad)
## Une escouade terminée attend une sortie libre.
signal production_waiting(building: Building)
signal construction_completed(building: Building)

@export var simulation: UnitSimulation
@export var production: ProductionSystem
## Facultatif : ordre de déplacement vers le point de ralliement.
@export var order_system: OrderSystem
## Composition des factions (unité constructrice, QG…).
@export var rosters: Array[FactionRoster] = []

@export_group("Sortie des escouades")
## Écart minimal (m) entre une escouade qui apparaît et les escouades ou bâtiments.
@export var spawn_margin: float = 1.0
## Distance (m) maximale de recherche d'un emplacement libre autour de la sortie.
@export var exit_search_radius: float = 30.0

@export_group("Placement")
## Zone où un bâtiment peut être posé (bornes de la carte).
@export var placement_bounds: Rect2 = Rect2(-160.0, -160.0, 320.0, 320.0)
## Marge (m) autour d'un bâtiment posé.
@export var placement_margin: float = 1.0

var buildings: Array[Building] = []

var _next_id: int = 0


func _ready() -> void:
	for child in get_children():
		var spawn := child as BuildingSpawn
		if spawn != null and spawn.data != null:
			add_building(spawn.data, spawn.team, spawn.global_position, spawn.global_rotation.y)


func _physics_process(delta: float) -> void:
	step(delta)


func add_building(data: BuildingData, team: int, position: Vector3, yaw: float,
		state: Building.State = Building.State.ACTIVE) -> Building:
	var building := Building.new(_next_id, data, team, position, yaw)
	_next_id += 1
	building.state = state
	if state == Building.State.CONSTRUCTING:
		building.construction_progress = 0.0
		building.hp = data.max_hp * 0.1
	buildings.append(building)
	building_added.emit(building)
	return building


func get_building(building_id: int) -> Building:
	for building in buildings:
		if building.id == building_id:
			return building
	return null


## QG vivant d'un camp, ou null.
func get_headquarters(team: int) -> Building:
	for building in buildings:
		if building.team == team and building.is_alive() and building.data.is_headquarters:
			return building
	return null


func get_roster(faction: FactionData) -> FactionRoster:
	for roster in rosters:
		if roster.faction == faction:
			return roster
	return null


## Escouades que ce bâtiment peut produire : l'unité constructrice de sa faction (si
## BuildingData.produces_builder), puis BuildingData.producible_squads.
func get_producible(building: Building) -> Array[SquadData]:
	var result: Array[SquadData] = []
	if building.data.produces_builder:
		var roster := get_roster(building.data.faction)
		if roster != null and roster.builder_squad != null:
			result.append(roster.builder_squad)
	for data in building.data.producible_squads:
		if not result.has(data):
			result.append(data)
	return result


# ---------------------------------------------------------------- Production

## Peut-on mettre `data` en file maintenant ? (sans rien modifier)
func can_queue(building: Building, data: SquadData) -> QueueResult:
	if building == null or data == null:
		return QueueResult.INVALID
	if not building.is_active():
		return QueueResult.NOT_ACTIVE
	if not get_producible(building).has(data):
		return QueueResult.NOT_PRODUCIBLE
	if building.queue.is_full():
		return QueueResult.QUEUE_FULL
	return _from_production(production.check(building.team, data))


## Met `data` en file : paie et réserve la population (tout ou rien).
func queue_production(building: Building, data: SquadData) -> QueueResult:
	var result := can_queue(building, data)
	if result != QueueResult.OK:
		return result
	result = _from_production(production.reserve(building.team, data))
	if result != QueueResult.OK:
		return result
	building.queue.items.append(data)
	if building.queue.state == ProductionQueue.State.IDLE:
		building.queue.state = ProductionQueue.State.PRODUCING
	queue_changed.emit(building)
	return QueueResult.OK


## Annule l'élément `index` de la file (remboursement intégral). La tête de file
## annulée perd son avancement.
func cancel_production(building: Building, index: int) -> bool:
	if building == null or index < 0 or index >= building.queue.items.size():
		return false
	var data := building.queue.items[index]
	building.queue.items.remove_at(index)
	production.refund(building.team, data)
	if index == 0:
		building.queue.elapsed = 0.0
		building.queue.state = ProductionQueue.State.PRODUCING
	if building.queue.is_empty():
		building.queue.state = ProductionQueue.State.IDLE
	queue_changed.emit(building)
	return true


func set_rally_point(building: Building, point: Vector3) -> void:
	building.rally_point = Vector3(point.x, 0.0, point.z)


func step(delta: float) -> void:
	for building in buildings:
		if building.is_active() and not building.queue.is_empty():
			_advance_queue(building, delta)


func _advance_queue(building: Building, delta: float) -> void:
	var queue := building.queue
	var data := queue.current()
	queue.elapsed = minf(queue.elapsed + delta, data.build_time)
	if queue.elapsed < data.build_time:
		return
	var spot: Variant = find_exit_spot(building, data)
	if spot == null:
		if queue.state != ProductionQueue.State.WAITING_FOR_EXIT:
			queue.state = ProductionQueue.State.WAITING_FOR_EXIT
			production_waiting.emit(building)
			queue_changed.emit(building)
		return
	queue.items.remove_at(0)
	queue.elapsed = 0.0
	queue.state = ProductionQueue.State.IDLE if queue.is_empty() else ProductionQueue.State.PRODUCING
	var squad := production.spawn_reserved(building.team, data, spot, building.yaw)
	if order_system != null and (spot as Vector3).distance_to(building.rally_point) > 1.0:
		order_system.issue_move([squad], building.rally_point)
	production_completed.emit(building, squad)
	queue_changed.emit(building)


## Emplacement libre pour une escouade `data` devant la sortie, hors des escouades et
## des bâtiments ; null si aucun dans `exit_search_radius`.
func find_exit_spot(building: Building, data: SquadData) -> Variant:
	var space := FormationSpace.from_simulation(simulation, spawn_margin)
	for other in buildings:
		if other.is_alive():
			space.add(other.position, other.get_half_extents(), other.yaw)
	var half := Squad.footprint_half_extents(data, data.unit_count)
	var spot := space.find_free(building.get_exit_position(), half, building.yaw, exit_search_radius, 1.0,
			building.get_forward())
	return spot if space.is_free(spot, half, building.yaw) else null


# ---------------------------------------------------------------- Points de vie

func apply_damage(building: Building, amount: float) -> void:
	if not building.is_alive() or amount <= 0.0:
		return
	building.hp = maxf(building.hp - amount, 0.0)
	if building.hp <= 0.0:
		_destroy(building)


## Destruction : la file est annulée et remboursée (règle provisoire).
func _destroy(building: Building) -> void:
	building.state = Building.State.DESTROYED
	for data in building.queue.items:
		production.refund(building.team, data)
	building.queue.items.clear()
	building.queue.elapsed = 0.0
	building.queue.state = ProductionQueue.State.IDLE
	building_destroyed.emit(building)
	queue_changed.emit(building)


# ---------------------------------------------------------------- Construction (préparée)
# Utilisée plus tard par les unités constructrices (FactionRoster.builder_squad) :
# placement validé, paiement, chantier (CONSTRUCTING) puis bâtiment actif.

## Le bâtiment peut-il être posé ici ? (bornes, autres bâtiments, escouades)
func can_place(data: BuildingData, position: Vector3, yaw: float) -> PlacementResult:
	var half := data.footprint_size * 0.5
	var reach := half.length()
	if not placement_bounds.grow(-reach).has_point(Vector2(position.x, position.z)):
		return PlacementResult.OUT_OF_BOUNDS
	var buildings_space := FormationSpace.new(placement_margin)
	for other in buildings:
		if other.is_alive():
			buildings_space.add(other.position, other.get_half_extents(), other.yaw)
	if not buildings_space.is_free(position, half, yaw):
		return PlacementResult.BLOCKED_BY_BUILDING
	if not FormationSpace.from_simulation(simulation, placement_margin).is_free(position, half, yaw):
		return PlacementResult.BLOCKED_BY_UNITS
	return PlacementResult.OK


## Pose un chantier (paie le coût de construction). Null si le placement ou le
## paiement est impossible (rien n'est alors modifié).
func place_construction(data: BuildingData, team: int, position: Vector3, yaw: float) -> Building:
	if can_place(data, position, yaw) != PlacementResult.OK:
		return null
	var team_economy := production.economy.get_team(team)
	if team_economy == null or not team_economy.spend(data.get_build_cost()):
		return null
	return add_building(data, team, position, yaw, Building.State.CONSTRUCTING)


## Travail de construction (s) ; le chantier devient actif à 100 %.
func add_construction_work(building: Building, seconds: float) -> void:
	if building.state != Building.State.CONSTRUCTING:
		return
	var ratio := seconds / maxf(building.data.build_time, 0.001)
	building.construction_progress = minf(building.construction_progress + ratio, 1.0)
	building.hp = minf(building.hp + building.data.max_hp * 0.9 * ratio, building.data.max_hp)
	if building.construction_progress >= 1.0:
		building.state = Building.State.ACTIVE
		building.hp = building.data.max_hp
		construction_completed.emit(building)


# ---------------------------------------------------------------- Textes

func _from_production(result: ProductionSystem.Result) -> QueueResult:
	match result:
		ProductionSystem.Result.OK:
			return QueueResult.OK
		ProductionSystem.Result.NOT_ENOUGH_PRIMARY:
			return QueueResult.NOT_ENOUGH_PRIMARY
		ProductionSystem.Result.NOT_ENOUGH_SECONDARY:
			return QueueResult.NOT_ENOUGH_SECONDARY
		ProductionSystem.Result.NOT_ENOUGH_TERTIARY:
			return QueueResult.NOT_ENOUGH_TERTIARY
		ProductionSystem.Result.NOT_ENOUGH_POPULATION:
			return QueueResult.NOT_ENOUGH_POPULATION
	return QueueResult.INVALID


## Raison lisible d'un refus, avec les noms de ressources de la faction.
static func queue_result_text(result: QueueResult, faction: FactionData) -> String:
	match result:
		QueueResult.OK:
			return ""
		QueueResult.NOT_ACTIVE:
			return "Bâtiment hors service"
		QueueResult.NOT_PRODUCIBLE:
			return "Production non disponible ici"
		QueueResult.QUEUE_FULL:
			return "File de production pleine"
		QueueResult.NOT_ENOUGH_PRIMARY, QueueResult.NOT_ENOUGH_SECONDARY, QueueResult.NOT_ENOUGH_TERTIARY:
			var kind := result - QueueResult.NOT_ENOUGH_PRIMARY
			var name := faction.resource_names[kind] if faction != null else "ressources"
			return "Pas assez de %s" % name
		QueueResult.NOT_ENOUGH_POPULATION:
			return "Population maximale atteinte"
	return "Production impossible"
