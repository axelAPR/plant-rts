class_name UnitRenderer
extends Node3D
## Représentation visuelle des unités et des escouades. Lit l'état de la simulation
## (sans jamais le modifier) et l'affiche, interpolé entre deux ticks physiques :
## - le modèle de chaque unité ;
## - un anneau au sol à la couleur de son escouade (épais et vif si sélectionnée) ;
## - le numéro de l'escouade au-dessus de son centre ;
## - la destination en cours.

@export var simulation: UnitSimulation
@export var selection: SelectionController

@export_group("Escouades")
## Couleurs attribuées aux escouades, dans l'ordre de leur création.
@export var squad_colors: Array[Color] = [
	Color(0.2, 0.75, 1.0),
	Color(1.0, 0.7, 0.1),
	Color(0.85, 0.35, 1.0),
	Color(1.0, 0.35, 0.35),
]
## Hauteur (m) du numéro d'escouade au-dessus du sol.
@export var label_height: float = 2.4

@export_group("Anneaux")
## Rayon (m) de l'anneau, en multiple du rayon de l'unité.
@export var ring_radius_scale: float = 1.2
@export var ring_width_idle: float = 0.06
@export var ring_width_selected: float = 0.16


## Éléments visuels d'une escouade.
class SquadVisual:
	var squad: Squad
	var unit_nodes: Array[Node3D] = []
	var rings: Array[MeshInstance3D] = []
	var label: Label3D
	var destination_marker: MeshInstance3D
	var idle_mesh: TorusMesh
	var selected_mesh: TorusMesh


var _visuals: Array[SquadVisual] = []


func _ready() -> void:
	simulation.squad_spawned.connect(_on_squad_spawned)
	selection.selection_changed.connect(_on_selection_changed)
	for squad in simulation.squads:
		_on_squad_spawned(squad)


func _process(_delta: float) -> void:
	var alpha := Engine.get_physics_interpolation_fraction()
	for visual in _visuals:
		var squad := visual.squad
		var center := Vector3.ZERO
		for i in squad.units.size():
			var unit := squad.units[i]
			var node := visual.unit_nodes[i]
			node.position = unit.previous_position.lerp(unit.position, alpha)
			node.rotation.y = lerp_angle(unit.previous_yaw, unit.yaw, alpha)
			center += node.position
		center /= maxi(squad.units.size(), 1)
		visual.label.position = center + Vector3.UP * label_height

		var move_order := squad.order as MoveOrder
		visual.destination_marker.visible = move_order != null
		if move_order != null:
			visual.destination_marker.position = move_order.target + Vector3.UP * 0.03


func _on_squad_spawned(squad: Squad) -> void:
	var color := squad_colors[squad.id % squad_colors.size()]
	var radius := squad.data.unit_data.radius * ring_radius_scale

	var visual := SquadVisual.new()
	visual.squad = squad
	visual.idle_mesh = _make_ring_mesh(radius, ring_width_idle, _make_material(color.darkened(0.25)))
	visual.selected_mesh = _make_ring_mesh(radius, ring_width_selected, _make_material(color.lightened(0.25)))

	for unit in squad.units:
		var node := Node3D.new()
		node.name = "Unit%d" % unit.id
		if unit.data.visual_scene != null:
			node.add_child(unit.data.visual_scene.instantiate())
		var ring := MeshInstance3D.new()
		ring.mesh = visual.idle_mesh
		ring.position.y = 0.03
		ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		node.add_child(ring)
		add_child(node)
		visual.unit_nodes.append(node)
		visual.rings.append(ring)

	visual.label = Label3D.new()
	visual.label.text = str(squad.id + 1)
	visual.label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	visual.label.no_depth_test = true
	visual.label.font_size = 72
	visual.label.outline_size = 18
	visual.label.pixel_size = 0.01
	visual.label.modulate = color.darkened(0.25)
	add_child(visual.label)

	var marker_radius := squad.get_formation_width() * 0.5
	visual.destination_marker = MeshInstance3D.new()
	visual.destination_marker.mesh = _make_ring_mesh(marker_radius, 0.08, _make_material(color))
	visual.destination_marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	visual.destination_marker.visible = false
	add_child(visual.destination_marker)

	_visuals.append(visual)
	_apply_selection_state(visual)


func _on_selection_changed(_squads: Array[Squad]) -> void:
	for visual in _visuals:
		_apply_selection_state(visual)


func _apply_selection_state(visual: SquadVisual) -> void:
	var selected := selection.is_selected(visual.squad)
	for ring in visual.rings:
		ring.mesh = visual.selected_mesh if selected else visual.idle_mesh
	var color := squad_colors[visual.squad.id % squad_colors.size()]
	visual.label.modulate = color.lightened(0.3) if selected else color.darkened(0.25)
	visual.label.outline_modulate = Color.WHITE if selected else Color.BLACK


func _make_ring_mesh(radius: float, width: float, material: Material) -> TorusMesh:
	var mesh := TorusMesh.new()
	mesh.inner_radius = radius - width * 0.5
	mesh.outer_radius = radius + width * 0.5
	mesh.rings = 32
	mesh.ring_segments = 4
	mesh.material = material
	return mesh


func _make_material(color: Color) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color = color
	return material
