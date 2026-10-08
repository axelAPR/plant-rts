extends SceneTree
## Test automatisé de l'économie : revenus de base, noms et couleurs propres à chaque
## camp, dépenses, et affichage de la barre de ressources.
##
## Lancement : Godot --headless --path . --script res://tests/economy_test/economy_runner.gd
## Code de sortie : 0 si tout passe, 1 sinon.

const TICK := 1.0 / 60.0

var _failures: Array[String] = []
var _checks: int = 0


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var economy := Economy.new()
	economy.set_physics_process(false)
	# Stock de départ à zéro pour vérifier les revenus seuls (le stock de départ par
	# défaut est vérifié par production_runner).
	economy.starting_primary = 0
	economy.starting_secondary = 0
	economy.starting_tertiary = 0
	economy.factions = [load("res://data/factions/plants.tres"), load("res://data/factions/zombies.tres")]
	root.add_child(economy)
	var bar := ResourceBar.new()
	bar.economy = economy
	bar.teams = [0, 1]
	root.add_child(bar)

	_check(economy.get_team_count() == 2, "deux camps")
	var plants := economy.get_team(0)
	var zombies := economy.get_team(1)
	_check(_names(plants) == ["Soleil", "Engrais", "Terre"], "plantes : %s" % [_names(plants)])
	_check(_names(zombies) == ["Cerveaux", "Engrenages", "Pesticides"], "zombies : %s" % [_names(zombies)])

	# 1. Revenus de base : une minute de ticks.
	for i in int(60.0 / TICK):
		economy.step(TICK)
	for team_economy: TeamEconomy in [plants, zombies]:
		var name: String = team_economy.faction.display_name
		_check(_amounts(team_economy) == [200, 5, 0], "%s après 1 min : %s (attendu [200, 5, 0])" % [name, _amounts(team_economy)])
	# Deux minutes et demie : revenu proportionnel au temps.
	for i in int(90.0 / TICK):
		economy.step(TICK)
	_check(_amounts(plants) == [500, 12, 0], "plantes après 2 min 30 : %s (attendu [500, 12, 0])" % [_amounts(plants)])

	# 2. Dépenses.
	_check(plants.can_afford(PackedInt32Array([500, 12, 0])), "peut payer exactement son stock")
	_check(not plants.can_afford(PackedInt32Array([0, 0, 1])), "ne peut pas payer 1 de Terre (stock 0)")
	_check(not plants.spend(PackedInt32Array([600, 0, 0])), "dépense refusée si le stock manque")
	_check(_amounts(plants) == [500, 12, 0], "rien n'est dépensé après un refus")
	_check(plants.spend(PackedInt32Array([300, 10])), "dépense acceptée")
	_check(_amounts(plants) == [200, 2, 0], "stock après dépense : %s (attendu [200, 2, 0])" % [_amounts(plants)])
	_check(_amounts(zombies) == [500, 12, 0], "le stock de l'autre camp ne change pas")

	# 3. Revenu supplémentaire (futurs points de capture).
	plants.add_income_per_minute(TeamEconomy.Kind.TERTIARY, 6.0)
	for i in int(30.0 / TICK):
		economy.step(TICK)
	_check(_amounts(plants)[2] == 3, "+6/min de Terre pendant 30 s → 3 (obtenu %d)" % _amounts(plants)[2])

	# 4. Affichage : stock et revenu par minute de chaque ressource, à sa couleur.
	await process_frame
	await process_frame
	var labels := bar.find_children("*", "Label", true, false).map(func(l: Label) -> String: return l.text)
	print("  info  barre : %s" % " | ".join(labels))
	for expected in ["Soleil", "300", "+200/min", "Engrais", "+5/min", "Terre", "+6/min",
			"Cerveaux", "600", "Engrenages", "Pesticides", "+0/min"]:
		_check(labels.has(expected), "barre de ressources : « %s » affiché" % expected)
	var soleil: Label = bar.find_children("*", "Label", true, false).filter(func(l: Label) -> bool: return l.text == "Soleil")[0]
	_check(soleil.get_theme_color("font_color") == plants.faction.get_resource_color(TeamEconomy.Kind.PRIMARY),
			"« Soleil » affiché à la couleur de la ressource")

	print("\n%d vérifications, %d échec(s)" % [_checks, _failures.size()])
	quit(0 if _failures.is_empty() else 1)


func _names(team_economy: TeamEconomy) -> Array[String]:
	var names: Array[String] = []
	for kind in TeamEconomy.KIND_COUNT:
		names.append(team_economy.faction.get_resource_name(kind as TeamEconomy.Kind))
	return names


func _amounts(team_economy: TeamEconomy) -> Array[int]:
	var amounts: Array[int] = []
	for kind in TeamEconomy.KIND_COUNT:
		amounts.append(team_economy.get_amount(kind as TeamEconomy.Kind))
	return amounts


func _check(condition: bool, label: String) -> void:
	_checks += 1
	print(("  OK    " if condition else "  ÉCHEC ") + label)
	if not condition:
		_failures.append(label)
