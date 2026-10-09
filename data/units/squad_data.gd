class_name SquadData
extends Resource
## Définition d'un type d'escouade : quelle unité, combien, et quelle formation.

@export var display_name: String = ""
@export var unit_data: UnitData
## Effectif (squad_size) : 1 = unité individuelle (Citron, Z-Mech…).
@export_range(1, 32) var unit_count: int = 6

@export_group("Production")
## Population occupée par l'escouade entière (pas par membre).
@export var population_cost: int = 0
## Coût en ressource principale (Soleil / Cerveaux), secondaire, tertiaire.
@export var primary_resource_cost: int = 0
@export var secondary_resource_cost: int = 0
@export var tertiary_resource_cost: int = 0
## Durée de production (s) dans un bâtiment (provisoire tant que non fixée par le design).
@export var build_time: float = 20.0

@export_group("Interface")
## Portrait du HUD publié avec le projet (null : vignette de repli).
@export var portrait: Texture2D
## Portrait local prioritaire s'il existe (dossiers ignorés par Git).
@export_file("*.png", "*.jpg", "*.webp") var local_portrait_path: String = ""

@export_group("Formation")
## Nombre d'unités par rangée.
@export_range(1, 16) var formation_columns: int = 3
## Distance (m) entre deux emplacements voisins de la formation (grille de base).
@export var formation_spacing: float = 1.8
## Irrégularité de la formation, en fraction de l'espacement : décalage des rangs,
## courbure et bruit sur chaque emplacement. 0 = grille parfaite.
@export_range(0.0, 0.45) var formation_irregularity: float = 0.3
## Écart d'orientation maximal (degrés) de chaque unité au repos par rapport à
## l'orientation de la formation.
@export_range(0.0, 45.0) var formation_yaw_jitter_degrees: float = 14.0


## Coût de production, dans l'ordre de TeamEconomy.Kind.
func get_cost() -> PackedInt32Array:
	return PackedInt32Array([primary_resource_cost, secondary_resource_cost, tertiary_resource_cost])


func is_individual() -> bool:
	return unit_count == 1


func get_portrait() -> Texture2D:
	if not local_portrait_path.is_empty() and ResourceLoader.exists(local_portrait_path):
		var local := load(local_portrait_path) as Texture2D
		if local != null:
			return local
	return portrait
