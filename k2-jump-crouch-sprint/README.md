# K2 Jump / Crouch / Sprint

Movimento "moderno" per il personaggio guidato in **KOTOR 2 (Steam/Aspyr 1.0.2.0)**: corsa veloce tenendo un tasto, postura accovacciata, rotolamento/salto mentre ci si muove. Tutto a runtime tramite [K2SE](../K2SE/) (nessun exe modificato; disinstallazione = cancellare due file).

**Stato (2026-09-02, sera):** design confermato da Renan; implementazione iniziata (infrastruttura K2SE e RE per il salto). Vedi `DESIGN.md` qui e il piano completo in [`../PIANO-DAZIONE-2026-09-02.md`](../PIANO-DAZIONE-2026-09-02.md) (Fasi 2–5).

## Cosa farà

| Feature | Tasto (default, configurabile) | Come funziona sotto |
|---|---|---|
| **Sprint** | `Left Shift` tenuto | moltiplica la velocità massima di guida del PC (`CSWPlayerControlCamRelative::GetMaxSpeed`, `0x00867B40`) — lo stesso valore che Force Speed scala; rampa di 0.25 s; off in combattimento |
| **Crouch** | `C` (toggle; il deploy sposta ActionLeft/Right sulle frecce) | imposta il bit "stealth" **lato client** del PC (`CSWCCreature+0x2EC` bit 0): animazioni `stealth`/`pausestl` e velocità ridotta, **senza** la meccanica stealth del server (niente XP, detection, cintura) |
| **Jump** | `Space` (il deploy sposta Pausa su `F9`; resta anche su Pause/Break) | **salto funzionale**: K2SE simula l'arco per ~0.9 s intercettando il commit di posizione del controller, valida traiettoria e atterraggio sul walkmesh (pareti no, casse basse sì, sporgenze ≤ 1 m, cadute ≤ 3 m) e consegna l'atterraggio all'engine |
| **Roll** | `Left Alt` | animazione **overlay** `diveroll` (già nel gioco) con breve impulso in avanti; in sprint diventa una scivolata |

## Limiti del salto

L'engine Odyssey è 2.5D: la quota viene dal walkmesh e non esiste aria. K2SE la simula per la durata del salto e riconsegna il personaggio all'engine all'atterraggio, che deve trovarsi su una faccia walkable. Quindi: altezza ~1 m, distanza ~2.5 m (3.5 in sprint), caduta ≤ 3 m, niente arrampicata né doppio salto; dove non c'è pavimento walkable il salto abortisce e si torna al punto di partenza.

## Requisiti

- KOTOR 2 Steam/Aspyr 1.0.2.0 (anche con patch 4GB/LAA).
- K2SE ≥ 0.2.0 (`version.dll` accanto a `swkotor2.exe`).
- `k2se_movement.ini` accanto all'exe (esempio in `PIANO-DAZIONE-2026-09-02.md`, Appendice C).

## Materiale in questa cartella

- `DESIGN.md` — decisioni di design e meccanismi (con indirizzi verificati).
- `docs/re/update_865830.asm` — disassembly completo del player controller update (2206 istruzioni).
- `docs/re/srv_appear_57FD00.asm` — loader server dell'appearance (raggi, driveaccl).
- (in arrivo) `override/` per la v1 del salto, `tools/` per il deploy.

## Crediti e licenza

MIT. Indirizzi ricavati dal disassembly di `swkotor2.exe` (K2SE, 2026); layout di riferimento KOTOR 1 dal database di [Kotor-Patch-Manager](https://github.com/LaneDibello/Kotor-Patch-Manager) (MIT, solo dati); semantica confermata leggendo [reone](https://github.com/seedhartha/reone) e [KotOR.js](https://github.com/KobaltBlu/KotOR.js). Nessun file del gioco è ridistribuito.
