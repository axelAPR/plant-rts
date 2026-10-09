class_name PlayerState
extends Node
## Joueur local : camp contrôlé (ressources affichées, commandes autorisées dans le
## HUD). Pas de multijoueur : un seul joueur local, changeable en développement.

signal team_changed(team: int)

## Camp du joueur (0 = plantes, 1 = zombies).
@export var team: int = 0:
	set(value):
		if value == team:
			return
		team = value
		team_changed.emit(team)
