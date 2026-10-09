class_name BuildingData
extends Resource
## Définition d'un type de bâtiment (QG, futurs bâtiments et structures) : identité,
## scène d'affichage, emprise, points de vie, production et coût de construction.
## Les valeurs marquées « provisoire » ne sont pas fixées par le design.

@export_group("Identité")
@export var id: StringName = &""
@export var display_name: String = ""
@export_multiline var description: String = ""
@export var faction: FactionData
## Bâtiment principal de la faction (un par camp en début de partie).
@export var is_headquarters: bool = false
## Scène d'affichage (modèle et effets). Pivot au sol, avant (sortie) vers +Z.
@export var scene: PackedScene
## Illustration du HUD publiée avec le projet.
@export var portrait: Texture2D
## Illustration locale prioritaire si elle existe (dossiers ignorés par Git).
@export_file("*.png", "*.jpg", "*.webp") var local_portrait_path: String = ""

@export_group("Emprise")
## Rectangle au sol (m) : largeur en X, profondeur en Z, centré sur le pivot.
@export var footprint_size: Vector2 = Vector2(10.0, 10.0)
## Hauteur (m) du volume de clic.
@export var height: float = 8.0
## Rayon (m) de l'anneau de sélection.
@export var selection_radius: float = 8.0

@export_group("Jeu")
## Points de vie (provisoire).
@export var max_hp: float = 5000.0

@export_group("Production")
## Produit l'unité constructrice de sa faction (FactionRoster.builder_squad).
@export var produces_builder: bool = false
## Autres escouades produites par ce bâtiment.
@export var producible_squads: Array[SquadData] = []
## Nombre maximal d'escouades en file (provisoire).
@export_range(1, 10) var queue_capacity: int = 5
## Point de sortie des escouades produites, dans le repère du bâtiment (+Z = avant).
@export var exit_offset: Vector3 = Vector3(0.0, 0.0, 9.0)
## Distance (m) du point de ralliement par défaut, devant la sortie.
@export var rally_distance: float = 8.0

@export_group("Construction")
## Coût de construction par une unité constructrice (provisoire ; 0 pour un QG posé
## sur la carte).
@export var primary_resource_cost: int = 0
@export var secondary_resource_cost: int = 0
@export var tertiary_resource_cost: int = 0
## Temps de construction (s) par une unité constructrice (provisoire).
@export var build_time: float = 60.0


func get_build_cost() -> PackedInt32Array:
	return PackedInt32Array([primary_resource_cost, secondary_resource_cost, tertiary_resource_cost])


func get_portrait() -> Texture2D:
	if not local_portrait_path.is_empty() and ResourceLoader.exists(local_portrait_path):
		var local := load(local_portrait_path) as Texture2D
		if local != null:
			return local
	return portrait
