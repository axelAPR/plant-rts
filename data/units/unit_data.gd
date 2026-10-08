class_name UnitData
extends Resource
## Définition d'un type d'unité (plante, zombie…), partagée par toutes ses instances.

@export_group("Identité")
@export var id: StringName = &""
@export var display_name: String = ""

@export_group("Représentation")
## Scène visuelle (modèle importé) : pivot au sol, orientée vers +Z (Vector3.MODEL_FRONT).
@export var visual_scene: PackedScene

@export_group("Déplacement")
## Vitesse maximale (m/s).
@export var move_speed: float = 3.5
## Accélération (m/s²).
@export var acceleration: float = 14.0
## Vitesse de rotation (degrés/s).
@export var turn_speed_degrees: float = 540.0
## Rayon du corps (m) : tronc, pieds — ni bras, ni armes, ni feuilles. Sert aux
## collisions et à l'évitement entre unités.
@export var radius: float = 0.35
## Rayon de l'emprise visuelle complète (m), armes et feuilles comprises : anneau de
## sélection, clic, et emprise des formations pour réserver les destinations.
@export var footprint_radius: float = 0.55
