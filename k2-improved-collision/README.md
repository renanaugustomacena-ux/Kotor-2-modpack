# K2 Improved Collision

Meno "incastri" in **KOTOR 2 (Steam/Aspyr 1.0.2.0)**: il PC non resta bloccato da compagni e NPC non ostili, i placeable più comuni non hanno collisioni più larghe del modello, lo scivolamento lungo i muri è più fluido. Due strati: **dati** (2DA e walkmesh dei placeable, nessuna DLL) e **runtime** (modulo di [K2SE](../K2SE/)).

**Stato (2026-09-02, sera):** definizione confermata; implementazione in avvio (Tier 0 con l'infrastruttura K2SE). Vedi `DESIGN.md` e il piano in [`../PIANO-DAZIONE-2026-09-02.md`](../PIANO-DAZIONE-2026-09-02.md) (Fase 6).

> ✅ Definizione confermata da Renan (2026-09-02): tutto quanto sopra **più** collisioni con ambiente (muri, spigoli) e pavimento (gradini, bordi, quota). I Tier 3 e 3b sono obbligatori.

## Livelli

| Tier | Cosa | Richiede |
|---|---|---|
| 0 | misurare: routine K2SE per leggere/scrivere i raggi di collisione di una creatura; log "stuck" | K2SE |
| 1 | **solo dati**: `appearance.2da` (`creperspace`/`perspace` di PC e party ridotti), walkmesh `PWK` più fedeli per i 10 placeable più frequenti | `build.py` + `override/` |
| 2 | runtime: raggio "morbido" verso creature non ostili, compagni che cedono il passo | K2SE |
| 3 | runtime: scivolamento multi-piano lungo muri e spigoli (stile Quake `PM_SlideMove`), anti-aggancio angoli | K2SE + RE (Q7) |
| 3b | runtime: pavimento — tolleranza gradini/bordi fra facce walkmesh, quota morbida, controllo affondamento | K2SE + RE |
| 4 | camera che non attraversa i muri (opzionale) | RE |

## Come funzionano le collisioni (in breve)

Ogni creatura ha in `appearance.2da` un raggio di **pathfinding** (`perspace`, 0.35 per gli umanoidi) e un raggio **creatura-creatura** (`creperspace`, 0.4). Il server li carica in `CSWSCreature+0x380 → CPathfindInformation` (`+0x08` creperspace, `+0x10` cameraspace, `+0x14` hitradius — verificato nel binario). Due creature collidono se la distanza è minore della somma dei raggi (confermato da KotOR.js `CollisionManager`). I placeable bloccano con il proprio walkmesh `PWK`.

## Materiale

- `DESIGN.md` — decisioni e meccanismi.
- `tools/perspace_audit.py` — distribuzione dei raggi in `appearance.2da` per categoria e proposta di patch (Tier 1).
- (in arrivo) `build.py` per patchare `appearance.2da`, `override/` con i PWK.

## Licenza

MIT. Nessun file del gioco è ridistribuito: `build.py` modifica la copia presente nell'installazione dell'utente.
