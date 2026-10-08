class_name FactionData
extends Resource
## Définition d'une faction (plantes, zombies…). Les deux camps ont la même économie :
## seuls les noms et les couleurs des ressources changent.

@export_group("Identité")
@export var id: StringName = &""
@export var display_name: String = ""
## Couleur des unités du camp à l'écran (anneaux au sol, numéro d'escouade).
@export var unit_color: Color = Color.WHITE

@export_group("Ressources")
## Noms des ressources, dans l'ordre de TeamEconomy.Kind : principale (effectifs),
## secondaire, tertiaire.
@export var resource_names: Array[String] = ["", "", ""]
## Couleurs d'affichage des ressources, même ordre.
@export var resource_colors: Array[Color] = [Color.WHITE, Color.WHITE, Color.WHITE]


func get_resource_name(kind: TeamEconomy.Kind) -> String:
	return resource_names[kind]


func get_resource_color(kind: TeamEconomy.Kind) -> Color:
	return resource_colors[kind]
