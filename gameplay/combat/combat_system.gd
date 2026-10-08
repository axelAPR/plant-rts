class_name CombatSystem
extends Node
## Combat au tick physique, après la simulation des déplacements : ciblage, cadence,
## tirs, projectiles, impacts et dégâts. Sans nœud par unité ni par projectile : l'état
## est lu par ProjectileRenderer et l'interface.
##
## Chaîne d'un tir (par membre, chacun avec ses HP, sa cible, sa cadence et ses jets) :
##   cible valide (vivante, ennemie, à portée) → cadence écoulée → tir :
##   - à distance : un Projectile est créé et vole en ligne droite vers le point visé
##     (anticipation du déplacement de la cible). À chaque tick, son trajet est testé
##     contre le corps des ennemis ; au contact : cible encore valide → jet de
##     précision → dégâts si réussi → projectile détruit. Un projectile ne touche jamais
##     son camp. Cible morte avant l'impact → projectile détruit, aucun dégât ;
##   - en mêlée (UnitData.projectile null) : pas de projectile ; jet de précision au
##     coup, puis dégâts si réussi.
## Les dégâts passent par un DamageContext (resolve_damage) : point d'entrée des règles
## à venir (armure, couvert…). Un membre à 0 HP meurt : il est retiré de la simulation
## à la fin du tick (UnitSimulation.remove_unit).
##
## Les membres tirent sur l'ennemi le plus proche à portée, même en marche ; un ordre
## d'attaque (AttackOrder) leur fait préférer les membres de l'escouade visée.

## Tir : un projectile vient d'être créé.
signal projectile_fired(projectile: Projectile)
## Fin d'un projectile : `hit_unit` = unité atteinte (null si la cible est morte avant
## l'impact ou si rien n'a été touché) ; `hit` = jet de précision réussi.
signal projectile_resolved(projectile: Projectile, hit_unit: Unit, hit: bool)
## Coup de mêlée porté ; `hit` = jet de précision réussi.
signal melee_resolved(attacker: Unit, target: Unit, hit: bool)
signal damage_applied(context: DamageContext)
signal unit_killed(unit: Unit, context: DamageContext)

@export var simulation: UnitSimulation
## Graine des jets de précision ; 0 = aléatoire à chaque partie.
@export var rng_seed: int = 0

@export_group("Ciblage")
## Délai (s) entre deux recherches de cible d'un membre qui n'en a pas.
@export var retarget_interval: float = 0.25
## Délai de réaction (s) maximal avant le premier tir sur une nouvelle cible, tiré au
## hasard par membre : les salves d'une escouade ne partent pas toutes au même instant.
@export var first_shot_delay_max: float = 0.3
## Viser là où sera la cible à l'arrivée du projectile (trajectoire toujours droite).
@export var lead_targets: bool = true

var projectiles: Array[Projectile] = []
var rng := RandomNumberGenerator.new()

var _grid := SpatialHashGrid.new(2.0)
var _max_unit_radius: float = 0.0
var _next_projectile_id: int = 0
var _pending_deaths: Array[Unit] = []


func _init() -> void:
	# Après UnitSimulation (priorité 0) : on tire depuis les positions du tick.
	process_physics_priority = 10


func _ready() -> void:
	if rng_seed != 0:
		rng.seed = rng_seed
	else:
		rng.randomize()


func _physics_process(delta: float) -> void:
	step(delta)


## Avance le combat d'un tick. Appelé au tick physique ; les tests peuvent l'appeler
## directement, après UnitSimulation.step().
func step(delta: float) -> void:
	_rebuild_grid()
	for unit in simulation.units:
		_update_attacker(unit, delta)
	_update_projectiles(delta)
	_flush_deaths()


## Cible valide pour `attacker` : vivante, ennemie, et à portée.
func is_valid_target(attacker: Unit, target: Unit) -> bool:
	return target != null and target.alive and target.team != attacker.team and is_in_range(attacker, target)


## Portée mesurée au sol, du centre de l'attaquant au bord du corps de la cible.
func is_in_range(attacker: Unit, target: Unit) -> bool:
	return _flat_distance(attacker.position, target.position) - target.data.radius <= attacker.data.attack_range


## Jet de précision d'un tir : réussi avec la probabilité `accuracy` (bornée à 0..1).
func roll_accuracy(accuracy: float) -> bool:
	accuracy = clampf(accuracy, 0.0, 1.0)
	if accuracy >= 1.0:
		return true
	if accuracy <= 0.0:
		return false
	return rng.randf() < accuracy


## Tire immédiatement sur `target` (sans vérifier la cadence) : crée le projectile, ou
## porte le coup de mêlée. Renvoie le projectile (null en mêlée).
func fire(attacker: Unit, target: Unit) -> Projectile:
	attacker.attack_cooldown_left = attacker.data.attack_cooldown
	if attacker.data.is_melee():
		var hit := roll_accuracy(attacker.data.accuracy)
		melee_resolved.emit(attacker, target, hit)
		if hit:
			apply_damage(DamageContext.new(attacker, attacker.team, target, attacker.data.damage_per_shot))
		return null
	var origin := attacker.position + Vector3.UP * attacker.data.muzzle_height
	var projectile := Projectile.new(_next_projectile_id, attacker.data.projectile, attacker, target, origin,
			_aim_point(origin, target, attacker.data.projectile_speed))
	_next_projectile_id += 1
	projectiles.append(projectile)
	projectile_fired.emit(projectile)
	return projectile


## Règles de dégâts. Première version : dégâts de base. Les modificateurs à venir
## (armure, couvert, distance, buffs…) s'appliquent ici, sur `context.final_damage`.
func resolve_damage(context: DamageContext) -> void:
	context.final_damage = maxf(context.base_damage, 0.0)


## Applique un coup réussi : une cible déjà morte ne reçoit plus rien.
func apply_damage(context: DamageContext) -> void:
	var target := context.target
	if target == null or not target.alive:
		return
	resolve_damage(context)
	target.health = maxf(target.health - context.final_damage, 0.0)
	damage_applied.emit(context)
	if target.health <= 0.0:
		target.alive = false
		_pending_deaths.append(target)
		unit_killed.emit(target, context)


func _update_attacker(unit: Unit, delta: float) -> void:
	if not unit.data.can_attack():
		unit.aiming = false
		return
	unit.attack_cooldown_left = maxf(unit.attack_cooldown_left - delta, 0.0)
	unit.retarget_time_left = maxf(unit.retarget_time_left - delta, 0.0)
	var target := _current_target(unit)
	unit.aiming = target != null
	if target == null:
		return
	var to_target := target.position - unit.position
	unit.aim_yaw = atan2(to_target.x, to_target.z)
	if unit.attack_cooldown_left <= 0.0:
		fire(unit, target)


## Cible courante du membre : la garde tant qu'elle est valide (sauf si un ordre
## d'attaque désigne une autre escouade dont un membre est à portée), sinon en
## cherche une nouvelle au plus tous les `retarget_interval`.
func _current_target(unit: Unit) -> Unit:
	var current := simulation.get_unit(unit.target_id) if unit.target_id >= 0 else null
	var preferred := _ordered_target_squad(unit)
	if is_valid_target(unit, current) and (preferred == null or current.squad_id == preferred.id):
		return current
	if unit.retarget_time_left > 0.0 and is_valid_target(unit, current):
		return current
	if unit.retarget_time_left > 0.0:
		unit.target_id = -1
		return null
	unit.retarget_time_left = retarget_interval
	var found := find_target(unit)
	if found == null:
		unit.target_id = -1
		return null
	if current == null or not current.alive:
		# Nouvelle cible après une période sans : délai de réaction.
		unit.attack_cooldown_left = maxf(unit.attack_cooldown_left, rng.randf() * first_shot_delay_max)
	unit.target_id = found.id
	return found


## Meilleure cible à portée : un membre de l'escouade visée par un ordre d'attaque s'il
## y en a un, sinon l'ennemi le plus proche ; null si aucun ennemi n'est à portée.
func find_target(unit: Unit) -> Unit:
	var preferred := _ordered_target_squad(unit)
	if preferred != null:
		var best := _nearest_in_squad(unit, preferred)
		if best != null:
			return best
	var nearest: Unit = null
	var nearest_distance := INF
	for squad in simulation.squads:
		if squad.team == unit.team:
			continue
		# Rejet rapide : escouade entière hors de portée.
		var reach := squad.get_footprint_half_extents().length() + unit.data.attack_range
		if _flat_distance(squad.get_center(), unit.position) > reach:
			continue
		var candidate := _nearest_in_squad(unit, squad)
		if candidate != null:
			var distance := _flat_distance(candidate.position, unit.position)
			if distance < nearest_distance:
				nearest = candidate
				nearest_distance = distance
	return nearest


func _nearest_in_squad(unit: Unit, squad: Squad) -> Unit:
	var best: Unit = null
	var best_distance := INF
	for other in squad.units:
		if not is_valid_target(unit, other):
			continue
		var distance := _flat_distance(other.position, unit.position)
		if distance < best_distance:
			best = other
			best_distance = distance
	return best


## Escouade désignée par l'ordre d'attaque en cours de l'escouade du membre, ou null.
func _ordered_target_squad(unit: Unit) -> Squad:
	var squad := simulation.get_squad(unit.squad_id)
	if squad == null:
		return null
	var attack := squad.order as AttackOrder
	if attack == null:
		return null
	return simulation.get_squad(attack.target_squad_id)


## Point visé : centre du corps de la cible, là où elle sera quand le projectile
## l'atteindra si elle garde sa vitesse (`lead_targets`).
func _aim_point(origin: Vector3, target: Unit, speed: float) -> Vector3:
	var center := target.position + Vector3.UP * target.data.hit_height * 0.5
	if not lead_targets or speed <= 0.0:
		return center
	var to_target := center - origin
	var velocity := target.velocity
	# |to_target + velocity·t| = speed·t → a·t² + b·t + c = 0.
	var a := velocity.length_squared() - speed * speed
	var b := 2.0 * to_target.dot(velocity)
	var c := to_target.length_squared()
	var time := -1.0
	if absf(a) < 0.000001:
		time = -c / b if absf(b) > 0.000001 else -1.0
	else:
		var discriminant := b * b - 4.0 * a * c
		if discriminant >= 0.0:
			var root := sqrt(discriminant)
			var t1 := (-b - root) / (2.0 * a)
			var t2 := (-b + root) / (2.0 * a)
			time = minf(t1, t2) if minf(t1, t2) > 0.0 else maxf(t1, t2)
	return center + velocity * time if time > 0.0 else center


func _update_projectiles(delta: float) -> void:
	for projectile in projectiles:
		if projectile.target == null or not projectile.target.alive:
			# Cible morte avant l'impact : le projectile disparaît, sans dégâts.
			_resolve(projectile, null, false)
			continue
		projectile.advance(delta)
		var hit_unit := _sweep(projectile)
		if hit_unit != null:
			var hit := roll_accuracy(projectile.accuracy)
			if hit:
				var context := DamageContext.new(projectile.source_unit, projectile.faction, hit_unit,
						projectile.damage, projectile)
				context.hit_position = projectile.position
				apply_damage(context)
			_resolve(projectile, hit_unit, hit)
		elif projectile.range_left <= 0.0:
			_resolve(projectile, null, false)
	var flying: Array[Projectile] = []
	for projectile in projectiles:
		if not projectile.destroyed:
			flying.append(projectile)
	projectiles = flying


func _resolve(projectile: Projectile, hit_unit: Unit, hit: bool) -> void:
	projectile.destroyed = true
	projectile_resolved.emit(projectile, hit_unit, hit)


## Première unité ennemie vivante traversée par le trajet du projectile pendant ce
## tick (corps = cylindre de rayon `radius` et de hauteur `hit_height`), ou null.
func _sweep(projectile: Projectile) -> Unit:
	var from := projectile.previous_position
	var to := projectile.position
	var segment := to - from
	var flat_segment := Vector2(segment.x, segment.z)
	var flat_length_squared := flat_segment.length_squared()
	var reach := segment.length() * 0.5 + _max_unit_radius + projectile.data.radius
	var best: Unit = null
	var best_t := INF
	for index in _grid.query((from + to) * 0.5, reach):
		var unit := simulation.units[index]
		if not unit.alive or unit.team == projectile.faction:
			continue
		var to_unit := Vector2(unit.position.x - from.x, unit.position.z - from.z)
		var t := 0.0
		if flat_length_squared > 0.000001:
			t = clampf(to_unit.dot(flat_segment) / flat_length_squared, 0.0, 1.0)
		var contact := unit.data.radius + projectile.data.radius
		if (to_unit - flat_segment * t).length_squared() > contact * contact:
			continue
		var height := from.y + segment.y * t - unit.position.y
		if height < -projectile.data.radius or height > unit.data.hit_height + projectile.data.radius:
			continue
		if t < best_t:
			best = unit
			best_t = t
	return best


func _rebuild_grid() -> void:
	_grid.clear()
	for i in simulation.units.size():
		var unit := simulation.units[i]
		_grid.insert(i, unit.position)
		_max_unit_radius = maxf(_max_unit_radius, unit.data.radius)


func _flush_deaths() -> void:
	for unit in _pending_deaths:
		simulation.remove_unit(unit)
	_pending_deaths.clear()


static func _flat_distance(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length()
