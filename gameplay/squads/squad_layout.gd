class_name SquadLayout
extends RefCounted
## Placement d'un groupe d'escouades (fonctions pures), pour les apparitions groupées.


## Positions des escouades d'un camp, en rangées centrées sur l'axe X de `center`.
## `side` = +1 : rangées vers +Z (sud) ; -1 : vers -Z (nord).
## La première rangée est à `front_distance` de `center`.
@warning_ignore("integer_division")
static func camp_positions(count: int, center: Vector3, side: float, per_row: int,
		column_spacing: float, row_spacing: float, front_distance: float) -> PackedVector3Array:
	var positions := PackedVector3Array()
	var cols := maxi(per_row, 1)
	for i in count:
		var row := i / cols
		var in_row := mini(cols, count - row * cols)
		var column := i % cols
		var x := (column - (in_row - 1) * 0.5) * column_spacing
		var z := side * (front_distance + row * row_spacing)
		positions.append(center + Vector3(x, 0.0, z))
	return positions
