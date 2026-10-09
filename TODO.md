# plantRTS — Suivi du projet

Avancement du travail. Les décisions validées (règles, valeurs, architecture) sont
dans `CLAUDE.md` ; ce fichier ne contient que l'état des tâches. Une tâche n'est
cochée qu'après vérification (test automatisé ou contrôle en jeu).

## En cours
- (rien)

## Problèmes connus
- [ ] Buissons `bush_a` et `bush_b` : flottent au-dessus du sol (bas à 0,14 m et
      0,21 m) ; signalé par `tests/environment_test/catalog_runner.gd`.
      Source : `blender/scripts/environment/vegetation.py` (`_bush`).

## À faire
Systèmes prévus (dossiers créés, encore vides) :
- [ ] Navigation (`world/navigation`) : le décor ne bloque pas encore le déplacement
      (le catalogue indique `blocks_movement`, non lu).
- [ ] Couvert (`gameplay/cover`) : `cover` du catalogue non lu ; à brancher sur
      `CombatSystem.resolve_damage()`.
- [ ] Capture des points (`gameplay/capture`) : points de jeu modélisés, revenu prévu
      via `TeamEconomy.add_income_per_minute()`.
- [ ] Brouillard de guerre (`world/fog_of_war`) : `blocks_vision` du catalogue non lu.
- [ ] Construction et bâtiments (`gameplay/construction`, `data/buildings`).
- [ ] IA (`gameplay/ai`).
- [ ] Pause tactique (la caméra y est déjà prête).
- [ ] Interface de production (aujourd'hui : `ProductionSystem` sans interface, menu DEV).

Contenu et équilibrage :
- [ ] Imp : remplacer le modèle provisoire (`assets/zombies/imp_placeholder.tscn`).
- [ ] Zombie classique : valeurs de combat (hors roster pour l'instant).
- [ ] Vitesses de déplacement par troupe (toutes à 3,5 m/s, à équilibrer).
- [ ] Plafond de population (100, valeur provisoire).
- [ ] LOD des unités éloignées (règle des modèles 3D, non fait).

## Fait (vérifié)
Détails et règles dans les sections correspondantes de `CLAUDE.md`.
- [x] Caméra RTS — vérification manuelle en jeu seulement (pas de test automatisé,
      choix assumé).
- [x] Escouades : sélection, ordres, formations, trafic — `squad_test_runner`,
      `all_troops_runner`, `traffic_runner`.
- [x] Économie et barre de ressources — `economy_runner`.
- [x] Production et population (sans interface) — `production_runner`.
- [x] Combat, projectiles, précision, mêlée, ordre d'attaque — `combat_runner`.
- [x] Kit de décor : 91 modèles, catalogue, vitrine, diorama — `catalog_runner`
      (sauf problème connu ci-dessus), captures `capture_runner`.
- [x] Modèles des 18 troupes (+ versions GW2 locales des plantes).
