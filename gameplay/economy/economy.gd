class_name Economy
extends Node
## Économie de la partie : une TeamEconomy par camp, avancée au tick physique (donc
## mise en pause avec l'arbre de scène, comme la simulation). Les autres systèmes
## lisent les stocks et dépensent via get_team().
##
## Revenu de base identique pour tous les camps ; les sources de revenu à venir
## (points de capture…) s'ajoutent avec TeamEconomy.add_income_per_minute().

signal team_added(team_economy: TeamEconomy)

## Faction de chaque camp, indexée par numéro de camp (0 = plantes, 1 = zombies).
@export var factions: Array[FactionData] = []

@export_group("Revenu de base (par minute)")
@export var base_income_primary: float = 200.0
@export var base_income_secondary: float = 5.0
@export var base_income_tertiary: float = 0.0

@export_group("Stock de départ")
@export var starting_primary: int = 500
@export var starting_secondary: int = 50
@export var starting_tertiary: int = 0

@export_group("Population")
## Population maximale de chaque camp (somme des population_cost des escouades produites).
@export var population_cap: int = 100

var _teams: Array[TeamEconomy] = []


func _ready() -> void:
	for team in factions.size():
		_add_team(team, factions[team])


func get_team(team: int) -> TeamEconomy:
	return _teams[team] if team >= 0 and team < _teams.size() else null


func get_team_count() -> int:
	return _teams.size()


func _physics_process(delta: float) -> void:
	step(delta)


## Avance l'économie d'un tick. Appelé au tick physique ; les tests peuvent l'appeler
## directement (physique désactivée).
func step(delta: float) -> void:
	for team_economy in _teams:
		team_economy.step(delta)


func _add_team(team: int, faction: FactionData) -> void:
	var team_economy := TeamEconomy.new(team, faction)
	team_economy.set_income_per_minute(TeamEconomy.Kind.PRIMARY, base_income_primary)
	team_economy.set_income_per_minute(TeamEconomy.Kind.SECONDARY, base_income_secondary)
	team_economy.set_income_per_minute(TeamEconomy.Kind.TERTIARY, base_income_tertiary)
	team_economy.add(TeamEconomy.Kind.PRIMARY, starting_primary)
	team_economy.add(TeamEconomy.Kind.SECONDARY, starting_secondary)
	team_economy.add(TeamEconomy.Kind.TERTIARY, starting_tertiary)
	team_economy.population_cap = population_cap
	_teams.append(team_economy)
	team_added.emit(team_economy)
