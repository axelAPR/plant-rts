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


## Emplacements « organiques » : la grille de base (compute_offsets), décalée rang par
## rang, courbée en arc et bruitée point par point, puis desserrée pour garder au moins
## `min_distance` entre deux emplacements, et recentrée. Chaque graine donne une
## variante différente de la même allure ; même graine → même forme (déterministe).
@warning_ignore("integer_division")
static func compute_organic_offsets(count: int, columns: int, spacing: float, irregularity: float,
		min_distance: float, seed: int) -> PackedVector3Array:
	var offsets := compute_offsets(count, columns, spacing)
	if count <= 1 or irregularity <= 0.0:
		return offsets
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var amplitude := spacing * irregularity
	var cols := maxi(mini(columns, count), 1)
	var rows := ceili(float(count) / cols)
	var half_width := maxf((cols - 1) * spacing * 0.5, 0.001)
	# Arc : centre en avant (bend > 0) ou en retrait ; les ailes suivent.
	var bend := rng.randf_range(-amplitude, amplitude)
	var row_shifts := PackedFloat32Array()
	for row in rows:
		row_shifts.append(rng.randf_range(-0.5, 0.5) * amplitude)
	for i in count:
		var p := offsets[i]
		var t := p.x / half_width
		p.x += row_shifts[i / cols] + rng.randf_range(-0.5, 0.5) * amplitude
		p.z += bend * (1.0 - t * t) * 0.5 + rng.randf_range(-0.5, 0.5) * amplitude
		offsets[i] = p
	_relax(offsets, min_distance)
	var center := Vector3.ZERO
	for p in offsets:
		center += p
	center /= count
	for i in count:
		offsets[i] -= center
	return offsets


## Orientation propre de chaque emplacement (rad), autour de celle de la formation.
static func compute_slot_yaws(count: int, max_degrees: float, seed: int) -> PackedFloat32Array:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var yaws := PackedFloat32Array()
	for i in count:
		yaws.append(deg_to_rad(rng.randf_range(-max_degrees, max_degrees)))
	return yaws


## Écarte les emplacements trop proches (quelques passes ; formations de 32 unités au
## plus, calculé à l'émission d'un ordre et non à chaque tick).
static func _relax(offsets: PackedVector3Array, min_distance: float) -> void:
	for pass_index in 12:
		var moved := false
		for i in offsets.size():
			for j in range(i + 1, offsets.size()):
				var delta := offsets[j] - offsets[i]
				var distance := delta.length()
				if distance >= min_distance:
					continue
				var direction := delta / distance if distance > 0.0001 else Vector3.RIGHT
				var push := direction * (min_distance - distance) * 0.5
				offsets[i] -= push
				offsets[j] += push
				moved = true
		if not moved:
			return


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
