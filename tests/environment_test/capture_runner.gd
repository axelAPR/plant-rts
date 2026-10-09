extends SceneTree
## Captures du kit de décor depuis la caméra de jeu RTS (champ vertical 50°,
## inclinaison de 40° à 65° selon la distance, comme camera/rts_camera.gd), en zoom
## proche, moyen et lointain, pour world/maps/kit_showcase et world/maps/kit_demo,
## plus des vues rapprochées des raccords modulaires du diorama.
##
## Lancement (fenêtré, pour le rendu) :
##   Godot --path . --script res://tests/environment_test/capture_runner.gd
## Option : -- --only=<nom> (ex. suburb) pour ne capturer qu'une scène.
## Les PNG sont écrits dans tests/environment_test/captures/.
## Vérifie aussi que chaque scène se charge et que chaque pièce du catalogue
## s'instancie (code de sortie 1 sinon).

const OUT := "res://tests/environment_test/captures/"
const ZOOM_MIN := 10.0
const ZOOM_MAX := 80.0

## [scène, nom, [[cible x, z, distance, lacet°, suffixe, (inclinaison° imposée)]…]]
const SHOTS := [
	["res://world/maps/kit_showcase/kit_showcase.tscn", "kit_showcase", [
		[30.0, 30.0, 18.0, -25.0, "near"], [50.0, 50.0, 45.0, -20.0, "mid"], [55.0, 60.0, 80.0, -15.0, "far"]]],
	["res://world/maps/kit_demo/kit_demo.tscn", "kit_demo", [
		[-8.0, -10.0, 18.0, -25.0, "near"], [0.0, 2.0, 45.0, -20.0, "mid"], [0.0, 0.0, 80.0, -15.0, "far"],
		[-30.0, -8.0, 10.0, -35.0, "joint_fence"], [14.0, 4.0, 12.0, -30.0, "joint_road"],
		[22.0, 10.0, 12.0, -30.0, "joint_iron"]]],
	["res://world/maps/suburb/suburb.tscn", "suburb", [
		[0.0, 40.0, 40.0, 0.0, "start"], [0.0, 0.0, 80.0, 0.0, "far_center"], [0.0, 6.0, 25.0, -20.0, "park"],
		[-20.0, 30.0, 18.0, 25.0, "street_plants"], [20.0, -30.0, 18.0, 205.0, "street_zombies"],
		[8.0, 62.0, 30.0, -30.0, "base_plants"], [-16.0, -64.0, 30.0, 160.0, "base_zombies"],
		[56.0, 0.0, 30.0, -60.0, "field"], [0.0, 30.0, 30.0, 0.0, "sky", 12.0]]],
]

var _failures: Array[String] = []


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	_check_catalog()
	var only := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--only="):
			only = arg.trim_prefix("--only=")
	for shot in SHOTS:
		if not only.is_empty() and shot[1] != only:
			continue
		var packed := load(shot[0]) as PackedScene
		if packed == null:
			_failures.append("scène introuvable : %s" % shot[0])
			continue
		var scene := packed.instantiate()
		root.add_child(scene)
		var camera := Camera3D.new()
		camera.fov = 50.0
		camera.far = 400.0
		scene.add_child(camera)
		camera.make_current()
		for view in shot[2]:
			_place(camera, Vector3(view[0], 0.0, view[1]), view[2], view[3], view[5] if view.size() > 5 else -1.0)
			for i in 4:
				await process_frame
			var path := OUT + "%s_%s.png" % [shot[1], view[4]]
			root.get_viewport().get_texture().get_image().save_png(ProjectSettings.globalize_path(path))
			print("capture : %s" % path)
		scene.queue_free()
		await process_frame
	print("%d échec(s)" % _failures.size())
	for failure in _failures:
		print("  ÉCHEC  %s" % failure)
	quit(0 if _failures.is_empty() else 1)


## Caméra placée comme celle du jeu : distance, inclinaison liée au zoom, lacet.
## `pitch_degrees` ≥ 0 impose l'inclinaison (vue hors jeu, par exemple pour le ciel).
func _place(camera: Camera3D, target: Vector3, distance: float, yaw_degrees: float, pitch_degrees: float = -1.0) -> void:
	var ratio := clampf((distance - ZOOM_MIN) / (ZOOM_MAX - ZOOM_MIN), 0.0, 1.0)
	var pitch := deg_to_rad(lerpf(40.0, 65.0, ratio) if pitch_degrees < 0.0 else pitch_degrees)
	var yaw := deg_to_rad(yaw_degrees)
	var offset := Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch)) * distance
	camera.look_at_from_position(target + offset, target)


## Chaque pièce du catalogue : scène présente, instanciable, hauteur cohérente.
func _check_catalog() -> void:
	var catalog := load("res://data/environment/environment_catalog.tres") as EnvironmentCatalog
	if catalog == null:
		_failures.append("catalogue introuvable")
		return
	for piece in catalog.pieces:
		if piece.scene == null:
			_failures.append("%s : scène manquante" % piece.id)
			continue
		var node := piece.scene.instantiate()
		if node == null:
			_failures.append("%s : instanciation impossible" % piece.id)
		else:
			node.free()
		if piece.height <= 0.0:
			_failures.append("%s : hauteur nulle" % piece.id)
	print("catalogue : %d pièces vérifiées" % catalog.pieces.size())
