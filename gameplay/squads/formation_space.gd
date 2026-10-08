class_name FormationSpace
extends RefCounted
## Occupation du sol par les formations, pour choisir des emplacements libres.
##
## Chaque escouade occupe un rectangle orienté : son emprise (demi-dimensions de
## Squad.get_footprint_half_extents) autour de la position qu'elle réserve (ancre au
## repos, destination de l'ordre en cours). Deux emprises doivent rester séparées d'au
## moins `margin`. Les recherches de voisins passent par une grille spatiale.

## Écart minimal (m) entre deux emprises.
var margin: float

var _centers: Array[Vector3] = []
var _half_extents: Array[Vector2] = []
var _facings: PackedFloat32Array = PackedFloat32Array()
var _grid: SpatialHashGrid
var _max_circumradius: float = 0.0


func _init(p_margin: float, cell_size: float = 8.0) -> void:
	margin = p_margin
	_grid = SpatialHashGrid.new(cell_size)


## Emprises réservées par les escouades de la simulation, sauf `excluded`
## (typiquement : les escouades qui reçoivent un nouvel ordre). `enemies_of` ≥ 0 : ne
## retient que les escouades ennemies de ce camp (les alliés peuvent se superposer).
static func from_simulation(simulation: UnitSimulation, p_margin: float, excluded: Array[Squad] = [],
		enemies_of: int = -1) -> FormationSpace:
	var space := FormationSpace.new(p_margin)
	var skip: Dictionary[int, bool] = {}
	for squad in excluded:
		skip[squad.id] = true
	for squad in simulation.squads:
		if enemies_of >= 0 and squad.team == enemies_of:
			continue
		if not skip.has(squad.id):
			space.add(squad.get_reserved_position(), squad.get_footprint_half_extents(), squad.get_reserved_facing())
	return space


func add(center: Vector3, half_extents: Vector2, facing: float) -> void:
	_grid.insert(_centers.size(), center)
	_centers.append(Vector3(center.x, 0.0, center.z))
	_half_extents.append(half_extents)
	_facings.append(facing)
	_max_circumradius = maxf(_max_circumradius, half_extents.length())


func is_free(center: Vector3, half_extents: Vector2, facing: float) -> bool:
	var reach := half_extents.length() + _max_circumradius + margin
	var grown := half_extents + Vector2.ONE * margin * 0.5
	for i in _grid.query(center, reach):
		if _overlaps(center, grown, facing, _centers[i], _half_extents[i] + Vector2.ONE * margin * 0.5, _facings[i]):
			return false
	return true


## Emplacement libre le plus proche de `target` : anneaux de rayon croissant (pas `step`)
## jusqu'à `max_distance`, en essayant d'abord la direction `preferred` puis de part et
## d'autre. Renvoie `target` si aucun emplacement libre n'est trouvé.
func find_free(target: Vector3, half_extents: Vector2, facing: float, max_distance: float,
		step: float, preferred: Vector3 = Vector3.ZERO) -> Vector3:
	target.y = 0.0
	if is_free(target, half_extents, facing):
		return target
	var base_angle := atan2(preferred.x, preferred.z) if preferred.length_squared() > 0.0001 else 0.0
	for ring in range(1, ceili(max_distance / step) + 1):
		var distance := ring * step
		var count := maxi(6, ceili(TAU * distance / step))
		for k in count:
			# Ordre des essais : direction préférée, puis alternativement de chaque côté.
			@warning_ignore("integer_division")
			var n := (k + 1) / 2 * (1 if k % 2 == 1 else -1)
			var angle := base_angle + TAU * n / count
			var candidate := target + Vector3(sin(angle), 0.0, cos(angle)) * distance
			if is_free(candidate, half_extents, facing):
				return candidate
	return target


## Recouvrement de deux rectangles orientés (théorème de l'axe séparateur, plan XZ).
## `facing` suit la convention de Squad.facing : axe local X = Basis(UP, facing) * RIGHT.
static func _overlaps(c1: Vector3, h1: Vector2, f1: float, c2: Vector3, h2: Vector2, f2: float) -> bool:
	var x1 := Vector2(cos(f1), -sin(f1))
	var z1 := Vector2(sin(f1), cos(f1))
	var x2 := Vector2(cos(f2), -sin(f2))
	var z2 := Vector2(sin(f2), cos(f2))
	var d := Vector2(c2.x - c1.x, c2.z - c1.z)
	for axis: Vector2 in [x1, z1, x2, z2]:
		var r1 := h1.x * absf(x1.dot(axis)) + h1.y * absf(z1.dot(axis))
		var r2 := h2.x * absf(x2.dot(axis)) + h2.y * absf(z2.dot(axis))
		if absf(d.dot(axis)) >= r1 + r2:
			return false
	return true
