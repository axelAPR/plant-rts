@tool
class_name RoadNetwork
extends Node3D
## Réseau routier généré à partir de courbes : routes (RoadPath) et carrefours ou
## raquettes de retournement (RoadJunction), placés sous ce nœud. Même profil et
## mêmes matériaux que les tuiles du kit (assets/environment/ground) : chaussée de
## 6 m, trottoirs de 1 m à 0,15 m, ligne médiane en tirets de 1,5 m au pas de 4 m.
## Une extrémité de route posée sur un carrefour (à moins de `attach_distance`) est
## raccourcie de la longueur de bras du carrefour ; le carrefour reprend exactement
## la section de fin de la route (raccord sans trou ni chevauchement).
## Maillages reconstruits au chargement et, dans l'éditeur, avec « Reconstruire ».
## Affichage seul : pas de collision, la navigation et le clic au sol ne les lisent pas.

## Tuile du kit dont on reprend les matériaux (chaussée, béton, peinture).
const KIT_TILE := "res://assets/environment/ground/road_straight.glb"
const KIT_MATERIALS: Array[String] = ["Env_Asphalt", "Env_Concrete", "Env_Paint"]

@export_group("Profil")
## Demi-largeur de la chaussée (m).
@export var lane_half_width: float = 3.0
@export var sidewalk_width: float = 1.0
@export var road_height: float = 0.02
@export var sidewalk_height: float = 0.15
## Épaisseur de la peinture au-dessus de la chaussée (m).
@export var paint_height: float = 0.006

@export_group("Marquages")
@export var dash_length: float = 1.5
@export var dash_period: float = 4.0
@export var dash_width: float = 0.14

@export_group("Carrefours")
## Rayon des bordures arrondies aux angles des carrefours (m).
@export var corner_radius: float = 6.0
## Distance maximale entre une extrémité de route et un carrefour pour les relier.
@export var attach_distance: float = 0.5

@export_group("Maillage")
## Pas d'échantillonnage le long des courbes (m).
@export var sample_step: float = 1.0
## Taille d'une répétition des textures (m), comme le kit.
@export var texture_meters: float = 4.0

@export_tool_button("Reconstruire") var rebuild_action: Callable = rebuild

var _materials: Array[Material] = []


func _ready() -> void:
	rebuild()


func rebuild() -> void:
	_load_materials()
	var roads: Array[RoadPath] = []
	var junctions: Array[RoadJunction] = []
	for node in find_children("*", "", true, false):
		if node is RoadPath:
			roads.append(node)
		elif node is RoadJunction:
			junctions.append(node)
	var arms: Dictionary = {}
	for junction in junctions:
		arms[junction] = []
	for road in roads:
		road.start_trim = 0.0
		road.end_trim = 0.0
		for at_start: bool in [true, false]:
			var junction := _junction_at(junctions, road.end_point(at_start))
			if junction == null:
				continue
			if at_start:
				road.start_trim = junction.arm_length
			else:
				road.end_trim = junction.arm_length
		road.build(self)
		for at_start: bool in [true, false]:
			var junction := _junction_at(junctions, road.end_point(at_start))
			if junction != null:
				arms[junction].append(road.end_edges(at_start))
	for junction in junctions:
		junction.build(self, arms[junction])


func get_materials() -> Array[Material]:
	return _materials


func _junction_at(junctions: Array[RoadJunction], point: Vector3) -> RoadJunction:
	for junction in junctions:
		var d := junction.global_position - point
		d.y = 0.0
		if d.length() <= attach_distance:
			return junction
	return null


func _load_materials() -> void:
	if _materials.size() == KIT_MATERIALS.size():
		return
	_materials.clear()
	var found: Dictionary = {}
	var packed := load(KIT_TILE) as PackedScene
	if packed != null:
		var tile := packed.instantiate()
		for node in tile.find_children("*", "MeshInstance3D", true, false):
			var mesh := (node as MeshInstance3D).mesh
			for i in mesh.get_surface_count():
				var material := mesh.surface_get_material(i)
				if material != null:
					found[material.resource_name] = material
		tile.free()
	for name in KIT_MATERIALS:
		var material: Material = found.get(name)
		if material == null:
			push_warning("RoadNetwork : matériau %s introuvable dans %s" % [name, KIT_TILE])
			material = StandardMaterial3D.new()
		_materials.append(material)
