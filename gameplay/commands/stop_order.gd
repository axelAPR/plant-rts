class_name StopOrder
extends SquadOrder
## Arrêt : la formation se reforme sur place, autour de la position actuelle.


func _init() -> void:
	type = Type.STOP


func start(squad: Squad, _simulation: UnitSimulation) -> void:
	squad.anchor = squad.get_center()
	squad.reassign_slots()
