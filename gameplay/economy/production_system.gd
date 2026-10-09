class_name ProductionSystem
extends Node
## Production d'escouades : vérifie et paie le coût (trois ressources) et la population,
## puis crée l'escouade dans la simulation. Tout ou rien : si une condition manque,
## rien n'est retiré, rien n'est ajouté, aucune escouade n'est créée.
##
## La population est celle de l'escouade entière (SquadData.population_cost), occupée
## à la production et libérée quand l'escouade est détruite (dernier membre mort).
## Les escouades créées autrement (menu DEV, scènes de test) n'occupent pas de population.

## Résultat d'une demande de production.
enum Result { OK, NOT_ENOUGH_PRIMARY, NOT_ENOUGH_SECONDARY, NOT_ENOUGH_TERTIARY, NOT_ENOUGH_POPULATION, INVALID }

signal squad_produced(squad: Squad)

@export var economy: Economy
@export var simulation: UnitSimulation

## Population occupée par chaque escouade produite (id d'escouade → [camp, population]).
var _population_by_squad: Dictionary[int, Vector2i] = {}


func _ready() -> void:
	simulation.squad_destroyed.connect(_on_squad_destroyed)


## Vérifie, dans l'ordre : ressource principale, secondaire, tertiaire, population.
func check(team: int, data: SquadData) -> Result:
	var team_economy := economy.get_team(team)
	if team_economy == null or data == null:
		return Result.INVALID
	var cost := data.get_cost()
	var kinds := [TeamEconomy.Kind.PRIMARY, TeamEconomy.Kind.SECONDARY, TeamEconomy.Kind.TERTIARY]
	var failures := [Result.NOT_ENOUGH_PRIMARY, Result.NOT_ENOUGH_SECONDARY, Result.NOT_ENOUGH_TERTIARY]
	for i in kinds.size():
		if team_economy.get_amount(kinds[i]) < cost[i]:
			return failures[i]
	if not team_economy.has_population(data.population_cost):
		return Result.NOT_ENOUGH_POPULATION
	return Result.OK


## Produit l'escouade si possible : retire les ressources, occupe la population, crée
## l'escouade. Renvoie l'escouade, ou null (rien n'a changé) ; voir check() pour la raison.
func produce(team: int, data: SquadData, position: Vector3, facing: float) -> Squad:
	if reserve(team, data) != Result.OK:
		return null
	return spawn_reserved(team, data, position, facing)


## Production différée (file d'un bâtiment), étape 1 : vérifie, paie et occupe la
## population, sans créer l'escouade. Tout ou rien.
func reserve(team: int, data: SquadData) -> Result:
	var result := check(team, data)
	if result != Result.OK:
		return result
	var team_economy := economy.get_team(team)
	if not team_economy.spend(data.get_cost()):
		return Result.INVALID
	team_economy.add_population(data.population_cost)
	return Result.OK


## Étape 2 : crée l'escouade déjà payée ; sa population sera libérée à sa destruction.
func spawn_reserved(team: int, data: SquadData, position: Vector3, facing: float) -> Squad:
	var squad := simulation.spawn_squad(data, team, position, facing)
	_population_by_squad[squad.id] = Vector2i(team, data.population_cost)
	squad_produced.emit(squad)
	return squad


## Annulation d'une production réservée et non créée : rend les ressources et la
## population.
func refund(team: int, data: SquadData) -> void:
	var team_economy := economy.get_team(team)
	if team_economy == null or data == null:
		return
	var cost := data.get_cost()
	for kind in cost.size():
		team_economy.add(kind, cost[kind])
	team_economy.release_population(data.population_cost)


static func result_text(result: Result) -> String:
	match result:
		Result.OK:
			return "OK"
		Result.NOT_ENOUGH_PRIMARY:
			return "ressource principale insuffisante"
		Result.NOT_ENOUGH_SECONDARY:
			return "ressource secondaire insuffisante"
		Result.NOT_ENOUGH_TERTIARY:
			return "ressource tertiaire insuffisante"
		Result.NOT_ENOUGH_POPULATION:
			return "population maximale atteinte"
	return "invalide"


func _on_squad_destroyed(squad: Squad) -> void:
	if not _population_by_squad.has(squad.id):
		return
	var entry: Vector2i = _population_by_squad[squad.id]
	_population_by_squad.erase(squad.id)
	var team_economy := economy.get_team(entry.x)
	if team_economy != null:
		team_economy.release_population(entry.y)
