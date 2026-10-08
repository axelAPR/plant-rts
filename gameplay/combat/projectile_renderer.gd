class_name ProjectileRenderer
extends MultiMeshInstance3D
## Affichage des projectiles en vol : une forme simple par projectile (sphère étirée
## dans le sens du vol), à la couleur et à la taille de son type (ProjectileData),
## interpolée entre deux ticks physiques. Un seul appel de rendu pour tous les
## projectiles. Lit CombatSystem sans jamais le modifier.
##
## Un type pourra plus tard fournir sa propre scène (ProjectileData.visual_scene :
## modèle, particules…) ; ce rendu reste celui par défaut.

@export var combat: CombatSystem
## Nombre de projectiles affichables avant agrandissement du tampon.
@export var initial_capacity: int = 256


func _ready() -> void:
	var mesh := SphereMesh.new()
	mesh.radius = 0.5
	mesh.height = 1.0
	mesh.radial_segments = 8
	mesh.rings = 4
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.vertex_color_use_as_albedo = true
	mesh.material = material
	multimesh = MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.use_colors = true
	multimesh.mesh = mesh
	multimesh.instance_count = initial_capacity
	multimesh.visible_instance_count = 0
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func _process(_delta: float) -> void:
	var projectiles := combat.projectiles
	if projectiles.size() > multimesh.instance_count:
		multimesh.instance_count = projectiles.size() * 2
	var alpha := Engine.get_physics_interpolation_fraction()
	for i in projectiles.size():
		var projectile := projectiles[i]
		var data := projectile.data
		var at := projectile.previous_position.lerp(projectile.position, alpha)
		var size := Vector3(data.visual_diameter, data.visual_diameter, data.visual_length)
		var basis := Basis.looking_at(projectile.direction, _up_for(projectile.direction)) * Basis.from_scale(size)
		multimesh.set_instance_transform(i, Transform3D(basis, at))
		multimesh.set_instance_color(i, data.color)
	multimesh.visible_instance_count = projectiles.size()


## Vecteur « haut » non colinéaire à la direction (tir vertical).
static func _up_for(direction: Vector3) -> Vector3:
	return Vector3.RIGHT if absf(direction.dot(Vector3.UP)) > 0.99 else Vector3.UP
