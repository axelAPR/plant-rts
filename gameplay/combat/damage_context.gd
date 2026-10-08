class_name DamageContext
extends RefCounted
## Un coup qui touche : qui frappe qui, avec quoi, et combien. Passe par
## CombatSystem.resolve_damage() avant d'être appliqué.
##
## Aujourd'hui : dégâts finaux = dégâts de base. Les règles à venir (armure,
## pénétration, couvert, distance, vétéran, buffs, résistances…) modifient
## `final_damage` dans resolve_damage() et ajoutent ici leurs propres champs, sans
## changer le tir, le projectile ni l'application.

## Source : unité attaquante (peut être retirée entre le tir et l'impact).
var source: Unit
var source_team: int
var target: Unit
## Projectile porteur ; null pour une attaque de mêlée.
var projectile: Projectile
## Dégâts d'un tir réussi (UnitData.damage_per_shot du tireur).
var base_damage: float
## Dégâts effectivement appliqués, après les règles de resolve_damage().
var final_damage: float
## Point d'impact (monde).
var hit_position: Vector3


func _init(p_source: Unit, p_source_team: int, p_target: Unit, p_base_damage: float,
		p_projectile: Projectile = null) -> void:
	source = p_source
	source_team = p_source_team
	target = p_target
	base_damage = p_base_damage
	final_damage = p_base_damage
	projectile = p_projectile
	hit_position = p_target.position
