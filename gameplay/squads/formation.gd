class_name Formation
extends RefCounted
## Calculs de formation (fonctions pures) : emplacements et attribution des unités.


## Décalages locaux des emplacements : x = latéral, z = profondeur (+Z = avant,
## Vector3.MODEL_FRONT). Rangées centrées ; la première rangée est à l'avant.
@warning_ignore("integer_division")
static func compute_offsets(count: int, columns: int, spacing: float) -> PackedVector3Array:
	var offsets := PackedVector3Array()
	var cols := maxi(mini(columns, count), 1)
	var rows := ceili(float(count) / cols)
	for i in count:
		var row := i / cols
		var in_row := mini(cols, count - row * cols)
		var col := i % cols
		var x := (col - (in_row - 1) * 0.5) * spacing
		var z := ((rows - 1) * 0.5 - row) * spacing
		offsets.append(Vector3(x, 0.0, z))
	return offsets


## Attribue un emplacement à chaque unité en limitant les croisements : algorithme
## glouton sur les paires (unité, emplacement) triées par distance croissante.
## Renvoie, pour chaque unité, l'index de son emplacement.
static func assign_slots(positions: PackedVector3Array, slots: PackedVector3Array) -> PackedInt32Array:
	var count := positions.size()
	var pairs: Array[Vector3i] = []
	var distances: Dictionary[Vector3i, float] = {}
	for unit in count:
		for slot in count:
			var pair := Vector3i(unit, slot, pairs.size())
			pairs.append(pair)
			distances[pair] = positions[unit].distance_squared_to(slots[slot])
	pairs.sort_custom(func(a: Vector3i, b: Vector3i) -> bool: return distances[a] < distances[b])

	var result := PackedInt32Array()
	result.resize(count)
	result.fill(-1)
	var slot_taken := PackedByteArray()
	slot_taken.resize(count)
	var assigned := 0
	for pair in pairs:
		if result[pair.x] != -1 or slot_taken[pair.y] == 1:
			continue
		result[pair.x] = pair.y
		slot_taken[pair.y] = 1
		assigned += 1
		if assigned == count:
			break
	return result
