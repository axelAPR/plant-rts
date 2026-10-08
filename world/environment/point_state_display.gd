@tool
class_name PointStateDisplay
extends Node3D
## Affichage d'un point de jeu du kit (capture_point, resource_point_*) dans l'un de
## ses trois états : seuls les nœuds « State_<état> » du modèle enfant correspondant
## restent visibles. Affichage seulement (aucune logique de capture).

enum State { NEUTRAL, PLANTS, ZOMBIES }

const STATE_NODES := {State.NEUTRAL: "State_Neutral", State.PLANTS: "State_Plants", State.ZOMBIES: "State_Zombies"}

@export var state: State = State.NEUTRAL:
	set(value):
		state = value
		_apply()


func _ready() -> void:
	_apply()


func _apply() -> void:
	if not is_inside_tree():
		return
	for state_value: State in STATE_NODES:
		for node in find_children(STATE_NODES[state_value], "Node3D", true, false):
			(node as Node3D).visible = state_value == state
