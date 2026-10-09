class_name HudMinimap
extends Control
## Mini-carte : vue de dessus de la carte (rendue une fois au démarrage par une caméra
## orthographique ; fond uni sans rendu, en headless), bâtiments, unités et champ de
## la caméra. Clic gauche ou glisser : centre la caméra sur le point visé.
##
## Visibilité : pas encore de brouillard de guerre (world/fog_of_war vide) ; toutes
## les unités sont donc connues, comme dans la vue 3D. `is_visible_to_player()` est le
## point d'entrée prévu pour le brouillard.

var camera_rig: RTSCamera
var simulation: UnitSimulation
var buildings: BuildingSystem
var selection: SelectionController
var player: PlayerState
var skin: HudSkin
## Zone représentée (bornes de la caméra, plan XZ).
var bounds: Rect2

var _overview: Texture2D
var _dragging: bool = false


func setup(p_camera: RTSCamera, p_simulation: UnitSimulation, p_buildings: BuildingSystem,
		p_selection: SelectionController, p_player: PlayerState, p_skin: HudSkin) -> void:
	camera_rig = p_camera
	simulation = p_simulation
	buildings = p_buildings
	selection = p_selection
	player = p_player
	skin = p_skin
	bounds = camera_rig.bounds
	mouse_filter = Control.MOUSE_FILTER_STOP
	tooltip_text = "Mini-carte : cliquer pour déplacer la caméra"
	_capture_overview.call_deferred()


func _process(_delta: float) -> void:
	queue_redraw()


## Point d'entrée du futur brouillard de guerre : l'unité ou le bâtiment de ce camp
## est-il connu du joueur ?
func is_visible_to_player(_team: int, _position: Vector3) -> bool:
	return true


func world_to_map(point: Vector3) -> Vector2:
	return Vector2((point.x - bounds.position.x) / bounds.size.x * size.x,
		(point.z - bounds.position.y) / bounds.size.y * size.y)


func map_to_world(point: Vector2) -> Vector3:
	return Vector3(bounds.position.x + point.x / size.x * bounds.size.x, 0.0,
		bounds.position.y + point.y / size.y * bounds.size.y)


func _gui_input(event: InputEvent) -> void:
	var button := event as InputEventMouseButton
	if button != null and button.button_index == MOUSE_BUTTON_LEFT:
		_dragging = button.pressed
		if button.pressed:
			camera_rig.focus_on(map_to_world(button.position))
		accept_event()
	elif event is InputEventMouseMotion and _dragging:
		camera_rig.focus_on(map_to_world((event as InputEventMouseMotion).position))
		accept_event()


func _draw() -> void:
	var area := Rect2(Vector2.ZERO, size)
	if _overview != null:
		draw_texture_rect(_overview, area, false)
	else:
		draw_rect(area, Color(0.22, 0.32, 0.2))
	for building in buildings.buildings:
		if not building.is_alive() or not is_visible_to_player(building.team, building.position):
			continue
		var half := building.data.footprint_size * 0.5 / bounds.size * size
		var center := world_to_map(building.position)
		var rect := Rect2(center - half, half * 2.0)
		draw_rect(rect, _team_color(building.data.faction))
		var selected := building == selection.selected_building
		draw_rect(rect, Color.WHITE if selected else Color.BLACK, false, 1.5)
	for squad in simulation.squads:
		var color := _team_color(squad.data.unit_data.faction)
		var selected := selection.is_selected(squad)
		for unit in squad.units:
			if not is_visible_to_player(unit.team, unit.position):
				continue
			var p := world_to_map(unit.position)
			if selected:
				draw_circle(p, 2.6, Color.WHITE)
			draw_circle(p, 1.8, color)
	_draw_camera_view()
	draw_rect(area, Color(0, 0, 0, 0.8), false, 2.0)


## Trapèze du champ de la caméra au sol.
func _draw_camera_view() -> void:
	var camera := camera_rig.get_camera()
	var viewport_size := camera.get_viewport().get_visible_rect().size
	var corners := [Vector2.ZERO, Vector2(viewport_size.x, 0.0), viewport_size, Vector2(0.0, viewport_size.y)]
	var points := PackedVector2Array()
	for corner: Vector2 in corners:
		var origin := camera.project_ray_origin(corner)
		var normal := camera.project_ray_normal(corner)
		if normal.y > -0.01:
			normal.y = -0.01                     # rayon au-dessus de l'horizon : borné
		var t := -origin.y / normal.y
		var hit := origin + normal * minf(t, 600.0)
		var p := world_to_map(hit)
		points.append(Vector2(clampf(p.x, 0.0, size.x), clampf(p.y, 0.0, size.y)))
	points.append(points[0])
	draw_polyline(points, Color(1, 1, 1, 0.85), 1.5)


func _team_color(faction: FactionData) -> Color:
	return faction.unit_color if faction != null else Color.WHITE


## Vue de dessus rendue une seule fois (même monde 3D, caméra orthographique, sans
## brouillard atmosphérique). Ignorée sans rendu (headless).
func _capture_overview() -> void:
	if DisplayServer.get_name() == "headless":
		return
	var viewport := SubViewport.new()
	viewport.size = Vector2i(256, 256)
	viewport.world_3d = camera_rig.get_viewport().world_3d
	viewport.render_target_update_mode = SubViewport.UPDATE_ONCE
	var camera := Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = maxf(bounds.size.x, bounds.size.y)
	camera.near = 1.0
	camera.far = 900.0
	var center := bounds.get_center()
	camera.position = Vector3(center.x, 400.0, center.y)
	camera.rotation_degrees = Vector3(-90.0, 0.0, 0.0)
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.22, 0.32, 0.2)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.85, 0.85, 0.85)
	environment.ambient_light_energy = 0.8
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	camera.environment = environment
	viewport.add_child(camera)
	add_child(viewport)
	camera.make_current()
	for i in 3:
		await RenderingServer.frame_post_draw
	var image := viewport.get_texture().get_image()
	if image != null and not image.is_empty():
		_overview = ImageTexture.create_from_image(image)
	viewport.queue_free()
