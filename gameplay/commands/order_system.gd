class_name OrderSystem
extends Node
## Transforme une intention (du joueur ou de l'IA) en ordres d'escouade.
##
## Un ordre de groupe donne à chaque escouade sa propre destination : les escouades
## se placent côte à côte au lieu de fusionner leurs formations.

@export var simulation: UnitSimulation
## Espace (m) laissé entre deux escouades d'un même ordre de groupe.
@export var squad_gap: float = 2.0
## En deçà de cette distance (m), un ordre de déplacement garde l'orientation actuelle.
@export var min_turn_distance: float = 1.0


func issue_move(squads: Array[Squad], target: Vector3) -> void:
	if squads.is_empty():
		return

	var group_center := Vector3.ZERO
	for squad in squads:
		group_center += squad.get_center()
	group_center /= squads.size()

	var direction := target - group_center
	direction.y = 0.0
	var facing := squads[0].facing
	if direction.length() > min_turn_distance:
		facing = atan2(direction.x, direction.z)

	# Axe latéral de la ligne d'escouades, perpendiculaire à la direction de marche.
	var lateral := Basis(Vector3.UP, facing) * Vector3.RIGHT
	# Trier selon la position latérale actuelle évite que les trajectoires se croisent.
	var ordered: Array[Squad] = squads.duplicate()
	ordered.sort_custom(func(a: Squad, b: Squad) -> bool:
		return a.get_center().dot(lateral) < b.get_center().dot(lateral))

	var total_width := squad_gap * (ordered.size() - 1)
	for squad in ordered:
		total_width += squad.get_formation_width()

	var cursor := -total_width * 0.5
	for squad in ordered:
		var width := squad.get_formation_width()
		var destination := target + lateral * (cursor + width * 0.5)
		cursor += width + squad_gap
		simulation.issue_order(squad, MoveOrder.new(destination, facing))


func issue_stop(squads: Array[Squad]) -> void:
	for squad in squads:
		simulation.issue_order(squad, StopOrder.new())
