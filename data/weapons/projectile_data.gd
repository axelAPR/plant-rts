class_name ProjectileData
extends Resource
## Type de projectile : comportement en vol et apparence. Partagé par toutes les unités
## qui tirent ce projectile ; la vitesse et les dégâts viennent du tireur (UnitData),
## pour équilibrer chaque unité sans dupliquer les types.
##
## Première version : trajectoire directe, vitesse constante, sans gravité, sans
## guidage, sans explosion. Les comportements à venir (balistique, guidé, traversant,
## zone d'effet…) s'ajoutent à `Trajectory` et à `Projectile` sans toucher au reste.

enum Trajectory {
	## Ligne droite vers le point visé (anticipation du déplacement de la cible).
	DIRECT,
}

@export_group("Identité")
@export var id: StringName = &""
@export var display_name: String = ""

@export_group("Vol")
@export var trajectory: Trajectory = Trajectory.DIRECT
## Rayon (m) de collision du projectile, ajouté au rayon du corps des unités.
@export var radius: float = 0.08
## Portée maximale de vol, en multiple de la portée du tireur : au-delà, un projectile
## qui n'a rien touché disparaît.
@export var max_range_factor: float = 1.5

@export_group("Apparence")
## Couleur du projectile (rendu non éclairé, lisible de loin).
@export var color: Color = Color.WHITE
## Taille affichée (m) : diamètre, et longueur dans le sens du vol (> diamètre pour
## une épine, une balle, un laser…).
@export var visual_diameter: float = 0.16
@export var visual_length: float = 0.16
## Scène visuelle optionnelle (modèle, particules…) : non utilisée pour l'instant, le
## rendu par défaut (ProjectileRenderer) affiche une forme simple à la couleur du type.
@export var visual_scene: PackedScene
