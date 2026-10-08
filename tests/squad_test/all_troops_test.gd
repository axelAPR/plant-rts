extends Node3D
## Scène de test : une escouade de chaque troupe, plantes et zombies face à face.
## Les plantes (camp 0) sont au sud (+Z) et regardent vers -Z ; les zombies
## (camp 1) sont au nord (-Z) et regardent vers +Z.

@export var plant_squads: Array[SquadData] = []
@export var zombie_squads: Array[SquadData] = []
## Distance (m) entre deux escouades voisines d'une même rangée.
@export var column_spacing: float = 12.0
## Distance (m) entre deux rangées d'escouades d'un même camp.
@export var row_spacing: float = 12.0
## Distance (m) entre la ligne médiane et la première rangée de chaque camp.
@export var front_distance: float = 8.0
@export_range(1, 10) var squads_per_row: int = 5

@onready var _simulation: UnitSimulation = $UnitSimulation


func _ready() -> void:
	_spawn_camp(plant_squads, 0, 1.0, PI)
	_spawn_camp(zombie_squads, 1, -1.0, 0.0)


## Fait apparaître les escouades d'un camp en rangées centrées ; `side` = +1 au sud, -1 au nord.
func _spawn_camp(squads: Array[SquadData], team: int, side: float, facing: float) -> void:
	for i in squads.size():
		@warning_ignore("integer_division")
		var row := i / squads_per_row
		var in_row := mini(squads_per_row, squads.size() - row * squads_per_row)
		var column := i % squads_per_row
		var x := (column - (in_row - 1) * 0.5) * column_spacing
		var z := side * (front_distance + row * row_spacing)
		_simulation.spawn_squad(squads[i], team, Vector3(x, 0.0, z), facing)
