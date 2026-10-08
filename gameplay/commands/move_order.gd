class_name MoveOrder
extends SquadOrder
## Déplacement en formation : l'ancre avance en ligne droite vers la destination et
## ralentit si des unités décrochent, pour que la formation reste cohérente.

## Écart (m) unité/emplacement toléré avant que l'ancre ne ralentisse.
const LAG_TOLERANCE := 1.0
## Écart (m) à partir duquel l'ancre attend complètement les retardataires.
const LAG_STOP := 3.5
## Fraction de la vitesse des unités utilisée par l'ancre : la marge permet de rattraper.
const ANCHOR_SPEED_RATIO := 0.9
## Écart (m) maximal pour considérer la formation arrivée et reformée.
const ARRIVAL_TOLERANCE := 0.3

var target: Vector3
## Orientation finale de la formation (rad).
var facing: float


func _init(p_target: Vector3, p_facing: float) -> void:
	type = Type.MOVE
	target = Vector3(p_target.x, 0.0, p_target.z)
	facing = p_facing


func start(squad: Squad) -> void:
	# On repart du barycentre réel : l'ancre d'un ordre précédent peut être en avance.
	squad.anchor = squad.get_center()
	squad.facing = facing
	squad.reassign_slots()


func update(squad: Squad, delta: float) -> bool:
	var to_target := target - squad.anchor
	to_target.y = 0.0
	var distance := to_target.length()
	if distance > 0.001:
		var lag := squad.get_formation_error()
		var lag_factor := clampf(1.0 - (lag - LAG_TOLERANCE) / (LAG_STOP - LAG_TOLERANCE), 0.0, 1.0)
		var speed := squad.get_move_speed() * ANCHOR_SPEED_RATIO * lag_factor
		var step := minf(speed * delta, distance)
		squad.anchor += to_target / distance * step
		squad.anchor_velocity = to_target / distance * (step / delta)
		return false
	return squad.get_formation_error() < ARRIVAL_TOLERANCE
