class_name HudCommandPanel
extends PanelContainer
## Commandes contextuelles de la sélection (grille d'emplacements à raccourcis) et
## file de production du bâtiment sélectionné. Les commandes sont décrites à partir
## des données (BuildingSystem.get_producible, coûts de SquadData) : aucun coût n'est
## codé dans les boutons. Une commande indisponible reste cliquable : son clic donne
## la raison du refus (message).

signal message(text: String, is_error: bool)

const SLOT_COUNT := 8
const SLOT_SIZE := Vector2(64, 64)
## Actions de raccourci des premiers emplacements (Input Map).
const HOTKEYS: Array[StringName] = [&"hud_command_1", &"hud_command_2", &"hud_command_3", &"hud_command_4"]
const QUEUED_SLOTS := 4


## Une commande affichable : titre, illustration, disponibilité et effet.
class Command:
	var title: String = ""
	var icon: Texture2D
	var color: Color = Color.WHITE
	var cost_text: String = ""
	var tooltip: String = ""
	var enabled: bool = true
	## Raison de l'indisponibilité (affichée au survol et au clic).
	var reason: String = ""
	var action: Callable


var selection: SelectionController
var buildings: BuildingSystem
var order_system: OrderSystem
var player: PlayerState
var skin: HudSkin

var _title: Label
var _slots: Array[Button] = []
var _slot_portraits: Array[HudPortrait] = []
var _slot_keys: Array[Label] = []
var _slot_costs: Array[Label] = []
var _commands: Array[Command] = []
var _hotkey_labels: PackedStringArray = []

var _queue_box: VBoxContainer
var _queue_portrait: HudPortrait
var _queue_name: Label
var _queue_bar: ProgressBar
var _queue_fill: StyleBoxFlat
var _queue_time: Label
var _queue_cancel: Button
var _queued: Array[Button] = []
var _queued_portraits: Array[HudPortrait] = []


func setup(p_selection: SelectionController, p_buildings: BuildingSystem, p_orders: OrderSystem,
		p_player: PlayerState, p_skin: HudSkin) -> void:
	selection = p_selection
	buildings = p_buildings
	order_system = p_orders
	player = p_player
	skin = p_skin
	mouse_filter = Control.MOUSE_FILTER_STOP
	add_theme_stylebox_override("panel", skin.make_panel_style())
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 6)
	add_child(column)
	_title = _label(14, skin.muted_text_color)
	column.add_child(_title)
	var grid := GridContainer.new()
	grid.columns = 4
	grid.add_theme_constant_override("h_separation", 6)
	grid.add_theme_constant_override("v_separation", 6)
	column.add_child(grid)
	for i in SLOT_COUNT:
		_hotkey_labels.append(_hotkey_text(i))
		grid.add_child(_make_slot(i))
	_queue_box = VBoxContainer.new()
	_queue_box.add_theme_constant_override("separation", 4)
	column.add_child(_queue_box)
	_queue_box.add_child(HSeparator.new())
	var current := HBoxContainer.new()
	current.add_theme_constant_override("separation", 8)
	_queue_box.add_child(current)
	_queue_portrait = HudPortrait.new()
	_queue_portrait.custom_minimum_size = Vector2(44, 44)
	current.add_child(_queue_portrait)
	var info := VBoxContainer.new()
	info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	info.add_theme_constant_override("separation", 0)
	current.add_child(info)
	var name_row := HBoxContainer.new()
	_queue_name = _label(14, skin.text_color)
	_queue_name.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_queue_time = _label(13, skin.muted_text_color)
	name_row.add_child(_queue_name)
	name_row.add_child(_queue_time)
	info.add_child(name_row)
	_queue_bar = ProgressBar.new()
	_queue_bar.show_percentage = false
	_queue_bar.max_value = 1.0
	_queue_bar.custom_minimum_size = Vector2(160, 12)
	_queue_fill = StyleBoxFlat.new()
	_queue_fill.set_corner_radius_all(3)
	_queue_bar.add_theme_stylebox_override("fill", _queue_fill)
	var track := StyleBoxFlat.new()
	track.bg_color = Color(0, 0, 0, 0.55)
	track.set_corner_radius_all(3)
	_queue_bar.add_theme_stylebox_override("background", track)
	info.add_child(_queue_bar)
	_queue_cancel = Button.new()
	_queue_cancel.text = "✕"
	_queue_cancel.tooltip_text = "Annuler (remboursé)"
	_queue_cancel.custom_minimum_size = Vector2(28, 28)
	_queue_cancel.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_queue_cancel.pressed.connect(func() -> void: _cancel(0))
	current.add_child(_queue_cancel)
	var queued_row := HBoxContainer.new()
	queued_row.add_theme_constant_override("separation", 4)
	_queue_box.add_child(queued_row)
	for i in QUEUED_SLOTS:
		var button := Button.new()
		button.custom_minimum_size = Vector2(34, 34)
		button.tooltip_text = "Annuler (remboursé)"
		var portrait := HudPortrait.new()
		portrait.set_anchors_preset(Control.PRESET_FULL_RECT)
		portrait.offset_left = 2
		portrait.offset_top = 2
		portrait.offset_right = -2
		portrait.offset_bottom = -2
		button.add_child(portrait)
		var index := i + 1
		button.pressed.connect(func() -> void: _cancel(index))
		queued_row.add_child(button)
		_queued.append(button)
		_queued_portraits.append(portrait)


func _process(_delta: float) -> void:
	_commands = _collect()
	var building := selection.selected_building
	visible = not _commands.is_empty() or building != null
	if building != null:
		_title.text = "Commandes — %s" % building.data.display_name
	elif not selection.selected_squads.is_empty():
		_title.text = "Commandes — escouades"
	for i in SLOT_COUNT:
		_apply_slot(i, _commands[i] if i < _commands.size() else null)
	_update_queue(building)


func _unhandled_input(event: InputEvent) -> void:
	if not visible:
		return
	for i in HOTKEYS.size():
		if event.is_action_pressed(HOTKEYS[i]) and i < _commands.size():
			trigger(i)
			get_viewport().set_input_as_handled()
			return


## Déclenche la commande `index` (clic ou raccourci). Commande indisponible : message.
func trigger(index: int) -> void:
	if index >= _commands.size():
		return
	var command := _commands[index]
	if not command.enabled:
		message.emit(command.reason, true)
		return
	command.action.call()


func get_commands() -> Array[Command]:
	return _commands


# ---------------------------------------------------------------- Commandes

func _collect() -> Array[Command]:
	var result: Array[Command] = []
	var building := selection.selected_building
	if building != null:
		var own := building.team == player.team
		for data in buildings.get_producible(building):
			result.append(_production_command(building, data, own))
		return result
	var squads := selection.selected_squads
	if not squads.is_empty():
		var own := true
		for squad in squads:
			own = own and squad.team == player.team
		var stop := Command.new()
		stop.title = "Arrêt"
		stop.color = Color(0.8, 0.8, 0.8)
		stop.tooltip = "Arrêt : annule l'ordre en cours"
		stop.enabled = own
		stop.reason = "Escouades ennemies" + _dev_hint()
		var selected := squads.duplicate()
		stop.action = func() -> void: order_system.issue_stop(selected)
		result.append(stop)
	return result


func _production_command(building: Building, data: SquadData, own: bool) -> Command:
	var faction := building.data.faction
	var command := Command.new()
	command.title = unit_name(data)
	command.icon = data.get_portrait()
	command.color = faction.unit_color if faction != null else Color.WHITE
	var cost := data.get_cost()
	var parts: PackedStringArray = []
	for kind in cost.size():
		if cost[kind] > 0:
			parts.append("%d %s" % [cost[kind], faction.resource_names[kind] if faction != null else ""])
	parts.append("%d population" % data.population_cost)
	command.cost_text = str(cost[0])
	command.tooltip = "Produire : %s (%d)\n%s\nDurée : %d s" % [unit_name(data), data.unit_count, " · ".join(parts),
		roundi(data.build_time)]
	if not own:
		command.enabled = false
		command.reason = "Bâtiment ennemi" + _dev_hint()
	else:
		var result := buildings.can_queue(building, data)
		command.enabled = result == BuildingSystem.QueueResult.OK
		command.reason = BuildingSystem.queue_result_text(result, faction)
	command.action = func() -> void:
		var queued := buildings.queue_production(building, data)
		if queued == BuildingSystem.QueueResult.OK:
			message.emit("%s : production lancée" % unit_name(data), false)
		else:
			message.emit(BuildingSystem.queue_result_text(queued, faction), true)
	return command


func _cancel(index: int) -> void:
	var building := selection.selected_building
	if building == null or building.team != player.team:
		return
	if index < building.queue.items.size():
		var data := building.queue.items[index]
		if buildings.cancel_production(building, index):
			message.emit("%s : production annulée (remboursée)" % unit_name(data), false)


## Nom affiché d'une escouade : celui de son unité (« Maïs »).
static func unit_name(data: SquadData) -> String:
	return data.unit_data.display_name if data.unit_data != null else data.display_name


func _dev_hint() -> String:
	return " (F2 : changer de camp)" if OS.is_debug_build() else ""


# ---------------------------------------------------------------- Affichage

func _make_slot(index: int) -> Button:
	var button := Button.new()
	button.custom_minimum_size = SLOT_SIZE
	button.focus_mode = Control.FOCUS_NONE
	var portrait := HudPortrait.new()
	portrait.set_anchors_preset(Control.PRESET_FULL_RECT)
	portrait.offset_left = 3
	portrait.offset_top = 3
	portrait.offset_right = -3
	portrait.offset_bottom = -3
	button.add_child(portrait)
	var key := _label(12, Color.WHITE)
	key.position = Vector2(5, 2)
	button.add_child(key)
	var cost := _label(12, Color.WHITE)
	cost.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	cost.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	cost.grow_vertical = Control.GROW_DIRECTION_BEGIN
	cost.offset_right = -4
	cost.offset_bottom = -1
	button.add_child(cost)
	button.pressed.connect(func() -> void: trigger(index))
	_slots.append(button)
	_slot_portraits.append(portrait)
	_slot_keys.append(key)
	_slot_costs.append(cost)
	return button


func _apply_slot(index: int, command: Command) -> void:
	var button := _slots[index]
	button.visible = command != null
	if command == null:
		return
	_slot_portraits[index].show_subject(command.icon, command.title, command.color)
	_slot_keys[index].text = _hotkey_labels[index]
	_slot_costs[index].text = command.cost_text
	button.tooltip_text = command.tooltip + ("" if command.enabled else "\n— " + command.reason)
	button.modulate = Color.WHITE if command.enabled else Color(0.55, 0.55, 0.55)
	if button.get_meta(&"accent", Color.TRANSPARENT) != command.color:
		button.set_meta(&"accent", command.color)
		button.add_theme_stylebox_override("normal", skin.make_slot_style(command.color))
		button.add_theme_stylebox_override("hover", skin.make_slot_style(command.color, true))
		button.add_theme_stylebox_override("pressed", skin.make_slot_style(command.color.lightened(0.3), true))


func _update_queue(building: Building) -> void:
	var queue := building.queue if building != null else null
	_queue_box.visible = queue != null and not queue.is_empty()
	if not _queue_box.visible:
		return
	var faction := building.data.faction
	var color := faction.unit_color if faction != null else Color.WHITE
	var current := queue.current()
	_queue_portrait.show_subject(current.get_portrait(), unit_name(current), color)
	_queue_name.text = unit_name(current)
	_queue_bar.value = queue.progress_ratio()
	_queue_fill.bg_color = color
	if queue.state == ProductionQueue.State.WAITING_FOR_EXIT:
		_queue_time.text = "sortie bloquée"
		_queue_time.add_theme_color_override("font_color", skin.warning_color)
	else:
		_queue_time.text = "%d s" % ceili(queue.remaining_time())
		_queue_time.add_theme_color_override("font_color", skin.muted_text_color)
	var own := building.team == player.team
	_queue_cancel.visible = own
	for i in QUEUED_SLOTS:
		var item_index := i + 1
		var shown := item_index < queue.items.size()
		_queued[i].visible = shown
		_queued[i].disabled = not own
		if shown:
			var data := queue.items[item_index]
			_queued_portraits[i].show_subject(data.get_portrait(), unit_name(data), color)


func _hotkey_text(index: int) -> String:
	if index >= HOTKEYS.size() or not InputMap.has_action(HOTKEYS[index]):
		return ""
	for event in InputMap.action_get_events(HOTKEYS[index]):
		var key := event as InputEventKey
		if key != null:
			if DisplayServer.get_name() == "headless":
				return OS.get_keycode_string(key.physical_keycode)
			return OS.get_keycode_string(DisplayServer.keyboard_get_keycode_from_physical(key.physical_keycode))
	return ""


func _label(font_size: int, color: Color) -> Label:
	var label := Label.new()
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	label.add_theme_constant_override("outline_size", 4)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label
