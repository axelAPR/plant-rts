class_name FactionRoster
extends Resource
## Composition d'une faction pour la partie : QG, unité constructrice et bâtiments
## constructibles. Séparé de FactionData (que les unités référencent) pour éviter les
## références circulaires entre ressources. Changer l'unité constructrice d'une
## faction = changer `builder_squad` ici, sans toucher au code de production.

@export var faction: FactionData
## Bâtiment principal (posé sur la carte en début de partie).
@export var headquarters: BuildingData
## Unité constructrice, produite par les bâtiments où BuildingData.produces_builder.
@export var builder_squad: SquadData
## Bâtiments que l'unité constructrice pourra construire (système de construction à
## venir : vide pour l'instant).
@export var constructible_buildings: Array[BuildingData] = []
