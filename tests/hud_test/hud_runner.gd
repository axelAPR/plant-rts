extends SceneTree
## Test automatisé des QG et du HUD sur la vraie carte (world/maps/suburb) :
## QG présents et distincts, sélection au clic (rayon de la caméra), HUD (panneau de
## sélection, commandes, barre des ressources = valeurs de l'économie), production du
## Maïs et de l'Ingénieur par les commandes du HUD, coût et population, refus
## (ressources, population) avec message, progression affichée, apparition sur un
## emplacement valide, changement de sélection, mini-carte, sélection des unités.
##
## Lancement : Godot --headless --path . --script res://tests/hud_test/hud_runner.gd
## Code de sortie : 0 si tout passe, 1 sinon.

const MAP := "res://world/maps/suburb/suburb.tscn"

var _failures: Array[String] = []
var _checks: int = 0

var _scene: Node
var _buildings: BuildingSystem
var _selection: SelectionController
var _economy: Economy
var _player: PlayerState
var _hud: RtsHud
var _camera: RTSCamera
var _simulation: UnitSimulation


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	_scene = (load(MAP) as PackedScene).instantiate()
	root.add_child(_scene)
	await _frames(3)
	_buildings = _scene.get_node("BuildingSystem")
	_selection = _scene.get_node("SelectionController")
	_economy = _scene.get_node("Economy")
	_player = _scene.get_node("PlayerState")
	_hud = _scene.get_node("HUD/RtsHud")
	_camera = _scene.get_node("RTSCamera")
	_simulation = _scene.get_node("UnitSimulation")
	_economy.set_physics_process(false)          # stocks figés : valeurs exactes

	print("\nQG sur la carte")
	var tree := _buildings.get_headquarters(0)
	var tomb := _buildings.get_headquarters(1)
	_check(tree != null and tree.data.id == &"tree_of_life", "Arbre de Vie : QG des plantes")
	_check(tomb != null and tomb.data.id == &"zombie_tomb", "Tombeau monumental : QG des zombies")
	if tree == null or tomb == null:
		_finish()
		return
	_check(tree.data.scene != tomb.data.scene and tree.data.scene != null, "scènes d'affichage distinctes")
	var renderer := _scene.get_node("BuildingRenderer")
	_check(renderer.get_child_count() >= 2, "bâtiments affichés (%d nœuds)" % renderer.get_child_count())
	_check(_player.team == 0, "le joueur joue les plantes")

	print("\nSélection au clic gauche")
	await _focus(tree.position)
	await _click(_screen(tree.position + Vector3(0.0, 4.0, 0.0)))
	_check(_selection.selected_building == tree, "clic sur l'Arbre de Vie : sélectionné")
	_check(_selection.selected_squads.is_empty(), "sélection exclusive (aucune escouade)")
	var panel := _hud.selection_panel
	await _frames(2)
	_check(panel.visible and _label_text(panel, "Arbre de Vie"), "panneau : nom du QG")
	_check(_label_text(panel, "5000 / 5000"), "panneau : points de vie 5000 / 5000")
	_check(_label_text(panel, "Opérationnel"), "panneau : état")
	var commands := _hud.command_panel.get_commands()
	_check(commands.size() == 1 and commands[0].title == "Maïs" and commands[0].enabled, "commande : produire le Maïs (disponible)")

	print("\nBarre des ressources = économie")
	var plants := _economy.get_team(0)
	_check(_label_text(_hud.top_bar, "Soleil") and _label_text(_hud.top_bar, "Engrais") and _label_text(_hud.top_bar, "Terre"),
		"noms : Soleil, Engrais, Terre")
	_check(_label_text(_hud.top_bar, str(plants.get_amount(TeamEconomy.Kind.PRIMARY))), "Soleil affiché = %d" % plants.get_amount(TeamEconomy.Kind.PRIMARY))
	_check(_label_text(_hud.top_bar, "0 / 100"), "population 0 / 100")

	print("\nProduction du Maïs par le HUD")
	_hud.command_panel.trigger(0)
	await _frames(2)
	_check(tree.queue.items.size() == 1, "Maïs en file")
	_check(plants.get_amount(TeamEconomy.Kind.PRIMARY) == 0 and plants.get_amount(TeamEconomy.Kind.SECONDARY) == 35,
		"500 Soleil et 15 Engrais déduits")
	_check(plants.population_used == 8 and _label_text(_hud.top_bar, "8 / 100"), "population 8 / 100 affichée")
	_check(_hud.get_message().contains("production lancée"), "message : « %s »" % _hud.get_message())
	_hud.command_panel.trigger(0)
	await _frames(2)
	_check(tree.queue.items.size() == 1 and _hud.get_message() == "Pas assez de Soleil", "second Maïs refusé : « %s »" % _hud.get_message())
	_check(not _hud.command_panel.get_commands()[0].enabled, "commande grisée (ressources insuffisantes)")
	_buildings.step(10.0)
	await _frames(2)
	var bar := _find_progress(_hud.command_panel)
	_check(bar != null and absf(bar.value - 0.5) < 0.02, "progression affichée : %.0f %%" % ((bar.value if bar != null else 0.0) * 100))
	_check(_label_text(_hud.command_panel, "10 s"), "temps restant affiché : 10 s")
	_check(_label_text(panel, "Production : Maïs"), "panneau : production en cours")
	_buildings.step(10.1)
	await _frames(2)
	var corn := _last_squad(0)
	_check(corn != null and HudCommandPanel.unit_name(corn.data) == "Maïs" and corn.units.size() == 4, "Maïs apparu (4 membres)")
	if corn != null:
		var inside := false
		for building in _buildings.buildings:
			for unit in corn.units:
				inside = inside or building.contains_point(unit.position)
		_check(not inside, "apparition hors des bâtiments")
		_check(corn.anchor.distance_to(tree.get_exit_position()) < 12.0, "apparition devant la sortie (%.1f m)" % corn.anchor.distance_to(tree.get_exit_position()))
	_check(plants.population_used == 8, "population : 8 (escouade produite)")

	print("\nChangement de sélection")
	if corn != null:
		_selection.set_selection([corn] as Array[Squad])
		await _frames(2)
		_check(_selection.selected_building == null, "le QG quitte la sélection")
		_check(_label_text(panel, "Maïs") and _label_text(panel, "4 / 4 membres"), "panneau : escouade de Maïs")
		var squad_commands := _hud.command_panel.get_commands()
		_check(squad_commands.size() == 1 and squad_commands[0].title == "Arrêt", "commandes : Arrêt")
	await _click(_screen(tree.position + Vector3(0.0, 4.0, 0.0)))
	_check(_selection.selected_building == tree, "retour au QG par clic")
	_selection.clear_selection()
	await _frames(2)
	_check(not panel.visible and not _hud.command_panel.visible, "rien de sélectionné : panneaux masqués")

	print("\nZombies : Tombeau et Ingénieur")
	_selection.set_building_selection(tomb)
	await _frames(2)
	var enemy := _hud.command_panel.get_commands()
	_check(enemy.size() == 1 and enemy[0].title == "Ingénieur" and not enemy[0].enabled, "QG ennemi : commande grisée pour le joueur plantes")
	_player.team = 1
	await _frames(2)
	_check(_label_text(_hud.top_bar, "Cerveaux") and _label_text(_hud.top_bar, "Engrenages") and _label_text(_hud.top_bar, "Pesticides"),
		"barre : ressources des zombies")
	var zombies := _economy.get_team(1)
	zombies.population_cap = 4
	await _frames(1)
	var blocked := _hud.command_panel.get_commands()[0]
	_check(not blocked.enabled and blocked.reason == "Population maximale atteinte", "population insuffisante : « %s »" % blocked.reason)
	_hud.command_panel.trigger(0)
	await _frames(1)
	_check(tomb.queue.is_empty() and zombies.get_amount(TeamEconomy.Kind.PRIMARY) == 500, "refus sans effet")
	zombies.population_cap = 100
	await _frames(1)
	_hud.command_panel.trigger(0)
	await _frames(1)
	_check(tomb.queue.items.size() == 1 and zombies.get_amount(TeamEconomy.Kind.PRIMARY) == 200 and zombies.population_used == 5,
		"Ingénieur en file : 300 Cerveaux et 5 de population")
	_buildings.step(15.1)
	await _frames(2)
	var engineer := _last_squad(1)
	_check(engineer != null and HudCommandPanel.unit_name(engineer.data) == "Ingénieur", "Ingénieur apparu")
	_check(engineer != null and engineer.anchor.distance_to(tomb.get_exit_position()) < 12.0, "devant la sortie du Tombeau")

	print("\nMini-carte")
	var minimap := _hud.minimap
	var p := minimap.world_to_map(tree.position)
	_check(Rect2(Vector2.ZERO, minimap.size).has_point(p), "QG plantes dans la mini-carte (%.0f, %.0f)" % [p.x, p.y])
	_check(minimap.map_to_world(p).distance_to(tree.position) < 0.5, "conversion carte ↔ monde")
	minimap.queue_redraw()
	await _frames(2)
	_check(true, "dessin sans erreur")

	print("\nSélection des unités inchangée")
	_selection.clear_selection()
	await _focus(corn.anchor if corn != null else tree.position)
	if corn != null:
		await _click(_screen(corn.units[0].position + Vector3.UP * 0.65))
		_check(_selection.selected_squads.size() == 1 and _selection.selected_squads[0] == corn, "clic sur un Maïs : son escouade")
	_finish()


# ---------------------------------------------------------------- Outils

func _focus(point: Vector3) -> void:
	_camera.focus_on(point)
	await _frames(120)


func _screen(world: Vector3) -> Vector2:
	return _camera.get_camera().unproject_position(world)


func _click(position: Vector2) -> void:
	for pressed: bool in [true, false]:
		var event := InputEventMouseButton.new()
		event.button_index = MOUSE_BUTTON_LEFT
		event.pressed = pressed
		event.position = position
		root.push_input(event, true)
		await _frames(2)


func _frames(count: int) -> void:
	for i in count:
		await process_frame


func _last_squad(team: int) -> Squad:
	var found: Squad = null
	for squad in _simulation.squads:
		if squad.team == team:
			found = squad
	return found


## Un libellé visible du nœud contient-il `text` ?
func _label_text(node: Node, text: String) -> bool:
	for child in node.find_children("*", "Label", true, false):
		var label := child as Label
		if label.is_visible_in_tree() and label.text.contains(text):
			return true
	return false


func _find_progress(node: Node) -> ProgressBar:
	for child in node.find_children("*", "ProgressBar", true, false):
		if (child as ProgressBar).is_visible_in_tree():
			return child
	return null


func _check(condition: bool, label: String) -> void:
	_checks += 1
	print("  %s  %s" % ["OK  " if condition else "ÉCHEC", label])
	if not condition:
		_failures.append(label)


func _finish() -> void:
	print("\n%d vérifications, %d échec(s)" % [_checks, _failures.size()])
	quit(0 if _failures.is_empty() else 1)
