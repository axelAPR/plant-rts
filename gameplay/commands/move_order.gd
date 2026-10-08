class_name MoveOrder
extends SquadOrder
## Déplacement en formation : l'ancre avance en ligne droite vers la destination,
## freine à l'approche (`settings.anchor_deceleration`) et ralentit si des unités
## décrochent, sans jamais s'arrêter en route : les retardataires rattrapent.
##
## L'ordre se termine toujours, en deux phases :
## - MOVING : l'ancre avance. Si le centre de l'escouade ne se rapproche plus de la
##   destination pendant `settings.stall_time`, l'escouade est bloquée : elle s'arrête
##   en formation à l'emplacement le plus proche hors des escouades ennemies (et hors
##   de toutes les escouades si `settings.avoid_occupied_destinations`) ;
## - SETTLING : l'ancre est à destination, la formation se reforme. Fin quand elle est
##   reformée, ou quand la reformation ne progresse plus pendant le même délai.
## Un délai maximal, proportionnel à la distance, borne l'ensemble.

enum Phase { MOVING, SETTLING }

## Écart (m) unité/emplacement toléré avant que l'ancre ne ralentisse.
const LAG_TOLERANCE := 1.0
## Écart (m) à partir duquel l'ancre n'avance plus qu'à sa vitesse minimale.
const LAG_SLOW := 3.5
## Fraction de la vitesse des unités utilisée par l'ancre : la marge permet de rattraper.
const ANCHOR_SPEED_RATIO := 0.9
## Écart (m) maximal pour considérer la formation arrivée et reformée.
const ARRIVAL_TOLERANCE := 0.3
## Vitesse (m/s) maximale des unités pour considérer la formation posée à l'arrivée.
const ARRIVAL_SPEED := 0.5

var target: Vector3
## Orientation finale de la formation (rad).
var facing: float
var settings: MoveOrderSettings
var phase: Phase = Phase.MOVING
## true si l'escouade a été bloquée et s'est arrêtée ailleurs qu'à sa destination initiale.
var stalled: bool = false

var _elapsed: float = 0.0
var _max_duration: float = 0.0
## Meilleure mesure de progression de la phase en cours (distance ou écart de formation).
var _best: float = INF
var _since_progress: float = 0.0


func _init(p_target: Vector3, p_facing: float, p_settings: MoveOrderSettings = null) -> void:
	type = Type.MOVE
	target = Vector3(p_target.x, 0.0, p_target.z)
	facing = p_facing
	settings = p_settings if p_settings != null else MoveOrderSettings.new()


func start(squad: Squad, _simulation: UnitSimulation) -> void:
	# On repart du barycentre réel : l'ancre d'un ordre précédent peut être en avance.
	squad.anchor = squad.get_center()
	squad.facing = facing
	squad.vary_formation()
	squad.reassign_slots()
	var travel_time := squad.anchor.distance_to(target) / (squad.get_move_speed() * ANCHOR_SPEED_RATIO)
	_max_duration = travel_time * settings.timeout_factor + settings.timeout_margin


func update(squad: Squad, simulation: UnitSimulation, delta: float) -> bool:
	_elapsed += delta
	if _elapsed >= _max_duration:
		return true
	if phase == Phase.SETTLING:
		var error := squad.get_formation_error()
		if error < ARRIVAL_TOLERANCE and squad.get_max_unit_speed() < ARRIVAL_SPEED:
			return true
		return _stalled(error, settings.min_reform_progress, delta)

	var to_target := target - squad.anchor
	to_target.y = 0.0
	var distance := to_target.length()
	if distance <= 0.001:
		_enter_settling()
		return false
	var lag := squad.get_formation_error()
	var lag_factor := clampf(1.0 - (lag - LAG_TOLERANCE) / (LAG_SLOW - LAG_TOLERANCE),
			settings.min_anchor_speed_ratio, 1.0)
	var speed := squad.get_move_speed() * ANCHOR_SPEED_RATIO * lag_factor
	# Freinage : vitesse permettant de s'arrêter pile sur la destination.
	speed = minf(speed, sqrt(2.0 * settings.anchor_deceleration * distance))
	var step := minf(speed * delta, distance)
	squad.anchor += to_target / distance * step
	squad.anchor_velocity = to_target / distance * (step / delta)
	if _stalled(squad.get_center().distance_to(target), settings.min_progress, delta):
		_stop_at_nearest_free(squad, simulation)
	return false


func reserved_position(_squad: Squad) -> Vector3:
	return target


func reserved_facing(_squad: Squad) -> float:
	return facing


## Escouade bloquée : elle s'arrête en formation à l'emplacement le plus proche de sa
## position, hors des emprises ennemies (les alliés peuvent se superposer, sauf si les
## destinations ne doivent pas se chevaucher), puis se reforme.
func _stop_at_nearest_free(squad: Squad, simulation: UnitSimulation) -> void:
	var excluded: Array[Squad] = [squad]
	var enemies_of := -1 if settings.avoid_occupied_destinations else squad.team
	var space := FormationSpace.from_simulation(simulation, settings.reservation_margin, excluded, enemies_of)
	target = space.find_free(squad.get_center(), squad.get_footprint_half_extents(), facing,
			settings.free_search_radius, settings.free_search_step)
	squad.anchor = target
	squad.anchor_velocity = Vector3.ZERO
	squad.reassign_slots()
	stalled = true
	_enter_settling()


func _enter_settling() -> void:
	phase = Phase.SETTLING
	_best = INF
	_since_progress = 0.0


## Suit une mesure qui doit décroître : true si elle n'a pas baissé d'au moins
## `min_step` depuis `settings.stall_time` secondes.
func _stalled(measure: float, min_step: float, delta: float) -> bool:
	if measure < _best - min_step:
		_best = measure
		_since_progress = 0.0
		return false
	_since_progress += delta
	return _since_progress >= settings.stall_time
