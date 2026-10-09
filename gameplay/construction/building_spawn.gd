@tool
class_name BuildingSpawn
extends Marker3D
## Bâtiment présent en début de partie (QG…), posé dans une scène de carte comme
## enfant du BuildingSystem : position et orientation du marqueur (avant = +Z local).

@export var data: BuildingData
## Camp propriétaire (0 = plantes, 1 = zombies).
@export var team: int = 0
