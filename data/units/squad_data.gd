class_name SquadData
extends Resource
## Définition d'un type d'escouade : quelle unité, combien, et quelle formation.

@export var display_name: String = ""
@export var unit_data: UnitData
@export_range(1, 32) var unit_count: int = 6

@export_group("Formation")
## Nombre d'unités par rangée.
@export_range(1, 16) var formation_columns: int = 3
## Distance (m) entre deux emplacements voisins de la formation.
@export var formation_spacing: float = 1.8
