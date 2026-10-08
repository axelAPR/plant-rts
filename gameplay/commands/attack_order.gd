class_name AttackOrder
extends SquadOrder
## Attaque d'une escouade ennemie : l'escouade s'en approche jusqu'à ce que ses membres
## soient à portée, s'y arrête face à elle, et la suit si elle s'éloigne. Les membres
## tirent en priorité sur elle (voir CombatSystem). Une escouade de mêlée va au contact.
## Fin quand l'escouade visée est détruite.
##
## L'ordre ne fait que déplacer l'ancre : le tir reste géré par CombatSystem.

## Part de la portée visée en approche : marge pour que la plupart des membres
## (répartis dans la formation) soient à portée.
const RANGE_MARGIN := 0.8
## Écart d'orientation (rad) au-delà duquel la formation se réoriente vers la cible.
const REFACE_ANGLE := deg_to_rad(40.0)
## Fraction de la vitesse des unités utilisée par l'ancre (marge de rattrapage).
const ANCHOR_SPEED_RATIO := 0.9

## Escouade visée (id plutôt que référence : deux escouades qui s'attaquent
## mutuellement formeraient un cycle de références jamais libéré).
var target_squad_id: int


func _init(p_target_squad_id: int) -> void:
	type = Type.ATTACK
	target_squad_id = p_target_squad_id


func start(squad: Squad, simulation: UnitSimulation) -> void:
	squad.anchor = squad.get_center()
	var target := simulation.get_squad(target_squad_id)
	if target != null:
		_face(squad, target, true)


func update(squad: Squad, simulation: UnitSimulation, delta: float) -> bool:
	var target := simulation.get_squad(target_squad_id)
	if target == null or target.units.is_empty():
		return true
	_face(squad, target, false)
	var to_target := target.get_center() - squad.anchor
	to_target.y = 0.0
	var distance := to_target.length()
	var stop_distance := engage_distance(squad, target)
	if distance <= stop_distance:
		return false
	var step := minf(squad.get_move_speed() * ANCHOR_SPEED_RATIO * delta, distance - stop_distance)
	squad.anchor += to_target / distance * step
	squad.anchor_velocity = to_target / distance * (step / delta)
	return false


## Distance (m) entre centres d'escouades à laquelle l'ancre s'arrête : à portée pour
## un tireur, au contact (centre sur centre) pour la mêlée.
static func engage_distance(squad: Squad, target: Squad) -> float:
	var data := squad.data.unit_data
	if data.is_melee():
		return 0.0
	return maxf(data.attack_range * RANGE_MARGIN, 0.0)


func reserved_position(squad: Squad) -> Vector3:
	return squad.anchor


## Oriente la formation vers la cible (au départ, ou si l'écart devient grand).
func _face(squad: Squad, target: Squad, force: bool) -> void:
	var direction := target.get_center() - squad.get_center()
	direction.y = 0.0
	if direction.length() < 0.5:
		return
	var facing := atan2(direction.x, direction.z)
	if force or absf(angle_difference(squad.facing, facing)) > REFACE_ANGLE:
		squad.facing = facing
		squad.reassign_slots()
