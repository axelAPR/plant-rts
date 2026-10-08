extends SceneTree
## Test automatisé des blocages entre escouades (trafic). Sans scène ni rendu : la
## simulation est avancée tick par tick (UnitSimulation.step), ce qui rend les
## scénarios rapides et reproductibles.
##
## Scénarios :
##   a. deux escouades alliées qui se croisent de face ;
##   b. une escouade qui traverse une escouade alliée à l'arrêt ;
##   c. 20 escouades envoyées ensemble sur un même point (ordre de groupe) ;
##   d. deux ordres séparés qui visent le même point ;
##   e. charge : ~150 escouades de troupes variées, ordre de groupe à travers la carte ;
##   e2. charge réaliste : 9 apparitions « Toutes les troupes » du menu DEV au même
##       endroit (153 escouades superposées, plantes et zombies), puis ordre de groupe.
## Critères communs : tous les ordres se terminent dans le délai, aucune superposition
## entre unités à l'arrêt, formations reformées à l'arrivée.
##
## Lancement : Godot --headless --path . --script res://tests/squad_test/traffic_runner.gd
## Option : -- --only=a,c pour ne lancer que certains scénarios.
## Code de sortie : 0 si tout passe, 1 sinon.

const TICK := 1.0 / 60.0
## Durée (s) simulée après la fin des ordres pour vérifier l'état au repos.
const SETTLE_TIME := 1.0
## Tolérance (m) sur la marge entre deux unités (distance moins la somme des rayons).
const OVERLAP_TOLERANCE := 0.02
## Écart unité/emplacement (m) maximal pour une formation reformée.
const REST_FORMATION_ERROR := 0.3
## Écart (m) toléré entre le centre d'une escouade et sa destination, quand celle-ci est libre.
const POSITION_TOLERANCE := 0.6
## Marge de délai : un ordre doit finir en moins de (distance / vitesse) × ce facteur + TIME_MARGIN.
const TIME_FACTOR := 2.0
const TIME_MARGIN := 10.0

const SQUAD_DIR := "res://data/units/"
const ALL_SQUADS: Array[String] = [
	"peashooter", "sunflower", "kernel_corn", "cactus", "rose", "chomper", "citron", "torchwood",
	"browncoat", "foot_soldier", "engineer", "scientist", "deadbeard", "all_star",
	"super_brainz", "action_hero_80s", "z_mech",
]

var _simulation: UnitSimulation
var _orders: OrderSystem
var _failures: Array[String] = []
var _checks: int = 0


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var only := PackedStringArray()
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--only="):
			only = arg.trim_prefix("--only=").split(",")
	var scenarios: Array[Array] = [
		["a", "croisement de face", _scenario_head_on],
		["b", "traversée d'une escouade à l'arrêt", _scenario_cross_idle],
		["c", "20 escouades vers un même point", _scenario_group_of_20],
		["d", "deux ordres séparés vers le même point", _scenario_same_point],
		["e", "charge : 150 escouades à travers la carte", _scenario_load],
		["e2", "charge réaliste : 9 × menu DEV au même endroit", _scenario_dev_menu_load],
	]
	for scenario in scenarios:
		if only.is_empty() or only.has(scenario[0]):
			print("\n== %s. %s" % [scenario[0], scenario[1]])
			_reset()
			await (scenario[2] as Callable).call()
	print("\n%d vérifications, %d échec(s)" % [_checks, _failures.size()])
	quit(0 if _failures.is_empty() else 1)


# --- Scénarios ---------------------------------------------------------------

func _scenario_head_on() -> void:
	for id in ["peashooter", "browncoat", "deadbeard", "z_mech"]:
		print("  -- %s contre %s" % [id, id])
		_reset()
		var data := _squad_data(id)
		var a := _simulation.spawn_squad(data, 0, Vector3(0.0, 0.0, -12.0), 0.0)
		var b := _simulation.spawn_squad(data, 0, Vector3(0.0, 0.0, 12.0), PI)
		_move([a], Vector3(0.0, 0.0, 12.0))
		_move([b], Vector3(0.0, 0.0, -12.0))
		await _run_until_idle([a, b], true)


func _scenario_cross_idle() -> void:
	var idle := _simulation.spawn_squad(_squad_data("peashooter"), 0, Vector3.ZERO, 0.0)
	var mover := _simulation.spawn_squad(_squad_data("peashooter"), 0, Vector3(0.0, 0.0, -14.0), 0.0)
	var idle_start := idle.get_center()
	_move([mover], Vector3(0.0, 0.0, 14.0))
	await _run_until_idle([mover], true)
	var drift := idle.get_center().distance_to(idle_start)
	print("  info  escouade à l'arrêt déplacée de %.2f m" % drift)


func _scenario_group_of_20() -> void:
	var squads := _spawn_grid(20, 5, Vector3(0.0, 0.0, -30.0), 12.0, 0)
	_move(squads, Vector3(0.0, 0.0, 30.0))
	await _run_until_idle(squads, false)


func _scenario_same_point() -> void:
	var data := _squad_data("peashooter")
	var a := _simulation.spawn_squad(data, 0, Vector3(-14.0, 0.0, -10.0), 0.0)
	var b := _simulation.spawn_squad(data, 0, Vector3(14.0, 0.0, -10.0), 0.0)
	var point := Vector3(0.0, 0.0, 10.0)
	_move([a], point)
	_move([b], point)
	await _run_until_idle([a, b], false)
	_check(_squads_separated(a, b), "formations distinctes : chaque unité est plus proche du centre de sa propre escouade")


func _scenario_load() -> void:
	var squads := _spawn_grid(150, 15, Vector3(0.0, 0.0, -70.0), 11.0, 0)
	_move(squads, Vector3(0.0, 0.0, 70.0))
	await _run_until_idle(squads, false)


## Reproduit 9 clics sur « Toutes les troupes » (DevMenu) sans bouger la caméra :
## les escouades apparaissent les unes sur les autres. Puis un seul ordre de groupe.
func _scenario_dev_menu_load() -> void:
	var menu := DevMenu.new()
	menu.simulation = _simulation
	var plants: Array[SquadData] = []
	var zombies: Array[SquadData] = []
	for i in ALL_SQUADS.size():
		(plants if i < 8 else zombies).append(_squad_data(ALL_SQUADS[i]))
	menu.plant_squads = plants
	menu.zombie_squads = zombies
	var rig: RTSCamera = (load("res://camera/rts_camera.tscn") as PackedScene).instantiate()
	root.add_child(rig)
	menu.camera_rig = rig
	for i in 9:
		menu.spawn_all_troops()
	rig.queue_free()
	menu.free()
	# Laisse les unités superposées se dégager, comme en jeu avant que le joueur ne donne l'ordre.
	for i in int(2.0 / TICK):
		_simulation.step(TICK)
	print("  info  avant l'ordre : %d paires d'unités en recouvrement" % _min_clearance().overlaps)
	var squads: Array[Squad] = _simulation.squads.duplicate()
	_move(squads, Vector3(0.0, 0.0, 80.0))
	print("  info  largeur de la ligne d'escouades de l'ordre de groupe : %.0f m" % _group_line_width(squads))
	await _run_until_idle(squads, false)


func _group_line_width(squads: Array[Squad]) -> float:
	var lo := INF
	var hi := -INF
	for squad in squads:
		var target := (squad.order as MoveOrder).target
		lo = minf(lo, target.x)
		hi = maxf(hi, target.x)
	return hi - lo


# --- Déroulement et mesures --------------------------------------------------

## Nouvelle simulation vide (la précédente est libérée).
func _reset() -> void:
	if _simulation != null:
		_simulation.queue_free()
		_orders.queue_free()
	_simulation = UnitSimulation.new()
	_simulation.set_physics_process(false)
	root.add_child(_simulation)
	_orders = OrderSystem.new()
	_orders.simulation = _simulation
	root.add_child(_orders)


## Escouades de troupes variées (rotation sur toutes les troupes), en grille centrée,
## orientées vers +Z.
func _spawn_grid(count: int, per_row: int, center: Vector3, spacing: float, team: int) -> Array[Squad]:
	var squads: Array[Squad] = []
	var positions := SquadLayout.camp_positions(count, center, -1.0, per_row, spacing, spacing, 0.0)
	for i in count:
		squads.append(_simulation.spawn_squad(_squad_data(ALL_SQUADS[i % ALL_SQUADS.size()]), team, positions[i], 0.0))
	return squads


func _move(squads: Array[Squad], target: Vector3) -> void:
	_orders.issue_move(squads, target)


## Avance la simulation jusqu'à ce que toutes les escouades aient fini leur ordre (ou
## jusqu'au délai), puis vérifie les critères communs sur toutes les escouades.
## `check_arrival` : les destinations sont libres, l'arrivée exacte est exigée.
func _run_until_idle(movers: Array[Squad], check_arrival: bool) -> void:
	var targets: Dictionary[Squad, Vector3] = {}
	var timeout := 0.0
	for squad in movers:
		var order := squad.order as MoveOrder
		targets[squad] = order.target
		var distance := squad.get_center().distance_to(order.target)
		timeout = maxf(timeout, distance / squad.get_move_speed() * TIME_FACTOR + TIME_MARGIN)

	var started := Time.get_ticks_msec()
	var elapsed := 0.0
	var pending := movers.size()
	var travel_clearance := INF
	var ticks := 0
	while elapsed < timeout:
		_simulation.step(TICK)
		elapsed += TICK
		ticks += 1
		if ticks % 10 == 0:
			travel_clearance = minf(travel_clearance, _min_clearance().clearance)
		pending = movers.filter(func(s: Squad) -> bool: return s.order != null).size()
		if pending == 0:
			break
		# Rend la main au moteur de temps en temps (fenêtre réactive, sortie console).
		if int(elapsed / TICK) % 600 == 0:
			await process_frame
	var wall := (Time.get_ticks_msec() - started) / 1000.0

	_check(pending == 0, "ordres terminés : %d/%d en %.1f s simulées (délai %.0f s ; %.1f s réelles, %d unités)"
			% [movers.size() - pending, movers.size(), elapsed, timeout, wall, _simulation.units.size()])
	print("  info  marge min entre unités pendant la marche : %.2f m" % travel_clearance)
	if pending > 0:
		_report_stuck(movers)

	for i in int(SETTLE_TIME / TICK):
		_simulation.step(TICK)

	var clearance := _min_clearance()
	_check(clearance.clearance >= -OVERLAP_TOLERANCE,
			"aucune superposition à l'arrêt (marge min %.3f m, %d paires en recouvrement)"
			% [clearance.clearance, clearance.overlaps])

	var unformed := 0
	var worst := 0.0
	for squad in _simulation.squads:
		var error := squad.get_formation_error()
		worst = maxf(worst, error)
		if error >= REST_FORMATION_ERROR:
			unformed += 1
	_check(unformed == 0, "formations reformées : %d/%d (écart max %.2f m)"
			% [_simulation.squads.size() - unformed, _simulation.squads.size(), worst])

	if check_arrival:
		for squad in movers:
			var offset := squad.get_center() - targets[squad]
			offset.y = 0.0
			_check(offset.length() < POSITION_TOLERANCE,
					"escouade %d arrivée à destination (écart %.2f m)" % [squad.id + 1, offset.length()])


## Diagnostic des ordres non terminés : distance restante de l'ancre, retard des unités
## (cause 2 : LAG_STOP fige l'ancre) et ancre arrivée sans formation reformée (cause 3).
func _report_stuck(movers: Array[Squad]) -> void:
	var anchor_frozen := 0
	var anchor_arrived := 0
	var lines: Array[String] = []
	for squad in movers:
		var order := squad.order as MoveOrder
		if order == null:
			continue
		var remaining := order.target.distance_to(squad.anchor)
		var lag := squad.get_formation_error()
		if remaining <= 0.001:
			anchor_arrived += 1
		elif lag >= MoveOrder.LAG_STOP:
			anchor_frozen += 1
		if lines.size() < 6:
			lines.append("escouade %d (%s) : ancre à %.1f m du but, centre à %.1f m, écart formation %.2f m"
					% [squad.id + 1, squad.data.unit_data.id, remaining, order.target.distance_to(squad.get_center()), lag])
	print("  info  bloquées : %d ancres figées (écart ≥ LAG_STOP), %d ancres arrivées sans formation reformée, %d autres"
			% [anchor_frozen, anchor_arrived, movers.filter(func(s: Squad) -> bool: return s.order != null).size() - anchor_frozen - anchor_arrived])
	for line in lines:
		print("        " + line)


## Plus petite marge entre deux unités (distance au sol moins la somme des rayons) et
## nombre de paires en recouvrement, via une grille pour rester rapide à 1 000 unités.
func _min_clearance() -> Dictionary:
	var units := _simulation.units
	var grid := SpatialHashGrid.new(4.0)
	for i in units.size():
		grid.insert(i, units[i].position)
	var best := INF
	var overlaps := 0
	for i in units.size():
		for j in grid.query(units[i].position, 4.0):
			if j <= i:
				continue
			var offset := units[i].position - units[j].position
			offset.y = 0.0
			var clearance := offset.length() - units[i].data.radius - units[j].data.radius
			best = minf(best, clearance)
			if clearance < -OVERLAP_TOLERANCE:
				overlaps += 1
	return {"clearance": best, "overlaps": overlaps}


func _squads_separated(a: Squad, b: Squad) -> bool:
	var center_a := a.get_center()
	var center_b := b.get_center()
	for unit in a.units:
		if unit.position.distance_to(center_a) >= unit.position.distance_to(center_b):
			return false
	for unit in b.units:
		if unit.position.distance_to(center_b) >= unit.position.distance_to(center_a):
			return false
	return true


# --- Utilitaires -------------------------------------------------------------

func _squad_data(id: String) -> SquadData:
	return load(SQUAD_DIR + id + "_squad.tres") as SquadData


func _check(condition: bool, label: String) -> void:
	_checks += 1
	print(("  OK    " if condition else "  ÉCHEC ") + label)
	if not condition:
		_failures.append(label)
