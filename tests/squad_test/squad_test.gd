extends Node3D
## Scène de test des escouades : fait apparaître des escouades de Pisto-pois.

@export var squad_data: SquadData
@export var team: int = 0
## Une escouade est créée à chaque position.
@export var spawn_positions: Array[Vector3] = [Vector3(-4.0, 0.0, 0.0), Vector3(4.0, 0.0, 0.0)]
## Orientation initiale des formations (degrés) ; 180 = vers -Z, dos à la caméra.
@export var spawn_facing_degrees: float = 180.0

@onready var _simulation: UnitSimulation = $UnitSimulation


func _ready() -> void:
	for position in spawn_positions:
		_simulation.spawn_squad(squad_data, team, position, deg_to_rad(spawn_facing_degrees))
