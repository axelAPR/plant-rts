class_name Projectile
extends RefCounted
## Projectile en vol : entité indépendante de son tireur, simulée par CombatSystem au
## tick physique et affichée par ProjectileRenderer (lecture seule).
##
## Il avance en ligne droite à vitesse constante ; à chaque tick, son trajet (segment
## entre deux positions) est testé contre le corps des unités ennemies. Les dégâts ne
## sont jamais appliqués au tir : seulement à l'impact, après le jet de précision.

var id: int
var data: ProjectileData
## Tireur. Peut mourir pendant le vol : le projectile continue.
var source_unit: Unit
## Camp du tireur : le projectile ne touche jamais ce camp.
var faction: int
## Cible visée ; si elle meurt avant l'impact, le projectile disparaît sans dégâts.
var target: Unit
## Dégâts d'un tir réussi.
var damage: float
## Précision du tireur au moment du tir (0 à 1), tirée à l'impact.
var accuracy: float
## Vitesse (m/s).
var speed: float
var position: Vector3
var previous_position: Vector3
## Direction de vol (normalisée).
var direction: Vector3
## Distance (m) restant à parcourir avant de disparaître (rien touché).
var range_left: float
## Détruit : retiré à la fin du tick.
var destroyed: bool = false


func _init(p_id: int, p_data: ProjectileData, p_source: Unit, p_target: Unit, p_origin: Vector3,
		p_aim_point: Vector3) -> void:
	id = p_id
	data = p_data
	source_unit = p_source
	faction = p_source.team
	target = p_target
	damage = p_source.data.damage_per_shot
	accuracy = clampf(p_source.data.accuracy, 0.0, 1.0)
	speed = p_source.data.projectile_speed
	position = p_origin
	previous_position = p_origin
	var to_aim := p_aim_point - p_origin
	direction = to_aim.normalized() if to_aim.length_squared() > 0.000001 else Vector3.MODEL_FRONT
	range_left = maxf(p_source.data.attack_range, to_aim.length()) * p_data.max_range_factor


## Avance d'un tick (trajectoire DIRECT). Renvoie le déplacement effectué.
func advance(delta: float) -> float:
	previous_position = position
	var step := minf(speed * delta, range_left)
	position += direction * step
	range_left -= step
	return step
