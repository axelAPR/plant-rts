class_name MoveOrderSettings
extends Resource
## Réglages des ordres de déplacement : détection de blocage, délais et choix des
## destinations libres. Partagés par tous les MoveOrder émis par un OrderSystem.

@export_group("Blocage")
## Délai (s) sans progression au-delà duquel l'escouade est considérée bloquée.
@export var stall_time: float = 3.0
## Rapprochement minimal (m) du centre de l'escouade vers sa destination pour
## compter comme une progression.
@export var min_progress: float = 0.5
## Réduction minimale (m) de l'écart de formation pour compter comme une progression
## pendant la reformation à l'arrivée.
@export var min_reform_progress: float = 0.1
## Fraction minimale de la vitesse de l'ancre quand des unités décrochent : l'ancre
## ne s'arrête jamais, les retardataires rattrapent.
@export_range(0.05, 1.0) var min_anchor_speed_ratio: float = 0.35
## Décélération (m/s²) de l'ancre à l'approche de la destination : la formation freine
## au lieu de s'arrêter net (sinon les unités dépassent leur place et reviennent).
@export var anchor_deceleration: float = 4.0

@export_group("Délai maximal")
## Un ordre dure au plus : temps de trajet × timeout_factor + timeout_margin (s).
@export var timeout_factor: float = 2.0
@export var timeout_margin: float = 10.0

@export_group("Destinations")
## true : une destination ne peut pas chevaucher une escouade à l'arrêt ni la
## destination d'un autre ordre (emplacement libre le plus proche). false : les
## escouades peuvent être superposées ; seules les escouades d'un même ordre de groupe
## se placent côte à côte.
@export var avoid_occupied_destinations: bool = false
## Écart minimal (m) entre les emprises de deux formations à l'arrêt.
@export var reservation_margin: float = 1.0
## Distance (m) maximale de recherche d'un emplacement libre autour de la cible.
@export var free_search_radius: float = 60.0
## Pas (m) de la recherche d'emplacement libre.
@export var free_search_step: float = 1.0
