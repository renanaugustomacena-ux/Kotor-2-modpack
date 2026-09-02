# Studio: movimento (sprint / crouch / jump) e collisioni in KOTOR 2 — 2026-09-02

*Base: swkotor2.exe Steam/Aspyr 1.0.2.0 (TimeDateStamp 0x5603005D), K2SE allo stato del 2026-08-30 (12 routine provate in gioco), reone (clone del 2026-09-02), KotOR.js (clone del 2026-09-02), database Kotor-Patch-Manager (KPM) locale, libreria personale `personal-resources`, libreria mod Skyrim `D:\mods` (1960 mod).*

Ogni indirizzo/offset qui sotto è marcato:
- **[V]** verificato oggi leggendo il binario (disassembly capstone su `swkotor2.exe.pre-laa-backup`);
- **[K1]** preso dall'oracolo strutturale KPM `kotor1_0_3.db` (KOTOR 1): utile come ipotesi di layout, **non** vale come indirizzo K2;
- **[H]** ipotesi da confermare (in gioco o con ulteriore disassembly).

Strumenti usati (ora in `K2SE/tools/re/`): `strxref_ci.py`, `dwxref.py`, `dispscan.py`, `funcdump.py`. Disassembly completi in `k2-jump-crouch-sprint/docs/re/`.

---

## 0. Sintesi in dieci righe

1. **Non serve inventare un sistema di movimento**: il player controller `CSWPlayerControlCamRelative` guida direttamente la creatura server con un integratore RK4; la velocità massima arriva da una funzione a sé (`0x00867B40` [V]) chiamata da tre punti. **Sprint = moltiplicare quel valore quando un tasto è premuto.** Il gioco fa già la stessa cosa per Force Speed e per il walk-modifier (tasto B, `×0.5` [V]).
2. **Il crouch esiste già come postura**: le animazioni `stealth` (camminata accovacciata) e `pausestl` (idle accovacciato) sono in `animations.2da` (righe 5 e 9) e nei supermodel `S_Male02`/`S_Female03`. Lato client la scelta di quelle animazioni dipende da un bit: `word [CSWCCreature+0x2EC] & 1` [V], con **un solo scrittore** nell'exe (`0x00809E01` [V]). Crouch = impostare quel bit senza attivare la modalità stealth del server (`CSWSCreature+0x1120 & 1` [V]).
3. **Il salto non esiste** (niente fisica verticale, niente animazione). Ma l'engine ha `PlayOverlayAnimation` (routine 854, handler `0x0068F440` [V]): un'animazione **overlay** si sovrappone al movimento. `diveroll` (riga 567, overlay=1, costante `ANIMATION_FIREFORGET_DIVE_ROLL=123`) è subito usabile come "roll/dodge"; un vero "jump" richiede un'animazione nuova nel supermodel (KotorBlender) + riga 2DA overlay.
4. **Le collisioni fra creature** usano i raggi `perspace`/`creperspace` di `appearance.2da`, caricati in `CSWSCreature+0x380 → CPathfindInformation` (+4 personal space, +8 creature personal space) [V]. La tua configurazione: PC `perspace 0.35 / creperspace 0.4`, party e commoner idem. Un primo "improved collision" è **solo dati** (2DA); la versione seria è un hook K2SE (raggio morbido verso creature non ostili + spinta).
5. La **keymap** (`keymap.2da`) ha già `WALKMODIFY` (B), `STEALTH` (G), `Flourish` (X): i nostri tasti nuovi si aggiungono via ini di K2SE (poll `GetAsyncKeyState` dentro l'hook del controller), non via 2DA, almeno nella v1.
6. `D:\mods` è una libreria **Skyrim**: nessun asset è riusabile in KOTOR, ma 25 plugin SKSE danno il *design* di riferimento (Better Jumping, SkyParkour, Dynamic Collision Adjustment, StepUpOnto, Sprint Stuttering Fix, True Directional Movement).
7. **KOTOR 1 non è installato** sulla macchina: niente diffing binario K1↔K2; l'oracolo KPM K1 resta valido solo per i nomi/layout.
8. Il gioco **era in esecuzione** durante tutto lo studio (PID 19152): nessun file del gioco è stato toccato; tutto il RE è statico.
9. reone e KotOR.js confermano la semantica: `creperspace` = raggio collisione creatura-creatura (KotOR.js `CollisionManager` usa esattamente `creperspace` per il test cerchio-cerchio e risolve con *collide-and-slide*), `perspace` = spazio personale per il pathfinding.
10. Tutto il lavoro nuovo passa per K2SE (già funzionante, con fingerprint e auto-validazione): **una DLL, zero exe modificati, disinstallazione = cancellare un file**.

---

## 1. Player controller: `CSWPlayerControlCamRelative`

Fonte: `k2-directional-movement/README.md` (vtable `0x009A4818`, update `0x00865830`, setter assi `0x008653C0`), oggi disassemblata tutta (`k2-jump-crouch-sprint/docs/re/update_865830.asm`, 2206 istruzioni, fine a `0x00867AA6`).

### 1.1 Layout (offset da `this`)

| Offset | Campo | Fonte |
|---|---|---|
| +0x00 | vtable | [V] |
| +0x04 | `player_id` (object id; 0x7F000000 = invalido) | [V] `cmp [eax+4], 0x7f000000` |
| +0x08 | `camera` (CAurCamera*; vtable+0x24 = GetOrientation) | [V] |
| +0x0C | `enabled` | [V] `cmp [edx+0xc], 0` |
| +0x10 | `up_down` (float, input avanti/indietro) | [V] (= K1 `up_down` @16) |
| +0x14 | `left_right` (float, negato all'uso) | [V] (= K1 @20; `k2-directional-movement`) |
| +0x18 | `walking` (int) — **il walk-modifier**: se ≠0 il vettore input è moltiplicato per `[0x0098C014] = 0.5f` | [V] `0x00865B49..0x00865B70` |
| +0x1C | vettore (3 float) azzerato quando la velocità è ~0 (`0x008674EE`) | [V] |
| +0x44 | stato corrente RK4 (6 float: posizione+velocità) copiato in +0x5C a fine update | [V] `0x008679EF..0x00867A20` |
| +0x5C | stato precedente | [V] |
| +0x74 | oggetto passato a `0x0044C8A0` (integratore) | [V] |
| +0x80 | oggetto passato a `0x008E28E0` (camera/turn) | [V] |
| (K1) +60 `camera_max_turn_rate`, +128 `CSWRK4SplitAcceleration` | | [K1] |

### 1.2 Flusso di `Update(float dt)` (`0x00865830`, `ret 4`)

1. clamp `dt` a 1.0; esce se `player_id` invalido, camera nulla, controller disabilitato;
2. risolve **creatura client** `[ebp-0x30]` via `CAppManager+4 → 0x0073F550(id)` (→ `0x0078BDF0`, lookup client) e **creatura server** `[ebp-0x34]` via `0x0077D800` (→ `0x007F2540` → vtable+0x30 "GetServerObject") [V];
3. esce se la creatura server è in uno stato che blocca (`vtable+0x94`, `vtable+0x9C`, campo `+0x11AC`) [V];
4. legge `CClientOptions` (`0x0072FB00` = `CClientExoApp::GetClientOptions`, in tabella KPM) e il **camera mode** `byte [opts+0x75]`: modalità 5 e 6 hanno rami dedicati (free look / dialog?) [V];
5. costruisce l'input `(−left_right, up_down, 0)`, normalizza (`0x00514340`), **se `walking` moltiplica per 0.5** [V];
6. ruota l'input nello spazio camera (matrice da quaternione, costante 2.0 a `0x00987490`) [V];
7. calcola l'accelerazione con `0x00867AB0` (4 chiamate) e integra con RK4 (`0x0083D040` ×13, `0x0083D170` ×4) [V];
8. flag `word [srvCreature+0x1114] & 2` decide un ramo (bit 1 dello stesso word viene azzerato da `SetMovementRate(1=Immobile)` con `0xFFFD`: **+0x1114 = flag di movimento del server**) [V];
9. commit: `0x00543F10(srvCreature, &vec)` e `client->vtable+0x88(&vec)` = posizione/orientamento; `0x00776E10(client, speed, 0.0)` scrive `client+0x3C8 = speed`, `client+0x3CC = 0.0` (**velocità di guida, letta per la velocità dell'animazione**); poi `0x007ED830(client)` → anim base → `vtable+0xD0(0.0)` [V];
10. `turnRate = min + (max−min)·(1 − speed/maxSpeed)` con `MaxTurnRate/MinTurnRate` da `camerastyle.2da` (stringhe `0x009A4854/0x009A4848`, lette in `0x008656F1..0x00865743`, tabella `CTwoDimArrays+0x78`) — già sfruttato da `k2-directional-movement` [V].

### 1.3 Le tre funzioni della velocità [V]

```
0x00867B40  float __thiscall GetMaxSpeed(this)            ; chiamata da 0x0086603C, 0x00867336 (Update) e 0x00867AC7 (GetAcceleration)
    if [0x00A7FFE8] != 0            -> return [0x00A10F5C]           ; override globale (debug)
    opts = GetClientOptions(); if [opts+0x90] != 0 -> return [0x00A10F5C]
    cre = client creature(player_id)
    if (word [cre+0x2EC] & 1)                                        ; STEALTH lato client
        if !HasFeat(cre->[+0x310], 0xC5 /*FEAT_STEALTH_RUN=197*/) -> return cre->[+0x224]->[+0x60]   ; velocita' stealth
    return cre->[+0x224]->[+0x5C]                                    ; drive max speed (appearance.2da drivemaxspeed = 5.4)
    (fallback se la creatura manca: [0x0098BE30] = 6.0)

0x00867CA0  float __thiscall GetAccel(this)               ; chiamata da GetAcceleration
    cre = client creature(player_id); return 0x0077F600(cre)         ; fallback [0x00996548]

0x0077F600  float __thiscall CSWCCreature::GetDriveAccel(this)
    if (word [this+0x2EC] & 1) && !HasFeat(this->[+0x310], 197) -> return [0x00996444]
    return this->[+0x224]->[+0x58]                                    ; appearance.2da driveaccl = 50

0x00867AB0  Vector* __thiscall GetAcceleration(this, out, vel, target) ret 0xC
    a = GetAccel(); m = GetMaxSpeed(); if m != 1.0: a *= m; k = a / m;  out = f(target, vel, a, k)   ; molla RK4 verso la velocita' bersaglio
```

**Conseguenza per lo sprint**: l'hook giusto è `0x00867B40` (ritorno × fattore sprint quando il tasto è premuto). Poiché `GetAcceleration` scala l'accelerazione con la velocità massima, l'accelerazione segue automaticamente; l'animazione di corsa si sincronizza alla velocità reale (`drive_anim_run` = metri per ciclo) → nessun "pattinamento". È lo stesso meccanismo con cui Force Speed accelera il PC (scala questi valori sul client). **Nessun clamp lato server** è emerso: il controller scrive la posizione direttamente (`0x00543F10`).

`CSWCCreatureAppearance` (K2, `client+0x224` → struct): `+0x58 driveaccl`, `+0x5C drivemaxspeed`, `+0x60` velocità in stealth (in K1 il campo a +96 è chiamato `drive_anim_walk`: il nome K1 è probabilmente sbagliato o il layout K2 differisce — verificare in gioco leggendo i valori) [V per gli offset usati, H per i nomi].

### 1.4 Stato stealth: client e server

| Cosa | Dove | Fonte |
|---|---|---|
| Bit stealth client | `word [CSWCCreature+0x2EC] & 1` | [V] letto da `0x0077713F, 0x007773EF, 0x00777519, 0x00777C5F, 0x00777D5F` (regione 0x0077xxxx = metodi CSWCCreature: scelta animazioni walk/run/idle), `0x0077F60C` (accelerazione), `0x00867BE0` (velocità), `0x008B9189` (regione grafica: **probabile effetto di trasparenza stealth**) |
| Scrittore unico | `0x00809E01  mov word [ecx+0x2EC], dx` → la funzione che lo contiene è `CSWCCreature::SetStealthState` (K1: `SetStealthState(8)`) | [V] (inizio funzione da ricavare: probabile `0x00809DA0..0x00809DF0`) |
| Modalità stealth server | `CSWSCreature+0x1120` (dword flag, bit 1 = stealth): `IsStealthed` (routine 810, handler `0x0068BCF0`) chiama `0x00563D70(srv, 1)` = `(srv+0x1120 & 1) != 0` | [V] |
| Stealth XP, detection | routine 474..482 (`GetCurrentStealthXP`…), `CSWSArea` K1 +692..+704 | [K1] |
| `FEAT_STEALTH_RUN` | 197 (0xC5): con il feat lo stealth non rallenta | [V] `nwscript.nss` + `0x00867C1E` |

**Conseguenza per il crouch**: impostando solo il bit client si ottengono postura (animazioni `stealth`/`pausestl`) e velocità ridotta (`+0x60`, salvo Stealth Run) **senza** il gioco dello stealth (nessun XP, nessuna detection, nessuna cintura richiesta). Due incognite da chiudere in gioco: (a) se il server risincronizza il bit client ogni frame (allora l'hook va messo sul lettore, non sul campo); (b) se `0x008B9189` applica la trasparenza (allora si neutralizza quel lettore quando il crouch è "nostro").

### 1.5 Animazioni disponibili (`animations.2da`, 571 righe; supermodel `S_Male02` 5.0 MB)

| Riga | name | descrizione | flag | Uso |
|---|---|---|---|---|
| 0/2 | `walk`/`run` | | walking/running | base |
| 5 | `stealth` | Walk_Stealthily | walking, looping | **crouch-walk** |
| 9 | `pausestl` | Idle_Stealthily | stationary, pause, looping | **crouch-idle** |
| 23 | `kneel` | Kneel_To_Meditate | fireforget | alternativa crouch statico |
| 302 | `dodge` | | fireforget, dodge | schivata |
| 567 | `diveroll` | Dive_Roll | **fireforget + overlay** | **roll/jump v0** (`ANIMATION_FIREFORGET_DIVE_ROLL = 123`) |
| 381/382 | `getupdead*` | | fireforget | no |
| — | *nessun* `jump`/`hop`/`crouch` | | | → animazione nuova (KotorBlender) |

Catena supermodel: `S_Female02 → S_Female01 → S_Male02 → S_Male01`; `diveroll`, `stealth`, `pausestl`, `walk*`, `run*` sono in `S_Male02`: **un'animazione aggiunta a `S_Male02` la ereditano tutti gli umanoidi** (PC di entrambi i sessi, party, NPC). Il file va in `override/` (5 MB, accettabile).

`PlayOverlayAnimation` (handler `0x0068F440` [V]): pop oggetto e `nAnimation`; accetta solo oggetti di tipo `byte [0x00994474]` (creature); mappa **0x7B (123) → 0x290D** e rifiuta il resto (`-1`); poi `animBase = 0x007ED830(clientCreature)`, `id = animBase->vtable[0xE0/4](0x290D, 1)`, `animBase->vtable[0x44/4](id)`. Quindi:
- K2SE può riprodurre un overlay **direttamente** con le stesse tre chiamate (senza NWScript, senza coda azioni);
- per un'animazione nuova serve capire la codifica `0x290D` (categoria 0x29 + indice?) o usare `CSWCAnimBase::SetAnimation` per nome (K1: `SetAnimation(16 byte di argomenti)`, `SetAnimationInternal(20)`).

### 1.6 Input e keymap

`keymap.2da` (81 righe, colonne `character` = codice tasto interno, `eventtype`, `remappable`…). Righe rilevanti [V]:

| Riga | label | name | tasto | note |
|---|---|---|---|---|
| 0–3 | action200–203 | MoveForward/Back, **StrafeLeft/Right** | frecce | `disabled=1`: gli strafe esistono ma sono spenti — esperimento a costo zero: riattivarli (`disabled=0`) e vedere se il controller li accetta (README directional-movement dice che A/D sono "turn", non "strafe") |
| 64 | action264 | STEALTH | G (57) | toggla la modalità stealth server |
| 66 | action268 | **WALKMODIFY** | B (52) | `eventtype=1` (tenuto premuto): imposta `walking` (+0x18) |
| 42 | action242 | Flourish | X (74) | template "tasto → animazione sul PC" |
| 67–70 | action280a/b, 281a/b | ActionUp/Down/Left/Right | W S Z C | movimento |
| 75/76 | action284a/b | CameraRotateLeft/Right | A D | |
| 21/22 | action221/222 | AlternateActions | Shift sx/dx | non rimappabile, usato dalla GUI (shift-click) — **libero in gameplay** → default sprint |
| 19/20 | action219/220 | Lookabout | Ctrl sx/dx | occupato |
| 41 | action241 | Pause | Space | occupato (Space = pausa) |

Codici tasto interni (tabella K1 `InputCodes`, coerenti con l'ini): `KEYBOARD_LEFTSHIFT=24`, `LEFTCTRL=28`, `LEFTALT=26`, `SPACE=87`, `B=52`, `G=57`, `X=74`, `W=73`, `S=69`, `A=51`, `D=54`, `Z=76`, `C=53`, `CAPSLOCK=89`. Nell'ini `[Keymapping] Action268=52` conferma la codifica (valore = codice tasto). L'engine legge la tastiera via **DirectInput** (KPM `ExpandedKeyboardControl` usa `DIK_*` e il flag 0x80): per la v1 K2SE userà `GetAsyncKeyState` con controllo finestra in primo piano (semplice, indipendente dalla keymap); l'integrazione con `keymap.2da`/menu opzioni è un obiettivo successivo.

---

## 2. Velocità di movimento lato server (per completezza)

| Cosa | Dove | Fonte |
|---|---|---|
| `CSWSCreature+0x1198` = `CSWSCreatureStats*` | handler `GetMovementRate` `0x00683B30` | [V] (già in K2SE) |
| `CSWSCreatureStats+0x1A4` = `movement_rate` (indice `creaturespeed.2da`) | idem; `SetMovementRate 0x006BA320` lo scrive (`0x006BA54F`) | [V] |
| `CSWSCreatureStats+0x1A8` = walkrate (float), `+0x1AC` = runrate (float) | `SetMovementRate` legge `creaturespeed` colonne `WALKRATE`/`RUNRATE` (indici in `0x00A0FF0C/0x00A0FF10`) con `0x0071B3F0` (GetFloatEntry-like) | [V] |
| `creaturespeed.2da` | PC_Movement walk 1.70 / run **5.40**; NORM idem; FAST 2.0/6.0; VFAST 2.5/6.5 | [V] |
| `EffectMovementSpeedIncrease/Decrease` | handler `0x00675B70 / 0x006759E0` (routine 165/451); applicazione effetto = `CSWSEffectListHandler::OnApplyMovementSpeedIncrease` (nome K1) | [V]/[K1] |
| `movement_rate_factor` (float su CSWSCreature, K1 @2568) | da localizzare in K2 (ricerca: chi legge `+0x1A8/+0x1AC` e moltiplica) | [K1]/[H] |
| `CSWSCreature+0x1114` word = flag movimento (bit1 azzerato per Immobile) | `0x006BA601` | [V] |
| `CSWSCreature+0x1184` ushort = appearance type | loader appearance server `0x0057FD00..0x00580200` | [V] |
| `CSWSCreature+0x11EC` = `driveaccl` (server) | `0x005800A0` | [V] |

Il PC guidato da tastiera **non** passa per questa via (il controller client scrive la posizione), ma i party member che seguono e tutte le creature in `ActionMoveTo*` sì: uno sprint "di gruppo" (party che ti segue correndo più veloce) richiederebbe di toccare anche questo lato (v2).

---

## 3. Collisioni

### 3.1 Semantica dei raggi (`appearance.2da`, 671 righe, 94 colonne)

| Colonna | PC (riga 173 `P_MAL_C_MED_03`) | Party | Commoner | Distribuzione | Significato |
|---|---|---|---|---|---|
| `perspace` | 0.35 | 0.35 | 0.35 | 0.35 ×583 | spazio personale per il **pathfinding** (contro geometria/altri) |
| `creperspace` | 0.4 | 0.36–0.4 | 0.4 | 0.4 ×557 | raggio **creatura-creatura** (KotOR.js: `hitDistance = creperspace`, test `dist < r1 + r2`, risposta collide-and-slide) |
| `hitdist` | 1 | 1 | 1 | 1 ×666 | distanza d'attacco preferita |
| `hitradius` | 0.25 | 0.25 | 0.25 | | raggio "hit" (colpi) |
| `cameraspace` | (vuoto) | 0.46–0.49 alcuni | | | spazio camera |
| `height` | 1.6 | 1–1.6 | 1 | | altezza |
| `driveaccl` / `drivemaxspeed` | 50 / 5.4 | 50 / 5.4 | 50 / 5.4 | 661 / 662 uguali | accelerazione e velocità massima **del drive client** |
| `walkdist` / `rundist` | 1.813 / 3.66 | 1.6–1.9 / 3.66 | | | metri per ciclo di animazione (sincronia anim/velocità) |
| `driveanimwalk` / `driveanimrun_pc` / `_xbox` | 1.813 / 3.66 / 3.35 | | | | idem per la guida |

Nell'exe i nomi colonna sono in case misto (`PERSPACE`, `CREPERSPACE`, `DRIVEACCl`, `DriveMaxSpeed`, `DriveAnimWalk`, `DriveAnimRun_PC`, `RUNDIST`, `HITRADIUS`, `hitdist`) e il loader degli indici colonna è in `0x006E7E40..0x006E841B`, che salva gli indici nei globali `0x00A0FD9C` (CREPERSPACE), `0x00A0FDA4` (DRIVEACCl), `0x00A0FDA8` (DriveAnimRun_PC), `0x00A0FDB0` (DriveMaxSpeed), `0x00A0FDB4` (DriveAnimWalk), `0x00A0FDD4` (HITRADIUS), `0x00A0FDE4` (PERSPACE), `0x00A0FDEC` (RUNDIST) [V]. **Non esiste `WALKDIST` come stringa** (il client usa `DriveAnimWalk`).

### 3.2 Dove finiscono i raggi

Loader **server** `0x0057FD00..0x00580200` (funzione grande: `CSWSCreature::LoadAppearance`-like) [V]:
```
srv+0x380 -> CPathfindInformation*   (K1: +4 personal_space, +8 cre_personal_space, +16 camera_space, +20 height, +24 hit_distance)
  [pf+0x08] = CREPERSPACE (o 0.6/0.5 di default)      @0x0057FDC1..0x0057FE36
  [pf+0x10] = CAMERASPACE                              @0x0057FE36
  [pf+0x14] = HITRADIUS (fallback 1.0)                 @0x0057FF27/0x0057FF3D
  srv+0x11EC = DRIVEACCL                                @0x005800A0
  (perspace -> [pf+0x04] e height -> [pf+0x0C/0x18]: da confermare leggendo il resto della funzione)
```
Consumatori **client** degli indici: PERSPACE letto a `0x0085AC4D` e `0x0085D701`, DriveMaxSpeed a `0x0085A2CF`, HITRADIUS a `0x0085A4ED`, RUNDIST a `0x0085AF10` (regione `0x0085Axxx` = `CSWCCreatureAppearance::Load`) [V]. K1 dice che il client tiene `personal_space` in `CCAppearanceInfo+36` e ha due **callback** sulla creatura (`get_personal_radius_callback`, `get_creature_radius_callback` → `Global::GetPersonalRadius/GetCreatureRadius`, cdecl 12 byte): ottimi punti di hook "morbidi" se esistono anche in K2 [K1]/[H].

### 3.3 Cosa fa l'engine quando due creature si toccano (K1, nomi KPM)

`CSWSCreature::BumpFriends(12)`, `CSWSCreature::GetIsCreatureBumpable(4)`, `CSWSCreature::UpdatePersonalSpace()`, `CAvoidCreature::{PlotPathAroundCreature, FindPath_Left/Right, IsPathClear, SideClearOfObstructions, ComputeHexPoints}` (steering esagonale attorno alle creature), `CSWCModule::UpdateCameraCollision / UpdateNormalCameraCollision / UpdatePushCameraCollision` (camera). In K2 vanno ritrovati (nessuna stringa: si parte dai lettori di `[pf+0x08]`).

Cosa dicono le reimplementazioni:
- **reone** (`Area::moveCreature`): `testWalk(origin, dest)`; se blocca, prova a scivolare lungo la normale (**una** iterazione), poi `testElevation`. Semplice: spiega perché "ci si incolla" agli spigoli — la soluzione moderna è *collide-and-slide* multi-iterazione (Quake 3 `PM_SlideMove`: fino a 4 piani, clip della velocità contro ogni normale con `overclip 1.001`).
- **KotOR.js** (`engine/CollisionManager.ts`, 982 righe): raccoglie collisioni per tipo (creature, porte, placeable, stanza) con priorità, usa `creperspace` come raggio, risolve con `applyCollideAndSlide` sui bordi (edge) del walkmesh, tiene `blockingObject`/`lastBlockingObject` e un `collisionTimer` per gli NPC. È la descrizione più vicina a un comportamento "migliorato".

### 3.4 Placeable, porte, walkmesh

- Walkmesh stanze `WOK`, placeable `PWK`, porte `DWK` (KotorBlender importa/esporta tutti e tre; PyKotor installato nel venv `scratchpad/pyk` li legge). `surfacemat.2da`: materiali `walk`/`walkcheck`/`lineofsight` (Nonwalk=7, Door=18, Trigger=30).
- K1 `CSWRoomSurfaceMesh`: `CheckAABBWalkable(28)`, `ClippedLineSegmentWalkable(28)`, maschere `walkable_material_mask`, `walk_check_material_mask` [K1].
- Il "restare incastrati" su casse/console viene quasi sempre da PWK più larghi del modello: correggibile **solo dati** (PWK ridisegnati per i placeable più frequenti) — indipendente da K2SE.

---

## 4. Cosa si porta a casa dalle librerie

### 4.1 `personal-resources` (GitHub, 374 MB)
Contenuto: percorsi IT (SaaS, Linux, Windows, Python, Web, piattaforme, GitHub, manutenzione, automazioni, Proxmox, **Godot**, software engineering, trading, data engineering, security, Fortran). Nulla su KOTOR/Odyssey. Riutilizzabile come metodo:
- `12-SOFTWARE-ENGINEERING-EXTRA/04_Security_Cryptography/07_Reverse_Engineering_Binary_Analysis.md` e `15-SECURITY/domain1_chapter2_pe_coff.md`, `domain12_chapter12A_static_dynamic_analysis.md`: la disciplina PE/disassembly che K2SE già applica (prologhi, xref, provenienza).
- `11-GODOT-ENGINE` (`CharacterBody2D`, `move_and_slide`, layer vs mask): il modello mentale del *collide-and-slide* e dei layer di collisione (creature vs geometria) che useremo nel Tier 2/3.
- `12-…/08_SDLC_Process/02_Testing_Strategies.md`: test a livelli — qui: statici (probe), build, in gioco (banner/log), regressione.

### 4.2 `D:\mods` (Skyrim, 1960 mod; catalogo in `docs/2026-09-02-catalogo-mod-skyrim-riferimenti.md`, 4.7 MB)
Solo **design**, niente asset (engine, formati e licenze diversi). Riferimenti scelti:

| Mod Skyrim | Idea da riusare in KOTOR 2 |
|---|---|
| **True Directional Movement** (settings.ini) | moltiplicatori di rotazione per stato (`fRunningRotationSpeedMult 1.5`, `fSprintingRotationSpeedMult 2`, `fDodgeUnlocked… 0.5`): lo sprint deve **ridurre** la prontezza di sterzo (in K2: `minturnrate` per stato via camerastyle o hook del turn rate); *leaning*; buffer input 0.02 s |
| **Better Jumping AE** (BetterJumpingSE.txt) | config minimale: salti multipli, perk richiesto, "allow jump when sprinting", moltiplicatori d'altezza (base / secondo salto / sprint-jump) → il nostro ini |
| **SkyParkour V3** | tasto unico contestuale (jump/sprint/activate), *crouch slide* premendo sneak in sprint, *landing roll*, costo stamina opzionale → in K2: roll premendo crouch durante lo sprint; nessuna stamina (K2 non ne ha) ma opzionale costo Force Points |
| **Dynamic Collision Adjustment** | riduce la capsula di collisione in sneak/nuoto (`fSneakControllerShapeHeightMultiplier 0.5–1`) → in K2: ridurre `creperspace` del PC in crouch (passare in spazi stretti fra NPC) |
| **StepUpOnto SKSE** (ini) | parametri di *step-up* (altezza min/max, distanza di rilevamento, cooldown, angolo massimo): schema di configurazione per un eventuale "superamento ostacoli bassi" (Tier 3, se mai) |
| **Sprint Stuttering Fix** | lo smoothing del movimento ha un limite di velocità (`fSpeedLimit`): nel nostro caso l'accelerazione RK4 va scalata con la velocità (già fatto dall'engine in `GetAcceleration`) e il turn-rate va controllato per evitare pop dell'animazione |
| **Sprint Sneak Movement Speed Fix** | interazione sprint×sneak: definire una priorità (in K2: sprint annulla crouch o è vietato in crouch — decisione di design) |
| **Dialogue Movement Enabler** (ini) | flag di permesso per contesto (dialogo/GUI/minigioco): il nostro input va **ignorato** fuori dal gameplay (controller disabilitato, GUI aperta, dialogo, minigiochi) |
| **Capital Whiterun – More Accurate Collision / Campfire Dynamic Collisions / Collision Dialogue Overhaul** | "improved collision" nel modding Skyrim significa quasi sempre **mesh di collisione più fedeli**: l'equivalente K2 è il Tier 1 sui PWK/DWK |
| **Address Library / Engine Fixes / CrashLogger** | l'infrastruttura che K2SE sta già replicando (CSV indirizzi con provenienza, fingerprint, log): manca un **crash handler** (dump minimo su eccezione non gestita nel nostro codice) |

### 4.3 Kotor-Patch-Manager (locale, Desktop)
- `Patches/ExpandedKeyboardControl` (K2 GOG): dove intercetta l'input grezzo (`0x00613863` GOG) e come naviga i pannelli GUI: conferma DirectInput e dà la mappa dei pannelli (`inGameMessagePanelVtable 0x0098E1EC`, `keyboardDeviceIndex 0x00997514`, `handleGuiInputEvent 0x0090EF20` — indirizzi GOG, da ri-localizzare su Steam).
- `Patches/Post-Combat Movement Fix` (K2 GOG `0x0045BDA8`): il famoso blocco del movimento post-combattimento ad alti FPS è nella macchina a stati dell'input W/S; su Steam va cercato l'equivalente (bonus: è un fix reale e gratuito da includere).
- `Patches/ScriptExtender/Extensions/clientCreatures.cpp`: `IsRunning`/`IsStealthed` leggendo offset del client (K1) — stesso schema che K2 offre già nativamente (routine 810/824).
- Roadmap 2026: "Better kotor 2 support" — il nostro lavoro è un contributo naturale (indirizzi K2 verificati).

---

## 5. Toolchain verificata oggi

| Cosa | Stato |
|---|---|
| Python 3.12 + capstone 5.0.7 | ✅ (`pefile` assente, non serve) |
| MSVC portabile `C:\Users\Renan Macena\tools\msvc` (14.44.35207) + CMake 4.4.2 portabile | ✅ (`K2SE\build.ps1` / `build_direct.ps1`; **non** nel PATH) |
| Java/Ghidra | ❌ assenti — il RE prosegue con gli script capstone (`K2SE/tools/re/`) |
| PyKotor | ✅ installato in `scratchpad/pyk` (venv temporaneo): da reinstallare in un venv del progetto per WOK/PWK/MDL |
| KotorBlender / Blender | da installare quando si arriva all'animazione di salto (Blender 4.x + KotorBlender fork seedhartha) |
| nwnnsscomp | ✅ `K2SE/tools/nwnnsscomp/` |
| reone / KotOR.js sorgenti | ✅ cloni in scratchpad (da ricopiare in `~/Documents/KOTOR2-Modding/ref/` se servono stabilmente) |

---

## 6. Incognite aperte (da chiudere in gioco o con RE mirato)

| # | Domanda | Come si chiude | Impatto |
|---|---|---|---|
| Q1 | `GetMaxSpeed` ×1.6 basta per uno sprint pulito (animazione, camera, party che segue)? | hook sperimentale con marker file, sessione di 10 min | Sprint |
| Q2 | il server risincronizza `word [client+0x2EC]` ogni frame? | impostare il bit da K2SE e loggare le transizioni per 30 s | Crouch |
| Q3 | `0x008B9189` è la trasparenza stealth? | disassemblare la funzione che lo contiene; test visivo | Crouch |
| Q4 | `0x290D` è una codifica generica (categoria+indice) riutilizzabile per una riga 2DA nuova? | disassemblare `animBase->vtable[0xE0]` | Jump v1 |
| Q5 | `pf+0x04` è `perspace` e chi lo legge durante il movimento del PC? | leggere il resto di `0x0057FD00` e `dispscan` su `+0x4/+0x8` con base = `[srv+0x380]` | Collisioni Tier 2 |
| Q6 | esistono in K2 `GetPersonalRadius/GetCreatureRadius` come callback del client? | cercare store di puntatori a funzione nel costruttore di `CSWCCreature` | Collisioni Tier 2 |
| Q7 | dove il controller clippa la velocità contro il walkmesh (per lo *sliding*)? | seguire `0x0083D170` e le chiamate `0x0051xxxx` nell'update | Collisioni Tier 3 |
| Q8 | riattivare `StrafeLeft/Right` in `keymap.2da` fa qualcosa? | 2DA in override, restart, test | bonus movimento |
| Q9 | il "Post-Combat Movement Fix" ha un equivalente Steam? | pattern-scan dei byte GOG `8B 8D A0 F9 FF FF 8B 91 A0 02 00 00` | bonus |

---

## 7. Aggiornamento serale (dopo le conferme): il "mover" e il commit di posizione [V]

Il controller **non scrive la posizione**: imposta orientamento (`CSWSObject::SetOrientation 0x00543F10`, campo `+0xA0`) e velocità di guida sul client (`CSWCCreature::SetDriveSpeed 0x00776E10` → `+0x3C8`). Il movimento vero è nel **server**:

- `CSWSCreature::MovementUpdate 0x005C3F70` (5 chiamanti) → se `[this+0x11B0]==3` chiama **`DriveMoverUpdate 0x005C6340`** (1565 istruzioni).
- Il mover legge la velocità di guida del PC (`client+0x3C8`), esegue una **macchina a stati** di risoluzione del movimento (`[state+4]` = caso, `[state+0x44]` = tentativi ≤ 50) i cui casi chiamano 11 helper `0x005C7370, 0x005C7AD0, 0x005C87E0, 0x005C8C20, 0x005CA000, 0x005CA6A0, 0x005CACD0, 0x005CAE00, 0x005CAF30, 0x005CB060, 0x005CB190` (tutti `ret 0x10`) — è qui che vive il *collide-and-slide* (Tier 3).
- Commit: `area = CSWSObject::GetArea(this) 0x005453C0`; test `area->0x00550980(&target, &pos, &pf.perspace, pf.hitradius, 0, 0)` (== 1 libero) [H]; `area->0x0054B130(&newpos, 1, 0, 0)` (quota, float) [H]; `area->0x0054B650(&target, pf)` [H]; poi **`CSWSObject::SetPosition 0x00543F50 (vec, 1, 1, 0)`** in tre siti: `0x005C6E87`, `0x005C6ED8`, `0x005C6F9E`. `SetPosition` = `ret 0x10`, early-out se il vettore è uguale (`0x00517980`), dirty bit 1 (`0x0054A430`), notifica client se il 2° argomento ≠ 0, chiusura con `0x00522E00`.
- **Salto (J1)**: `movement.cpp` redirige i tre siti `SetPosition` del mover e, mentre il PC è in aria, sostituisce `vec.z` con `z0 + h(t)`.

Altro:
- **Codici animazione**: `CSWCAnimBase::vtable[0xE0] (0x00863650)` è uno switch da codici 10000-based a **righe di `animations.2da`** (`0x290D → 0x237 = 567 diveroll`); `vtable[0x44] (0x00860280)` riproduce una riga (`0x008602C0(model, row, flag)`). Quindi **qualsiasi riga 2DA, anche nuova, si riproduce con `vtable[0x44](row, 1)`** su `GetAnimBase(client) 0x007ED830`: la strada per l'animazione di salto autoriale è aperta senza toccare il mapper.
- **Bit stealth client**: scritto solo dall'handler di aggiornamento server→client `0x008079B0` (3537 istruzioni) insieme a `+0x2E8/+0x2EA/+0x2F0/+0x2F4` → il crouch lo riafferma ogni frame. Il lettore grafico `0x008B9120` è lo **stato del pulsante stealth dell'HUD** (0x9403/0x9404), non uno shader.
- **Combattimento**: `[srv+0x520]` (combat round) ≠ 0; `byte [srv+0x11E8]` = combattimento "reale".
- **`JumpToLocation`** accoda un'azione (tipo `byte [0x994473] = 4`; tag engine-structure **2 = location** confermato); `CutsceneMove` accoda l'azione 0x3F via `0x0053F7F0`: nessuno dei due teletrasporta direttamente.
- **Q9**: il pattern del Post-Combat Movement Fix ha tre candidati Steam: `0x007AF19E, 0x007AF306, 0x007AF3BA`.
- Vtable RTTI: `CSWCAnimBase 0x009A454C` (62 slot), `CSWCCreature 0x0099EE14` (88), `CSWSCreature 0x00994F5C` (57), `CSWPlayerControlCamRelative 0x009A4818` (12).

Tutto è in `K2SE/data/k2se_addresses.csv` (178 righe, `verify_offsets.py` = ALL PROBES PASSED) e in `K2SE/docs/session-2026-09-02-movement-re.md`.
