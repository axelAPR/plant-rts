class_name SquadData
extends Resource
## Définition d'un type d'escouade : quelle unité, combien, et quelle formation.

@export var display_name: String = ""
@export var unit_data: UnitData
@export_range(1, 32) var unit_count: int = 6

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
