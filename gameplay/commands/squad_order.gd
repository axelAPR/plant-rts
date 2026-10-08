class_name SquadOrder
extends RefCounted
## Ordre donné à une escouade. Chaque type d'ordre est une sous-classe qui pilote
## l'ancre et l'orientation de la formation ; la simulation gère le reste (déplacement
## des unités, évitement).
##
## Implémentés : MOVE, STOP. Prévus avec le combat : ATTACK, ATTACK_MOVE, HOLD_POSITION.

enum Type { MOVE, STOP, ATTACK, ATTACK_MOVE, HOLD_POSITION }

var type: Type


## Appelé une fois, quand l'ordre devient l'ordre en cours de l'escouade.
func start(_squad: Squad) -> void:
	pass


## Appelé à chaque tick de simulation ; renvoie true quand l'ordre est terminé.
func update(_squad: Squad, _delta: float) -> bool:
	return true
