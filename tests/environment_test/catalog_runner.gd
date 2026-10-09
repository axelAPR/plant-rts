extends SceneTree
## Test automatisé du catalogue du kit de décor (data/environment) : chaque fiche se
## charge, pointe vers un modèle existant et rangé dans sa catégorie, et ses données
## (emprise, hauteur, propriétés de jeu) correspondent au modèle .glb : pivot au sol,
## modèle contenu dans son emprise, budget de triangles, 4 matériaux au plus.
##
## Lancement : Godot --headless --path . --script res://tests/environment_test/catalog_runner.gd
## Code de sortie : 0 si tout passe, 1 sinon.

const CATALOG_PATH := "res://data/environment/environment_catalog.tres"
const DATA_DIR := "res://data/environment/"
const EXPECTED_PIECE_COUNT := 91
## Grille du décor (m) : emprises rectangulaires multiples de 2 m.
const GRID := 2.0
## Tolérance des mesures (m) : arrondis de l'export et de la mesure de hauteur.
const TOLERANCE := 0.03
## Budgets de triangles (CLAUDE.md, « Kit de décor ») : bâtiment ≤ 3 000, comme les
## points de jeu (trois états dans un même modèle, budget « building » à l'export) ;
## le reste (petit décor et pièces moyennes, non distingués dans les fiches) ≤ 1 500.
const BUILDING_BUDGET := 3000
const OTHER_BUDGET := 1500
const MAX_MATERIALS := 4
## Objets obligatoires d'un point de jeu (`PointStateDisplay`).
const POINT_PARTS: Array[String] = ["State_Neutral", "State_Plants", "State_Zombies", "Pole", "Flag"]
const POINT_RESOURCES := {
	&"capture_point": EnvironmentPieceData.ResourceKind.NONE,
	&"resource_point_primary": EnvironmentPieceData.ResourceKind.PRIMARY,
	&"resource_point_secondary": EnvironmentPieceData.ResourceKind.SECONDARY,
	&"resource_point_tertiary": EnvironmentPieceData.ResourceKind.TERTIARY,
}

var _failures: Array[String] = []
var _checks: int = 0


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	print("Catalogue")
	var catalog := load(CATALOG_PATH) as EnvironmentCatalog
	_check(catalog != null, "catalogue chargé (%s)" % CATALOG_PATH)
	if catalog == null:
		_finish()
		return
	_check(catalog.pieces.size() == EXPECTED_PIECE_COUNT,
		"%d pièces (attendu %d)" % [catalog.pieces.size(), EXPECTED_PIECE_COUNT])
	_check_catalog_matches_files(catalog)

	print("Pièces")
	var categories: Dictionary = {}
	for piece in catalog.pieces:
		if piece == null:
			_check(false, "fiche nulle dans le catalogue")
			continue
		categories[piece.category] = true
		_check_piece(piece)
	_check(categories.size() == EnvironmentPieceData.Category.size(),
		"toutes les catégories sont représentées (%d / %d)" % [categories.size(), EnvironmentPieceData.Category.size()])

	print("Points de jeu")
	for id: StringName in POINT_RESOURCES:
		var piece := catalog.get_piece(id)
		_check(piece != null, "%s présent" % id)
		if piece != null:
			_check_point(piece, POINT_RESOURCES[id])
	_finish()


## Chaque fiche de data/environment est dans le catalogue, une seule fois.
func _check_catalog_matches_files(catalog: EnvironmentCatalog) -> void:
	var catalog_ids: Dictionary = {}
	var duplicates: Array[StringName] = []
	for piece in catalog.pieces:
		if piece == null:
			continue
		if catalog_ids.has(piece.id):
			duplicates.append(piece.id)
		catalog_ids[piece.id] = true
	_check(duplicates.is_empty(), "identifiants uniques %s" % [duplicates])

	var missing: Array[String] = []
	for file in ResourceLoader.list_directory(DATA_DIR):
		if not file.ends_with(".tres") or file == CATALOG_PATH.get_file():
			continue
		if not catalog_ids.has(StringName(file.get_basename())):
			missing.append(file)
	_check(missing.is_empty(), "toutes les fiches de %s sont au catalogue %s" % [DATA_DIR, missing])


func _check_piece(piece: EnvironmentPieceData) -> void:
	var id := String(piece.id)
	var problems: Array[String] = []
	if piece.resource_path.get_file().get_basename() != id:
		problems.append("fichier %s ≠ id" % piece.resource_path.get_file())
	if piece.display_name.strip_edges().is_empty():
		problems.append("nom affiché vide")

	# Modèle : assets/environment/<catégorie>/<id>.glb.
	var category_dir: String = EnvironmentPieceData.Category.keys()[piece.category].to_lower()
	var expected_scene := "res://assets/environment/%s/%s.glb" % [category_dir, id]
	if piece.scene == null:
		_check(false, "%s : aucune scène" % id)
		return
	if piece.scene.resource_path != expected_scene:
		problems.append("scène %s (attendu %s)" % [piece.scene.resource_path, expected_scene])

	# Emprise déclarée.
	var half := Vector2.ZERO
	if piece.footprint_shape == EnvironmentPieceData.FootprintShape.CIRCLE:
		if piece.footprint_radius <= 0.0:
			problems.append("rayon d'emprise nul")
		half = Vector2.ONE * piece.footprint_radius
	else:
		var size := piece.footprint_size
		if size.x <= 0.0 or size.y <= 0.0:
			problems.append("emprise nulle %s" % size)
		if not (_on_grid(size.x) and _on_grid(size.y)):
			problems.append("emprise %s hors grille de 2 m" % size)
		half = size * 0.5

	# Modèle instancié : mesures.
	var model := piece.scene.instantiate() as Node3D
	if model == null:
		_check(false, "%s : scène non instanciable" % id)
		return
	root.add_child(model)
	var stats := _measure(model)
	model.queue_free()
	var aabb: AABB = stats.aabb
	if stats.meshes == 0:
		problems.append("aucun maillage")
	else:
		if absf(aabb.position.y) > TOLERANCE:
			problems.append("pivot hors du sol : y min %.3f" % aabb.position.y)
		if absf(aabb.end.y - piece.height) > TOLERANCE:
			problems.append("hauteur %.2f m (fiche : %.2f m)" % [aabb.end.y, piece.height])
		# Emprise : Blender X → Godot X, Blender Y → Godot -Z (symétrique, centrée).
		var reach := Vector2(maxf(-aabb.position.x, aabb.end.x), maxf(-aabb.position.z, aabb.end.z))
		if piece.footprint_shape == EnvironmentPieceData.FootprintShape.RECTANGLE:
			if reach.x > half.x + TOLERANCE or reach.y > half.y + TOLERANCE:
				problems.append("dépasse l'emprise : ±(%.2f, %.2f) pour ±(%.2f, %.2f)" % [reach.x, reach.y, half.x, half.y])
		elif reach.length() > piece.footprint_radius * sqrt(2.0) + TOLERANCE:
			problems.append("dépasse l'emprise : ±(%.2f, %.2f) pour un rayon de %.2f" % [reach.x, reach.y, piece.footprint_radius])
	var budget := BUILDING_BUDGET if piece.category in [EnvironmentPieceData.Category.BUILDINGS,
		EnvironmentPieceData.Category.GAMEPLAY] else OTHER_BUDGET
	if stats.triangles > budget:
		problems.append("%d triangles > %d" % [stats.triangles, budget])
	if stats.materials.size() > MAX_MATERIALS:
		problems.append("%d matériaux > %d : %s" % [stats.materials.size(), MAX_MATERIALS, stats.materials.keys()])

	# Cohérence des propriétés de jeu.
	if piece.cover == EnvironmentPieceData.Cover.HEAVY and not piece.blocks_movement:
		problems.append("couvert lourd sans blocage du déplacement")
	if piece.resource != EnvironmentPieceData.ResourceKind.NONE and piece.category != EnvironmentPieceData.Category.GAMEPLAY:
		problems.append("ressource hors point de jeu")

	_check(problems.is_empty(), "%s (%d tri, %d mat, %.2f m)%s" % [
		id, stats.triangles, stats.materials.size(), aabb.end.y,
		"" if problems.is_empty() else " : " + "; ".join(problems)])


## Points de jeu : disque de 5 m, franchissables, objets d'état présents.
func _check_point(piece: EnvironmentPieceData, resource: EnvironmentPieceData.ResourceKind) -> void:
	var id := String(piece.id)
	_check(piece.category == EnvironmentPieceData.Category.GAMEPLAY, "%s : catégorie « points de jeu »" % id)
	_check(piece.footprint_shape == EnvironmentPieceData.FootprintShape.CIRCLE and is_equal_approx(piece.footprint_radius, 5.0),
		"%s : disque de 5 m de rayon" % id)
	_check(not piece.blocks_movement, "%s : ne bloque pas le déplacement" % id)
	_check(piece.resource == resource, "%s : ressource %s" % [id, EnvironmentPieceData.ResourceKind.keys()[resource]])
	var model := piece.scene.instantiate()
	var missing: Array[String] = []
	for part in POINT_PARTS:
		if model.find_child(part, true, false) == null:
			missing.append(part)
	model.free()
	_check(missing.is_empty(), "%s : objets %s présents %s" % [id, POINT_PARTS, missing])


## Boîte englobante (repère du modèle), triangles et matériaux de tous les maillages.
func _measure(model: Node3D) -> Dictionary:
	var stats := {"aabb": AABB(), "triangles": 0, "materials": {}, "meshes": 0}
	var inverse := model.global_transform.affine_inverse()
	for node in model.find_children("*", "MeshInstance3D", true, false):
		var instance := node as MeshInstance3D
		var mesh := instance.mesh
		if mesh == null:
			continue
		var box := inverse * instance.global_transform * mesh.get_aabb()
		stats.aabb = box if stats.meshes == 0 else stats.aabb.merge(box)
		stats.meshes += 1
		for surface in mesh.get_surface_count():
			var array_mesh := mesh as ArrayMesh
			if array_mesh != null:
				var count := array_mesh.surface_get_array_index_len(surface)
				if count <= 0:
					count = array_mesh.surface_get_array_len(surface)
				stats.triangles += count / 3
			var material := instance.get_active_material(surface)
			if material != null:
				stats.materials[material.resource_name] = true
	return stats


func _on_grid(value: float) -> bool:
	return is_equal_approx(fmod(value, GRID), 0.0)


func _check(condition: bool, label: String) -> void:
	_checks += 1
	print(("  OK    " if condition else "  ÉCHEC ") + label)
	if not condition:
		_failures.append(label)


func _finish() -> void:
	print("%d vérifications, %d échec(s)" % [_checks, _failures.size()])
	for failure in _failures:
		print("  - " + failure)
	quit(0 if _failures.is_empty() else 1)
