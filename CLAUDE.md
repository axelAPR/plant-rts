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
- `data/` — définitions de données : `buildings`, `factions`, `units`, `weapons`.
- `gameplay/` — un sous-dossier par système : `ai`, `capture`, `combat`,
  `commands`, `construction`, `cover`, `economy`, `squads`, `units`.
- `player/` — logique propre au joueur.
- `ui/` — interface.
- `world/` — `maps`, `navigation`, `fog_of_war`.
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

## Modèles 3D — À CONFIRMER
- Tailles de référence (personnages, plantes, zombies, bâtiments) : à définir.

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
  | Tournesol | sunflower | 4 | 2 | 1,8 | 0,30 | 0,60 | 1,20 |
  | Maïs | kernel_corn | 4 | 2 | 2,1 | 0,30 | 0,90 | 1,50 |
  | Cactus | cactus | 3 | 3 | 2,2 | 0,35 | 0,65 | 1,50 |
  | Rose | rose | 3 | 3 | 2,0 | 0,60 | 0,60 | 0,80 |
  | Chomper | chomper | 3 | 3 | 2,4 | 0,45 | 0,80 | 1,50 |
  | Citron | citron | 2 | 2 | 2,6 | 0,50 | 0,90 | 1,60 |
  | Torchwood | torchwood | 1 | 1 | 1,9 | 0,55 | 0,80 | — |
  | Zombie classique | browncoat | 8 | 4 | 2,0 | 0,35 | 0,85 | 1,30 |
  | Soldat | foot_soldier | 6 | 3 | 2,5 | 0,40 | 1,10 | 1,70 |
  | Ingénieur | engineer | 4 | 2 | 2,5 | 0,35 | 1,10 | 1,80 |
  | Scientifique | scientist | 4 | 2 | 2,1 | 0,35 | 0,90 | 1,40 |
  | Deadbeard | deadbeard | 3 | 3 | 2,9 | 0,35 | 1,30 | 2,20 |
  | All-Star | all_star | 3 | 3 | 2,4 | 0,40 | 1,00 | 1,60 |
  | Super Brainz | super_brainz | 2 | 2 | 2,4 | 0,45 | 0,70 | 1,50 |
  | Héros d'action des années 80 | action_hero_80s | 1 | 1 | 2,3 | 0,40 | 1,00 | — |
  | Z-Mech | z_mech | 1 | 1 | 3,5 | 0,80 | 1,60 | — |

  Déplacement identique pour tous (3,5 m/s, accél. 14, rotation 540°/s) : à équilibrer.
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
- Générique (camp = entier) : le même code servira aux zombies.
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
  (départ à 0). Revenus supplémentaires (points de capture…) :
  `add_income_per_minute()` ; dépenses : `can_afford()` / `spend()` (coût = un
  montant par ressource).
- Affichage : `ResourceBar` (`ui/`), en haut au centre : pastille et nom à la couleur
  de la ressource, stock possédé, revenu par minute. Carte de test : les deux camps.
- Test : `tests/economy_test/economy_runner.gd`.

## Gameplay — À CONFIRMER
<!-- Déduit de l'arborescence, pas encore validé explicitement -->
- RTS en 3D, orienté escouades (`squads`), avec couvert (`cover`), capture de
  points (`capture`), économie, construction, brouillard de guerre et plusieurs
  factions.
- Pause tactique prévue.
