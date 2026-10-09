class_name ProductionQueue
extends RefCounted
## File de production d'un bâtiment : escouades déjà payées (ressources et
## population réservées), produites une à la fois dans l'ordre. La première avance
## au tick physique ; à la fin de son temps, elle attend une sortie libre si besoin.

enum State { IDLE, PRODUCING, WAITING_FOR_EXIT }

var capacity: int
var items: Array[SquadData] = []
## Temps écoulé (s) sur l'escouade en tête de file.
var elapsed: float = 0.0
var state: State = State.IDLE


func _init(p_capacity: int) -> void:
	capacity = p_capacity


func is_empty() -> bool:
	return items.is_empty()


func is_full() -> bool:
	return items.size() >= capacity


func current() -> SquadData:
	return items[0] if not items.is_empty() else null


## Avancement (0..1) de l'escouade en tête de file.
func progress_ratio() -> float:
	var data := current()
	if data == null:
		return 0.0
	return clampf(elapsed / maxf(data.build_time, 0.001), 0.0, 1.0)


## Temps restant (s) pour l'escouade en tête de file.
func remaining_time() -> float:
	var data := current()
	return maxf(data.build_time - elapsed, 0.0) if data != null else 0.0
