extends SceneTree
## Test automatisé du réseau routier courbe de la Banlieue (RoadNetwork) : routes
## raccordées à leurs deux extrémités, bords des routes et des bras de carrefour
## confondus (ni trou ni chevauchement), maillages présents, rayon de courbure
## minimal, tronçon droit à l'approche des carrefours, aucun décor sur la route.
##
## Lancement : Godot --headless --path . --script res://tests/roads_test/road_runner.gd
## Code de sortie : 0 si tout passe, 1 sinon.

const MAP := "res://world/maps/suburb/suburb.tscn"
const EXPECTED_ROADS := 24
const EXPECTED_JUNCTIONS := 21
## Rayon de courbure minimal de l'axe (m), règle du tracé.
const MIN_RADIUS := 30.0
## Écart toléré entre les bords d'une route et ceux du bras du carrefour (m).
const SEAM_TOLERANCE := 0.01
## Pièces posées volontairement sur la route ou le trottoir.
const ON_ROAD_ALLOWED: Array[String] = ["mailbox", "street_lamp", "fire_hydrant", "road_sign", "traffic_cone",
	"trash_cans", "car_sedan", "car_wreck", "pickup_truck"]
const CHECKED_CATEGORIES := [EnvironmentPieceData.Category.BUILDINGS, EnvironmentPieceData.Category.COVER_HEAVY,
	EnvironmentPieceData.Category.COVER_LIGHT, EnvironmentPieceData.Category.VEGETATION]

var _failures: Array[String] = []
var _checks: int = 0


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var scene := (load(MAP) as PackedScene).instantiate()
	root.add_child(scene)
	await process_frame
	var network := scene.get_node_or_null("Roads") as RoadNetwork
	_check(network != null, "nœud Roads (RoadNetwork) présent")
	if network == null:
		_finish()
		return
	var roads: Array[RoadPath] = []
	var junctions: Array[RoadJunction] = []
	for node in network.get_children():
		if node is RoadPath:
			roads.append(node)
		elif node is RoadJunction:
			junctions.append(node)
	_check(roads.size() == EXPECTED_ROADS, "%d routes (attendu %d)" % [roads.size(), EXPECTED_ROADS])
	_check(junctions.size() == EXPECTED_JUNCTIONS,
		"%d carrefours et raquettes (attendu %d)" % [junctions.size(), EXPECTED_JUNCTIONS])

	print("Raccords")
	var edges: Array = []
	for junction in junctions:
		edges.append_array(junction.arm_edges)
	var hw := network.lane_half_width
	var unattached: Array[String] = []
	var bad_seams: Array[String] = []
	for road in roads:
		if road.start_trim <= 0.0 or road.end_trim <= 0.0:
			unattached.append(road.name)
		for at_start: bool in [true, false]:
			var end := road.end_edges(at_start)
			var c: Vector3 = end["center"]
			var d: Vector3 = end["direction"]
			var n := d.cross(Vector3.UP).normalized() * hw
			var gap := _seam_gap(edges, c + n, c - n)
			if gap > SEAM_TOLERANCE:
				bad_seams.append("%s (%s) : %.3f m" % [road.name, "départ" if at_start else "arrivée", gap])
	_check(unattached.is_empty(), "chaque route est raccordée à ses deux extrémités %s" % [unattached])
	_check(bad_seams.is_empty(), "bords des routes = bords des bras (≤ %.2f m) %s" % [SEAM_TOLERANCE, bad_seams])
	var arms: Array[String] = []
	for junction in junctions:
		var turnaround := junction.name.begins_with("end")
		var count := junction.arm_edges.size()
		if (turnaround and count != 1) or (not turnaround and count < 3):
			arms.append("%s : %d bras" % [junction.name, count])
	_check(arms.is_empty(), "carrefours à 3 ou 4 bras, raquettes à 1 bras %s" % [arms])

	print("Maillages")
	var empty: Array[String] = []
	for node: Node3D in roads + junctions:
		var mesh_node := node.get_node_or_null("Mesh") as MeshInstance3D
		if mesh_node == null or mesh_node.mesh == null or mesh_node.mesh.get_surface_count() < 2:
			empty.append(node.name)
	_check(empty.is_empty(), "chaque route et carrefour a un maillage (chaussée + béton) %s" % [empty])

	print("Tracé")
	for road in roads:
		var radius := _min_radius(road)
		_check(radius >= MIN_RADIUS, "%s : rayon minimal %.0f m (≥ %.0f)" % [road.name, radius, MIN_RADIUS])
	var bent: Array[String] = []
	for road in roads:
		for at_start: bool in [true, false]:
			var o := road.start_trim if at_start else road.length() - road.end_trim
			var tip := road.point_at(0.0 if at_start else road.length())
			var section := road.point_at(o)
			var inner := road.point_at(o + (1.0 if at_start else -1.0))
			var axis := (section - tip).normalized()
			var off := (inner - tip) - axis * (inner - tip).dot(axis)
			if off.length() > 0.05:
				bent.append("%s : %.2f m" % [road.name, off.length()])
	_check(bent.is_empty(), "tronçon droit au-delà du raccord des carrefours %s" % [bent])

	print("Décor")
	_check_decor_clearance(scene, roads, network)
	scene.queue_free()
	_finish()


## Plus grand écart entre les deux bords (gauche, droite) d'une fin de route et les
## bords du bras de carrefour le plus proche.
func _seam_gap(edges: Array, left: Vector3, right: Vector3) -> float:
	var best := INF
	for pair in edges:
		var a: Vector3 = pair[0]
		var b: Vector3 = pair[1]
		best = minf(best, maxf(a.distance_to(left), b.distance_to(right)))
		best = minf(best, maxf(a.distance_to(right), b.distance_to(left)))
	return best


## Rayon de courbure minimal de l'axe entre les raccords (cercle par trois points
## espacés de 5 m).
func _min_radius(road: RoadPath) -> float:
	var best := INF
	var o := road.start_trim + 5.0
	while o + 5.0 <= road.length() - road.end_trim:
		var a := road.point_at(o - 5.0)
		var b := road.point_at(o)
		var c := road.point_at(o + 5.0)
		var area := absf((b - a).cross(c - a).y) * 0.5
		if area > 1e-4:
			best = minf(best, a.distance_to(b) * b.distance_to(c) * c.distance_to(a) / (4.0 * area))
		o += 1.0
	return best


## Bâtiments, couverts et végétation : emprise hors de la chaussée et des trottoirs.
func _check_decor_clearance(scene: Node, roads: Array[RoadPath], network: RoadNetwork) -> void:
	var catalog := load("res://data/environment/environment_catalog.tres") as EnvironmentCatalog
	var by_scene: Dictionary = {}
	for piece in catalog.pieces:
		by_scene[piece.scene.resource_path] = piece
	var samples := PackedVector3Array()
	for road in roads:
		var o := 0.0
		while o <= road.length():
			samples.append(road.global_transform * road.point_at(o))
			o += 1.0
	var road_half := network.lane_half_width + network.sidewalk_width
	var offenders: Array[String] = []
	var checked := 0
	for group in scene.get_children():
		if group.name in ["Roads", "Border", "Horizon", "Points"]:
			continue
		for node in group.get_children():
			var piece: EnvironmentPieceData = by_scene.get((node as Node).scene_file_path)
			if piece == null or piece.category not in CHECKED_CATEGORIES or String(piece.id) in ON_ROAD_ALLOWED:
				continue
			checked += 1
			var p := (node as Node3D).global_position
			var half := minf(piece.footprint_size.x, piece.footprint_size.y) * 0.5
			var nearest := INF
			for s in samples:
				nearest = minf(nearest, Vector2(p.x - s.x, p.z - s.z).length())
			if nearest < road_half + half - 0.3:
				offenders.append("%s en (%.0f, %.0f) à %.1f m de l'axe" % [node.name, p.x, p.z, nearest])
	_check(offenders.is_empty(), "%d pièces de décor hors de la route %s" % [checked, offenders])


func _check(condition: bool, label: String) -> void:
	_checks += 1
	print(("  OK    " if condition else "  ÉCHEC ") + label)
	if not condition:
		_failures.append(label)


func _finish() -> void:
	print("%d vérifications, %d échec(s)" % [_checks, _failures.size()])
	quit(0 if _failures.is_empty() else 1)
