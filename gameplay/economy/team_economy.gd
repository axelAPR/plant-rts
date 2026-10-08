class_name TeamEconomy
extends RefCounted
## Ressources d'un camp : stock et revenu par minute de chacune des trois ressources.
## Aucune dépendance aux nœuds ; avancée par Economy au tick physique.
##
## Même fonctionnement pour tous les camps ; les noms et couleurs viennent de la
## faction (FactionData).

## Les trois ressources : principale (effectifs : Soleil / Cerveaux), secondaire
## (Engrais / Engrenages), tertiaire (Terre / Pesticides).
enum Kind { PRIMARY, SECONDARY, TERTIARY }

const KIND_COUNT := 3
## Tolérance d'arrondi : 3 600 ticks de 200/3 600 font 199,999 999… et non 200.
const ROUNDING_EPSILON := 1e-6

var team: int
var faction: FactionData

## Stocks (fractionnaires : le revenu s'accumule à chaque tick).
var _amounts := PackedFloat64Array([0.0, 0.0, 0.0])
## Revenus (par minute).
var _income_per_minute := PackedFloat64Array([0.0, 0.0, 0.0])


func _init(p_team: int, p_faction: FactionData) -> void:
	team = p_team
	faction = p_faction


## Stock disponible (arrondi à l'unité inférieure, tel qu'affiché et dépensable).
func get_amount(kind: Kind) -> int:
	return floori(_amounts[kind] + ROUNDING_EPSILON)


func get_income_per_minute(kind: Kind) -> float:
	return _income_per_minute[kind]


func set_income_per_minute(kind: Kind, per_minute: float) -> void:
	_income_per_minute[kind] = per_minute


## Ajoute (ou retire, si négatif) un revenu par minute : points de capture, bonus…
func add_income_per_minute(kind: Kind, per_minute: float) -> void:
	_income_per_minute[kind] += per_minute


func add(kind: Kind, amount: float) -> void:
	_amounts[kind] = maxf(_amounts[kind] + amount, 0.0)


## `cost` : un montant par ressource, dans l'ordre de Kind.
func can_afford(cost: PackedInt32Array) -> bool:
	for kind in KIND_COUNT:
		if kind < cost.size() and get_amount(kind as Kind) < cost[kind]:
			return false
	return true


## Dépense `cost` si le stock suffit ; renvoie false (et ne dépense rien) sinon.
func spend(cost: PackedInt32Array) -> bool:
	if not can_afford(cost):
		return false
	for kind in mini(cost.size(), KIND_COUNT):
		_amounts[kind] -= cost[kind]
	return true


## Avance le temps : chaque stock reçoit son revenu au prorata de `delta` (s).
func step(delta: float) -> void:
	for kind in KIND_COUNT:
		_amounts[kind] = maxf(_amounts[kind] + _income_per_minute[kind] * delta / 60.0, 0.0)
