class_name HudPortrait
extends Panel
## Portrait carré d'une unité ou d'un bâtiment : l'illustration si elle existe, sinon
## une vignette de repli (initiales sur la couleur de la faction).

var _texture_rect: TextureRect
var _initials: Label
var _style: StyleBoxFlat


func _init() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip_contents = true
	_style = StyleBoxFlat.new()
	_style.set_corner_radius_all(4)
	_style.set_border_width_all(2)
	add_theme_stylebox_override("panel", _style)
	_texture_rect = TextureRect.new()
	_texture_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	_texture_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_texture_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_texture_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_texture_rect)
	_initials = Label.new()
	_initials.set_anchors_preset(Control.PRESET_FULL_RECT)
	_initials.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_initials.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_initials.add_theme_color_override("font_outline_color", Color.BLACK)
	_initials.add_theme_constant_override("outline_size", 6)
	_initials.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_initials)


## `texture` null : vignette de repli avec les initiales de `title`.
func show_subject(texture: Texture2D, title: String, color: Color) -> void:
	_texture_rect.texture = texture
	_texture_rect.visible = texture != null
	_initials.visible = texture == null
	_initials.text = initials(title)
	_initials.add_theme_font_size_override("font_size", maxi(12, int(size.y * 0.32)))
	_style.bg_color = color.darkened(0.55) if texture == null else Color(0.05, 0.05, 0.05)
	_style.border_color = color


static func initials(title: String) -> String:
	var words := title.replace("-", " ").split(" ", false)
	var result := ""
	for word in words:
		if word.length() > 2 or words.size() == 1:
			result += word.substr(0, 1).to_upper()
		if result.length() >= 2:
			break
	return result if not result.is_empty() else title.substr(0, 2).to_upper()
