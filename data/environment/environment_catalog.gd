class_name EnvironmentCatalog
extends Resource
## Liste de toutes les pièces du kit de décor (data/environment/<id>.tres).

@export var pieces: Array[EnvironmentPieceData] = []


func get_piece(id: StringName) -> EnvironmentPieceData:
	for piece in pieces:
		if piece.id == id:
			return piece
	return null


func by_category(category: EnvironmentPieceData.Category) -> Array[EnvironmentPieceData]:
	var result: Array[EnvironmentPieceData] = []
	for piece in pieces:
		if piece.category == category:
			result.append(piece)
	return result
