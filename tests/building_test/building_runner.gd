extends SceneTree
## Test automatisé des bâtiments (simulation, sans affichage) : unité constructrice
## de chaque faction, mise en file (coût et population réservés, tout ou rien),
## refus (ressources, population, file pleine), progression et temps restant,
## apparition sur un emplacement libre devant la sortie, ralliement, sortie
## encombrée, annulation remboursée, destruction, construction préparée.
##
## Lancement : Godot --headless --path . --script res://tests/building_test/building_runner.gd
## Code de sortie : 0 si tout passe, 1 sinon.

const TICK := 1.0 / 60.0

var _failures: Array[String] = []
var _checks: int = 0

var _economy: Economy
var _simulation: UnitSimulation
var _production: ProductionSystem
var _orders: OrderSystem
var _buildings: BuildingSystem


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	_build()
	var plants := _economy.get_team(0)
	var zombies := _economy.get_team(1)
	var corn := _squad("kernel_corn")
	var engineer := _squad("engineer")
	var tree := _buildings.add_building(_hq_data("test_tree", plants.faction), 0, Vector3.ZERO, PI)
	var tomb := _buildings.add_building(_hq_data("test_tomb", zombies.faction), 1, Vector3(0.0, 0.0, -80.0), 0.0)

	print("\nUnité constructrice configurable")
	_check(_buildings.get_producible(tree) == [corn], "QG plantes → Maïs")
	_check(_buildings.get_producible(tomb) == [engineer], "QG zombies → Ingénieur")
	_check(_buildings.get_headquarters(0) == tree and _buildings.get_headquarters(1) == tomb, "QG de chaque camp")
	_check(_buildings.can_queue(tree, engineer) == BuildingSystem.QueueResult.NOT_PRODUCIBLE,
		"le QG plantes ne produit pas d'Ingénieur")

	print("\nMise en file : coût et population réservés")
	_check(_buildings.queue_production(tree, corn) == BuildingSystem.QueueResult.OK, "Maïs mis en file")
	_check(_amounts(plants) == [0, 35, 0], "500 Soleil et 15 Engrais retirés : %s" % [_amounts(plants)])
	_check(plants.population_used == 8, "population +8 réservée (obtenu %d)" % plants.population_used)
	_check(_simulation.squads.is_empty(), "aucune escouade avant la fin du temps de production")
	var refused := _buildings.queue_production(tree, corn)
	_check(refused == BuildingSystem.QueueResult.NOT_ENOUGH_PRIMARY, "second Maïs refusé : Soleil insuffisant")
	_check(_amounts(plants) == [0, 35, 0] and plants.population_used == 8 and tree.queue.items.size() == 1,
		"refus sans aucun effet")
	_check(BuildingSystem.queue_result_text(refused, plants.faction) == "Pas assez de Soleil",
		"message : « %s »" % BuildingSystem.queue_result_text(refused, plants.faction))

	print("\nProgression")
	_steps(10.0)
	_check(absf(tree.queue.progress_ratio() - 0.5) < 0.01, "à 10 s : 50 %% (obtenu %.0f %%)" % (tree.queue.progress_ratio() * 100))
	_check(absf(tree.queue.remaining_time() - 10.0) < 0.05, "temps restant 10 s (obtenu %.2f)" % tree.queue.remaining_time())
	_check(tree.queue.state == ProductionQueue.State.PRODUCING, "état : en production")
	_steps(10.1)
	_check(_simulation.squads.size() == 1, "Maïs apparu à la fin des 20 s")
	var squad: Squad = _simulation.squads[0] if not _simulation.squads.is_empty() else null
	if squad != null:
		_check(squad.team == 0 and squad.data == corn and squad.units.size() == 4, "escouade de 4 Maïs, camp des plantes")
		var inside := false
		for unit in squad.units:
			inside = inside or tree.contains_point(unit.position)
		_check(not inside, "aucun membre dans l'emprise du QG")
		_check(squad.anchor.distance_to(tree.get_exit_position()) < 6.0, "apparue près de la sortie (%.1f m)" % squad.anchor.distance_to(tree.get_exit_position()))
		_check(squad.order is MoveOrder, "ordre de ralliement donné")
	_check(plants.population_used == 8, "population toujours occupée par l'escouade (8)")
	_check(tree.queue.is_empty() and tree.queue.state == ProductionQueue.State.IDLE, "file vide, état au repos")

	print("\nPopulation insuffisante")
	zombies.population_cap = 4
	var pop_result := _buildings.queue_production(tomb, engineer)
	_check(pop_result == BuildingSystem.QueueResult.NOT_ENOUGH_POPULATION, "Ingénieur (5) refusé avec 4 de population")
	_check(_amounts(zombies) == [500, 50, 0] and zombies.population_used == 0, "refus sans aucun effet")
	zombies.population_cap = 100

	print("\nFile pleine et annulation")
	zombies.add(TeamEconomy.Kind.PRIMARY, 5000)
	zombies.add(TeamEconomy.Kind.SECONDARY, 500)
	var before := _amounts(zombies)
	for i in tomb.data.queue_capacity:
		_buildings.queue_production(tomb, engineer)
	_check(tomb.queue.items.size() == 5, "5 Ingénieurs en file")
	_check(_buildings.queue_production(tomb, engineer) == BuildingSystem.QueueResult.QUEUE_FULL, "6e refusé : file pleine")
	_check(zombies.population_used == 25, "population réservée 5 × 5 = 25")
	_steps(5.0)
	_buildings.cancel_production(tomb, 4)
	_buildings.cancel_production(tomb, 0)
	_check(tomb.queue.items.size() == 3 and tomb.queue.elapsed == 0.0, "annulations : 3 restants, tête remise à zéro")
	_check(zombies.population_used == 15, "population rendue (15)")
	_check(_amounts(zombies)[0] == before[0] - 900, "ressources rendues (%d Cerveaux)" % _amounts(zombies)[0])

	print("\nSortie encombrée")
	_buildings.exit_search_radius = 0.0
	var blocker := _simulation.spawn_squad(_squad("foot_soldier"), 1, tomb.get_exit_position(), 0.0)
	_steps(15.1)
	_check(tomb.queue.state == ProductionQueue.State.WAITING_FOR_EXIT, "Ingénieur terminé en attente de sortie")
	_check(_count_team_squads(1) == 1, "aucune apparition dans le bâtiment ni sur l'escouade")
	for unit in blocker.units.duplicate():
		_simulation.remove_unit(unit)
	_buildings.exit_search_radius = 30.0
	_steps(TICK * 2)
	_check(_count_team_squads(1) == 1 and tomb.queue.items.size() == 2, "sortie libérée : l'Ingénieur apparaît")

	print("\nDestruction")
	var used_before := zombies.population_used
	_buildings.apply_damage(tomb, tomb.data.max_hp * 0.4)
	_check(tomb.is_active() and is_equal_approx(tomb.hp, tomb.data.max_hp * 0.6), "60 % des points de vie")
	_buildings.apply_damage(tomb, tomb.data.max_hp)
	_check(tomb.state == Building.State.DESTROYED and tomb.hp == 0.0, "détruit à 0 point de vie")
	_check(tomb.queue.is_empty() and zombies.population_used == used_before - 10, "file annulée et remboursée")
	_check(_buildings.can_queue(tomb, engineer) == BuildingSystem.QueueResult.NOT_ACTIVE, "plus de production")
	_check(_buildings.get_headquarters(1) == null, "plus de QG zombie")

	print("\nConstruction (préparée)")
	var shed := _hq_data("test_shed", plants.faction)
	shed.is_headquarters = false
	shed.footprint_size = Vector2(6.0, 6.0)
	shed.primary_resource_cost = 100
	shed.build_time = 30.0
	_check(_buildings.can_place(shed, Vector3(500.0, 0.0, 0.0), 0.0) == BuildingSystem.PlacementResult.OUT_OF_BOUNDS, "hors de la carte : refusé")
	_check(_buildings.can_place(shed, Vector3(3.0, 0.0, 2.0), 0.0) == BuildingSystem.PlacementResult.BLOCKED_BY_BUILDING, "sur le QG : refusé")
	_check(_buildings.can_place(shed, Vector3(-40.0, 0.0, 40.0), 0.0) == BuildingSystem.PlacementResult.OK, "terrain libre : accepté")
	plants.add(TeamEconomy.Kind.PRIMARY, 100)
	var site := _buildings.place_construction(shed, 0, Vector3(-40.0, 0.0, 40.0), 0.0)
	_check(site != null and site.state == Building.State.CONSTRUCTING and _amounts(plants)[0] == 0, "chantier posé, 100 Soleil payés")
	if site != null:
		_check(_buildings.can_queue(site, corn) == BuildingSystem.QueueResult.NOT_ACTIVE, "chantier : pas de production")
		_buildings.add_construction_work(site, 15.0)
		_check(is_equal_approx(site.construction_progress, 0.5) and site.state == Building.State.CONSTRUCTING, "50 % après 15 s de travail")
		_buildings.add_construction_work(site, 15.0)
		_check(site.state == Building.State.ACTIVE and site.hp == shed.max_hp, "terminé : actif, points de vie pleins")
	_check(_buildings.place_construction(shed, 0, Vector3(40.0, 0.0, 40.0), 0.0) == null, "sans ressources : rien n'est posé")

	print("\nDonnées du projet")
	for id in ["plants", "zombies"]:
		var roster := load("res://data/factions/%s_roster.tres" % id) as FactionRoster
		_check(roster != null and roster.headquarters != null and roster.builder_squad != null
			and roster.headquarters.is_headquarters and roster.headquarters.produces_builder,
			"%s_roster : QG et unité constructrice" % id)
	_finish()


func _build() -> void:
	_simulation = UnitSimulation.new()
	_simulation.set_physics_process(false)
	root.add_child(_simulation)
	_economy = Economy.new()
	_economy.set_physics_process(false)
	_economy.factions = [load("res://data/factions/plants.tres"), load("res://data/factions/zombies.tres")]
	root.add_child(_economy)
	_production = ProductionSystem.new()
	_production.economy = _economy
	_production.simulation = _simulation
	root.add_child(_production)
	_orders = OrderSystem.new()
	_orders.simulation = _simulation
	root.add_child(_orders)
	_buildings = BuildingSystem.new()
	_buildings.simulation = _simulation
	_buildings.production = _production
	_buildings.order_system = _orders
	_buildings.set_physics_process(false)
	for faction: FactionData in _economy.factions:
		var roster := FactionRoster.new()
		roster.faction = faction
		roster.builder_squad = _squad("kernel_corn" if faction.id == &"plants" else "engineer")
		_buildings.rosters.append(roster)
	root.add_child(_buildings)


func _hq_data(id: String, faction: FactionData) -> BuildingData:
	var data := BuildingData.new()
	data.id = StringName(id)
	data.display_name = id
	data.faction = faction
	data.is_headquarters = true
	data.produces_builder = true
	data.footprint_size = Vector2(12.0, 12.0)
	data.exit_offset = Vector3(0.0, 0.0, 9.0)
	return data


func _steps(seconds: float) -> void:
	for i in roundi(seconds / TICK):
		_simulation.step(TICK)
		_buildings.step(TICK)


func _count_team_squads(team: int) -> int:
	var count := 0
	for squad in _simulation.squads:
		if squad.team == team:
			count += 1
	return count


func _squad(id: String) -> SquadData:
	return load("res://data/units/%s_squad.tres" % id)


func _amounts(team_economy: TeamEconomy) -> Array[int]:
	var result: Array[int] = []
	for kind in TeamEconomy.KIND_COUNT:
		result.append(team_economy.get_amount(kind as TeamEconomy.Kind))
	return result


func _check(condition: bool, label: String) -> void:
	_checks += 1
	print("  %s  %s" % ["OK  " if condition else "ÉCHEC", label])
	if not condition:
		_failures.append(label)


func _finish() -> void:
	print("\n%d vérifications, %d échec(s)" % [_checks, _failures.size()])
	quit(0 if _failures.is_empty() else 1)
