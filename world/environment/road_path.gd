@tool
class_name RoadPath
extends Path3D
## Route générée le long de sa courbe (Curve3D, plan XZ) : chaussée, bordures,
## trottoirs et ligne médiane suivent la courbe. Profil et matériaux donnés par le
## RoadNetwork parent, qui raccourcit les extrémités posées sur un carrefour.
## Près d'un carrefour, la courbe doit être droite sur au moins la longueur de bras
## (la section d'extrémité est alors perpendiculaire au bras).

const MESH_NAME := "Mesh"

@export_group("Marquages")
@export var center_line: bool = true
## Passage piéton à l'extrémité de départ / d'arrivée (juste avant le carrefour).
@export var crosswalk_start: bool = false
@export var crosswalk_end: bool = false

## Longueurs retirées aux extrémités (m), fixées par le RoadNetwork.
var start_trim: float = 0.0
var end_trim: float = 0.0
## Pas d'échantillonnage du dernier build (pour les sections de fin).
var sample_step_hint: float = 1.0


func length() -> float:
	return curve.get_baked_length() if curve != null else 0.0


## Point de la courbe (repère du nœud, ramené au sol) à une abscisse curviligne.
func point_at(offset: float) -> Vector3:
	var p := curve.sample_baked(clampf(offset, 0.0, length()), true)
	return Vector3(p.x, 0.0, p.z)


## Extrémité de la courbe, en coordonnées monde.
func end_point(at_start: bool) -> Vector3:
	return global_transform * point_at(0.0 if at_start else length())


## Section de fin (monde) : centre et direction allant du carrefour vers la route.
func end_edges(at_start: bool) -> Dictionary:
	var sections := _sections(sample_step_hint)
	var i := 0 if at_start else sections.size() - 1
	var center: Vector3 = global_transform * sections[i][0]
	var tangent: Vector3 = global_transform.basis * sections[i][1]
	return {"center": center, "direction": tangent if at_start else -tangent, "road": self}



func build(network: RoadNetwork) -> void:
	sample_step_hint = network.sample_step
	var mesh_node := get_node_or_null(MESH_NAME) as MeshInstance3D
	if mesh_node == null:
		mesh_node = MeshInstance3D.new()
		mesh_node.name = MESH_NAME
		add_child(mesh_node)
	if curve == null or curve.point_count < 2:
		mesh_node.mesh = null
		return
	var builder := RoadMeshBuilder.new(network.texture_meters, global_position)
	var sections := _sections(network.sample_step)
	var hw := network.lane_half_width
	var ow := hw + network.sidewalk_width
	var y_road := network.road_height
	var y_walk := network.sidewalk_height
	var u := 0.0
	for i in sections.size() - 1:
		var c0: Vector3 = sections[i][0]
		var c1: Vector3 = sections[i + 1][0]
		var r0: Vector3 = _lateral(sections[i][1])
		var r1: Vector3 = _lateral(sections[i + 1][1])
		var up_road := Vector3(0.0, y_road, 0.0)
		var up_walk := Vector3(0.0, y_walk, 0.0)
		builder.top_quad(RoadMeshBuilder.Layer.ASPHALT, c0 - r0 * hw + up_road, c0 + r0 * hw + up_road,
				c1 + r1 * hw + up_road, c1 - r1 * hw + up_road)
		for s: float in [-1.0, 1.0]:
			var in0 := c0 + r0 * hw * s
			var in1 := c1 + r1 * hw * s
			var out0 := c0 + r0 * ow * s
			var out1 := c1 + r1 * ow * s
			builder.top_quad(RoadMeshBuilder.Layer.CONCRETE, in0 + up_walk, out0 + up_walk, out1 + up_walk,
					in1 + up_walk)
			var toward_center := Vector2(-r0.x, -r0.z) * s
			builder.wall(RoadMeshBuilder.Layer.CONCRETE, _xz(in0), _xz(in1), y_road, y_walk, toward_center, u)
			builder.wall(RoadMeshBuilder.Layer.CONCRETE, _xz(out0), _xz(out1), -0.05, y_walk, -toward_center, u)
		u += c0.distance_to(c1)
	_add_markings(builder, network, sections)
	mesh_node.mesh = builder.commit(network.get_materials())


## Sections [centre, tangente] du tronçon conservé (repère du nœud). Aux extrémités
## raccourcies, la tangente est la direction depuis l'extrémité de la courbe, pour
## coïncider exactement avec le bras du carrefour.
func _sections(step: float) -> Array:
	var total := length()
	var o0 := start_trim
	var o1 := total - end_trim
	var n := maxi(1, ceili((o1 - o0) / maxf(step, 0.1)))
	var out: Array = []
	for i in n + 1:
		var o := lerpf(o0, o1, float(i) / n)
		var c := point_at(o)
		var t := (point_at(o + 0.25) - point_at(o - 0.25)).normalized()
		if i == 0 and start_trim > 0.0:
			t = (c - point_at(0.0)).normalized()
		elif i == n and end_trim > 0.0:
			t = (point_at(total) - c).normalized()
		out.append([c, t])
	return out


func _add_markings(builder: RoadMeshBuilder, network: RoadNetwork, sections: Array) -> void:
	var y := network.road_height + network.paint_height
	var o0 := start_trim
	var o1 := length() - end_trim
	var hw := network.lane_half_width
	var first := o0 + 1.0
	var last := o1 - 1.0
	if crosswalk_start:
		_crosswalk(builder, o0 + 2.0, y, hw)
		first = o0 + 4.5
	if crosswalk_end:
		_crosswalk(builder, o1 - 2.0, y, hw)
		last = o1 - 4.5
	if not center_line:
		return
	var half := network.dash_width * 0.5
	var o := first
	while o + network.dash_length <= last:
		var a := o
		for k in 3:
			var b := a + network.dash_length / 3.0
			var pa := point_at(a)
			var pb := point_at(b)
			var ra := _lateral(_tangent(a)) * half
			var rb := _lateral(_tangent(b)) * half
			var lift := Vector3(0.0, y, 0.0)
			builder.paint_quad(pa - ra + lift, pa + ra + lift, pb + rb + lift, pb - rb + lift,
					RoadMeshBuilder.PAINT_YELLOW)
			a = b
		o += network.dash_period


## Passage piéton (bandes de 0,5 m dans le sens de la route, comme la tuile du kit).
func _crosswalk(builder: RoadMeshBuilder, center: float, y: float, hw: float) -> void:
	var c := point_at(center)
	var t := _tangent(center)
	var r := _lateral(t)
	var lift := Vector3(0.0, y, 0.0)
	for i in 7:
		var s0 := -hw + 0.3 + i * 0.85
		var s1 := s0 + 0.5
		builder.paint_quad(c - t * 1.4 + r * s0 + lift, c - t * 1.4 + r * s1 + lift,
				c + t * 1.4 + r * s1 + lift, c + t * 1.4 + r * s0 + lift, RoadMeshBuilder.PAINT_WHITE)


func _tangent(offset: float) -> Vector3:
	return (point_at(offset + 0.25) - point_at(offset - 0.25)).normalized()


## Vecteur latéral (perpendiculaire horizontale) d'une tangente.
static func _lateral(tangent: Vector3) -> Vector3:
	return tangent.cross(Vector3.UP).normalized()


static func _xz(p: Vector3) -> Vector2:
	return Vector2(p.x, p.z)
