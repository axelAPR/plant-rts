class_name BuildingRenderer
extends Node3D
## Représentation visuelle des bâtiments (lecture seule de BuildingSystem) :
## - la scène d'affichage de chaque bâtiment (BuildingData.scene) ;
## - un volume de clic (StaticBody3D sur `pick_layer`, sans collision avec les
##   unités) qui porte l'identifiant du bâtiment, pour la sélection au rayon ;
## - un anneau au sol à la couleur de la faction quand il est sélectionné ;
## - le point de ralliement (fanion) du bâtiment sélectionné.
## Un bâtiment détruit est masqué et n'est plus cliquable.

const BUILDING_ID_META := &"building_id"

@export var buildings: BuildingSystem
@export var selection: SelectionController
## Couche physique des volumes de clic (distincte du terrain, couche 1).
@export_flags_3d_physics var pick_layer: int = 2

@export_group("Apparence")
@export var ring_width: float = 0.35
@export var rally_height: float = 2.2
@export var fallback_color: Color = Color(0.8, 0.8, 0.8)


class BuildingVisual:
	var building: Building
	var root: Node3D
	var model: Node3D
	var body: StaticBody3D
	var ring: MeshInstance3D
	var rally: Node3D


var _visuals: Dictionary[int, BuildingVisual] = {}


func _ready() -> void:
	buildings.building_added.connect(_on_building_added)
	buildings.building_destroyed.connect(_on_building_destroyed)
	if selection != null:
		selection.selected_building_changed.connect(_on_selected_building_changed)
	for building in buildings.buildings:
		_on_building_added(building)


func _process(_delta: float) -> void:
	var selected := selection.selected_building if selection != null else null
	for visual: BuildingVisual in _visuals.values():
		var shown := visual.building == selected and visual.building.is_alive()
		visual.rally.visible = shown
		if shown:
			visual.rally.global_position = visual.building.rally_point


func _on_building_added(building: Building) -> void:
	var visual := BuildingVisual.new()
	visual.building = building
	visual.root = Node3D.new()
	visual.root.name = "Building%d" % building.id
	visual.root.position = building.position
	visual.root.rotation.y = building.yaw
	add_child(visual.root)
	if building.data.scene != null:
		visual.model = building.data.scene.instantiate() as Node3D
		visual.root.add_child(visual.model)
	visual.body = _make_pick_body(building)
	visual.root.add_child(visual.body)
	var color := _color(building)
	visual.ring = MeshInstance3D.new()
	visual.ring.mesh = _ring_mesh(building.data.selection_radius, color)
	visual.ring.position.y = 0.06
	visual.ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	visual.ring.visible = false
	visual.root.add_child(visual.ring)
	visual.rally = _make_rally_marker(color)
	add_child(visual.rally)
	_visuals[building.id] = visual


func _on_building_destroyed(building: Building) -> void:
	var visual: BuildingVisual = _visuals.get(building.id)
	if visual == null:
		return
	if visual.model != null:
		visual.model.visible = false
	visual.ring.visible = false
	visual.body.collision_layer = 0


func _on_selected_building_changed(selected: Building) -> void:
	for visual: BuildingVisual in _visuals.values():
		visual.ring.visible = visual.building == selected and visual.building.is_alive()


func _make_pick_body(building: Building) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.collision_layer = pick_layer
	body.collision_mask = 0
	body.set_meta(BUILDING_ID_META, building.id)
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	var size := building.data.footprint_size
	box.size = Vector3(size.x, building.data.height, size.y)
	shape.shape = box
	shape.position.y = building.data.height * 0.5
	body.add_child(shape)
	return body


func _make_rally_marker(color: Color) -> Node3D:
	var marker := Node3D.new()
	marker.visible = false
	var pole := MeshInstance3D.new()
	var pole_mesh := CylinderMesh.new()
	pole_mesh.top_radius = 0.05
	pole_mesh.bottom_radius = 0.05
	pole_mesh.height = rally_height
	pole_mesh.material = _material(Color(0.9, 0.9, 0.9))
	pole.mesh = pole_mesh
	pole.position.y = rally_height * 0.5
	marker.add_child(pole)
	var flag := MeshInstance3D.new()
	var flag_mesh := BoxMesh.new()
	flag_mesh.size = Vector3(0.8, 0.5, 0.04)
	flag_mesh.material = _material(color)
	flag.mesh = flag_mesh
	flag.position = Vector3(0.42, rally_height - 0.3, 0.0)
	marker.add_child(flag)
	var foot := MeshInstance3D.new()
	foot.mesh = _ring_mesh(0.6, color)
	foot.position.y = 0.05
	marker.add_child(foot)
	for child in marker.get_children():
		(child as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return marker


func _ring_mesh(radius: float, color: Color) -> TorusMesh:
	var mesh := TorusMesh.new()
	mesh.inner_radius = radius - ring_width * 0.5
	mesh.outer_radius = radius + ring_width * 0.5
	mesh.rings = 48
	mesh.ring_segments = 4
	mesh.material = _material(color)
	return mesh


func _material(color: Color) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color = color
	return material


func _color(building: Building) -> Color:
	var faction := building.data.faction
	return faction.unit_color if faction != null else fallback_color
