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
- `assets/` — `audio`, `materials`, `models`, `shaders`, `textures`.
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

## Gameplay — À CONFIRMER
<!-- Déduit de l'arborescence, pas encore validé explicitement -->
- RTS en 3D, orienté escouades (`squads`), avec couvert (`cover`), capture de
  points (`capture`), économie, construction, brouillard de guerre et plusieurs
  factions.
- Pause tactique prévue.
