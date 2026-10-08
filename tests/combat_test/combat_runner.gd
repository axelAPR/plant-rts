extends SceneTree
## Test automatisé du combat : HP individuels, tirs, projectiles, précision, dégâts,
## portée, cadence, alliés, cibles mortes, unités individuelles, mêlée, ordre
## d'attaque et bataille complète. Simulation pas à pas (physique désactivée).
##
## Lancement : Godot --headless --path . --script res://tests/combat_test/combat_runner.gd
## Option : -- --screenshots=<dossier absolu> pour une capture d'un échange de tirs
## (lancer alors sans --headless).
## Code de sortie : 0 si tout passe, 1 sinon.

const TICK := 1.0 / 60.0

var _failures: Array[String] = []
var _checks: int = 0
var _screenshot_dir: String = ""

var _simulation: UnitSimulation
var _combat: CombatSystem
var _world: Node3D

## Journal des événements du scénario en cours.
var _fired: Array[Projectile] = []
var _fire_times: Dictionary[int, Array] = {}
var _resolved: Array[Array] = []
var _damage: Array[DamageContext] = []
var _melee: Array[Array] = []
var _time: float = 0.0


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--screenshots="):
			_screenshot_dir = arg.trim_prefix("--screenshots=")
	_run.call_deferred()


func _run() -> void:
	_test_squad_members()
	_test_salvos_and_cooldown()
	_test_accuracy_rolls()
	_test_damage_per_hit()
	_test_projectiles_move()
	_test_no_friendly_fire()
	_test_dead_target()
	_test_range()
	_test_individual("citron", 2000.0, 1.8)
	_test_individual("z_mech", 2400.0, 2.0)
	_test_melee()
	_test_attack_order()
	_test_battle()
	if not _screenshot_dir.is_empty():
		await _capture()
	print("\n%d vérifications, %d échec(s)" % [_checks, _failures.size()])
	quit(0 if _failures.is_empty() else 1)


# --- Tests ------------------------------------------------------------------------

## TEST 1 et 2 : 6 membres vivants à 100 HP chacun ; un membre tué → 5 vivants, les
## autres gardent leurs HP (pas de réserve commune).
func _test_squad_members() -> void:
	print("\n[1-2] Escouade de Pisto-pois : HP individuels")
	_reset()
	var squad := _simulation.spawn_squad(_squad("peashooter"), 0, Vector3.ZERO, 0.0)
	_check(squad.units.size() == 6, "6 membres vivants (obtenu %d)" % squad.units.size())
	var all_full := squad.units.all(func(u: Unit) -> bool: return u.alive and u.health == 100.0)
	_check(all_full, "chaque membre a 100 HP")
	var victim := squad.units[2]
	var other := squad.units[3]
	_combat.apply_damage(DamageContext.new(null, 1, victim, 60.0))
	_check(victim.health == 40.0 and other.health == 100.0, "60 dégâts sur un membre : 40 / 100 pour les autres")
	_combat.apply_damage(DamageContext.new(null, 1, victim, 40.0))
	_step(1)
	_check(not victim.alive, "membre à 0 HP : mort")
	_check(squad.units.size() == 5, "5 membres vivants (obtenu %d)" % squad.units.size())
	_check(not _simulation.units.has(victim), "le membre mort est retiré de la simulation")
	var healths: Array = squad.units.map(func(u: Unit) -> float: return u.health)
	_check(healths == [100.0, 100.0, 100.0, 100.0, 100.0], "HP des survivants : %s" % [healths])


## TEST 3 et 11 : 5 membres vivants → au plus 5 projectiles par cycle ; le mort ne tire
## jamais ; deux tirs d'un même membre sont espacés d'au moins la cadence (1,2 s).
func _test_salvos_and_cooldown() -> void:
	print("\n[3, 11] Salves et cadence")
	_reset()
	var squad := _simulation.spawn_squad(_squad("peashooter"), 0, Vector3.ZERO, 0.0)
	_spawn_dummy(Vector3(0.0, 0.0, 15.0))
	var dead := squad.units[0]
	_combat.apply_damage(DamageContext.new(null, 1, dead, 1000.0))
	_step(1)
	_step_seconds(12.0)
	var cooldown := squad.data.unit_data.attack_cooldown
	_check(not _fire_times.has(dead.id), "le membre mort n'a jamais tiré")
	_check(_fire_times.size() == 5, "5 membres ont tiré (obtenu %d)" % _fire_times.size())
	var min_interval := INF
	for times: Array in _fire_times.values():
		for i in range(1, times.size()):
			min_interval = minf(min_interval, times[i] - times[i - 1])
	_check(min_interval >= cooldown - TICK * 0.5, "intervalle minimal entre deux tirs d'un membre : %.3f s (cadence %.1f s)" % [min_interval, cooldown])
	# Toute fenêtre d'une cadence contient au plus un tir par membre vivant.
	var all_times: Array[float] = []
	for times: Array in _fire_times.values():
		for t: float in times:
			all_times.append(t)
	all_times.sort()
	var max_in_window := 0
	for i in all_times.size():
		var count := 0
		for j in range(i, all_times.size()):
			if all_times[j] < all_times[i] + cooldown - TICK * 0.5:
				count += 1
		max_in_window = maxi(max_in_window, count)
	_check(max_in_window <= 5, "au plus 5 projectiles par cycle de %.1f s (maximum observé %d)" % [cooldown, max_in_window])
	var expected := 5 * int(12.0 / cooldown)
	_check(_fired.size() >= expected - 5 and _fired.size() <= expected + 5,
			"%d tirs en 12 s (attendu ≈ %d : 5 membres × 12 s / %.1f s)" % [_fired.size(), expected, cooldown])


## TEST 4 : un jet de précision par projectile (75 %) ; les dégâts suivent les jets.
func _test_accuracy_rolls() -> void:
	print("\n[4] Jet de précision par projectile")
	_reset()
	_simulation.spawn_squad(_squad("peashooter"), 0, Vector3.ZERO, 0.0)
	var dummy := _spawn_dummy(Vector3(0.0, 0.0, 12.0))
	_step_seconds(60.0)
	var hits := 0
	var mixed_volleys := 0
	var volleys: Dictionary[int, Array] = {}
	for entry in _resolved:
		var projectile: Projectile = entry[0]
		if entry[1] != null and entry[2]:
			hits += 1
		volleys.get_or_add(int(projectile.id / 6), []).append(entry[2])
	for outcomes: Array in volleys.values():
		if outcomes.has(true) and outcomes.has(false):
			mixed_volleys += 1
	var ratio := float(hits) / maxf(_resolved.size(), 1.0)
	_check(_resolved.size() == _fired.size() or _resolved.size() >= _fired.size() - 6,
			"chaque projectile est résolu individuellement (%d tirés, %d résolus)" % [_fired.size(), _resolved.size()])
	_check(ratio > 0.65 and ratio < 0.85, "taux de réussite %.1f %% sur %d projectiles (précision 75 %%)" % [ratio * 100.0, _resolved.size()])
	_check(mixed_volleys > 0, "des projectiles d'une même salve ont des résultats différents (%d salves mixtes)" % mixed_volleys)
	var lost := 1.0e6 - dummy.health
	_check(is_equal_approx(lost, hits * 18.0), "dégâts reçus %.0f = %d réussites × 18" % [lost, hits])


## TEST 5 et 6 : 3 projectiles réussis → 54 dégâts ; aucun réussi → 0.
func _test_damage_per_hit() -> void:
	print("\n[5-6] Dégâts = réussites × dégâts par tir")
	for case in [[[1.0, 1.0, 1.0, 0.0], 54.0], [[0.0, 0.0, 0.0, 0.0], 0.0]]:
		_reset()
		var squad := _simulation.spawn_squad(_squad("peashooter"), 0, Vector3.ZERO, 0.0)
		var dummy := _spawn_dummy(Vector3(0.0, 0.0, 12.0))
		var accuracies: Array = case[0]
		for i in accuracies.size():
			var projectile := _combat.fire(squad.units[i], dummy)
			projectile.accuracy = accuracies[i]
		_simulate_projectiles_only(3.0)
		var lost := 1.0e6 - dummy.health
		var hits := accuracies.count(1.0)
		_check(is_equal_approx(lost, case[1]), "%d projectiles réussis sur 4 → %.0f dégâts (attendu %.0f)" % [hits, lost, case[1]])
		_check(_resolved.size() == 4, "4 projectiles résolus (obtenu %d)" % _resolved.size())


## TEST 7 : les projectiles existent dans le monde et s'y déplacent à leur vitesse ;
## le rendu les affiche.
func _test_projectiles_move() -> void:
	print("\n[7] Projectiles visibles et en mouvement")
	_reset()
	var squad := _simulation.spawn_squad(_squad("peashooter"), 0, Vector3.ZERO, 0.0)
	var dummy := _spawn_dummy(Vector3(0.0, 0.0, 20.0))
	var projectile := _combat.fire(squad.units[0], dummy)
	_check(projectile != null and _combat.projectiles.has(projectile), "le tir crée un projectile dans le monde")
	_check(dummy.health == 1.0e6, "aucun dégât au moment du tir")
	var start := projectile.position
	var renderer := ProjectileRenderer.new()
	renderer.combat = _combat
	_world.add_child(renderer)
	renderer._process(0.0)
	_check(renderer.multimesh.visible_instance_count == 1, "le rendu affiche le projectile")
	_simulate_projectiles_only(0.25)
	var travelled := projectile.position.distance_to(start)
	_check(absf(travelled - 30.0 * 0.25) < 0.05, "en 0,25 s : %.2f m parcourus (30 m/s → 7,5 m)" % travelled)
	_check(projectile.position.z > start.z + 7.0, "il avance vers la cible")
	_simulate_projectiles_only(1.0)
	_check(projectile.destroyed and not _combat.projectiles.has(projectile), "détruit après l'impact")
	renderer._process(0.0)
	_check(renderer.multimesh.visible_instance_count == 0, "plus affiché après l'impact")


## TEST 8 : un projectile traverse les alliés (et son tireur) sans les toucher.
func _test_no_friendly_fire() -> void:
	print("\n[8] Pas de tir allié")
	_reset()
	var shooter := _simulation.spawn_squad(_squad("peashooter"), 0, Vector3.ZERO, 0.0).units[0]
	var ally := _simulation.spawn_squad(_dummy_squad(), 0, shooter.position + Vector3(0.0, 0.0, 6.0), 0.0).units[0]
	var enemy := _spawn_dummy(shooter.position + Vector3(0.0, 0.0, 14.0))
	var projectile := _combat.fire(shooter, enemy)
	projectile.accuracy = 1.0
	_simulate_projectiles_only(2.0)
	_check(ally.health == 1.0e6, "l'allié sur la trajectoire n'est pas touché")
	_check(shooter.health == 100.0, "le tireur n'est pas touché")
	_check(_resolved.size() == 1 and _resolved[0][1] == enemy, "le projectile atteint l'ennemi derrière l'allié")
	_check(enemy.health == 1.0e6 - 18.0, "l'ennemi reçoit 18 dégâts")


## TEST 9 : cible morte avant l'impact → projectile détruit, aucun dégât, pas d'erreur ;
## une unité morte ne reçoit plus de dégâts.
func _test_dead_target() -> void:
	print("\n[9] Cible morte")
	_reset()
	var squad := _simulation.spawn_squad(_squad("peashooter"), 0, Vector3.ZERO, 0.0)
	var target := _spawn_dummy(Vector3(0.0, 0.0, 20.0), 50.0)
	var projectile := _combat.fire(squad.units[0], target)
	projectile.accuracy = 1.0
	_simulate_projectiles_only(0.2)
	_combat.apply_damage(DamageContext.new(null, 0, target, 50.0))
	var damage_events := _damage.size()
	_simulate_projectiles_only(2.0)
	_check(not target.alive, "cible tuée pendant le vol")
	_check(projectile.destroyed and _resolved.size() == 1 and _resolved[0][1] == null, "le projectile est détruit sans impact")
	_check(_damage.size() == damage_events, "aucun dégât après la mort")
	_combat.apply_damage(DamageContext.new(null, 0, target, 30.0))
	_check(target.health == 0.0 and _damage.size() == damage_events, "un coup direct sur une unité morte est ignoré")


## TEST 10 : hors de portée, aucun tir ; à portée, tir.
func _test_range() -> void:
	print("\n[10] Portée")
	_reset()
	var squad := _simulation.spawn_squad(_squad("peashooter"), 0, Vector3.ZERO, 0.0)
	var target := _spawn_dummy(Vector3(0.0, 0.0, 32.0))
	var shooter := squad.units[0]
	_check(not _combat.is_in_range(shooter, target), "cible à %.1f m (portée 25 m) : hors de portée" % (target.position.distance_to(shooter.position) - target.data.radius))
	_step_seconds(4.0)
	_check(_fired.is_empty(), "aucun tir hors de portée (obtenu %d)" % _fired.size())
	_teleport(target, Vector3(0.0, 0.0, 22.0))
	_step_seconds(2.0)
	_check(not _fired.is_empty(), "à 22 m : tirs (%d)" % _fired.size())
	var max_distance := 0.0
	for projectile in _fired:
		max_distance = maxf(max_distance, _flat(projectile.source_unit.position, target.position) - target.data.radius)
	_check(max_distance <= 25.0, "aucun tir au-delà de 25 m (max %.1f m)" % max_distance)


## TEST 16 et 17 : unité individuelle (1 membre, un seul pool de HP, un tir par cadence).
func _test_individual(id: String, hp: float, cooldown: float) -> void:
	print("\n[%s] Unité individuelle" % id)
	_reset()
	var data := _squad(id)
	var squad := _simulation.spawn_squad(data, 0 if data.unit_data.faction.id == &"plants" else 1, Vector3.ZERO, 0.0)
	var unit := squad.units[0]
	_check(data.is_individual() and squad.units.size() == 1, "1 membre")
	_check(unit.health == hp, "HP %.0f (attendu %.0f)" % [unit.health, hp])
	_spawn_dummy(Vector3(0.0, 0.0, 15.0), 1.0e6, 1 - squad.team)
	_step_seconds(10.0)
	var expected := int(10.0 / cooldown)
	_check(absi(_fired.size() - expected) <= 1, "%d tirs en 10 s (attendu ≈ %d, cadence %.1f s)" % [_fired.size(), expected, cooldown])
	_check(UnitInfoPanel.describe(squad).contains("Unité individuelle"), "panneau : unité individuelle")
	_combat.apply_damage(DamageContext.new(null, 1 - squad.team, unit, hp - 1.0))
	_check(unit.alive and unit.health == 1.0, "%.0f dégâts : 1 HP restant" % (hp - 1.0))
	var destroyed := [false]
	_simulation.squad_destroyed.connect(func(s: Squad) -> void: destroyed[0] = destroyed[0] or s == squad)
	_combat.apply_damage(DamageContext.new(null, 1 - squad.team, unit, 1.0))
	_step(1)
	_check(not unit.alive and destroyed[0], "mort → escouade détruite")
	_check(_simulation.get_squad(squad.id) == null, "retirée de la simulation")


## Mêlée (Chomper) : pas de projectile ; jets et dégâts au contact seulement.
func _test_melee() -> void:
	print("\n[Mêlée] Chomper")
	_reset()
	var squad := _simulation.spawn_squad(_squad("chomper"), 0, Vector3.ZERO, 0.0)
	var target := _spawn_dummy(Vector3(0.0, 0.0, 12.0))
	_step_seconds(3.0)
	_check(_melee.is_empty(), "cible à 12 m (portée 3 m) : pas d'attaque")
	_teleport(target, squad.units[0].position + Vector3(0.0, 0.0, 2.5))
	_step_seconds(10.0)
	_check(_fired.is_empty(), "aucun projectile")
	_check(not _melee.is_empty(), "coups de mêlée portés (%d)" % _melee.size())
	var hits := _melee.filter(func(entry: Array) -> bool: return entry[2]).size()
	_check(is_equal_approx(1.0e6 - target.health, hits * 70.0), "dégâts = %d coups réussis × 70" % hits)


## Ordre d'attaque : l'escouade s'approche à portée de l'escouade visée et la détruit.
func _test_attack_order() -> void:
	print("\n[Ordre d'attaque]")
	_reset()
	var attackers := _simulation.spawn_squad(_squad("peashooter"), 0, Vector3.ZERO, 0.0)
	var target_squad := _simulation.spawn_squad(_dummy_squad(300.0), 1, Vector3(0.0, 0.0, 60.0), PI)
	_simulation.issue_order(attackers, AttackOrder.new(target_squad.id))
	_step_seconds(4.0)
	_check(_fired.is_empty(), "hors de portée au départ : pas de tir")
	_step_seconds(30.0)
	var distance := _flat(attackers.get_center(), target_squad.get_center())
	_check(_simulation.get_squad(target_squad.id) == null, "escouade visée détruite")
	_check(attackers.order == null, "ordre terminé")
	_check(distance <= 25.0, "approche jusqu'à portée (centre à %.1f m)" % distance)


## Bataille : toutes les troupes, face à face, sans erreur ; des membres meurent, des
## escouades sont détruites et retirées.
func _test_battle() -> void:
	print("\n[Bataille] Toutes les troupes")
	_reset()
	var plants := ["peashooter", "sunflower", "kernel_corn", "cactus", "rose", "chomper", "citron", "torchwood"]
	var zombies := ["foot_soldier", "engineer", "scientist", "imp", "deadbeard", "all_star", "super_brainz", "action_hero_80s", "z_mech"]
	var squads: Array[Squad] = []
	for i in plants.size():
		squads.append(_simulation.spawn_squad(_squad(plants[i]), 0, Vector3((i - 3.5) * 9.0, 0.0, 22.0), PI))
	for i in zombies.size():
		squads.append(_simulation.spawn_squad(_squad(zombies[i]), 1, Vector3((i - 4.0) * 9.0, 0.0, -22.0), 0.0))
	var start_units := _simulation.units.size()
	# Les escouades de mêlée chargent l'escouade ennemie la plus proche.
	for squad in squads:
		if squad.data.unit_data.is_melee():
			_simulation.issue_order(squad, AttackOrder.new(_nearest_enemy_squad(squad).id))
	_step_seconds(60.0)
	_check(_fired.size() > 100, "%d projectiles tirés" % _fired.size())
	_check(_simulation.units.size() < start_units, "%d membres morts sur %d" % [start_units - _simulation.units.size(), start_units])
	var consistent := true
	for squad in _simulation.squads:
		for unit in squad.units:
			consistent = consistent and unit.alive and unit.health > 0.0 and _simulation.units.has(unit)
	_check(consistent, "seuls des membres vivants restent dans les escouades")
	_check(_combat.projectiles.all(func(p: Projectile) -> bool: return not p.destroyed), "aucun projectile détruit encore en vol")


# --- Monde de test ---------------------------------------------------------------

func _reset() -> void:
	if _world != null:
		_world.queue_free()
	_world = Node3D.new()
	root.add_child(_world)
	_simulation = UnitSimulation.new()
	_simulation.set_physics_process(false)
	_world.add_child(_simulation)
	_combat = CombatSystem.new()
	_combat.simulation = _simulation
	_combat.rng_seed = 12345
	_combat.set_physics_process(false)
	_world.add_child(_combat)
	_combat.projectile_fired.connect(_on_fired)
	_combat.projectile_resolved.connect(func(p: Projectile, unit: Unit, hit: bool) -> void: _resolved.append([p, unit, hit]))
	_combat.damage_applied.connect(func(context: DamageContext) -> void: _damage.append(context))
	_combat.melee_resolved.connect(func(a: Unit, t: Unit, hit: bool) -> void: _melee.append([a, t, hit]))
	_fired.clear()
	_fire_times.clear()
	_resolved.clear()
	_damage.clear()
	_melee.clear()
	_time = 0.0


func _on_fired(projectile: Projectile) -> void:
	_fired.append(projectile)
	_fire_times.get_or_add(projectile.source_unit.id, []).append(_time)


func _step(count: int) -> void:
	for i in count:
		_simulation.step(TICK)
		_combat.step(TICK)
		_time += TICK


func _step_seconds(seconds: float) -> void:
	_step(roundi(seconds / TICK))


## Fait voler les projectiles déjà tirés sans que personne ne tire à nouveau.
func _simulate_projectiles_only(seconds: float) -> void:
	for unit in _simulation.units:
		unit.attack_cooldown_left = 1.0e9
	_step_seconds(seconds)


func _squad(id: String) -> SquadData:
	return load("res://data/units/%s_squad.tres" % id)


## Cible d'entraînement : un membre immobile, sans attaque, aux HP choisis.
func _dummy_squad(hp: float = 1.0e6) -> SquadData:
	var unit := (load("res://data/units/browncoat.tres") as UnitData).duplicate() as UnitData
	unit.member_hp = hp
	unit.attack_range = 0.0
	unit.radius = 0.4
	var squad := (load("res://data/units/browncoat_squad.tres") as SquadData).duplicate() as SquadData
	squad.unit_data = unit
	squad.unit_count = 1
	return squad


func _spawn_dummy(position: Vector3, hp: float = 1.0e6, team: int = 1) -> Unit:
	return _simulation.spawn_squad(_dummy_squad(hp), team, position, PI).units[0]


## Déplace instantanément une cible d'entraînement (et l'ancre de son escouade).
func _teleport(unit: Unit, position: Vector3) -> void:
	unit.position = position
	unit.previous_position = position
	_simulation.get_squad(unit.squad_id).anchor = position


func _nearest_enemy_squad(squad: Squad) -> Squad:
	var best: Squad = null
	for other in _simulation.squads:
		if other.team != squad.team and (best == null
				or _flat(other.get_center(), squad.get_center()) < _flat(best.get_center(), squad.get_center())):
			best = other
	return best


static func _flat(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length()


func _check(condition: bool, label: String) -> void:
	_checks += 1
	print("  %s  %s" % ["OK  " if condition else "ÉCHEC", label])
	if not condition:
		_failures.append(label)


# --- Capture (fenêtré) -------------------------------------------------------------

## Capture d'un échange de tirs : Pisto-pois contre Soldats, projectiles en vol.
func _capture() -> void:
	_reset()
	var camera := Camera3D.new()
	_world.add_child(camera)
	camera.look_at_from_position(Vector3(14.0, 11.0, 0.0), Vector3(0.0, 0.5, 0.0))
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-55.0, 30.0, 0.0)
	_world.add_child(light)
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(80.0, 80.0)
	ground.mesh = plane
	_world.add_child(ground)
	var selection := SelectionController.new()
	selection.simulation = _simulation
	_world.add_child(selection)
	var renderer := UnitRenderer.new()
	renderer.simulation = _simulation
	renderer.selection = selection
	_world.add_child(renderer)
	var projectiles := ProjectileRenderer.new()
	projectiles.combat = _combat
	_world.add_child(projectiles)
	_simulation.spawn_squad(_squad("peashooter"), 0, Vector3(0.0, 0.0, 9.0), PI)
	_simulation.spawn_squad(_squad("foot_soldier"), 1, Vector3(0.0, 0.0, -9.0), 0.0)
	_step_seconds(1.6)
	for i in 3:
		await process_frame
	DirAccess.make_dir_recursive_absolute(_screenshot_dir)
	var path := _screenshot_dir.path_join("combat.png")
	root.get_viewport().get_texture().get_image().save_png(path)
	print("  capture : %s" % path)
