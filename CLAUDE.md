# plantRTS — Mémoire du projet

Ce fichier contient les décisions validées du projet. Il est mis à jour à chaque
décision définitive (gameplay, architecture, technique, contraintes).
Pas d'informations temporaires ici.

## Technique
- Moteur : Godot 4.7, rendu Forward+, langage GDScript.
- Physique : Jolt Physics.
- Pilote de rendu Windows : D3D12.
- Fichiers en UTF-8, fins de ligne LF (voir `.editorconfig`, `.gitattributes`).

## Versionnement (Git)
- Dépôt Git, branche principale `main`, distant `origin` (GitHub).
- Vérifier `git status` avant toute modification importante.
- Ne jamais faire de `git push` sans confirmation explicite.

## Conventions de code
- Commentaires et documentation (`##`) en français ; identifiants en anglais.
- Typage statique systématique (`: float`, `-> void`, `:=`).
- Paramètres réglables exposés via `@export`, regroupés avec `@export_group`.
- Membres privés préfixés par `_`.
- Les entrées passent par des actions nommées de l'Input Map (jamais de touches
  codées en dur). Touches clavier en `physical_keycode` (indépendant AZERTY/QWERTY).

## Architecture (dossiers)
- `camera/` — caméra RTS.
- `core/` — systèmes transverses.
- `data/` — définitions de données : `buildings`, `environment` (catalogue du kit de
  décor), `factions`, `units`, `weapons`.
- `gameplay/` — un sous-dossier par système : `ai`, `capture`, `combat`,
  `commands`, `construction`, `cover`, `economy`, `squads`, `units`.
- `player/` — logique propre au joueur.
- `ui/` — interface.
- `world/` — `maps`, `navigation`, `fog_of_war`, `environment` (affichage du décor).
- `assets/` — `audio`, `materials`, `shaders`, `textures` ; modèles 3D dans
  `plants`, `zombies`, `buildings`, `environment` (voir « Modèles 3D ») ;
  `models` pour les modèles sans catégorie.
- `tests/` — tests.

## Caméra RTS (implémentée : `camera/rts_camera.gd`)
- Caméra orbitale : un nœud pivot au sol + une Camera3D enfant (yaw, pitch, distance).
- L'inclinaison dépend du zoom (plus rasante de près, plus plongeante de loin).
- Déplacement au clavier et aux bords de l'écran, relatif à l'orientation, plus
  rapide quand on est loin ; limité aux bornes de la carte.
- Fonctionne en temps réel, indépendamment de `Engine.time_scale`, et reste active
  pendant la pause (`PROCESS_MODE_ALWAYS`) → prévu pour une pause tactique.
- API publique : `zoom_by()`, `focus_on()`, `reset_view()`, `get_camera()`.

## Contrôles (Input Map)
- Déplacement : ZQSD (physique WASD) + flèches ; Shift = rapide.
- Rotation : A/E (physique Q/E) + glisser avec le bouton du milieu.
- Zoom : molette. Recentrer : Origine.
- `select` = clic gauche, `command` = clic droit.

## Modèles 3D (règles obligatoires sauf instruction explicite contraire)
Priorités pour chaque modèle, dans l'ordre : 1. lisibilité, 2. cohérence
artistique, 3. performance, 4. facilité d'intégration dans Godot, 5. détails.
Avant de créer un modèle, vérifier ceux déjà présents et rester cohérent avec eux.

### Direction artistique
- 3D stylisée, cartoon, low-poly propre ; jamais de photoréalisme.
- Référence : **Plants vs Zombies: Garden Warfare** — s'en rapprocher le plus
  possible (DA, personnages, proportions, couleurs), adapté à un RTS : même
  look, polycount réduit. Projet personnel et éducatif, jamais diffusé.
- Silhouettes très lisibles de loin ; formes simples, exagérées, reconnaissables.
- Pas de petits détails invisibles en jeu.

### Optimisation RTS
- Conçus pour afficher beaucoup d'unités simultanément.
- Polygones limités ; géométrie simple ; pas de subdivisions excessives.
- Matériaux simples et peu nombreux ; pas d'effets coûteux inutiles.
- Prévoir des LOD pour les unités éloignées.

### Échelle, pivot, orientation
- Échelle cohérente entre toutes les unités (1 unité Blender = 1 m = 1 unité Godot).
- Pivot (origine) au sol, au centre de rotation logique de l'unité.
- Blender est Z-up, Godot Y-up : l'export glTF convertit (option « +Y Up »).
  Le modèle regarde vers -Y dans Blender → +Z dans Godot (`Vector3.MODEL_FRONT`).
- Transformations appliquées avant export (rotation 0, échelle 1).

### Matériaux
- Simples, compatibles Godot (Principled BSDF → StandardMaterial3D via glTF).
- Couleurs franches et lisibles ; textures seulement si réel avantage.
- Cohérence visuelle entre les factions.

### Animation
- Simples, lisibles à distance depuis la caméra RTS.
- Minimum quand pertinent : `Idle`, `Walk`, `Attack`, `Hit`, `Death`.

### Export Godot
- Format : `.glb`, rangé par catégorie dans `assets/plants/`, `assets/zombies/`,
  `assets/buildings/`, `assets/environment/`.
- Avant export, vérifier dans Blender : dimensions, orientation, pivot,
  matériaux, animations.
- Ne jamais écraser un modèle existant sans vérifier son utilisation dans le projet.

### Modèles issus de Garden Warfare 2
- Source : `blender/plants imp/` (maillages et textures extraits du jeu, fournis par
  l'utilisateur). Contenu sous droits d'EA/PopCap : usage personnel uniquement.
- Le dépôt GitHub est **public** : rien de ce qui en est extrait ou dérivé n'est
  commité. Sources et résultats sont dans des dossiers ignorés par Git
  (`blender/plants imp/`, `blender/gw2/`, `assets/gw2/`).
- Le jeu les utilise en local via `UnitData.local_visual_path` : modèle prioritaire
  s'il existe sur la machine, sinon `visual_scene` (modèle publié, procédural).
- Tournesol : `blender/scripts/sunflower_gw2.py` → `assets/gw2/plants/sunflower.glb`,
  mis à l'échelle (1,45 m), pivot au sol, polygones réduits (≈ 5 400 triangles),
  pièces `Body`, `Arms`, `Head` (pivot au cou), textures de couleur seules réduites à
  512 px (exception à la règle « textures seulement si avantage réel » : elles
  portent le rendu du modèle d'origine).
- Autres plantes : `blender/scripts/plants_gw2.py` (outils : `gw2_lib.py`, dont un
  lecteur `.dae`) → `assets/gw2/plants/<id>.glb`. Hauteur de l'ancien modèle, pivot
  au sol, ≈ 5 000 triangles (Maïs 7 600, Torchwood 6 600), bras abaissés depuis la
  pose de référence, textures de couleur 512 px. Sources : GW2, sauf Citron (Battle
  for Neighborville), Chomper (cartes AR mobiles), Torchwood (Giga Torchwood). Le
  Pisto-pois garde l'animation `Walk`.

## Tailles de référence (unités et décor)
Mesurées sur les modèles publiés (`assets/plants`, `assets/zombies`) ; le décor est
dimensionné à partir d'elles. 1 unité = 1 m.

| Élément | Taille | Remarque |
|---|---|---|
| Pisto-pois | 1,26 m de haut | plante d'infanterie |
| Zombie classique | 2,04 m de haut | zombie d'infanterie |
| Z-Mech | 3,57 m de haut | plus grande unité |
| Porte | 1,1 × 2,3 m | un zombie y passe |
| Maison de plain-pied | soubassement 0,35 m + murs 2,8 m ; faîtage ≈ 5,2 m ; cheminée ≤ 6 m | maisons basses |
| Maison à étage | faîtage ≤ 8 m | |
| Clôture à piquets | 1,0 m (poteau 1,15 m) | couvert léger |
| Haie | 1,2 m (bordure de carte : 3 m) | |
| Muret de pierre | 1,1 m | couvert lourd |
| Grand arbre | ≈ 6 m ; tronc dégagé jusqu'à 2,6 m ; couronne ≤ 4 m de diamètre | |
| Route | tuile 8 × 8 m : chaussée 6 m + deux trottoirs de 1 m (0,15 m) | |
| Voiture (berline) | 4,0 × 1,9 × 1,45 m | emprise 4 × 2 m |
| Point de jeu | disque de 5 m de rayon ; mât 4,6 m | |

- Grille du décor : emprises au sol multiples de 2 m ; segments modulaires de 4 m le
  long de X, centrés sur leur pivot ; tuiles de route de 8 × 8 m.

## Kit de décor (implémenté : 91 modèles)
- Procédural, publiable : scripts `blender/scripts/environment/<famille>.py`
  (`ground`, `buildings`, `cover_heavy`, `cover_light`, `vegetation`, `props`,
  `gameplay`, `borders`), bibliothèque `blender/scripts/env_lib.py` (s'appuie sur
  `prts_lib.py`). `.blend` dans `blender/environment/<catégorie>/`, `.glb` dans
  `assets/environment/<catégorie>/<id>.glb`. Lancement :
  `blender -b --python blender/scripts/environment/<famille>.py -- [ids…] [--render]` ;
  planche de contrôle d'une famille : `environment/sheet.py`.
- Lisibilité d'abord : décor un peu moins saturé que les unités (textures désaturées
  de 12 %), verts du décor plus bleus et plus sombres que ceux des plantes jouables,
  maisons basses, arbres au tronc dégagé.
- Matériaux texturés, communs à tout le kit (`env_lib.TEXTURES`, noms `Env_*`),
  4 au plus par modèle ; textures 512 px intégrées aux `.glb`. Sources dans
  `blender/environment/textures/` : pack peint à la main fourni par l'utilisateur
  (`pack_*.png`, copié de `blender/Texture imp/`) et textures générées dans le même
  style (`environment/textures_gen.py` : bruit périodique posterisé en 5 nuances ;
  variantes de couleur des bardages, tuiles, crépis, carrosseries). Atlas : `Env_Trim`
  (bois peint blanc, rouge, bois naturel, vitre) et `Env_Paint` (8 peintures vives) ;
  une face prend une région avec le nom « Env_Trim:glass ». UV automatiques en mètres
  (densité constante). Couleurs d'équipe et de ressources des points de jeu : unies.
- Budgets : petit décor ≤ 300 triangles, pièce moyenne ≤ 1 500, bâtiment ≤ 3 000.
  Dessous et faces cachées supprimés. Contrôles à chaque export (`env_lib.check`) :
  budget, matériaux, transformations, sol, emprise.
- Raccords : segments de 4 m (bordures : 8 m) de -L/2 à +L/2 le long de X ; angles et
  extrémités sur 2 × 2 m, bras de 1 m vers -X et +Z (Godot) depuis le centre — le
  segment voisin est centré à 3 m (bordures : 5 m) ; piquets et barreaux sur une
  grille globale (pas régulier d'une pièce à l'autre). Routes : entrées au milieu des
  bords de tuile, ligne médiane en tirets au pas de 4 m.
- Points de jeu (`capture_point`, `resource_point_primary/secondary/tertiary`) : disque
  de 5 m ; objets `State_Neutral`, `State_Plants`, `State_Zombies`, `Pole`, `Flag`
  (pivots à la base). Silhouette par ressource (structure ≈ 3 / 2 / 1 m) et anneau
  à la couleur de la ressource du camp (data/factions) ; état neutre sous bâche.
  `PointStateDisplay` (`world/environment/`) n'affiche qu'un état (affichage seul).
- Catalogue `data/environment/` : `EnvironmentPieceData` par modèle (id, nom affiché,
  catégorie, scène, emprise rectangle ou rayon, hauteur mesurée, bloque le
  déplacement / la vue, couvert aucun / léger / lourd, ressource) et
  `environment_catalog.tres`, générés par `environment/catalog.py` (Python seul).
  Données seulement : navigation, couvert et capture ne les lisent pas encore.
- Scènes `world/maps/kit_showcase` (toutes les pièces par catégorie, points dans leurs
  trois états, unités pour l'échelle) et `world/maps/kit_demo` (diorama de 80 × 80 m),
  générées par `environment/scenes_gen.py` (dans un `.tscn`, Transform3D s'écrit ligne
  par ligne). Captures : `tests/environment_test/capture_runner.gd` (fenêtré) →
  `tests/environment_test/captures/`.

## Escouades (implémenté : prototype)
- Sélection et ordres par escouade, jamais par unité isolée.
- Effectif et formation propres à chaque type d'escouade (`SquadData` : `unit_count`,
  `formation_columns`, `formation_spacing`) ; ne jamais supposer un effectif fixe.
- Deux rayons par unité (UnitData), arrondis au 0,05 m supérieur :
  - `radius` = **corps** (tronc, pieds ; pour une plante sans tronc, le bulbe de la
    tête), sans bras, armes, feuilles, pétales, cape ni épines. Sert aux collisions
    et à l'évitement.
  - `footprint_radius` = emprise visuelle complète, armes comprises. Sert à l'anneau
    de sélection, au clic et à l'emprise des formations (réservation des destinations).
  - Règle : `formation_spacing` ≥ 2 × footprint_radius + 0,3 m (exception : Pisto-pois,
    0,55 pour une emprise réelle de 0,65). Passage entre deux voisins d'une formation
    = espacement − 2 × radius.
- Troupes (`data/units/<id>.tres` + `<id>_squad.tres`) :

  | Troupe | id | Effectif | Colonnes | Espacement | radius | footprint | Passage |
  |---|---|---|---|---|---|---|---|
  | Pisto-pois | peashooter | 6 | 3 | 1,8 | 0,35 | 0,55 | 1,10 |
  | Tournesol | sunflower | 5 | 3 | 1,8 | 0,30 | 0,60 | 1,20 |
  | Maïs | kernel_corn | 4 | 2 | 2,1 | 0,30 | 0,90 | 1,50 |
  | Cactus | cactus | 4 | 2 | 2,2 | 0,35 | 0,65 | 1,50 |
  | Rose | rose | 4 | 2 | 2,0 | 0,60 | 0,60 | 0,80 |
  | Chomper | chomper | 4 | 2 | 2,4 | 0,45 | 0,80 | 1,50 |
  | Citron | citron | 1 | 1 | 2,6 | 0,50 | 0,90 | — |
  | Torchwood | torchwood | 3 | 3 | 1,9 | 0,55 | 0,80 | 0,80 |
  | Zombie classique | browncoat | 8 | 4 | 2,0 | 0,35 | 0,85 | 1,30 |
  | Soldat | foot_soldier | 6 | 3 | 2,5 | 0,40 | 1,10 | 1,70 |
  | Ingénieur | engineer | 5 | 3 | 2,5 | 0,35 | 1,10 | 1,80 |
  | Scientifique | scientist | 4 | 2 | 2,1 | 0,35 | 0,90 | 1,40 |
  | Imp | imp | 8 | 4 | 1,4 | 0,25 | 0,45 | 0,90 |
  | Deadbeard | deadbeard | 4 | 2 | 2,9 | 0,35 | 1,30 | 2,20 |
  | All-Star | all_star | 4 | 2 | 2,4 | 0,40 | 1,00 | 1,60 |
  | Super Brainz | super_brainz | 3 | 3 | 2,4 | 0,45 | 0,70 | 1,50 |
  | Héros d'action des années 80 | action_hero_80s | 4 | 2 | 2,3 | 0,40 | 1,00 | 1,50 |
  | Z-Mech | z_mech | 1 | 1 | 3,5 | 0,80 | 1,60 | — |

  Déplacement identique pour tous (`move_speed` 3,5 m/s, accél. 14, rotation 540°/s) :
  à équilibrer. Imp : modèle provisoire en formes simples
  (`assets/zombies/imp_placeholder.tscn`), à remplacer par un vrai modèle.
- Couches séparées : données (`data/units`, ressources `UnitData` / `SquadData`) ;
  simulation sans nœuds au tick physique (`UnitSimulation`, `Squad`, `Unit`) ;
  ordres (`gameplay/commands` : une sous-classe de `SquadOrder` par type) ;
  sélection et commandes (`player/`) ; affichage (`UnitRenderer`, en lecture seule).
- Formation pilotée par une ancre ; un ordre de groupe donne à chaque escouade sa
  propre destination, côte à côte, sur plusieurs rangs au-delà de `max_line_width`
  (`OrderSystem`, 40 m par défaut).
- Formations organiques : la grille (`formation_columns`, `formation_spacing`) est
  décalée par rang, courbée et bruitée (`SquadData.formation_irregularity`, 0,3 de
  l'espacement), chaque unité ayant sa propre orientation au repos
  (`formation_yaw_jitter_degrees`, 14°). Écart minimal entre deux emplacements :
  max(2 × radius + 0,3 ; espacement × (1 − irrégularité)). Chaque escouade tire une
  nouvelle variante à chaque ordre de déplacement ; tirage déterministe (graine =
  id de l'escouade + numéro de variante).
- Superposition autorisée : des escouades alliées peuvent recevoir la même
  destination, ou une destination sur une escouade à l'arrêt. Option
  `MoveOrderSettings.avoid_occupied_destinations` (désactivée) pour imposer des
  destinations libres (`FormationSpace` : emprise = rectangle orienté, marge 1 m).
  Le menu DEV fait toujours apparaître les troupes sur des emplacements libres.
- Pas de course dans le vide : au repos, une unité qui ne se rapproche plus de son
  emplacement pendant 1 s (occupé) reste sur place (`Unit.holding`) ; elle le
  retente au plus tôt 3 s après, s'il est libre, et le reprend à chaque nouvel ordre.
- Contacts entre unités (`UnitSimulation`) : séparation douce entre toutes ;
  contournement latéral des unités des autres escouades par une unité en marche
  (face à face : chacune passe à sa droite) ; correction dure (aucun recouvrement)
  dans une même escouade, entre ennemis, et entre alliés seulement si leurs deux
  escouades sont à l'arrêt. Une unité à l'arrêt ne se laisse pas pousser par un
  ennemi en mouvement.
- Un ordre de déplacement se termine toujours (`MoveOrder`, réglages
  `MoveOrderSettings`) : l'ancre garde une vitesse minimale (35 %) et les
  retardataires rattrapent ; sans progression du centre pendant `stall_time` (3 s),
  l'escouade s'arrête en formation à l'emplacement le plus proche hors des emprises
  ennemies ; arrivée = écart < 0,3 m et unités posées (< 0,5 m/s) ; la reformation
  s'arrête aussi si elle ne progresse plus ; délai maximal = trajet × 2 + 10 s.
- Générique (camp = entier) : le même code sert aux plantes et aux zombies.
- Couleur des anneaux, du numéro et du trajet = couleur de la faction
  (`FactionData.unit_color`) : vert pour les plantes, violet pour les zombies.
- Menu DEV (`ui/dev_menu.gd`, sous la barre de ressources) : « Toutes les troupes »,
  un bouton par troupe rangé par camp (plantes au sud du point visé, zombies au nord,
  sur un emplacement libre), « Tout supprimer ». Apparitions gratuites, hors
  production et population.
- Tests : `tests/squad_test/` — `squad_test` (sélection, 2 escouades de Pisto-pois)
  et `all_troops_test` (une escouade par troupe, plantes camp 0 / zombies camp 1,
  tous camps sélectionnables : `SelectionController.team = -1`),
  chacun avec une scène manuelle et un runner automatisé ; `traffic_runner` (sans
  scène : croisements, traversées, destinations communes, charge de 150 escouades,
  mur ennemi, superposition). Lancer les runners en `--headless` (en fenêtré, la vraie souris peut
  fausser les clics simulés) ; captures avec `-- --screenshots=<dossier>`, fenêtré.

## Économie (implémenté : base)
- Trois ressources, même fonctionnement pour les deux camps ; seuls les noms et
  couleurs changent (`data/factions/` : `FactionData`, `plants.tres`, `zombies.tres`) :

  | Ressource | Plantes | Zombies | Revenu de base |
  |---|---|---|---|
  | Principale (effectifs, « manpower ») | Soleil (jaune) | Cerveaux (rose) | +200 / min |
  | Secondaire | Engrais (vert) | Engrenages (gris acier) | +5 / min |
  | Tertiaire | Terre (brun) | Pesticides (vert acide) | +0 / min |

- Simulation : `TeamEconomy` (stocks et revenus d'un camp, sans nœud) ; `Economy`
  (nœud, une `TeamEconomy` par camp indexée par numéro de camp, avancée au tick
  physique → mise en pause avec le jeu). Revenus et stocks de départ en `@export`
  (départ : 500 / 50 / 0 pour chaque camp). Revenus supplémentaires (points de capture…) :
  `add_income_per_minute()` ; dépenses : `can_afford()` / `spend()` (coût = un
  montant par ressource).
- Affichage : `ResourceBar` (`ui/`), en haut au centre : pastille et nom à la couleur
  de la ressource, stock possédé, revenu par minute. Carte de test : les deux camps.
- Rôle des ressources : principale = production des unités ; secondaire = unités
  spécialisées et lourdes ; tertiaire = ressource rare, contenu avancé.
- Test : `tests/economy_test/economy_runner.gd`.

## Production et population (implémenté : base, sans interface)
- Coût et population par **escouade entière** (`SquadData` : `primary_resource_cost`,
  `secondary_resource_cost`, `tertiary_resource_cost`, `population_cost`) : un
  Pisto-pois occupe 6, pas 6 × 6.
- `ProductionSystem.produce()` (`gameplay/economy/`) : vérifie, dans l'ordre,
  ressource principale, secondaire, tertiaire, puis population ; tout ou rien (si une
  condition manque : rien retiré, rien ajouté, aucune escouade). Sinon : paie, occupe
  la population, crée l'escouade.
- Population (`TeamEconomy.population_used` / `population_cap`) : maximum 100 par
  camp par défaut (`Economy.population_cap`, valeur provisoire, non fixée par le
  design) ; libérée quand l'escouade est détruite (dernier membre mort), pas à chaque
  membre.
- Test : `tests/production_test/production_runner.gd`.

## Combat (implémenté : première version)
- Statistiques d'un membre dans `UnitData` : `member_hp`, `damage_per_shot` (dégâts
  d'UN tir réussi, pas un DPS), `accuracy` (0 à 1, bornée), `attack_cooldown`,
  `attack_range` (mesurée jusqu'au bord du corps de la cible), `projectile`
  (`ProjectileData`, null = mêlée), `projectile_speed`, `faction`. Unité individuelle
  = escouade d'un seul membre.
- HP **individuels** : chaque membre a ses HP, sa cible, sa cadence et ses jets ;
  jamais de réserve commune. À 0 HP, le membre est retiré de la simulation
  (`UnitSimulation.remove_unit`) : il ne tire plus et ne compte plus ; escouade sans
  membre détruite (`squad_destroyed`).
- `CombatSystem` (`gameplay/combat/`, tick physique, après la simulation) : cible
  valide (vivante, ennemie, à portée) → cadence écoulée → tir. Les dégâts ne sont
  jamais appliqués au tir :
  - à distance : un `Projectile` réel vole en ligne droite, à vitesse constante, vers
    le point où sera la cible (anticipation, pas de guidage) ; son trajet est testé
    à chaque tick contre le corps des ennemis (cylindre `radius` × `hit_height`).
    À l'impact : cible encore valide → jet de précision → dégâts si réussi →
    projectile détruit. Ne touche jamais son camp (alliés, tireur) ; un ennemi sur la
    trajectoire peut intercepter le tir. Cible morte avant l'impact → projectile
    détruit, sans dégâts. Rien touché → disparaît à 1,5 × la portée ;
  - mêlée (Chomper, Super Brainz) : pas de projectile ; jet de précision au coup.
- Un jet de précision par tir, jamais `dégâts × effectif × précision`.
- Dégâts via `DamageContext` → `CombatSystem.resolve_damage()` : point d'entrée des
  règles à venir (armure, couvert, distance, buffs…), non implémentées.
- Ciblage : chaque membre tire sur l'ennemi le plus proche à portée, même en marche
  (sans malus) ; `AttackOrder` (clic droit sur un ennemi) : approche à 80 % de la
  portée (au contact en mêlée), tir prioritaire sur l'escouade visée, fin quand elle
  est détruite. Délai de réaction aléatoire (≤ 0,3 s) avant le premier tir.
- Types de projectiles : `data/weapons/` (`ProjectileData` : trajectoire, rayon de
  collision, couleur, taille). Affichage : `ProjectileRenderer` (MultiMesh).
- Roster (première base d'équilibrage théorique, ne pas modifier sans décision) :

  | Troupe | HP / membre | Dégâts | Précision | Cadence (s) | Portée (m) | Projectile (m/s) | Coût | Population |
  |---|---|---|---|---|---|---|---|---|
  | Pisto-pois | 100 | 18 | 0,75 | 1,2 | 25 | 30 | 300 / 0 / 0 | 6 |
  | Tournesol | 80 | 8 | 0,70 | 1,5 | 20 | 25 | 350 / 0 / 0 | 5 |
  | Cactus | 75 | 75 | 0,90 | 2,5 | 45 | 50 | 400 / 5 / 0 | 4 |
  | Chomper | 180 | 70 | 0,85 | 2,0 | 3 | mêlée | 450 / 10 / 0 | 8 |
  | Maïs | 150 | 55 | 0,75 | 1,5 | 28 | 30 | 500 / 15 / 0 | 8 |
  | Rose | 100 | 20 | 0,80 | 1,4 | 30 | 35 | 450 / 10 / 0 | 5 |
  | Citron | 2000 | 100 | 0,80 | 1,8 | 35 | 35 | 800 / 25 / 0 | 12 |
  | Torchwood | 500 | 65 | 0,70 | 1,3 | 20 | 25 | 900 / 30 / 5 | 12 |
  | Soldat | 100 | 18 | 0,75 | 1,2 | 28 | 30 | 300 / 0 / 0 | 6 |
  | Scientifique | 90 | 10 | 0,70 | 1,5 | 20 | 25 | 350 / 0 / 0 | 5 |
  | Ingénieur | 90 | 12 | 0,70 | 1,5 | 22 | 25 | 300 / 5 / 0 | 5 |
  | Imp | 50 | 10 | 0,65 | 1,0 | 18 | 25 | 250 / 0 / 0 | 5 |
  | All-Star | 300 | 50 | 0,70 | 1,6 | 22 | 25 | 550 / 15 / 0 | 10 |
  | Deadbeard | 80 | 75 | 0,90 | 2,8 | 50 | 55 | 400 / 5 / 0 | 4 |
  | Héros d'action des années 80 | 110 | 45 | 0,80 | 1,3 | 35 | 35 | 500 / 15 / 0 | 6 |
  | Super Brainz | 500 | 90 | 0,85 | 1,8 | 3 | mêlée | 750 / 25 / 0 | 10 |
  | Z-Mech | 2400 | 120 | 0,75 | 2,0 | 30 | 30 | 900 / 30 / 5 | 14 |

  Zombie classique : hors roster (100 HP, pas d'attaque, coût 0) en attendant ses
  valeurs. Effectifs : voir le tableau des troupes (section Escouades).
- Panneau de débogage (`ui/unit_info_panel.gd`, bas à gauche) : escouade
  sélectionnée — nom, faction, membres vivants et HP de chacun, dégâts, précision,
  cadence, portée, projectile, coût, population.
- Carte de test : `CombatSystem`, `ProjectileRenderer`, `ProductionSystem`,
  `UnitInfoPanel` ; la scène `all_troops_test` n'a pas de combat (tests de
  déplacement).
- Test : `tests/combat_test/combat_runner.gd` (HP individuels, salves, cadence,
  précision, dégâts, projectiles, tir allié, cible morte, portée, unités
  individuelles, mêlée, ordre d'attaque, bataille) ; capture avec
  `-- --screenshots=<dossier>`, fenêtré.

## Gameplay — À CONFIRMER
<!-- Déduit de l'arborescence, pas encore validé explicitement -->
- RTS en 3D, orienté escouades (`squads`), avec couvert (`cover`), capture de
  points (`capture`), économie, construction, brouillard de guerre et plusieurs
  factions.
- Pause tactique prévue.
