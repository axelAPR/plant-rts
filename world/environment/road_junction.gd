@tool
class_name RoadJunction
extends Node3D
## Carrefour (plusieurs bras) ou raquette de retournement (un seul bras) d'un
## RoadNetwork. Les bras sont déduits des routes qui s'y terminent : chaque bras
## commence exactement sur la section de fin de sa route. Entre deux bras voisins,
## la bordure est arrondie (arc de RoadNetwork.corner_radius, réduit si le bras est
## trop court) et le trottoir suit l'arrondi ; côté fermé d'un T : bordure droite.

const MESH_NAME := "Mesh"

## Distance du centre à la section de raccord des routes (m). Les routes doivent
## être droites sur cette longueur.
@export var arm_length: float = 9.0
## Rayon de chaussée de la raquette (un seul bras), en m.
@export var turnaround_radius: float = 7.0

## Bords (gauche, droite) de chaque bras en coordonnées monde, après build (tests).
var arm_edges: Array = []


## `arms` : sections de fin des routes (RoadPath.end_edges) : centre et direction
## allant du carrefour vers la route, en coordonnées monde.
func build(network: RoadNetwork, arms: Array) -> void:
	var mesh_node := get_node_or_null(MESH_NAME) as MeshInstance3D
	if mesh_node == null:
		mesh_node = MeshInstance3D.new()
		mesh_node.name = MESH_NAME
		add_child(mesh_node)
	arm_edges.clear()
	if arms.is_empty():
		mesh_node.mesh = null
		return
	var inverse := global_transform.affine_inverse()
	var local: Array = []
	for arm in arms:
		var c: Vector3 = inverse * (arm["center"] as Vector3)
		var d: Vector3 = inverse.basis * (arm["direction"] as Vector3)
		local.append([Vector2(c.x, c.z), Vector2(d.x, d.z).normalized()])
	local.sort_custom(func(a: Array, b: Array) -> bool: return (a[0] as Vector2).angle() < (b[0] as Vector2).angle())
	var hw := network.lane_half_width
	for arm in local:
		var a: Vector2 = arm[0]
		var n := _normal(arm[1])
		arm_edges.append([_world(a + n * hw), _world(a - n * hw)])
	var builder := RoadMeshBuilder.new(network.texture_meters, global_position)
	if local.size() == 1:
		_build_turnaround(builder, network, local[0])
	else:
		_build_crossing(builder, network, local)
	mesh_node.mesh = builder.commit(network.get_materials())


func _build_crossing(builder: RoadMeshBuilder, network: RoadNetwork, arms: Array) -> void:
	var hw := network.lane_half_width
	var asphalt := PackedVector2Array()
	for i in arms.size():
		var arm_i: Array = arms[i]
		var arm_j: Array = arms[(i + 1) % arms.size()]
		var corner := _corner(network, arm_i, arm_j)
		asphalt.append(arm_i[0] - _normal(arm_i[1]) * hw)
		var inner: PackedVector2Array = corner[0]
		for k in inner.size() - 1:
			asphalt.append(inner[k])
		_sidewalk(builder, network, corner[0], corner[1])
	builder.top_polygon(RoadMeshBuilder.Layer.ASPHALT, asphalt, network.road_height)


## Bordure entre le bras i et le bras suivant (sens trigonométrique du plan XZ) :
## [bord de chaussée, bord extérieur du trottoir], du bras i au bras j.
func _corner(network: RoadNetwork, arm_i: Array, arm_j: Array) -> Array:
	var hw := network.lane_half_width
	var sw := network.sidewalk_width
	var ow := hw + sw
	var a_i: Vector2 = arm_i[0]
	var d_i: Vector2 = arm_i[1]
	var a_j: Vector2 = arm_j[0]
	var d_j: Vector2 = arm_j[1]
	var n_i := _normal(d_i)
	var n_j := _normal(d_j)
	var gap := fposmod(d_j.angle() - d_i.angle(), TAU)
	if gap >= PI - 0.15:
		if gap > PI + 0.15:
			push_warning("RoadJunction %s : angle de %d° entre deux bras" % [name, roundi(rad_to_deg(gap))])
		return [PackedVector2Array([a_i + n_i * hw, a_j - n_j * hw]),
				PackedVector2Array([a_i + n_i * ow, a_j - n_j * ow])]
	var corner_hit: Variant = Geometry2D.line_intersects_line(a_i + n_i * hw, d_i, a_j - n_j * hw, d_j)
	var q: Vector2 = corner_hit
	var half := gap * 0.5
	var radius := network.corner_radius
	var reach := minf(arm_length - 0.3 - q.dot(d_i), arm_length - 0.3 - q.dot(d_j))
	radius = clampf(minf(radius, reach * tan(half)), sw + 0.2, network.corner_radius)
	var center := q + (d_i + d_j).normalized() * (radius / sin(half))
	var t_i := q + d_i * (radius / tan(half))
	var t_j := q + d_j * (radius / tan(half))
	var a0 := (t_i - center).angle()
	var sweep := wrapf((t_j - center).angle() - a0, -PI, PI)
	var steps := maxi(2, ceili(absf(sweep) * radius / 0.6))
	var inner := PackedVector2Array([a_i + n_i * hw])
	var outer := PackedVector2Array([a_i + n_i * ow])
	for k in steps + 1:
		var dir := Vector2.from_angle(a0 + sweep * k / steps)
		inner.append(center + dir * radius)
		outer.append(center + dir * (radius - sw))
	inner.append(a_j - n_j * hw)
	outer.append(a_j - n_j * ow)
	return [inner, outer]


## Raquette : chaussée en disque raccordé au bras, trottoir tout autour.
func _build_turnaround(builder: RoadMeshBuilder, network: RoadNetwork, arm: Array) -> void:
	var hw := network.lane_half_width
	var sw := network.sidewalk_width
	var ow := hw + sw
	var a: Vector2 = arm[0]
	var d: Vector2 = arm[1]
	var n := _normal(d)
	var r_in := turnaround_radius
	var r_out := turnaround_radius + sw
	var s_in := sqrt(r_in * r_in - hw * hw)
	var s_out := sqrt(r_out * r_out - ow * ow)
	var inner := PackedVector2Array([a + n * hw])
	var outer := PackedVector2Array([a + n * ow])
	var steps := ceili(TAU * r_out / 0.6)
	inner.append_array(_far_arc(d * s_in + n * hw, d * s_in - n * hw, r_in, steps))
	outer.append_array(_far_arc(d * s_out + n * ow, d * s_out - n * ow, r_out, steps))
	inner.append(a - n * hw)
	outer.append(a - n * ow)
	builder.top_polygon(RoadMeshBuilder.Layer.ASPHALT, inner, network.road_height)
	_sidewalk(builder, network, inner, outer)


## Arc de cercle (centre à l'origine) de `from` à `to` par le grand côté, en
## `steps` segments (même nombre pour les deux bords d'un trottoir).
static func _far_arc(from: Vector2, to: Vector2, radius: float, steps: int) -> PackedVector2Array:
	var a0 := from.angle()
	var sweep := wrapf(to.angle() - a0, -PI, PI)
	sweep -= TAU * signf(sweep)
	var out := PackedVector2Array()
	for k in steps + 1:
		out.append(Vector2.from_angle(a0 + sweep * k / steps) * radius)
	return out


## Trottoir entre deux bordures de même nombre de points : dessus, bordure côté
## chaussée (tournée vers le centre du carrefour) et paroi extérieure.
func _sidewalk(builder: RoadMeshBuilder, network: RoadNetwork, inner: PackedVector2Array,
		outer: PackedVector2Array) -> void:
	var y_road := network.road_height
	var y_walk := network.sidewalk_height
	var u_in := 0.0
	var u_out := 0.0
	for k in inner.size() - 1:
		var i0 := inner[k]
		var i1 := inner[k + 1]
		var o0 := outer[k]
		var o1 := outer[k + 1]
		builder.top_quad(RoadMeshBuilder.Layer.CONCRETE, Vector3(i0.x, y_walk, i0.y), Vector3(o0.x, y_walk, o0.y),
				Vector3(o1.x, y_walk, o1.y), Vector3(i1.x, y_walk, i1.y))
		var toward_center := -(i0 + i1) * 0.5
		builder.wall(RoadMeshBuilder.Layer.CONCRETE, i0, i1, y_road, y_walk, toward_center, u_in)
		builder.wall(RoadMeshBuilder.Layer.CONCRETE, o0, o1, -0.05, y_walk, (o0 + o1) * 0.5, u_out)
		u_in += i0.distance_to(i1)
		u_out += o0.distance_to(o1)


## Normale gauche d'une direction (sens trigonométrique du plan XZ), comme le côté
## « + » des routes (tangente × haut).
static func _normal(d: Vector2) -> Vector2:
	return Vector2(-d.y, d.x)


func _world(p: Vector2) -> Vector3:
	return global_transform * Vector3(p.x, 0.0, p.y)
