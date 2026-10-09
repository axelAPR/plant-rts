class_name HudSkin
extends Resource
## Habillage du HUD : couleurs et cadres. Les textures locales (extraites des
## ressources d'interface de Garden Warfare 2, dossier assets/gw2/ui/ ignoré par Git)
## sont facultatives : absentes (dépôt cloné), le HUD utilise des styles simples.

@export_group("Couleurs")
@export var panel_color: Color = Color(0.08, 0.1, 0.08, 0.88)
@export var border_color: Color = Color(0.42, 0.52, 0.34, 0.95)
@export var text_color: Color = Color(0.96, 0.95, 0.88)
@export var muted_text_color: Color = Color(0.72, 0.75, 0.66)
@export var warning_color: Color = Color(1.0, 0.55, 0.4)
@export var slot_color: Color = Color(0.16, 0.19, 0.15, 0.95)

@export_group("Textures locales (facultatives)")
## Cadre des panneaux (9 tranches).
@export_file("*.png") var panel_texture_path: String = "res://assets/gw2/ui/panel_stone.png"
## Marges des 9 tranches du cadre (gauche, haut, droite, bas), en pixels de texture.
@export var panel_texture_margins: Vector4 = Vector4(28, 24, 28, 24)
## Fond des emplacements de commande.
@export_file("*.png") var slot_texture_path: String = "res://assets/gw2/ui/slot_stone.png"
@export var slot_texture_margins: Vector4 = Vector4(10, 10, 10, 10)


## Style d'un panneau : texture locale en 9 tranches, sinon fond uni bordé.
func make_panel_style() -> StyleBox:
	var texture := load_local(panel_texture_path)
	if texture != null:
		return _texture_style(texture, panel_texture_margins, 10.0)
	var style := StyleBoxFlat.new()
	style.bg_color = panel_color
	style.border_color = border_color
	style.set_border_width_all(2)
	style.set_corner_radius_all(6)
	style.set_content_margin_all(8.0)
	return style


## Style d'un emplacement de commande (bouton) ; `accent` colore la bordure.
func make_slot_style(accent: Color, hovered: bool = false) -> StyleBox:
	var texture := load_local(slot_texture_path)
	if texture != null:
		var textured := _texture_style(texture, slot_texture_margins, 3.0)
		textured.modulate_color = Color(1.15, 1.15, 1.15) if hovered else Color.WHITE
		return textured
	var style := StyleBoxFlat.new()
	style.bg_color = slot_color.lightened(0.12) if hovered else slot_color
	style.border_color = accent if hovered else accent.darkened(0.35)
	style.set_border_width_all(2)
	style.set_corner_radius_all(4)
	style.set_content_margin_all(2.0)
	return style


func load_local(path: String) -> Texture2D:
	if path.is_empty() or not ResourceLoader.exists(path):
		return null
	return load(path) as Texture2D


static func _texture_style(texture: Texture2D, margins: Vector4, content: float) -> StyleBoxTexture:
	var style := StyleBoxTexture.new()
	style.texture = texture
	style.texture_margin_left = margins.x
	style.texture_margin_top = margins.y
	style.texture_margin_right = margins.z
	style.texture_margin_bottom = margins.w
	style.set_content_margin_all(content)
	return style
