class_name SpatialHashGrid
extends RefCounted
## Grille de hachage spatiale sur le plan XZ : retrouve les éléments proches d'un
## point sans tester toutes les paires (coût linéaire au lieu de quadratique),
## indispensable pour simuler beaucoup d'unités.

var cell_size: float
var _cells: Dictionary[Vector2i, PackedInt32Array] = {}


func _init(p_cell_size: float = 2.0) -> void:
	cell_size = p_cell_size


func clear() -> void:
	_cells.clear()


func insert(index: int, position: Vector3) -> void:
	var cell := _cell_of(position)
	# Les tableaux compacts sont copiés à la lecture : on relit, modifie, puis réécrit.
	var bucket: PackedInt32Array = _cells.get(cell, PackedInt32Array())
	bucket.append(index)
	_cells[cell] = bucket


## Indices des éléments situés dans les cellules couvrant le cercle (position, radius).
## Résultat approximatif : l'appelant doit encore tester la distance réelle.
func query(position: Vector3, radius: float) -> PackedInt32Array:
	var result := PackedInt32Array()
	var min_cell := _cell_of(position - Vector3(radius, 0.0, radius))
	var max_cell := _cell_of(position + Vector3(radius, 0.0, radius))
	for x in range(min_cell.x, max_cell.x + 1):
		for y in range(min_cell.y, max_cell.y + 1):
			var cell := Vector2i(x, y)
			if _cells.has(cell):
				result.append_array(_cells[cell])
	return result


func _cell_of(position: Vector3) -> Vector2i:
	return Vector2i(floori(position.x / cell_size), floori(position.z / cell_size))
