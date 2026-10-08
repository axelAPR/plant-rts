class_name RTSCamera
extends Node3D
## Caméra RTS orbitale : déplacement (clavier + bords d'écran), zoom (molette)
## et rotation (touches + glisser avec le bouton du milieu).
##
## Ce nœud est le point de focus au sol ; la Camera3D enfant orbite autour de lui
## selon l'angle horizontal (yaw), l'inclinaison (pitch) et la distance (zoom).
## L'inclinaison dépend du zoom : vue plus rasante de près, plus plongeante de loin.

@export_group("Déplacement")
## Vitesse de déplacement (m/s) au zoom minimum.
@export var pan_speed_near: float = 15.0
## Vitesse de déplacement (m/s) au zoom maximum.
@export var pan_speed_far: float = 60.0
## Multiplicateur appliqué tant que l'action « camera_fast » est maintenue.
@export var fast_multiplier: float = 2.0
## Zone de la carte (plan XZ) dans laquelle le point de focus est contenu.
@export var bounds: Rect2 = Rect2(-100.0, -100.0, 200.0, 200.0)

@export_group("Défilement aux bords")
@export var edge_scroll_enabled: bool = true
## Épaisseur (en pixels) de la bande de bord qui déclenche le défilement.
@export var edge_scroll_margin: float = 8.0

@export_group("Zoom")
@export var zoom_min_distance: float = 10.0
@export var zoom_max_distance: float = 80.0
@export var initial_distance: float = 40.0
## Fraction de la distance actuelle ajoutée/retirée à chaque cran de molette.
@export_range(0.01, 0.5) var zoom_step: float = 0.12
## Inclinaison (degrés sous l'horizontale) au zoom minimum.
@export_range(10.0, 89.0) var pitch_near_degrees: float = 40.0
## Inclinaison (degrés sous l'horizontale) au zoom maximum.
@export_range(10.0, 89.0) var pitch_far_degrees: float = 65.0

@export_group("Rotation")
## Vitesse de rotation au clavier (degrés/s).
@export var rotate_speed_degrees: float = 120.0
## Rotation (degrés) par pixel de déplacement de la souris pendant le glisser.
@export var drag_rotate_sensitivity: float = 0.3

@export_group("Lissage")
## Réactivité du lissage : plus la valeur est haute, plus la caméra suit vite sa cible.
@export var smoothing: float = 12.0

var _target_position: Vector3
var _target_yaw: float
var _target_distance: float
var _yaw: float
var _distance: float
var _is_drag_rotating: bool = false
## Hors de la fenêtre, Godot conserve la dernière position de la souris (souvent au bord) :
## sans ce suivi, la caméra défilerait indéfiniment quand le curseur part sur un autre écran.
var _is_mouse_in_window: bool = true

var _home_position: Vector3
var _home_yaw: float
var _home_distance: float

## Temps réel du dernier _process, pour rester indépendant de Engine.time_scale
## (vitesse de jeu, ralenti) : la caméra doit rester réactive même jeu ralenti.
var _last_ticks_usec: int = 0

@onready var _camera: Camera3D = $Camera3D


func _ready() -> void:
	# La caméra doit rester utilisable pendant la pause (pause tactique).
	process_mode = Node.PROCESS_MODE_ALWAYS

	_target_position = _clamp_to_bounds(global_position)
	_target_yaw = rotation.y
	_target_distance = clampf(initial_distance, zoom_min_distance, zoom_max_distance)
	_home_position = _target_position
	_home_yaw = _target_yaw
	_home_distance = _target_distance
	_snap_to_target()
	_last_ticks_usec = Time.get_ticks_usec()

	get_window().mouse_entered.connect(func() -> void: _is_mouse_in_window = true)
	get_window().mouse_exited.connect(func() -> void: _is_mouse_in_window = false)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("camera_zoom_in"):
		zoom_by(-zoom_step)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("camera_zoom_out"):
		zoom_by(zoom_step)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("camera_rotate_drag"):
		_is_drag_rotating = true
		get_viewport().set_input_as_handled()
	elif event.is_action_released("camera_rotate_drag"):
		_is_drag_rotating = false
	elif event.is_action_pressed("camera_reset"):
		reset_view()
		get_viewport().set_input_as_handled()
	elif event is InputEventMouseMotion and _is_drag_rotating:
		var motion := event as InputEventMouseMotion
		# screen_relative (pixels écran) et non relative (pixels du viewport étiré),
		# sinon la sensibilité changerait avec la résolution de la fenêtre.
		_target_yaw -= deg_to_rad(motion.screen_relative.x * drag_rotate_sensitivity)
		get_viewport().set_input_as_handled()


func _process(_delta: float) -> void:
	var now := Time.get_ticks_usec()
	# Plafonné pour éviter un saut de caméra après un gel (chargement, débogueur).
	var dt := minf((now - _last_ticks_usec) / 1_000_000.0, 0.1)
	_last_ticks_usec = now

	# Le relâchement du bouton peut être consommé par l'UI : on resynchronise.
	if _is_drag_rotating and not Input.is_action_pressed("camera_rotate_drag"):
		_is_drag_rotating = false

	_update_pan(dt)
	_target_yaw += Input.get_axis("camera_rotate_right", "camera_rotate_left") \
			* deg_to_rad(rotate_speed_degrees) * dt

	var weight := 1.0 - exp(-smoothing * dt)
	global_position = global_position.lerp(_target_position, weight)
	_yaw = lerpf(_yaw, _target_yaw, weight)
	_distance = lerpf(_distance, _target_distance, weight)
	_apply_transform()


## Zoom relatif : valeur négative pour rapprocher, positive pour éloigner.
func zoom_by(fraction: float) -> void:
	_target_distance = clampf(_target_distance * (1.0 + fraction), zoom_min_distance, zoom_max_distance)


## Centre la caméra sur un point du monde (utile plus tard : minimap, alertes, sélection).
func focus_on(world_position: Vector3) -> void:
	_target_position = _clamp_to_bounds(Vector3(world_position.x, _target_position.y, world_position.z))


## Retour à la vue initiale.
func reset_view() -> void:
	_target_position = _home_position
	# Revenir à l'angle initial par le chemin le plus court.
	_target_yaw = _yaw + angle_difference(_yaw, _home_yaw)
	_target_distance = _home_distance


func get_camera() -> Camera3D:
	return _camera


func _update_pan(dt: float) -> void:
	var input := Input.get_vector("camera_pan_left", "camera_pan_right", "camera_pan_forward", "camera_pan_back")
	input = (input + _get_edge_scroll_input()).limit_length(1.0)
	if input == Vector2.ZERO:
		return

	var zoom_ratio := inverse_lerp(zoom_min_distance, zoom_max_distance, _distance)
	var speed := lerpf(pan_speed_near, pan_speed_far, zoom_ratio)
	if Input.is_action_pressed("camera_fast"):
		speed *= fast_multiplier

	# Déplacement relatif à l'orientation de la caméra, à plat sur le sol.
	var direction := Vector3(input.x, 0.0, input.y).rotated(Vector3.UP, _yaw)
	_target_position = _clamp_to_bounds(_target_position + direction * speed * dt)


func _get_edge_scroll_input() -> Vector2:
	if not edge_scroll_enabled or _is_drag_rotating or not _is_mouse_in_window \
			or not get_window().has_focus():
		return Vector2.ZERO

	var viewport := get_viewport()
	var mouse := viewport.get_mouse_position()
	var size := viewport.get_visible_rect().size
	if not Rect2(Vector2.ZERO, size).has_point(mouse):
		return Vector2.ZERO

	var input := Vector2.ZERO
	if mouse.x <= edge_scroll_margin:
		input.x -= 1.0
	elif mouse.x >= size.x - edge_scroll_margin:
		input.x += 1.0
	if mouse.y <= edge_scroll_margin:
		input.y -= 1.0
	elif mouse.y >= size.y - edge_scroll_margin:
		input.y += 1.0
	return input


func _apply_transform() -> void:
	rotation = Vector3(0.0, _yaw, 0.0)
	var zoom_ratio := inverse_lerp(zoom_min_distance, zoom_max_distance, _distance)
	var pitch := deg_to_rad(lerpf(pitch_near_degrees, pitch_far_degrees, zoom_ratio))
	_camera.position = Vector3(0.0, sin(pitch) * _distance, cos(pitch) * _distance)
	_camera.rotation = Vector3(-pitch, 0.0, 0.0)


func _snap_to_target() -> void:
	global_position = _target_position
	_yaw = _target_yaw
	_distance = _target_distance
	_apply_transform()


func _clamp_to_bounds(point: Vector3) -> Vector3:
	return Vector3(
		clampf(point.x, bounds.position.x, bounds.end.x),
		point.y,
		clampf(point.z, bounds.position.y, bounds.end.y),
	)
