# plantRTS — Suivi du projet

Avancement du travail. Les décisions validées (règles, valeurs, architecture) sont
dans `CLAUDE.md` ; ce fichier ne contient que l'état des tâches. Une tâche n'est
cochée qu'après vérification (test automatisé ou contrôle en jeu).

## En cours
- (rien)

## Problèmes connus
- [ ] Carte « Banlieue » : le décor ne bloque pas encore les unités (pas de navigation) ;
      elles traversent maisons, clôtures et bordure.
- [ ] Sol corrompu (base zombie) : violet proche de la couleur des anneaux zombies,
      lisibilité à vérifier en jeu avec des escouades.

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
- [ ] Emprises (`footprint_radius`) des zombies GW2 : valeurs actuelles gardées pour
      l'instant, mais les armes dépassent l'anneau (mesuré : All-Star 1,73 / 1,00 m,
      Z-Mech 1,96 / 1,60, Ingénieur 1,29 / 1,10, Super Brainz 0,97 / 0,70) ; à revoir.
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
- [x] Kit de décor : 91 modèles, catalogue, vitrine, diorama — `catalog_runner`,
      captures `capture_runner`.
- [x] Carte « Banlieue » (`world/maps/suburb/`, 320 × 320 m, sans symétrie, scène
      principale) : quartiers, 9 points de jeu, sol texturé à mélange, ciel cartoon
      visible de près — captures `capture_runner -- --only=suburb` (vue d'ensemble).
- [x] Routes courbes de la Banlieue (RoadNetwork / RoadPath / RoadJunction dans
      `world/environment/`) : 24 routes, 11 carrefours arrondis, 10 raquettes —
      `road_runner` (raccords, rayon ≥ 30 m, décor hors route), captures.
- [x] Modèles des 18 troupes (+ versions GW2 locales des plantes).
