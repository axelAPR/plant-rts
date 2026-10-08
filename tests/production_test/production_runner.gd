extends SceneTree
## Test automatisé de la production : stock de départ, coût retiré, population ajoutée
## (par escouade entière), refus sans aucun effet si une ressource ou la population
## manque, population libérée à la destruction de l'escouade.
##
## Lancement : Godot --headless --path . --script res://tests/production_test/production_runner.gd
## Code de sortie : 0 si tout passe, 1 sinon.

var _failures: Array[String] = []
var _checks: int = 0

var _economy: Economy
var _simulation: UnitSimulation
var _production: ProductionSystem


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	_build()
	var plants := _economy.get_team(0)
	var zombies := _economy.get_team(1)

	print("\nStock de départ")
	for team_economy: TeamEconomy in [plants, zombies]:
		_check(_amounts(team_economy) == [500, 50, 0], "%s : %s (attendu [500, 50, 0])" % [team_economy.faction.display_name, _amounts(team_economy)])
		_check(team_economy.population_used == 0 and team_economy.population_cap == 100, "%s : population 0 / 100" % team_economy.faction.display_name)

	print("\n[12-13] Production : ressources retirées, population ajoutée")
	var peashooter := _squad("peashooter")
	var squad := _production.produce(0, peashooter, Vector3.ZERO, 0.0)
	_check(squad != null and squad.units.size() == 6, "escouade de Pisto-pois créée (6 membres)")
	_check(_amounts(plants) == [200, 50, 0], "coût 300 Soleil retiré : %s" % [_amounts(plants)])
	_check(plants.population_used == 6, "population +6 pour l'escouade entière (obtenu %d, pas 36)" % plants.population_used)
	_check(_amounts(zombies) == [500, 50, 0] and zombies.population_used == 0, "l'autre camp n'est pas touché")
	var soldiers := _production.produce(1, _squad("foot_soldier"), Vector3(0.0, 0.0, 40.0), PI)
	_check(soldiers != null and _amounts(zombies) == [200, 50, 0] and zombies.population_used == 6,
			"zombies : même fonctionnement (Soldats : 300 Cerveaux, population 6)")

	print("\n[14] Ressources insuffisantes : rien ne change")
	var squads_before := _simulation.squads.size()
	_expect_refusal(0, _squad("kernel_corn"), ProductionSystem.Result.NOT_ENOUGH_PRIMARY, "Maïs (500 Soleil) avec 200 Soleil")
	plants.add(TeamEconomy.Kind.PRIMARY, 1000.0)
	plants.spend(PackedInt32Array([0, 40, 0]))
	_expect_refusal(0, _squad("torchwood"), ProductionSystem.Result.NOT_ENOUGH_SECONDARY, "Torchwood (30 Engrais) avec 10 Engrais")
	plants.add(TeamEconomy.Kind.SECONDARY, 40.0)
	_expect_refusal(0, _squad("torchwood"), ProductionSystem.Result.NOT_ENOUGH_TERTIARY, "Torchwood (5 Terre) avec 0 Terre")
	_check(_simulation.squads.size() == squads_before, "aucune escouade créée par les refus")

	print("\n[15] Population maximale")
	plants.population_cap = 10
	_expect_refusal(0, peashooter, ProductionSystem.Result.NOT_ENOUGH_POPULATION, "Pisto-pois (6) avec 6 / 10 occupés")
	plants.population_cap = 12
	_check(_production.produce(0, peashooter, Vector3(20.0, 0.0, 0.0), 0.0) != null, "à 6 / 12 : production acceptée (limite atteinte exactement)")
	_check(plants.population_used == 12, "population 12 / 12")
	_expect_refusal(0, _squad("cactus"), ProductionSystem.Result.NOT_ENOUGH_POPULATION, "Cactus (4) à 12 / 12")

	print("\nPopulation libérée à la destruction")
	for unit in squad.units.duplicate():
		_simulation.remove_unit(unit)
	_check(_simulation.get_squad(squad.id) == null, "escouade détruite")
	_check(plants.population_used == 6, "population libérée : 6 / 12 (obtenu %d)" % plants.population_used)

	print("\n%d vérifications, %d échec(s)" % [_checks, _failures.size()])
	quit(0 if _failures.is_empty() else 1)


## Production refusée pour la raison attendue, sans aucun effet.
func _expect_refusal(team: int, data: SquadData, expected: ProductionSystem.Result, label: String) -> void:
	var team_economy := _economy.get_team(team)
	var amounts := _amounts(team_economy)
	var population := team_economy.population_used
	var squads := _simulation.squads.size()
	var result := _production.check(team, data)
	var squad := _production.produce(team, data, Vector3(0.0, 0.0, -30.0), 0.0)
	_check(result == expected and squad == null, "%s : refusé (%s)" % [label, ProductionSystem.result_text(result)])
	_check(_amounts(team_economy) == amounts and team_economy.population_used == population
			and _simulation.squads.size() == squads, "%s : ressources, population et escouades inchangées" % label)


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
