# K2 Jump / Crouch / Sprint — design

*2026-09-02, rev. 2 dopo le conferme di Renan: tasti Shift (sprint), C (crouch), Space (salto), Alt (roll); **salto funzionale**. Riferimenti: `../docs/2026-09-02-studio-movimento-collisioni.md` (prove) e `../PIANO-DAZIONE-2026-09-02.md` (piano, Fase 5 per il salto).*

## 1. Il modello che rende tutto semplice

Il PC da tastiera non usa il pathfinding: `CSWPlayerControlCamRelative::Update` (`0x00865830`) legge gli assi, li ruota nello spazio camera, integra con RK4 verso una velocità bersaglio e **scrive la posizione sulla creatura server**. La velocità bersaglio viene da `GetMaxSpeed` (`0x00867B40`), che ritorna `appearance.drivemaxspeed` (5.4 m/s) o la velocità stealth se il bit stealth client è acceso. L'animazione di corsa si sincronizza alla velocità reale (`driveanimrun_pc` metri per ciclo), quindi cambiare la velocità non produce pattinamento: è esattamente ciò che fa Force Speed.

Tre conseguenze:
1. **Sprint** = `GetMaxSpeed() * fattore` quando il tasto è premuto.
2. **Crouch** = accendere il bit stealth client (`word [CSWCCreature+0x2EC] & 1`) senza il flag server (`CSWSCreature+0x1120 & 1`): postura e velocità cambiano, la meccanica stealth no.
3. **Roll** = animazione overlay (`PlayOverlayAnimation`, routine 854) riprodotta direttamente sull'anim base del client.
4. **Jump** = K2SE simula l'aria: intercetta il commit di posizione del controller (`0x008679D3 → 0x00543F10`) e per ~0.9 s impone una parabola; l'atterraggio è validato sul walkmesh e consegnato all'engine con la sequenza di `JumpToLocation`.

## 2. Sprint

- **Hook**: redirezione delle tre `call 0x00867B40` (`0x0086603C`, `0x00867336`, `0x00867AC7`) verso `HookGetMaxSpeed(this)`; verifica dei byte `E8 rel32` prima di scrivere; ripristino al detach. Opzionale la stessa cosa per `GetAccel` (`0x00867ABC → 0x00867CA0`).
- **Stato**: `factor` interpolato linearmente in `RampSeconds` (default 0.25) fra 1.0 e `Factor` (default 1.6 ✅); `MaxTotalFactor` (2.5) limita la combinazione con Force Speed misurando il rapporto `orig / drivemaxspeed`.
- **Input**: `GetAsyncKeyState(VK)` risolto a runtime da `user32` (la DLL continua a importare solo KERNEL32), letto una volta per frame (contatore), solo se la finestra del gioco è in primo piano.
- **Esclusioni**: combattimento (`GetIsInCombat` sul PC, opzione), stealth server attivo, `walking` (B) attivo, controller disabilitato (dialoghi/GUI → l'hook non gira affatto).
- **Sterzo**: da valutare in S2/S3; opzione futura `TurnRateScale` (l'engine riduce già la prontezza con la velocità: `minturnrate` in `camerastyle.2da`).

## 3. Crouch

- **Meccanismo**: chiamare la funzione client che scrive il bit (contiene `0x00809E01`; firma da ricavare in F1.1) sul PC; piano B: riscrivere il bit ogni frame nel nostro update se il server lo resetta; piano C: hook dei lettori delle animazioni (`0x0077713F…`).
- **Cosa cambia**: animazioni `stealth` (riga 5) e `pausestl` (riga 9); velocità = `appearance+0x60` salvo `FEAT_STEALTH_RUN` (197) — opzione `SpeedFactor` per forzare un valore.
- **Cosa non deve cambiare**: `IsStealthed()` (server) resta 0; nessun XP stealth; nessuna detection; nessuna trasparenza (se il lettore grafico `0x008B9189` la applica, lo neutralizziamo quando il crouch è nostro).
- **Tasto**: `C` (toggle). Il gioco lega `C` ad *ActionRight* (`action281b`): il deploy sposta ActionLeft/Right sulle frecce (`Action281A=7`, `Action281B=8`) con backup dell'ini, oppure si fa dal menu Opzioni → Tasti; la DLL segnala il conflitto nel log se `C` risulta ancora legato.
- **Uscite**: sprint (`CancelCrouch=1`), salto (esce prima di saltare), combattimento (`ExitOnCombat=1`), transizione area, ripristino dopo dialogo.
- **Persistenza**: nessuna (stato client, non nel salvataggio).

## 4. Roll (Alt) e Jump funzionale (Space)

### 4.1 Roll
`animBase = 0x007ED830(client)`; `id = animBase->vtable[0xE0/4](0x290D, 1)`; `animBase->vtable[0x44/4](id)` — la catena esatta di `PlayOverlayAnimation` (`diveroll`, riga 567, overlay). Cooldown 1.0 s; `Boost=1.3` sul fattore velocità per 0.6 s (via `HookGetMaxSpeed`); roll in sprint = slide (sprint mantenuto).

### 4.2 Jump: il modello
L'engine non ha aria, quindi K2SE la simula per la durata dell'arco e poi restituisce il PC all'engine:

1. **Decollo** (Space, controller attivo, non in combattimento/stealth/crouch, `+0x1114` non immobile, non in roll, cooldown scaduto): salva `p0`, velocità orizzontale `v_h` = velocità di guida corrente limitata a `MaxDistance / T` (T ≈ 0.9 s), `v_z = sqrt(2·g·Height)` (Height 1.0 → 4.43 m/s).
2. **Aria** (ogni frame, dentro `HookCommitPosition(srv, vec)` che intercetta la `call 0x00543F10` a `0x008679D3`): `p(t) = p0 + v_h·t·dirAria + (v_z·t − ½·g·t²)·ẑ`; `dirAria` è la direzione di decollo con `AirControl=0.2` di sterzo; la stessa posizione va al client (commit `vtable+0x88`) così camera e modello seguono. L'input W/S non accelera in aria.
3. **Validazione** (al decollo e ogni frame): segmento `p0 → p(T)` contro le facce walkmesh con line-of-sight bloccante (pareti) → se interseca, il salto si accorcia o abortisce; atterraggio `(x,y)` deve avere una faccia walkable con `|Z_faccia − Z_parabola| ≤ LandTolerance` (0.5 m) oppure una faccia più in basso entro `MaxFall` (3 m) → si prolunga la caduta; salita ammessa fino a `MaxStepUp` (1 m).
4. **Atterraggio**: consegna all'engine con la sequenza del server per `JumpToLocation` (SetPosition + aggiornamento stanza/trigger) e ripristino dello stato normale; cooldown 0.4 s.
5. **Abort/recovery**: nessuna faccia valida → il PC torna a `p0` (riga `jump: aborted/recovered` nel log). Se dopo l'atterraggio la query walkmesh fallisce → teletrasporto a `p0`.

### 4.3 Cosa serve dall'RE (Fase 5 J0)
Le query walkmesh del server (walkable a (x,y) → Z e faccia; test segmento con materiali), la sequenza di `JumpToLocation`/`CutsceneMove`, l'eventuale punto in cui il server ri-applica la Z del PC fuori dal controller, e quale posizione segue la camera. Tutto elencato in `../PIANO-DAZIONE-2026-09-02.md` F5.0.x.

### 4.4 Animazione
v0: placeholder (`diveroll` overlay o posa congelata con velocità animazione 0); v1: animazione `jump` autoriale in `S_Male02` (KotorBlender), tre righe `animations.2da` overlay (`jump_start`, `jump_loop`, `jump_land`), riprodotte per codice o per nome.

### 4.5 Limiti dichiarati (nel README)
Altezza ~1 m, distanza 2.5 m (3.5 in sprint), caduta 3 m, atterraggio solo su walkmesh, niente arrampicata né doppio salto. Con questi limiti si superano casse basse, piccoli vuoti e sporgenze, e si scende da bordi; non si esce dall'area di gioco prevista se non dove esiste un pavimento walkable raggiungibile (possibile *sequence break*: scelta consapevole di Renan).

## 5. Sicurezza e osservabilità

- Ogni indirizzo passa dal CSV con provenienza e probe di fingerprint; nessuna scrittura senza verifica dei byte attesi.
- Ogni chiamata engine è dentro `__try/__except`; un fault disattiva la feature per la sessione e lascia una riga nel log con VA e registri.
- Log solo di **transizioni** (`sprint ON/OFF`, `crouch ON/OFF`, `roll`), mai per frame; traccia thinned con `K2SE_DIAGNOSTIC`.
- Banner opzionale `[Debug] Banner=1` per confrontare schermo e log (lezione della sessione 2026-08-29 di K2SE).

## 6. Alternative considerate

| Alternativa | Perché no |
|---|---|
| Scrivere `appearance+0x5C` (drivemaxspeed) | è condiviso da tutte le creature con la stessa appearance; va ripristinato ogni frame |
| `EffectMovementSpeedIncrease` da script su heartbeat | latenza di secondi, VFX blur di Force Speed, stato nel salvataggio |
| Modalità stealth vera per il crouch | XP stealth, detection, requisito cintura, trasparenza |
| `PlayAnimation(kneel)` per il crouch | non è looping-walk, ferma il movimento |
| Spostare la Z senza validare l'atterraggio | esce dal walkmesh: trigger, pathing, camera e salvataggi rotti — per questo l'atterraggio è validato e consegnato all'engine |
| Salto solo cosmetico | rifiutato da Renan: deve essere funzionale |
| Hook inline con trampolino | più byte, più rischio; le call-site sono tre e note |
| Riga nuova in `keymap.2da` | richiede il dispatcher azioni; v2 |
