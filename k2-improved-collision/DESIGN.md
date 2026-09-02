# K2 Improved Collision — design

*2026-09-02. Prove in `../docs/2026-09-02-studio-movimento-collisioni.md` §3; piano in `../PIANO-DAZIONE-2026-09-02.md` Fase 6.*

## 1. Definizione (✅ confermata da Renan il 2026-09-02)

"Migliorare le collisioni" = ridurre i blocchi che non hanno senso di gioco:
1. compagni e NPC non ostili che fanno da muro nei corridoi;
2. casse, console, banchi con walkmesh (`PWK`) più larghi del modello;
3. spigoli e angoli che "agganciano" il PC durante la corsa (ambiente);
4. gradini e bordi fra facce walkmesh che bloccano o fanno sussultare, quota che scatta, piedi che affondano o galleggiano (pavimento);
5. (opzionale) camera che entra nei muri.

Restano intatte: le collisioni con gli **ostili** (il combattimento in mischia usa `hitdist`/posizionamento), porte chiuse, geometria delle stanze (`WOK`).

## 2. Dati verificati nel binario

- Colonne `appearance.2da`: `perspace` (pathfinding), `creperspace` (creatura-creatura), `hitradius`, `hitdist`, `cameraspace`, `height`. PC: 0.35 / 0.4 / 0.25 / 1 / – / 1.6. Party e commoner uguali (0.36–0.4 il creperspace di alcuni compagni).
- Loader server `0x0057FD00..0x00580200`: `[srv+0x380]+0x08 = creperspace`, `+0x10 = cameraspace`, `+0x14 = hitradius (fallback 1.0)`, `srv+0x11EC = driveaccl`; `perspace → +0x04` e `height` da confermare (F1.5).
- Indici colonna cache: `0x00A0FD9C` (CREPERSPACE), `0x00A0FDE4` (PERSPACE), `0x00A0FDD4` (HITRADIUS) → i consumatori client sono in `0x0085Axxx` (`CSWCCreatureAppearance::Load`).
- K1 (KPM) indica due callback sul client (`get_personal_radius_callback`, `get_creature_radius_callback` → `Global::GetPersonalRadius/GetCreatureRadius`) e un sistema di steering `CAvoidCreature`: da ritrovare in K2 (F1.6).

## 3. Tier 1 — solo dati

- `build.py` (schema di `k2-directional-movement/build.py`): estrae/legge `appearance.2da` presente (override → Workshop TSLRCM → BIF), applica `creperspace 0.4→0.25` e `perspace 0.35→0.25` ⚠️ alle righe `P_*` (PC) e `Party_NPC_*`, e opzionalmente ai commoner/civili (`Commoner_*`, `Czerka_*`, `N_*` non ostili per convenzione di label); non tocca creature grandi (`sizecategory` 4–5), droidi da combattimento, `hitdist`/`hitradius`. Rifiuta di scrivere se cambiano colonne inattese. `--install/--uninstall/--show`.
- I raggi si ricaricano quando la creatura viene caricata (nuova area / load): nessun effetto sui salvataggi, reversibile.
- PWK: audit con PyKotor (conteggio istanze per `.utp` nei `.git` dei moduli), 10 placeable peggiori ridisegnati con KotorBlender; verifica che gli oggetti restino attivabili (il walkmesh definisce anche le posizioni d'uso: `relative_use_position` in `CSWCollisionMesh`).

## 4. Tier 2 — runtime (K2SE)

- **Raggio morbido**: intercettare il punto in cui l'engine legge il raggio dell'*altra* creatura durante il test di collisione del PC (callback client se esiste in K2, altrimenti il lettore di `[pf+0x08]` individuato in F1.5) e restituire `r * SoftFactorFriendly` (0.5) se la creatura è amica/neutrale e nessuno dei due è in combattimento; `PlayerPassThroughParty=1` → 0 verso i compagni.
- **Cedimento**: se il PC preme contro un compagno per > `PartyYieldDelay` (0.4 s) fuori dal combattimento, il compagno riceve un `ActionMoveToLocation` di ~1 m perpendicolare alla direzione del PC, verso un punto walkable; una sola azione ogni 2 s (anti ping-pong).
- **Routine**: `K2SE_GetCreatureRadii`, `K2SE_SetCreatureRadii`, `K2SE_SetCollisionSoftFactor`.

## 5. Tier 3 — ambiente (muri, spigoli)

Dove il controller clippa la velocità contro il walkmesh (Q7, F1.7): fino a 4 iterazioni di clip lungo i piani incontrati (`overclip 1.001` come `PM_SlideMove`), senza azzerare la velocità quando il primo piano non è parallelo al movimento; micro-passo laterale negli angoli concavi stretti quando la velocità residua è < 10%. Vincolo assoluto: mai autorizzare una destinazione fuori dal walkmesh.

## 5b. Tier 3b — pavimento (gradini, bordi, quota)

Come il controller passa fra facce con Z diversa: introdurre una tolleranza di gradino (`StepTolerance=0.35 m`) sotto la quale il bordo non blocca; filtrare la Z del modello sui bordi per evitare sussulti (senza toccare la Z logica del server); misurare l'offset piedi–walkmesh in cinque aree e, se sistematico, correggere l'offset di rendering (solo client, opzionale). Diagnostica `edge-stall` nel log.

## 6. Diagnostica

- `stuck at (x,y,z) for N ms near <tag/appearance> d=…` quando la velocità richiesta è > 0 e lo spostamento reale ≈ 0.
- Banner con i raggi del PC e delle 3 creature più vicine (`[Debug] Banner=1`).
- Eventuale riattivazione del flag di debug `RENDER_PERSONAL_SPACE` (K1: disegna i cerchi) se esiste in K2.

## 7. Rischi specifici

- `creperspace` troppo piccolo → i compagni si sovrappongono nelle cutscene o si "accalcano" nelle porte; mitigazione: valori moderati (0.25), solo party/PC nel Tier 1.
- Il cedimento interferisce con gli script di follow durante scene scriptate → disattivo se il compagno ha un'azione non-follow in coda o se c'è un dialogo in corso.
