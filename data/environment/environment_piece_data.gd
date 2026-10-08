class_name EnvironmentPieceData
extends Resource
## Pièce du kit de décor (assets/environment) : identité, scène, emprise au sol et
## propriétés de jeu. Données seulement : la navigation, le couvert et la capture ne
## les lisent pas encore.

enum Category { GROUND, BUILDINGS, COVER_HEAVY, COVER_LIGHT, VEGETATION, PROPS, GAMEPLAY, BORDERS }
enum FootprintShape { RECTANGLE, CIRCLE }
enum Cover { NONE, LIGHT, HEAVY }
enum ResourceKind { NONE, PRIMARY, SECONDARY, TERTIARY }

@export_group("Identité")
@export var id: StringName = &""
@export var display_name: String = ""
@export var category: Category = Category.PROPS
## Modèle (pivot au sol, avant vers +Z, 1 unité = 1 m).
@export var scene: PackedScene

@export_group("Emprise")
@export var footprint_shape: FootprintShape = FootprintShape.RECTANGLE
## Rectangle (m) : largeur en X, profondeur en Z, centré sur le pivot. Multiples de 2 m.
@export var footprint_size: Vector2 = Vector2(2.0, 2.0)
## Rayon (m) si l'emprise est un cercle.
@export var footprint_radius: float = 0.0
## Hauteur (m) du modèle, mesurée dans le .glb.
@export var height: float = 0.0

@export_group("Jeu")
@export var blocks_movement: bool = false
@export var blocks_vision: bool = false
@export var cover: Cover = Cover.NONE
## Ressource produite (points de jeu seulement).
@export var resource: ResourceKind = ResourceKind.NONE
