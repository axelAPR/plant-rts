class_name RoadMeshBuilder
extends RefCounted
## Accumule les triangles d'une route ou d'un carrefour, par matériau (chaussée,
## béton, peinture), puis produit un ArrayMesh. Dessus plaqués en coordonnées monde
## (une répétition tous les `texture_meters`, comme les tuiles du kit) ; bordures
## plaquées le long de leur tracé ; peinture sur une bande de l'atlas Env_Paint.

enum Layer { ASPHALT, CONCRETE, PAINT }

## Bandes de l'atlas Env_Paint (8 couleurs côte à côte, voir env_lib.TEXTURES).
const PAINT_YELLOW := 2
const PAINT_WHITE := 6

var _texture_meters: float
var _origin: Vector3
var _tools: Array[SurfaceTool] = []
var _used: Array[bool] = [false, false, false]


## `origin` : position monde du nœud qui portera le maillage (pour les UV monde).
func _init(texture_meters: float, origin: Vector3) -> void:
	_texture_meters = texture_meters
	_origin = origin
	for i in 3:
		var tool := SurfaceTool.new()
		tool.begin(Mesh.PRIMITIVE_TRIANGLES)
		_tools.append(tool)


## Triangle orienté selon `normal` (face avant de Godot : sens horaire vu de face).
func triangle(layer: Layer, points: Array[Vector3], normal: Vector3, uvs: Array[Vector2]) -> void:
	var order: Array[int] = [0, 1, 2]
	if (points[1] - points[0]).cross(points[2] - points[0]).dot(normal) > 0.0:
		order = [0, 2, 1]
	var tool := _tools[layer]
	for i in order:
		tool.set_normal(normal)
		tool.set_uv(uvs[i])
		tool.add_vertex(points[i])
	_used[layer] = true


func top_uv(p: Vector3) -> Vector2:
	var w := p + _origin
	return Vector2(w.x, w.z) / _texture_meters


## Quadrilatère horizontal a-b-c-d (dans l'ordre du contour).
func top_quad(layer: Layer, a: Vector3, b: Vector3, c: Vector3, d: Vector3) -> void:
	triangle(layer, [a, b, c], Vector3.UP, [top_uv(a), top_uv(b), top_uv(c)])
	triangle(layer, [a, c, d], Vector3.UP, [top_uv(a), top_uv(c), top_uv(d)])


## Polygone horizontal simple (contour dans le plan XZ) à la hauteur `y`.
func top_polygon(layer: Layer, outline: PackedVector2Array, y: float) -> void:
	var indices := Geometry2D.triangulate_polygon(outline)
	for i in range(0, indices.size(), 3):
		var pts: Array[Vector3] = []
		var uvs: Array[Vector2] = []
		for k in 3:
			var q := outline[indices[i + k]]
			var p := Vector3(q.x, y, q.y)
			pts.append(p)
			uvs.append(top_uv(p))
		triangle(layer, pts, Vector3.UP, uvs)


## Paroi verticale de p0 à p1 (plan XZ), de y0 à y1, tournée vers `facing`
## (vecteur horizontal). `u0` : abscisse de plaquage au début de la paroi (m).
func wall(layer: Layer, p0: Vector2, p1: Vector2, y0: float, y1: float, facing: Vector2, u0: float) -> void:
	var seg := p1 - p0
	if seg.length() < 0.001:
		return
	var n := Vector2(-seg.y, seg.x).normalized()
	if n.dot(facing) < 0.0:
		n = -n
	var normal := Vector3(n.x, 0.0, n.y)
	var a := Vector3(p0.x, y0, p0.y)
	var b := Vector3(p1.x, y0, p1.y)
	var c := Vector3(p1.x, y1, p1.y)
	var d := Vector3(p0.x, y1, p0.y)
	var m := _texture_meters
	var u1 := u0 + seg.length()
	var uva := Vector2(u0 / m, y0 / m)
	var uvb := Vector2(u1 / m, y0 / m)
	var uvc := Vector2(u1 / m, y1 / m)
	var uvd := Vector2(u0 / m, y1 / m)
	triangle(layer, [a, b, c], normal, [uva, uvb, uvc])
	triangle(layer, [a, c, d], normal, [uva, uvc, uvd])


## Marquage peint (quadrilatère horizontal) dans la bande `band` de l'atlas.
func paint_quad(a: Vector3, b: Vector3, c: Vector3, d: Vector3, band: int) -> void:
	var u0 := (band + 0.2) / 8.0
	var u1 := (band + 0.8) / 8.0
	triangle(Layer.PAINT, [a, b, c], Vector3.UP, [Vector2(u0, 0.2), Vector2(u1, 0.2), Vector2(u1, 0.8)])
	triangle(Layer.PAINT, [a, c, d], Vector3.UP, [Vector2(u0, 0.2), Vector2(u1, 0.8), Vector2(u0, 0.8)])


## Maillage final : une surface par matériau utilisé.
func commit(materials: Array[Material]) -> ArrayMesh:
	var mesh := ArrayMesh.new()
	for layer in 3:
		if not _used[layer]:
			continue
		_tools[layer].commit(mesh)
		mesh.surface_set_material(mesh.get_surface_count() - 1, materials[layer])
	return mesh
