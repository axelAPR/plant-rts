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
- `radius` (UnitData) = cercle centré sur le pivot contenant toute l'emprise au sol
  du modèle, armes comprises (arrondi au 0,05 m sup.). Règle : `formation_spacing`
  ≥ 2 × radius + 0,3 m. Exception : Pisto-pois conservé à 0,55 (emprise réelle 0,65).
- Troupes (`data/units/<id>.tres` + `<id>_squad.tres`) :

  | Troupe | id | Effectif | Colonnes | Espacement | Radius |
  |---|---|---|---|---|---|
  | Pisto-pois | peashooter | 6 | 3 | 1,8 | 0,55 |
  | Tournesol | sunflower | 4 | 2 | 1,8 | 0,60 |
  | Maïs | kernel_corn | 4 | 2 | 2,1 | 0,90 |
  | Cactus | cactus | 3 | 3 | 2,2 | 0,65 |
  | Rose | rose | 3 | 3 | 2,0 | 0,60 |
  | Chomper | chomper | 3 | 3 | 2,4 | 0,80 |
  | Citron | citron | 2 | 2 | 2,6 | 0,90 |
  | Torchwood | torchwood | 1 | 1 | 1,9 | 0,80 |
  | Zombie classique | browncoat | 8 | 4 | 2,0 | 0,85 |
  | Soldat | foot_soldier | 6 | 3 | 2,5 | 1,10 |
  | Ingénieur | engineer | 4 | 2 | 2,5 | 1,10 |
  | Scientifique | scientist | 4 | 2 | 2,1 | 0,90 |
  | Deadbeard | deadbeard | 3 | 3 | 2,9 | 1,30 |
  | All-Star | all_star | 3 | 3 | 2,4 | 1,00 |
  | Super Brainz | super_brainz | 2 | 2 | 2,4 | 0,70 |
  | Héros d'action des années 80 | action_hero_80s | 1 | 1 | 2,3 | 1,00 |
  | Z-Mech | z_mech | 1 | 1 | 3,5 | 1,60 |

  Déplacement identique pour tous (3,5 m/s, accél. 14, rotation 540°/s) : à équilibrer.
- Couches séparées : données (`data/units`, ressources `UnitData` / `SquadData`) ;
  simulation sans nœuds au tick physique (`UnitSimulation`, `Squad`, `Unit`) ;
  ordres (`gameplay/commands` : une sous-classe de `SquadOrder` par type) ;
  sélection et commandes (`player/`) ; affichage (`UnitRenderer`, en lecture seule).
- Formation pilotée par une ancre ; un ordre de groupe donne à chaque escouade sa
  propre destination, côte à côte.
- Générique (camp = entier) : le même code servira aux zombies.
- Tests : `tests/squad_test/` — `squad_test` (sélection, 2 escouades de Pisto-pois)
  et `all_troops_test` (une escouade par troupe, plantes camp 0 / zombies camp 1,
  tous camps sélectionnables : `SelectionController.team = -1`),
  chacun avec une scène manuelle et un runner automatisé.

## Gameplay — À CONFIRMER
<!-- Déduit de l'arborescence, pas encore validé explicitement -->
- RTS en 3D, orienté escouades (`squads`), avec couvert (`cover`), capture de
  points (`capture`), économie, construction, brouillard de guerre et plusieurs
  factions.
- Pause tactique prévue.
