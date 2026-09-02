# PIANO D'AZIONE — «K2 Jump / Crouch / Sprint» e «K2 Improved Collision»

**Data:** 2026-09-02 (rev. 2, stessa sera, dopo le conferme di Renan) · **Autore:** Claude (sessione con Renan) · **Stato:** approvato nelle decisioni di design (✅); in esecuzione dalla Fase 0 · **Studio di riferimento:** `docs/2026-09-02-studio-movimento-collisioni.md` (tutti gli indirizzi citati qui sono spiegati e marcati [V]/[K1]/[H] lì).

> Il piano copre l'intero ciclo: preparazione, reverse engineering residuo, infrastruttura K2SE, le tre feature di movimento, le collisioni a livelli, test, convalida, packaging, pubblicazione e chiusura. È lungo di proposito: ogni task ha un criterio di accettazione e dice **quale prova** deve esistere prima di dichiararlo fatto. Il gioco può restare acceso per tutto il lavoro tranne che nelle **sessioni di test** (marcate 🎮), che richiedono chiusura + salvataggio.

---

## Indice

0. Come leggere il piano
1. Obiettivi, non-obiettivi, definizioni
2. Stato di partenza
3. Decisioni di design (con alternative)
4. Architettura tecnica
5. Fasi, milestone e task
   - Fase 0 — Preparazione
   - Fase 1 — Reverse engineering residuo
   - Fase 2 — Infrastruttura K2SE per il movimento
   - Fase 3 — SPRINT
   - Fase 4 — CROUCH
   - Fase 5 — JUMP / ROLL
   - Fase 6 — IMPROVED COLLISION (Tier 0–4)
   - Fase 7 — Testing e convalida
   - Fase 8 — Packaging, documentazione, pubblicazione
   - Fase 9 — Conclusione e manutenzione
6. Protocollo di lavoro con Renan (sessioni 🎮)
7. Rischi e mitigazioni
8. Stime
9. Appendici (A indirizzi, B nomi K1 da ritrovare, C ini di esempio, D checklist, E glossario, F fonti)

---

## 0. Come leggere il piano

> **Stato al 2026-09-02 sera:** Fase 0 e Fase 2 completate; Fase 1 in gran parte chiusa (RE del mover `0x005C6340`, `SetPosition`, vtable anim base); codice di sprint, crouch, roll e salto v0 **scritto e compilato** (`K2SE 0.2.0`, `check_dll` e `routine_id_test` verdi) ma **mai eseguito in gioco**: le sessioni S1/S6 sono il prossimo passo. Dettagli in `K2SE/docs/session-2026-09-02-movement-re.md`.

- **Task** = `Fx.y` (fase x, numero y). Ogni task ha: *cosa*, *come*, *accettazione* (la prova), *dipendenze*.
- **Stati**: `[ ]` da fare · `[~]` in corso · `[x]` fatto con prova · `[!]` bloccato · `[?]` da confermare con Renan.
- **Prove ammesse**: output di uno script di verifica (`verify_offsets.py`, `check_dll.py`, `routine_id_test.py`), riga di `k2se.log`, foto/frame dello schermo (banner `AurPostString`), diff di file. Un'affermazione senza prova non chiude un task (regola ereditata da K2SE: *"static verification is necessary but not sufficient"*).
- ✅ = decisione confermata da Renan il 2026-09-02 sera: *improved collision* = tutto quanto assunto **più** collisioni con ambiente e pavimento; tasti default Shift/Space/Alt/C; sprint come proposto; **salto funzionale, non solo cosmetico**. ⚠️ resta solo su dettagli di taratura (valori numerici) da decidere provando.
- 🎮 = richiede il gioco chiuso (deploy della DLL) e poi una sessione di test con checklist.
- Convenzione indirizzi: VA su image base `0x00400000`, exe Steam/Aspyr 1.0.2.0. Ogni indirizzo che entra nel codice **deve** prima entrare in `K2SE/data/k2se_addresses.csv` con `provenance` e `verified_by`, e avere una probe in `fingerprint.cpp` se viene scritto o chiamato.

---

## 1. Obiettivi, non-obiettivi, definizioni

### 1.1 Obiettivi

| Mod | Obiettivo utente | Definizione operativa |
|---|---|---|
| **K2 Jump / Crouch / Sprint** | il PC si muove "come in un gioco moderno": corsa veloce a comando, postura accovacciata, salto vero, rotolamento | (a) **Sprint** (Shift tenuto): la velocità del PC sale di un fattore configurabile (default ×1.6), con accelerazione e animazione coerenti, senza effetti collaterali su combattimento/dialoghi; (b) **Crouch** (C, toggle): postura accovacciata (animazioni `stealth`/`pausestl`) con velocità ridotta, **senza** attivare la meccanica stealth (XP, detection, cintura); (c) **Jump** (Space): **salto funzionale** — traiettoria balistica reale (Z sale e scende, il PC avanza in aria), atterraggio validato sul walkmesh, capacità di superare ostacoli bassi e piccoli vuoti e di scendere da sporgenze entro limiti configurati; (d) **Roll** (Alt): animazione overlay `diveroll` con breve impulso in avanti |
| **K2 Improved Collision** ✅ | "non restare incastrati", con ambiente e pavimento inclusi | (a) il PC non viene bloccato da party member e NPC non ostili (scivola/li spinge), (b) i placeable più comuni non hanno collisioni più larghe del modello, (c) **ambiente**: scivolamento fluido lungo muri e spigoli (clip multi-piano), niente agganci sugli angoli, (d) **pavimento**: nessun blocco su gradini/bordi fra facce walkmesh adiacenti, transizioni di quota morbide, niente affondamenti/galleggiamenti visibili del modello dove il walkmesh e la mesh visiva differiscono (nei limiti del possibile: la Z è del walkmesh), (e) opzionale: la camera non attraversa i muri |

### 1.2 Non-obiettivi (dichiarati per non discuterne a metà strada)

- **Salto illimitato**: il salto è funzionale ma **vincolato**: altezza massima ~1 m, distanza massima ~2.5 m (di più in sprint), atterraggio **solo** su una faccia walkable (altrimenti il salto abortisce e il PC torna dove è partito), traiettoria che non attraversa pareti (test line-of-sight sul walkmesh), caduta massima ~3 m. Niente arrampicata, niente doppio salto, niente salto in combattimento (opzione). Il salto è un'estensione di un engine 2.5D: l'aria è simulata da K2SE, l'atterraggio è consegnato all'engine (stessa strada di `JumpToLocation`) perché stanza, trigger e camera restino coerenti.
- Sprint per i party member in follow (v2: richiede il lato server, §2 dello studio).
- Rimappatura dal menu opzioni del gioco (v2: richiede riga in `keymap.2da` + hook del dispatcher azioni).
- Supporto gamepad (v2: il controller alimenta già gli assi analogici; sprint via stick-click è fattibile ma non ora).
- Compatibilità con exe diversi da Steam/Aspyr 1.0.2.0 (GOG ha indirizzi diversi; K2SE rifiuta di installarsi via fingerprint).

### 1.3 Definizioni

- **Client/Server**: KOTOR è un gioco single-process con due metà (Aurora): `CSWC*` = client (rendering, animazioni, controller), `CSWS*` = server (regole, posizione autoritativa, AI). Il player controller è client e scrive direttamente sulla creatura server.
- **Drive**: il movimento del PC da tastiera/stick ("driving"), distinto da `ActionMoveTo*` (pathfinding).
- **Overlay**: animazione che si sovrappone alla locomozione senza fermarla (`animations.2da` colonna `overlay`).
- **Marker file**: file vuoto accanto all'exe che abilita una parte opzionale di K2SE (già usato per fog e diagnostica).

---

## 2. Stato di partenza (2026-09-02)

- **K2SE**: DLL proxy `version.dll` funzionante, 12 routine (877–888) provate in gioco, fingerprint + auto-validazione, log in `%LOCALAPPDATA%\K2SE\k2se.log`, deploy con `tools/deploy_test.py`, build con `build_direct.ps1` (MSVC portabile). Fog disarmata (marker `.DISABLED`). Nessun hook inline: un solo dword di vtable riscritto.
- **k2-directional-movement**: fatta e installata (`override/camerastyle.2da`), README con gli indirizzi del controller.
- **Cartelle** `k2-jump-crouch-sprint/` e `k2-improved-collision/`: create da Renan, oggi popolate con README/DESIGN e materiale RE.
- **Gioco**: in esecuzione durante lo studio; exe LAA-patched; 63 file in `override/` (UI gamepad, camerastyle); Workshop TSLRCM 1.8.6 + 22 mod.
- **Toolchain**: Python 3.12 + capstone; MSVC/CMake portabili; PyKotor in venv temporaneo; **niente Ghidra/Java**; reone e KotOR.js clonati in scratchpad.
- **Conoscenza acquisita oggi** (studio §1–3): funzioni della velocità (`0x00867B40`, `0x00867CA0`, `0x0077F600`, `0x00867AB0`), bit stealth client (`+0x2EC`) e scrittore (`0x00809E01`), flag server (`+0x1120`, `+0x1114`), `PlayOverlayAnimation` (`0x0068F440`) e catena anim base (`0x007ED830` → vtable `0xE0`/`0x44`), raggi in `CSWSCreature+0x380` (`+8` creperspace, `+0x10` cameraspace, `+0x14` hitradius), loader indici colonna 2DA (`0x006E7E40..`), `SetMovementRate` e rate float (`stats+0x1A8/+0x1AC`).

---

## 3. Decisioni di design (con alternative)

| # | Decisione | Alternative scartate e perché |
|---|---|---|
| **D1** | Tutto il runtime vive in **K2SE** come *moduli feature* opt-in, configurati da `k2se_movement.ini` accanto all'exe; ogni feature ha un interruttore e un default conservativo; disinstallazione = cancellare ini/DLL | (a) DLL separate per mod: moltiplica proxy e conflitti sullo slot `version.dll`; (b) patch statiche dell'exe: rompono "Verifica integrità" e la filosofia K2SE |
| **D2** | Hook di `GetMaxSpeed` con **redirezione dei call-site** (riscrittura del `rel32` nelle 3 `call E8` a `0x0086603C`, `0x00867336`, `0x00867AC7`), con verifica byte-per-byte prima di scrivere e ripristino al detach | (a) trampolino inline su `0x00867B40`: più byte da riscrivere, prologo da rilocare; (b) scrivere direttamente `appearance->[+0x5C]`: modifica dati condivisi (party, NPC con la stessa appearance) e va ripristinato ogni frame |
| **D3** | Input letto con **`GetAsyncKeyState`** dentro gli hook del controller (quindi solo quando il PC è guidato), con controllo `GetForegroundWindow()==HWND del gioco`, edge detection per i toggle, VK configurabili nell'ini | (a) hook del buffer DirectInput (KPM ExpandedKeyboardControl): più preciso ma richiede localizzare la capture su Steam; rimandato a v2 insieme alla keymap; (b) riga nuova in `keymap.2da`: richiede il dispatcher azioni (v2) |
| **D4** ✅ | **Sprint**: tenere premuto (default `Left Shift`), fattore 1.6 su `GetMaxSpeed`, rampa di 0.25 s in ingresso/uscita, **disattivato in combattimento** (opzione), disattivato se il PC è in stealth server, spegne il crouch | fattore fisso senza rampa: pop dell'animazione (lezione "Sprint Stuttering Fix"); sprint in combattimento: sbilancia i round e il "Combat Movement" |
| **D5** ✅ | **Crouch**: toggle (default `C`; il gioco lega `C` a *ActionRight*: il deploy sposta ActionLeft/Right sulle frecce ← → con backup dell'ini, oppure lo fai tu dal menu Opzioni → Tasti), imposta il bit stealth **client** del PC (`+0x2EC` bit 0) tramite la stessa funzione che il gioco usa (`SetStealthState`, corpo attorno a `0x00809E01`), velocità = quella stealth dell'engine (o fattore ini), niente flag server; si spegne con sprint/combattimento/cambio area | usare la modalità stealth vera (tasto G): porta XP stealth, detection, requisito cintura in K1-style, trasparenza; crouch via `PlayAnimation(kneel)`: ferma il movimento |
| **D6** ✅ | **Jump** (`Space`; il gioco lega Space a *Pausa*, azione `action241` rimappabile: il deploy la sposta su `F9` con backup dell'ini, oppure dal menu Opzioni; la Pausa resta anche sul tasto Pause/Break): salto **funzionale** simulato da K2SE — per ~0.9 s K2SE prende il controllo della posizione del PC (intercettando il commit di posizione del controller a `0x008679D3 → 0x00543F10` e il commit client), integra una parabola (v₀ verticale ≈ 4.4 m/s → apice ~1 m; orizzontale = velocità corrente limitata), valida la traiettoria (nessuna parete fra partenza e atterraggio) e l'atterraggio (faccia walkable entro tolleranza di quota; altrimenti abort e ritorno al punto di partenza), poi consegna l'atterraggio all'engine con la stessa sequenza di `JumpToLocation` (stanza, trigger, camera aggiornati dall'engine). Animazione: v0 placeholder `diveroll`/posa, v1 animazione **"jump"** autoriale in `S_Male02`. **Roll** (`Left Alt`): overlay `diveroll` via anim base (`0x007ED830` → `vtable[0xE0](0x290D,1)` → `vtable[0x44]`), cooldown 1.0 s, impulso in avanti opzionale | spostare la Z senza validare l'atterraggio: PC fuori dal walkmesh, trigger/pathing/camera rotti; salto solo cosmetico: rifiutato da Renan |
| **D7** ✅ | **Improved Collision** a livelli: Tier 0 introspezione (routine di lettura/scrittura raggi + log), Tier 1 **solo dati** (`appearance.2da` `creperspace`/`perspace` per party/PC/commoner + PWK più fedeli), Tier 2 runtime (raggio "morbido" verso creature non ostili + spinta/cedimento party), **Tier 3 ambiente** (clip multi-piano lungo muri e spigoli, anti-aggancio angoli), **Tier 3b pavimento** (tolleranza gradini/bordi fra facce, quota morbida, controllo affondamento), Tier 4 camera (opzionale). Tier 3/3b sono **obbligatori** per Renan, non opzionali | fare subito il Tier 2 senza Tier 0/1: senza strumenti di misura non si distingue "meglio" da "diverso" |
| **D8** | Due mod distinte che condividono K2SE core: **K2 Jump/Crouch/Sprint** (ini + eventuale `S_Male02.mdl/mdx` + `animations.2da` per v1) e **K2 Improved Collision** (ini + `appearance.2da`/PWK opzionali). Il core K2SE resta un progetto a sé con versione propria | un'unica mega-mod: chi vuole solo le collisioni si porterebbe dietro lo sprint |
| **D9** | Ogni feature fa **fail-safe**: se una probe fallisce, la feature non si installa e il log lo dice; se una routine engine chiamata da noi fault-a, SEH la cattura e disattiva la feature per la sessione | "installare comunque": un hook inerte o parziale è peggio di nessun hook (DESIGN.md K2SE §3.6) |
| **D10** | Per i 2DA si spedisce uno **script che patcha il 2DA presente nell'installazione** (come `k2-directional-movement/build.py`) invece del file già fatto: rispetta altre mod che toccano `appearance.2da`; in alternativa un `changes.ini` TSLPatcher/HoloPatcher | file 2DA pre-costruito: sovrascrive silenziosamente le modifiche di altre mod (regola "una sola copia vince in override") |

---

## 4. Architettura tecnica

### 4.1 Nuovi moduli in `K2SE/src/`

```
config.*      parser ini minimale (senza CRT stream), sezioni [Sprint] [Crouch] [Jump] [Collision] [Debug]; default sicuri; hot-reload opzionale su marker
input.*       KeyState: down/pressed/released per VK; focus check; timer; nessuna dipendenza dal gioco
callsite.*    RedirectCall(siteVA, expectedTarget, newTarget): verifica E8 + rel32 atteso, VirtualProtect, scrive, registra per il ripristino
player.*      accesso a CSWPlayerControlCamRelative (this dal hook), client creature (0x0073F550 via CAppManager+4), server creature (0x0077D800), appearance (+0x224), flag (+0x2EC, +0x1120, +0x1114)
movement.*    macchina a stati Sprint/Crouch/Jump: aggiornata da HookGetMaxSpeed (chiamata ogni frame in cui si guida); applica fattori, rampe, esclusioni
anim.*        PlayOverlay(clientCreature, code): la catena di PlayOverlayAnimation; in v1 anche lookup per nome/riga 2DA
collision.*   Tier 0 accessori ai raggi (CPathfindInformation via srv+0x380); Tier 2 hook (vedi F6)
crashguard.*  filtro eccezioni non gestite nel nostro codice → riga di log con VA e registri, disattiva la feature
```

### 4.2 Punti di aggancio

| Hook | Tecnica | Quando gira | Cosa fa |
|---|---|---|---|
| `GetMaxSpeed` (`0x00867B40`) | redirezione 3 call-site | ogni frame di guida (3×) | aggiorna input/stato, ritorna `orig * fattore(sprint, crouch)` |
| `GetAccel` (`0x00867CA0`) | redirezione 1 call-site (`0x00867ABC`) | ogni frame di guida | ritorna `orig * fattoreAccel` (opzionale, per rampe più nette) |
| Overlay (jump) | **nessun hook**: chiamata attiva alla catena anim base dal nostro update | su pressione tasto | riproduce `diveroll`/`jump` |
| Crouch | chiamata attiva a `SetStealthState`-client (o scrittura diretta del bit come piano B) | su toggle | postura |
| Collisioni Tier 2 | da definire in F6 dopo Q5/Q6 (redirezione di `GetCreatureRadius`-K2 o hook del lettore di `[pf+0x08]`) | per creatura per frame | raggio effettivo ridotto verso creature amiche |
| Routine NWScript 889+ | slot tabella (meccanismo K2SE esistente) | da script | introspezione/test: `K2SE_GetDriveMaxSpeed`, `K2SE_SetSprintFactor`, `K2SE_GetCrouch`, `K2SE_SetCrouch`, `K2SE_PlayOverlay`, `K2SE_GetCreatureRadii`, `K2SE_SetCreatureRadii` |

### 4.3 Flusso di un frame (sprint attivo)

1. `Update(dt)` del controller chiama `GetMaxSpeed` → il nostro stub `HookGetMaxSpeed(this)`.
2. Lo stub: `input.Poll()` (solo se il frame è nuovo: confronto con un contatore), `movement.Update(this, dt≈)` (transizioni: sprint on/off, crouch, jump), poi `v = orig(this)`; `return v * movement.SpeedFactor()`.
3. `GetAcceleration` chiama `GetAccel` → stub opzionale → `orig * movement.AccelFactor()`.
4. L'RK4 integra con la velocità massima aumentata; `0x00776E10` scrive la velocità di guida → l'animazione di corsa accelera da sola.
5. Se `jumpPressed`: `anim.PlayOverlay(client, code)`, cooldown.

### 4.4 Configurazione (`k2se_movement.ini`, accanto all'exe) — vedi Appendice C.

### 4.5 Log e diagnostica

- Riga di stato all'avvio: feature abilitate, tasti, fattori, esito probe/redirezioni (`callsite: 0x0086603C E8 -> 0x00867B40 OK, redirected`).
- Transizioni (non per-frame): `sprint ON at t+…`, `sprint OFF (combat)`, `crouch ON`, `jump (diveroll) cooldown 1.0`.
- Marker `K2SE_DIAGNOSTIC` esistente: traccia per-frame thinned (1/64).
- Banner `AurPostString` opzionale `[Debug] Banner=1`: `SPR x1.60  CRH off  spd 8.64` per confronto visivo con il log.

---

## 5. Fasi, milestone e task

### Fase 0 — Preparazione (nessuna sessione 🎮)

| Task | Cosa | Accettazione |
|---|---|---|
| F0.1 `[x]` | Studio e raccolta prove (questo documento e lo studio) | file presenti |
| F0.2 `[x]` | Copiare in `~/Documents/KOTOR2-Modding/ref/` i cloni `reone`, `kotorjs/src` e il venv PyKotor (`python -m venv .venv && pip install pykotor capstone`) | `python -c "import pykotor, capstone"` OK dal venv del progetto |
| F0.3 `[x]` | In K2SE: branch `feature/movement` (repo git esistente); versione core → 0.2.0 | `git branch` mostra il branch; `CMakeLists.txt`/`build_direct.ps1` versione 0.2.0 |
| F0.4 `[x]` | Estendere `tools/kotor_res.py` con i tipi `mdl/mdx/wok/pwk/dwk/lyt/vis/gui/utp/utd` (già fatto in scratchpad, portare nel repo) | `python tools/kotor_res.py list pwk` elenca i walkmesh dei placeable |
| F0.5 `[ ]` | Baseline 🎮 (alla prima sessione utile): con la DLL attuale, 5 min di gioco, verificare `TEST 1..21 PASS`, annotare FPS medi (Adrenalin overlay) in un'area di riferimento | riga nel log di sessione `docs/sessioni/2026-xx-xx-baseline.md` |
| F0.6 `[x]` | Backup: copia di `version.dll` corrente in `K2SE/out/version.dll.backup-2026-09-02` e dello `swkotor2.ini` | file presenti |

### Fase 1 — Reverse engineering residuo (statico; senza gioco chiuso)

| Task | Cosa | Come | Accettazione |
|---|---|---|---|
| F1.1 `[x]` | Inizio funzione di `SetStealthState` client (contiene `0x00809E01`) e sua firma | `funcdump` a ritroso da `0x00809D00`; cercare prologo `55 8B EC`; leggere gli argomenti (`ret imm16`) | firma documentata nello studio §1.4; riga CSV con `verified_by=disasm` |
| F1.2 `[~]` | Chi chiama `SetStealthState` client (il server sync?) — risponde a **Q2** | `dwxref.py <inizio funzione>`; leggere i chiamanti | lista chiamanti + giudizio "sync per frame: sì/no" |
| F1.3 `[x]` | Funzione che contiene `0x008B9189` (lettore grafico del bit stealth) — **Q3** | `funcdump` attorno; capire se imposta alpha/shader | verdetto documentato |
| F1.4 `[x]` | `animBase->vtable[0xE0]` (mappatura codice `0x290D`) e `vtable[0x44]` (play overlay) — **Q4** | trovare la vtable di CSWCAnimBase (RTTI `.?AVCSWCAnimBase@@`), disassemblare gli slot | codifica spiegata (categoria/indice) o alternativa per nome |
| F1.5 `[~]` | Layout completo di `CPathfindInformation` K2 (`srv+0x380`): confermare `+0x04` perspace, `+0x0C/+0x18` height, e lettori dei raggi durante il movimento — **Q5** | leggere il resto di `0x0057FD00..0x00580200`; `dispscan.py 0x4 0x8` filtrato sulle funzioni che leggono `[srv+0x380]` | tabella offset nello studio §3.2 |
| F1.6 `[ ]` | Esistenza dei callback raggio nel client K2 (`GetPersonalRadius/GetCreatureRadius`) — **Q6** | nel costruttore di `CSWCCreature` (RTTI) cercare store di puntatori a funzione in campi adiacenti | trovati → indirizzi in CSV; non trovati → piano B in F6 |
| F1.7 `[ ]` | Clip della velocità contro il walkmesh nel controller — **Q7** | seguire `0x0083D170` e le `call 0x0051xxxx` nell'update (regione `0x008672xx`) | funzione e firma documentate |
| F1.8 `[ ]` | HWND del gioco: come ottenerlo in modo robusto | `EnumWindows` + `GetWindowThreadProcessId` = pid corrente, classe finestra dell'exe (leggere `RegisterClass` in `WinMain` `0x0051D5A2`) | codice in `input.cpp` con fallback `GetForegroundWindow()` |
| F1.9 `[x]` | Stato "in combattimento" e "in dialogo/GUI" leggibili dal client | handler `GetIsInCombat 0x00680000` (campo letto), `GetIsInConversation 0x0068B810`; pannelli GUI (KPM K2 `MANAGER_PANEL_LIST_OFFSET`) | tre predicati implementati in `player.cpp` con SEH |
| F1.10 `[~]` | Bonus Q8/Q9: `keymap.2da` strafe (`disabled=0`) e pattern GOG del Post-Combat Movement Fix su Steam | 2DA in override (test 🎮 in F7); `strxref`/byte-scan | esito registrato (anche negativo) |
| F1.11 `[x]` | Tutti gli indirizzi nuovi nel CSV (`data/k2se_addresses.csv`) con provenienza `k2se-2026-09-02` e `verified_by`; `gen_offsets.py`; `verify_offsets.py` esteso con le probe dei call-site (`E8` + rel32) | `python tools/verify_offsets.py` → `ALL PROBES PASSED` |

### Fase 2 — Infrastruttura K2SE per il movimento

| Task | Cosa | Accettazione |
|---|---|---|
| F2.1 `[x]` | `config.*`: parser ini (chiavi `int/float/bool/key`), default, dump nel log | test unitario host (eseguibile di test o script) con ini di esempio; log mostra i valori |
| F2.2 `[x]` | `input.*`: `Poll()` una volta per frame (guard su contatore frame), `IsDown/Pressed/Released(vk)`, focus check, parsing nomi tasto (`LSHIFT`, `SPACE`, `N`, `0x41`) | test host con simulazione; in gioco: log `key SPRINT down/up` in modalità diagnostica |
| F2.3 `[x]` | `callsite.*`: `Redirect(site, expected, hook)` con verifica `E8` + rel32 atteso, `VirtualProtect`, `FlushInstructionCache`, ripristino in `DllMain DETACH`, contatore | probe in `fingerprint.cpp`; log `callsite … OK`; `check_dll.py` verde |
| F2.4 `[x]` | `player.*`: accessori con SEH (creatura client/server, appearance, flag) + `ReportWalk`-style transizioni | in gioco (F3 🎮): una riga `player: chain OK id=… cli=… srv=… app=…` |
| F2.5 `[x]` | `crashguard.*`: `__try/__except` attorno a ogni chiamata engine nostra; su fault: log + disattiva la feature | test artificiale (indirizzo volutamente errato dietro marker `K2SE_FAULT_TEST`) → log e gioco che continua |
| F2.6 `[x]` | Routine 889–895 (introspezione) + header `nss/nwscript_k2se.nss` + `routine_id_test.py` aggiornato | `routine_id_test.py` PASS; `deploy_test.py` rifiuta bytecode non coerente |
| F2.7 `[x]` | `deploy_movement.py` (deriva da `deploy_test.py`): build, backup, copia DLL + ini, opzioni `--enable sprint,crouch,jump`, `--clean` | dry-run senza gioco: stampa il piano di copia; con gioco chiuso: installa |
| F2.8 `[x]` | Build 32-bit pulita (`build_direct.ps1`), `check_dll.py` (solo KERNEL32 + USER32 per `GetAsyncKeyState`/`GetForegroundWindow` — **nuovo import**, da accettare e documentare) | DLL prodotta, import elencati nel log di `check_dll.py` |

> Nota su USER32: finora la DLL importava solo KERNEL32. `GetAsyncKeyState`/`GetForegroundWindow` stanno in USER32. Alternativa senza import: risolvere a runtime con `GetModuleHandleA("user32")` + `GetProcAddress` (user32 è certamente caricata dal gioco). **Scelta**: risoluzione a runtime, così `check_dll.py` resta "solo KERNEL32".

### Fase 3 — SPRINT

| Task | Cosa | Accettazione |
|---|---|---|
| F3.1 `[~]` | `HookGetMaxSpeed`: chiama l'originale, applica `SpeedFactor()`; senza input logica (fattore fisso da ini) — **esperimento Q1** | 🎮 sessione S1: con `[Sprint] Factor=2.0 AlwaysOn=1` il PC corre visibilmente più veloce; animazione sincronizzata (nessun pattinamento); camera segue; nessun crash in 10 min; log `redirected 3/3` |
| F3.2 `[ ]` | Macchina a stati: `HOLD` (tasto), rampa 0.25 s (interpolazione lineare del fattore), isteresi | 🎮 S2: pressione/rilascio fluidi, nessun pop dell'animazione (frame per frame a 90 FPS cap) |
| F3.3 `[ ]` | Esclusioni: combattimento (opzione `AllowInCombat=0`), dialogo/GUI (controller disabilitato → già naturale), stealth server attivo, `walking` (B) ha precedenza, cutscene | 🎮 S2: entrare in combattimento con sprint attivo → `sprint OFF (combat)`; aprire menu → nessun effetto residuo |
| F3.4 `[ ]` | Interazione con Force Speed (che scala gli stessi valori): fattori moltiplicativi, cap totale configurabile (`MaxTotalFactor=2.5`) | 🎮 S3: Force Speed + sprint non superano il cap; nessun tunneling attraverso porte |
| F3.5 `[ ]` | Sterzo in sprint: opzione `TurnRateScale` (default 0.8) applicata tramite… (a) nulla (usa camerastyle attuale) o (b) hook del turn rate (`0x00866057` area) — decidere dopo S2 | 🎮 S3: nessuna inversione "a pattino" percepita; valori documentati |
| F3.6 `[ ]` | Effetto opzionale FOV (+5°) durante lo sprint via `k2-multi-fov` quando esisterà; **off** di default | rinviato; segnaposto nell'ini |
| F3.7 `[ ]` | Party che segue: verificare che i compagni non restino indietro in modo assurdo (follow usa `ActionMoveTo` a runrate 5.4) — se sì, opzione `PartyCatchUp` (v2, lato server) | 🎮 S3: nota nel log di sessione; decisione v2 |
| F3.8 `[ ]` | Routine NWScript: `K2SE_SetSprintFactor(float)`, `K2SE_GetIsSprinting()` per modder | battery test in `deploy_movement.py` |

### Fase 3b — Movimento direzionale da tastiera e camera con il mouse (richiesta della sera del 2026-09-02)

Renan: "il true directional movement funziona solo col joystick": con la tastiera A/D ruotano la camera e nessun tasto alimenta l'asse laterale del controller (`+0x14`), che solo lo stick scrive. Obiettivo: WASD = movimento a 8 direzioni relativo alla camera con il personaggio che si gira verso la direzione di corsa, e il mouse che ruota la camera, insieme a sprint/crouch/salto/roll.

| Task | Cosa | Accettazione |
|---|---|---|
| F3b.1 `[x]` | Hook per frame sull'`Update` del controller (vtable `0x009A4818` slot 10) invece di `GetMaxSpeed`, che il controller chiama solo mentre la velocità converge (scoperto in S1: sprint e roll reagivano solo girando col mouse) | log `movement: vtable hook [0x009A4840] Update`; sprint e roll rispondono correndo dritto 🎮 |
| F3b.2 `[x]` | WASD → assi del controller (`+0x10` avanti/indietro, `+0x14` laterale) scritti nell'hook prima che l'engine li legga; azzeramento singolo al rilascio per convivere col gamepad; `[Directional]` nell'ini con `InvertStrafe` | 🎮: W+A muove in diagonale e il personaggio si orienta verso la corsa; A/D da soli fanno strafe |
| F3b.3 `[x]` | `--remap-keys` sposta CameraRotateLeft/Right da A/D a Numpad 4/6 (`Action284A/B` 51/54 → 14/16) | `--status` senza conflitti |
| F3b.4 `[~]` | Camera con il mouse: verificare in gioco se l'opzione **Mouse Look** del gioco (bit 1 di `CClientOptions+8`, invertito nel gestore camera `0x0078C350`) fa già ruotare la camera senza tenere premuto; altrimenti K2SE chiama la rotazione dell'engine `0x007F4220(camCtrl, -dx*sign, dt)` ogni frame con il proprio delta mouse (RMB tenuto o sempre, opzione) | 🎮: muovendo il mouse la camera gira, il cursore resta usabile per cliccare |
| F3b.5 `[ ]` | Rifiniture TDM: sensibilità e inversione da ini; opzione "personaggio guarda la camera" quando fermo; sterzo ridotto in sprint (`camerastyle` o hook del turn rate) | taratura con Renan |
| F3b.6 `[ ]` | Verifica compatibilità con click-to-move, dialoghi, minigiochi (l'hook gira solo con il controller attivo) | checklist |

### Fase 4 — CROUCH

| Task | Cosa | Accettazione |
|---|---|---|
| F4.1 `[~]` | Toggle via `SetStealthState`-client (F1.1) sul PC; se il server risincronizza (F1.2/Q2) → piano B: mantenere il bit nel nostro update ogni frame; piano C: hook dei lettori | 🎮 S4: il PC cammina/idle accovacciato (`stealth`/`pausestl`), `IsStealthed()` script ritorna 0 (nessuno stealth server), nessun XP stealth, nessuna trasparenza (o gestita in F4.2) |
| F4.2 `[ ]` | Trasparenza: se `0x008B9189` la applica (Q3), neutralizzare quando il crouch è "nostro" (flag interno) | 🎮 S4: PC opaco in crouch |
| F4.3 `[ ]` | Velocità in crouch: default = comportamento engine (`appearance+0x60`, con `FEAT_STEALTH_RUN` → normale); opzione `SpeedFactor` esplicita | 🎮 S4: velocità ridotta coerente con animazione |
| F4.4 `[ ]` | Uscite automatiche: sprint, combattimento (opzione), transizione area, dialogo (ripristino dopo) | 🎮 S5: nessun crouch "fantasma" dopo un dialogo o un caricamento |
| F4.5 `[ ]` | Camera più bassa in crouch: opzione `CameraHeightDelta` (via `camerastyle` height per stile o hook camera) — valutare dopo S4 | decisione documentata |
| F4.6 `[ ]` | Salvataggi: il crouch è solo client → non persiste; verificare che caricare un salvataggio con crouch attivo non lasci stati incoerenti | 🎮 S5: save/load ×3 |
| F4.7 `[ ]` | Routine `K2SE_SetCrouch(int)`, `K2SE_GetCrouch()` | battery test |

### Fase 5 — JUMP (funzionale) e ROLL

**Perché è la fase più difficile.** L'engine non ha aria: la Z di una creatura è quella della faccia walkmesh sotto di lei, e il controller scrive la posizione ogni frame. Un salto vero richiede che K2SE (1) prenda il controllo della posizione per la durata dell'arco, (2) impedisca all'engine di riportare la Z a terra, (3) validi traiettoria e atterraggio con le stesse strutture walkmesh dell'engine, (4) restituisca il PC all'engine in uno stato coerente (stanza corrente, trigger, camera, animazione). Si procede a scalini: ogni scalino è una release utilizzabile.

**J0 — Reverse engineering mirato (statico)**

| Task | Cosa | Accettazione |
|---|---|---|
| F5.0.1 `[x]` | Il commit di posizione nel controller: `0x00543F10(srv, &vec)` (server) a `0x008679D3` e `client->vtable+0x88(&vec)` a `0x008679ED`; da dove viene `[ebp-0x168]` (regione `0x00867600..0x008679D0`, costante 900.0 a `0x00A10F58`): qui l'engine calcola la Z (query walkmesh) e clippa il movimento | funzioni di query walkmesh identificate con firma (`GetElevation`/`TestWalk`-like) |
| F5.0.2 `[x]` | Handler NWScript `JumpToLocation`/`ActionJumpToLocation`/`JumpToObject` e `CutsceneMove` (`0x0066DC80`): la sequenza server per riposizionare una creatura (SetPosition + aggiornamento stanza + trigger) | sequenza documentata; funzione riutilizzabile per l'atterraggio |
| F5.0.3 `[~]` | Funzioni walkmesh server: walkable a (x,y) → Z e faccia (`CSWSArea`/`CSWRoomSurfaceMesh`: K1 `CheckAABBWalkable`, `ClippedLineSegmentWalkable`), test segmento (line-of-sight materiale) | firme e indirizzi nel CSV; verifica in J1 |
| F5.0.4 `[ ]` | Dove il server ri-applica la Z della creatura fuori dal controller (heartbeat/AI update) per evitare che la "riporti a terra" durante l'arco | punto identificato o dimostrato inesistente per il PC guidato |
| F5.0.5 `[ ]` | Camera: quale posizione segue (client o server) e se ha uno smoothing verticale | nota di design |

**J1 — Salto sul posto (prova del controllo di posizione)** 🎮 S6

| Task | Cosa | Accettazione |
|---|---|---|
| F5.1.1 `[~]` | Redirezione della `call 0x00543F10` a `0x008679D3` verso `HookCommitPosition(srv, vec)`: durante il salto sostituisce `vec.z` con `z0 + h(t)` (parabola: `h = v0·t − ½·g·t²`, `v0 = 4.4`, `g = 9.81` → apice 0.99 m a 0.45 s, durata 0.9 s) e rispecchia la stessa Z sul client | 🎮 S6: il PC si alza e riscende sul posto; la camera segue senza scatti; nessun "ritorno a terra" a metà arco (F5.0.4) |
| F5.1.2 `[ ]` | Animazione placeholder: overlay `diveroll` o posa statica (`vtable[0xD0]` con velocità 0 per congelare la corsa) — scelta dopo S6 | video/frame |
| F5.1.3 `[ ]` | Fine salto: consegna all'engine con la sequenza di F5.0.2 (SetPosition a terra + aggiornamento stanza); stato `airborne=0` | nessuna riga `stuck`, `IsRunning` coerente |

**J2 — Salto in avanti sullo stesso walkmesh** 🎮 S7

| Task | Cosa | Accettazione |
|---|---|---|
| F5.2.1 `[ ]` | In aria la velocità orizzontale è congelata a quella del decollo (sterzo ridotto `AirControl=0.2`); l'input W/S non accelera; `MaxDistance=2.5` (3.5 in sprint) ottenuto limitando la velocità orizzontale in aria | 🎮 S7: arco credibile, distanza ≈ 2.5 m |
| F5.2.2 `[ ]` | Atterraggio: query walkable a (x,y) di arrivo; se Z_faccia entro `LandTolerance=0.5 m` dalla parabola → atterra lì; altrimenti prosegue la caduta fino a `MaxFall=3 m`; se non trova walkable → **abort**: ritorno al punto di decollo | 🎮 S7: saltare verso un muro → abort pulito; saltare in corridoio → atterraggio normale |
| F5.2.3 `[ ]` | Trigger e stanze: attraversare un trigger di transizione area saltando deve comportarsi come a piedi (o essere impedito): decidere in S7 | comportamento documentato |

**J3 — Ostacoli e vuoti** 🎮 S8

| Task | Cosa | Accettazione |
|---|---|---|
| F5.3.1 `[ ]` | Traiettoria: test segmento partenza→atterraggio contro facce **non walkable con line-of-sight bloccante** (pareti) → se interseca, abort; le facce non walkable **senza** LOS-block (ringhiere basse, casse) si possono sorvolare | 🎮 S8: saltare una cassa bassa a Peragus → sì; saltare "attraverso" una parete → no |
| F5.3.2 `[ ]` | Salita su sporgenze: atterraggio ammesso su facce fino a `MaxStepUp=1.0 m` sopra la partenza; discesa fino a `MaxFall` | 🎮 S8: cassa/piattaforma bassa raggiungibile |
| F5.3.3 `[ ]` | Regole di sicurezza: niente salto se `+0x1114` dice immobile, in combattimento (`AllowInCombat=0`), in stealth server, in crouch (prima esce dal crouch), con GUI/dialogo (controller spento), durante un roll; cooldown 0.4 s dopo l'atterraggio | log delle transizioni |
| F5.3.4 `[ ]` | Anti-softlock: se dopo l'atterraggio il PC risulta fuori walkmesh (query fallita) → teletrasporto al decollo e riga `jump: recovered` | test forzato con `K2SE_FAULT_TEST` |

**J4 — Sensazione e animazione** 🎮 S9

| Task | Cosa | Accettazione |
|---|---|---|
| F5.4.1 `[ ]` | Taratura ⚠️: `Height` (1.0), `MaxDistance` (2.5 corsa / 3.5 sprint), `AirControl`, `LandTolerance`, `MaxFall`; salto da fermo = hop verticale con spostamento minimo | valori scelti con Renan in S9 |
| F5.4.2 `[ ]` | Animazione **"jump"** autoriale: Blender 4.x + KotorBlender, `S_Male02`: decollo (0.15 s), volo (loop 0.5 s, gambe raccolte), atterraggio (0.25 s); righe `animations.2da` `jump_start/jump_loop/jump_land` con `overlay=1` | 🎮 S9: si vede, il modello torna a `run/pause` senza glitch; `AR_ERROR.LOG` pulito |
| F5.4.3 `[ ]` | Camera: se lo smoothing verticale è brusco, filtro sulla Z della camera durante l'arco (solo se necessario) | giudizio visivo |
| F5.4.4 `[ ]` | Effetti opzionali: suono di atterraggio (`snd_hitground`-like già nei modelli) | opzione ini |

**ROLL** (indipendente dal salto) 🎮 S6

| Task | Cosa | Accettazione |
|---|---|---|
| F5.R.1 `[~]` | `Alt` → `anim.PlayOverlay(client, 0x290D)`; cooldown 1.0 s; solo se il controller guida e non in combattimento (opzione) | 🎮 S6: `diveroll` mentre si corre, movimento continua |
| F5.R.2 `[~]` | `Boost=1.3` per 0.6 s sul fattore velocità (via `HookGetMaxSpeed`) | sensazione dodge; nessun attraversamento di porte chiuse |
| F5.R.3 `[ ]` | Roll durante lo sprint = "slide" (sprint mantenuto per la durata) — cfr. SkyParkour | opzione |

**Routine per modder**: `K2SE_Jump(object, float fHeight, float fDistance)`, `K2SE_GetIsAirborne(object)`, `K2SE_PlayOverlayByName(object, string)` (se Q4 lo permette).

### Fase 6 — IMPROVED COLLISION

**Tier 0 — Misurare prima di cambiare**

| Task | Cosa | Accettazione |
|---|---|---|
| F6.0.1 `[ ]` | Routine `K2SE_GetCreatureRadii(object) → string "per,cre,cam,hit"` e `K2SE_SetCreatureRadii(object, float per, float cre)` (scrittura su `[srv+0x380]+4/+8`) | 🎮 S8: banner con i raggi del PC e di Kreia/Atton; valori coerenti con `appearance.2da` |
| F6.0.2 `[ ]` | Diagnostica "blocco": nel nostro update, quando la velocità di guida richiesta è > 0 ma lo spostamento reale ≈ 0 per > 0.3 s → log `stuck at (x,y) near <creatura/placeable più vicini>` | 🎮 S8: incastrarsi di proposito dietro Kreia produce la riga |
| F6.0.3 `[ ]` | Script `k2-improved-collision/tools/perspace_audit.py`: distribuzione raggi per categoria (PC, party, commoner, droidi, creature grandi) e proposta di patch | output CSV/markdown in `k2-improved-collision/docs/` |

**Tier 1 — Solo dati**

| Task | Cosa | Accettazione |
|---|---|---|
| F6.1.1 `[ ]` | `build.py` che patcha `appearance.2da` dell'installazione: `creperspace` party/PC 0.4→0.25 e `perspace` 0.35→0.25 (valori ⚠️ da tarare), lasciando invariati hostili e creature grandi; `--install/--uninstall/--show`, rifiuto se colonne inattese cambiano (schema `k2-directional-movement`) | diff leggibile; 🎮 S9: si passa accanto ai compagni nei corridoi di Peragus senza fermarsi; nessun effetto visibile sul combattimento (attacchi in mischia connettono) |
| F6.1.2 `[ ]` | Audit PWK: con PyKotor elencare i placeable più frequenti nei moduli (conteggio istanze `.git`), misurare l'ingombro del PWK vs bounding box del modello; scegliere i 10 peggiori | tabella in `docs/pwk-audit.md` |
| F6.1.3 `[ ]` | PWK ridisegnati (KotorBlender) per i 10 placeable scelti, in `override/` | 🎮 S9: casse/console non bloccano oltre il modello visibile; nessun oggetto diventa inattivabile |
| F6.1.4 `[ ]` | Compatibilità con altre mod che portano `appearance.2da` (`build.py` legge la copia presente; documentare) | README |

**Tier 2 — Runtime (K2SE)**

| Task | Cosa | Accettazione |
|---|---|---|
| F6.2.1 `[ ]` | In base a Q5/Q6: hook del raggio creatura (callback client o lettore server) che ritorna `r * SoftFactor` (default 0.5) quando **l'altra** creatura è amica/neutrale e non in combattimento; raggio pieno con ostili | 🎮 S10: il PC scivola attorno agli NPC di Nar Shaddaa; gli ostili bloccano come prima |
| F6.2.2 `[ ]` | "Cedimento" party: se il PC preme contro un compagno per > 0.4 s, il compagno riceve una `ActionMoveToLocation` di 1 m laterale (walkable check via funzione trovata in Q7 o `GetNearestWalkable`-like) — v1 semplice: solo compagni, solo fuori combattimento | 🎮 S10: i compagni si spostano; niente ping-pong |
| F6.2.3 `[ ]` | Opzione `PlayerPassThroughParty=1`: raggio 0 verso i compagni (compenetrazione tollerata) — per chi vuole il comportamento "moderno" | 🎮 S10 |
| F6.2.4 `[ ]` | Routine `K2SE_SetCollisionSoftFactor(float)` | battery |

**Tier 3 — Ambiente: muri e spigoli (dopo Q7)** 🎮 S13

| Task | Cosa | Accettazione |
|---|---|---|
| F6.3.1 `[ ]` | RE: dove il controller clippa la velocità/posizione contro il walkmesh (regione `0x008672xx`, `0x0083D170`, query di F5.0.1) e come tratta il caso "bloccato" | funzione e firma documentate |
| F6.3.2 `[ ]` | Prototipo *collide-and-slide* multi-piano: fino a 4 iterazioni di clip contro i piani incontrati (stile `PM_SlideMove`, `overclip 1.001`), niente azzeramento della velocità se il primo piano non è parallelo al movimento; vincolo assoluto: destinazione sempre walkable | 🎮 S13: spigoli di Peragus/Telos non agganciano; pareti sottili non attraversate; movimento diagonale contro un muro scorre |
| F6.3.3 `[ ]` | Anti-aggancio angoli: se due piani formano un angolo concavo stretto (< 60°) e la velocità residua è < 10% → micro-passo laterale verso il lato libero | 🎮 S13: nessuno stop secco negli angoli delle porte |

**Tier 3b — Pavimento: gradini, bordi, quota** 🎮 S13

| Task | Cosa | Accettazione |
|---|---|---|
| F6.3b.1 `[ ]` | RE: come il controller passa da una faccia walkmesh all'altra con Z diversa (bordi, gradini) e dove si può inceppare (tolleranza attuale) | valore/tolleranza documentati |
| F6.3b.2 `[ ]` | Tolleranza di gradino configurabile (`StepTolerance=0.35 m`): i bordi fra facce adiacenti con differenza di quota sotto la soglia non bloccano | 🎮 S13: scale/gradini di Telos e Nar Shaddaa senza blocchi |
| F6.3b.3 `[ ]` | Quota morbida: la Z del modello segue la faccia con un filtro (evita "scattini" su facce a gradino), senza mai fermare il movimento; controllo affondamento/galleggiamento: misurare l'offset piedi–walkmesh in 5 aree e correggere l'offset di rendering se sistematico (solo client, opzionale) | 🎮 S13: nessun sussulto visibile sui bordi; piedi a terra |
| F6.3b.4 `[ ]` | Diagnostica: log `edge-stall at (x,y) dz=… faces a→b` quando il movimento si ferma su un bordo | riga prodotta nei test forzati |

**Tier 4 — Camera (opzionale, solo se Tier 1–3 chiusi)**

| Task | Cosa | Accettazione |
|---|---|---|
| F6.4.1 `[ ]` | Localizzare `UpdateCameraCollision` K2; valutare raggio camera (`cameraspace`) | decisione go/no-go documentata |

### Fase 7 — Testing e convalida

**7.1 Livelli di test**

| Livello | Cosa | Quando |
|---|---|---|
| Statico | `verify_offsets.py`, `routine_id_test.py`, `check_dll.py`, build senza warning | ad ogni build |
| Host | test del parser ini, dell'input state machine, del `callsite` su un buffer finto | ad ogni commit |
| In gioco — smoke | avvio, banner K2SE, `TEST 1..21 PASS`, `callsite … OK` | ogni sessione 🎮 |
| In gioco — feature | checklist per feature (Appendice D) | S1…S11 |
| In gioco — regressione | 30 min di gioco normale con tutte le feature attive: combattimenti, dialoghi, minigioco (swoop/pazaak), transizioni, save/load, cutscene | prima di ogni release |
| Prestazioni | FPS medi/minimi vs baseline (F0.5), tempo per frame degli hook (contatore nel log) | prima di ogni release |

**7.2 Aree di test (perché)**

| Area | Modulo | Cosa stressa |
|---|---|---|
| Ebon Hawk | `003ebo` | interni stretti, `camerastyle` EbonHawk, compagni ovunque → collisioni Tier 1/2 |
| Peragus | `101per`–`106per` | corridoi, porte, Kreia/Atton in follow, minigioco… |
| Telos Citadel | `201tel`–`2xxtel` | folla, NPC scriptati, dialoghi frequenti → esclusioni |
| Nar Shaddaa Refugee | `301nar`, `302nar` | densità NPC massima → Tier 2 |
| Dxun | `401dxn` | esterni, pendenze, `camerastyle` OutDoor → sprint/turn rate, sliding su terreno |
| Onderon Iziz | `501ond` | piazza grande, camera | 
| Korriban | `701kor` | pendenze, sabbia | 

**7.3 Convalida di compatibilità**

- Mod attive di Renan (TSLRCM, texture pack, UI widescreen, camerastyle di directional-movement): nessuna interferenza attesa; verificare che `appearance.2da` di Tier 1 non collida con UCO REDUX (non tocca 2DA) e con altre mod (grep dei 2DA in Workshop).
- Wrapper Mesa / ReShade (`opengl32.dll`): irrilevanti per `version.dll`; annotare.
- Exe LAA / pristino: fingerprint già maschera `Characteristics`.
- Workshop "Verifica integrità": `version.dll` è aggiunta → sopravvive; l'ini pure.
- Salvataggi: nessuna scrittura persistente (client-only); Tier 1 2DA: i raggi si ricaricano al load → reversibile.

**7.4 Criteri di uscita della convalida**

- 0 crash attribuibili in ≥ 3 sessioni da 30 min con tutte le feature attive.
- FPS medi entro −3% dalla baseline.
- Tutte le checklist di Appendice D spuntate con prova.
- Log di sessione archiviati in `docs/sessioni/`.

### Fase 8 — Packaging, documentazione, pubblicazione

| Task | Cosa | Accettazione |
|---|---|---|
| F8.1 `[ ]` | Struttura release **K2SE core 0.2.0**: `version.dll`, `README`, `nss/k2se.nss`, `nwscript_k2se.nss`, licenza MIT, `CHANGELOG` | zip riproducibile da script `tools/release.py` |
| F8.2 `[ ]` | **K2 Jump/Crouch/Sprint 1.0**: `k2se_movement.ini` (sezioni Sprint/Crouch/Jump), `override/` (v1: `S_Male02.mdl/.mdx`, `animations.2da` patch script), README ITA/ENG con: requisiti (K2SE), tasti, limiti (salto cosmetico), compatibilità, disinstallazione | zip + README |
| F8.3 `[ ]` | **K2 Improved Collision 1.0**: `k2se_movement.ini` sezione `[Collision]`, `build.py` 2DA, PWK, README con tiers e "cosa aspettarsi" | zip + README |
| F8.4 `[ ]` | Installazione alternativa via HoloPatcher (`changes.ini` per 2DA) — opzionale | testato con HoloPatcher su copia pulita |
| F8.5 `[ ]` | Pagine Deadly Stream (categoria Mods → TSL) e Nexus (kotor2): descrizione, screenshot/gif (sprint, crouch, roll, collisioni), requisiti, changelog; **licenza e crediti** (KPM per gli indirizzi importati, reone/KotOR.js come documentazione, comunità DS) | pagine pubblicate (dopo OK di Renan) |
| F8.6 `[ ]` | Contattare LaneDibello (KPM) con il CSV indirizzi K2 verificati (`export_to_kpm.py`) — obiettivo del README K2SE | messaggio inviato / PR aperta |
| F8.7 `[ ]` | Aggiornare `DOSSIER.md` (§6) e i README delle cartelle | diff |

### Fase 9 — Conclusione e manutenzione

| Task | Cosa | Accettazione |
|---|---|---|
| F9.1 `[ ]` | Definizione di "fatto": F7.4 soddisfatto, release pubblicate, issue tracker aperto (GitHub) con template bug (log + save) | link |
| F9.2 `[ ]` | Backlog v2 documentato: strafe (Q8), party sprint (lato server), keymap/menu opzioni, gamepad, FOV sprint, Post-Combat Movement Fix (Q9), crash handler, Tier 4 camera | `docs/backlog.md` |
| F9.3 `[ ]` | Retrospettiva: cosa ha richiesto più sessioni 🎮 del previsto e perché (per il prossimo progetto: k2-multi-fov, tessellation, high-poly Ebon Hawk) | `docs/retro.md` |

---

## 6. Protocollo di lavoro con Renan (sessioni 🎮)

1. **Io** preparo build + ini + checklist e scrivo nel messaggio finale: *"Pronto per la sessione Sx: chiudi il gioco (salva prima), poi esegui `python K2SE/tools/deploy_movement.py --install --enable sprint`"*.
2. **Tu** chiudi il gioco, salvi, lanci il comando, riavvii il gioco, carichi il salvataggio di test (consiglio: un salvataggio dedicato "TEST" sull'Ebon Hawk + uno a Nar Shaddaa).
3. Segui la checklist (Appendice D) — bastano 10–20 minuti; se qualcosa va storto, `Esc` → esci → `python K2SE/tools/deploy_movement.py --clean` ripristina la DLL precedente (backup automatico).
4. Mi mandi (o lascio che legga) `%LOCALAPPDATA%\K2SE\k2se.log` e due righe di impressioni ("lo sprint è troppo veloce", "la camera strattona").
5. Io analizzo, correggo, e si ripete. **Mai due feature nuove nella stessa sessione**: una variabile alla volta.
6. **Rollback totale**: cancellare `version.dll` e `k2se_movement.ini` dalla cartella del gioco; `override/appearance.2da` si rimuove con `build.py --uninstall`.

Cosa NON farò mai senza il tuo via: toccare il Workshop, i salvataggi, `swkotor2.exe`. `swkotor2.ini` viene modificato **solo** da `deploy_movement.py --remap-keys` (che hai autorizzato scegliendo Space e C), a gioco chiuso, con backup `swkotor2.ini.backup-<data>`.

---

## 7. Rischi e mitigazioni

| Rischio | Prob. | Impatto | Mitigazione |
|---|---|---|---|
| La velocità del PC è clampata anche lato server (non emerso, ma non escluso) | media | sprint inefficace | S1 lo rivela in 5 minuti; piano B: scalare anche `stats+0x1AC` (runrate) del PC per la durata dello sprint con ripristino |
| Il server risincronizza il bit stealth client ogni frame | media | crouch lampeggia | F1.2 lo dice prima; piano B/C in F4.1 |
| `0x290D` non generalizza a una riga 2DA nuova | media | jump v1 richiede lookup per nome | F1.4; alternativa `SetAnimation` per nome |
| Le redirezioni dei call-site vengono sovrascritte da un'altra mod/patch (KPM, 3C-FD) | bassa | hook perso, log lo mostra | probe byte prima di scrivere; refuse + messaggio se i byte non sono quelli attesi |
| Ridurre `creperspace` rompe il combattimento in mischia (portata) | media | attacchi a vuoto | Tier 1 tocca solo party/PC; S9 verifica; `hitdist` non si tocca |
| Compagni che "cedono" creano oscillazioni (ping-pong) | media | fastidio | isteresi 0.4 s, una sola azione per 2 s, solo fuori combattimento |
| Crash da puntatore sbagliato in un accessore nuovo | bassa (SEH) | sessione persa | `crashguard`, `LooksLikePointer`, transizioni loggate |
| Perdita di FPS per poll input | molto bassa | — | `GetAsyncKeyState` ×3/frame è trascurabile; misurato in F7 |
| Versione DLL diversa tra test e release | bassa | bug non riproducibili | `deploy_movement.py` logga hash SHA-256 della DLL installata; il log K2SE stampa la versione |
| Blender/KotorBlender: curva di apprendimento per l'animazione di salto | alta | v1 slitta | v0 (`diveroll`) è già una release valida; v1 è un obiettivo separato |
| Definizione di "improved collision" | — | — | ✅ confermata (include ambiente e pavimento) |
| Il server riporta a terra la Z del PC durante l'arco (F5.0.4) | media | salto "tremola" o non parte | intercettare anche quel punto o disabilitarlo per la durata dell'arco |
| Atterraggio su isole walkable non previste (sequence break) | alta | possibile softlock narrativo | `MaxDistance`/`MaxStepUp` prudenti; v2: test di connettività del pathfinding; documentazione |
| Salvataggio a metà arco | bassa | PC a mezz'aria al load | durata 0.9 s; al load lo stato K2SE è azzerato e l'engine ri-snappa alla prima mossa; F5.3.4 recovered |
| Query walkmesh chiamate fuori dal thread/contesto giusto | media | crash | usare solo funzioni server dal thread di gioco (l'hook gira nel controller: stesso thread) |

---

## 8. Stime (sessioni di lavoro mie + sessioni 🎮 tue)

| Fase | Lavoro mio | Sessioni 🎮 |
|---|---|---|
| F0–F1 | 2–3 blocchi | 1 (baseline) |
| F2 | 2 blocchi | 0 |
| F3 Sprint | 1–2 blocchi | 3 (S1–S3) |
| F4 Crouch | 1–2 blocchi | 2 (S4–S5) |
| F5 Roll + Jump J1 | 2 blocchi | 1 (S6) |
| F5 Jump J2–J3 | 3–4 blocchi (RE + fisica + validazione) | 2 (S7–S8) |
| F5 Jump J4 (animazione) | 3–5 blocchi (Blender) | 1 (S9) |
| F6 Tier 0–1 | 2 blocchi | 2 (S8–S9) |
| F6 Tier 2 | 2–3 blocchi | 1–2 (S10) |
| F6 Tier 3 + 3b | 3–4 blocchi | 1–2 (S13) |
| F7 regressione | 1 blocco | 3 |
| F8 release | 1–2 blocchi | 0 |

Ordine consigliato per massimizzare il valore presto: **F0 → F1 (incluso J0) → F2 → F3 (S1!) → F5 Roll + J1 → F4 → F5 J2–J3 → F6 Tier 0–1 → F6 Tier 2 → F5 J4 → F6 Tier 3/3b → F7 → F8**.

---

## Appendice A — Indirizzi e offset K2 (Steam/Aspyr 1.0.2.0) da inserire nel CSV

| Nome proposto | VA / offset | Tipo | Stato | Nota |
|---|---|---|---|---|
| `CSWPlayerControlCamRelative::Update` | `0x00865830` | function | V | `ret 4`, arg dt |
| `CSWPlayerControlCamRelative::GetMaxSpeed` | `0x00867B40` | function | V | `__thiscall`, ret float ST0 |
| `CSWPlayerControlCamRelative::GetAccel` | `0x00867CA0` | function | V | |
| `CSWPlayerControlCamRelative::GetAcceleration` | `0x00867AB0` | function | V | `ret 0xC` |
| call-site GetMaxSpeed #1/#2/#3 | `0x0086603C`, `0x00867336`, `0x00867AC7` | callsite | V | `E8 rel32` |
| call-site GetAccel #1 | `0x00867ABC` | callsite | V | |
| `PlayerControl::+0x04 player_id`, `+0x08 camera`, `+0x0C enabled`, `+0x10 up_down`, `+0x14 left_right`, `+0x18 walking`, `+0x44 state`, `+0x5C prev_state` | offset | V | |
| `walk modifier factor` | `[0x0098C014] = 0.5f` | constant | V | |
| `CSWCCreature::GetDriveAccel` | `0x0077F600` | function | V | |
| `CSWCCreature::SetDriveSpeed` | `0x00776E10` | function | V | scrive +0x3C8/+0x3CC |
| `CSWCCreature::+0x224 appearance`, `+0x2EC flags (bit0 stealth)`, `+0x310 stats?`, `+0x3C8 drive_speed`, `+0x3F8 running (byte)` | offset | V | +0x3F8 da `IsRunning` handler |
| `CSWCCreatureAppearance::+0x58 accel`, `+0x5C maxspeed`, `+0x60 stealth speed` | offset | V/H | nomi H |
| `CSWCCreature::SetStealthState` (contiene) | `0x00809E01` | function | V (sito) | inizio da F1.1 |
| `CSWCCreature::GetAnimBase` | `0x007ED830` | function | V | |
| `CSWCAnimBase vtable +0xE0 (MapAnimCode)`, `+0x44 (PlayOverlay)` | vtable slot | V | |
| `overlay code DIVE_ROLL` | `0x290D` | constant | V | |
| `CClientExoApp::GetClientObject` | `0x0073F550` (→ `0x0078BDF0`) | function | V | |
| `CSWCObject::GetServerObject` | `0x0077D800` | function | V | |
| `CSWSCreature::+0x380 pathfind_info`, `+0x1114 move_flags(word)`, `+0x1120 mode_flags`, `+0x1184 appearance`, `+0x1198 stats`, `+0x11AC ?`, `+0x11EC driveaccl` | offset | V | |
| `CPathfindInformation::+0x08 creperspace`, `+0x10 cameraspace`, `+0x14 hitradius` | offset | V | `+0x04 perspace` H |
| `CSWSCreature::HasModeFlag` | `0x00563D70` | function | V | `(this+0x1120 & arg) != 0` |
| `CSWSCreatureStats::+0x1A4 movement_rate`, `+0x1A8 walkrate`, `+0x1AC runrate` | offset | V | |
| `CSWSCreatureStats::SetMovementRate` | `0x006BA320` | function | V | già in CSV |
| `Appearance2DA col index globals` | `0x00A0FD9C…0x00A0FDEC` | global | V | vedi studio §3.1 |
| `Load2DA appearance columns` | `0x006E7E40..0x006E841B` | function | V | |
| `CSWSCreature::LoadAppearance` | `0x0057FD00..0x00580200` | function | V (range) | |
| handler `PlayOverlayAnimation` | `0x0068F440` | routine 854 | V | |
| handler `IsStealthed` / `IsRunning` / `GetMovementRate` | `0x0068BCF0` / `0x0069B060` / `0x00683B30` | routine 810/824/496 | V | |
| `CTwoDimArrays+0x78 camerastyle` | offset | V | |
| `camerastyle MaxTurnRate/MinTurnRate` strings | `0x009A4854` / `0x009A4848` | string | V | letti a `0x00865709/0x00865743` |

## Appendice B — Nomi K1 (KPM) da ritrovare in K2

`CSWSCreature::BumpFriends`, `GetIsCreatureBumpable`, `UpdatePersonalSpace`, `ComputeModifiedMovementRate`, `Get/SetMovementRateFactor`, `SetStealthMode`; `CSWCCreature::ComputeSpeedFactor`, `SetSWAnimationSpeed`, `SetStealthState`, `IsStealthCapable`; `Global::GetPersonalRadius`, `GetCreatureRadius`; `CAvoidCreature::*`; `CSWCModule::UpdateCameraCollision*`; `CSWRoomSurfaceMesh::CheckAABBWalkable`, `ClippedLineSegmentWalkable`; `CSWPlayerControlCamRelative::SetPlayerWalking`, `ResetDriveAcceleration`, `Control`; `CSWSEffectListHandler::OnApplyMovementSpeedIncrease`; globali `RENDER_PERSONAL_SPACE`, `RENDER_AABB`, `RENDER_WIREFRAME`.

## Appendice C — `k2se_movement.ini` di esempio

```ini
; K2SE movement features - metti questo file accanto a swkotor2.exe.
; Ogni sezione ha Enabled=0/1. I tasti sono nomi VK (LSHIFT, LALT, SPACE, C, N, F6...) o esadecimali (0x41).
; ATTENZIONE: Space e C sono legati dal gioco a Pausa (action241) e ActionRight (action281b).
; deploy_movement.py --remap-keys li sposta (Pausa -> F9, ActionLeft/Right -> frecce) con backup di swkotor2.ini;
; in alternativa fallo dal menu Opzioni -> Tasti. All'avvio la DLL legge swkotor2.ini e scrive nel log i conflitti.

[Sprint]
Enabled=1
Key=LSHIFT
Factor=1.6            ; moltiplicatore della velocita' massima di guida (5.4 m/s -> 8.64)
RampSeconds=0.25
AllowInCombat=0
MaxTotalFactor=2.5    ; cap con Force Speed
CancelCrouch=1

[Crouch]
Enabled=1
Key=C
Toggle=1
SpeedFactor=0         ; 0 = usa la velocita' stealth dell'engine
ExitOnCombat=1
CameraHeightDelta=0   ; riservato

[Jump]
Enabled=1
Key=SPACE
Height=1.0            ; apice in metri (v0 = sqrt(2*g*h) = 4.43 m/s)
MaxDistance=2.5       ; orizzontale, corsa
MaxDistanceSprint=3.5
AirControl=0.2
LandTolerance=0.5
MaxStepUp=1.0
MaxFall=3.0
AllowInCombat=0
Cooldown=0.4
Animation=diveroll    ; v0 placeholder; v1: jump

[Roll]
Enabled=1
Key=LALT
Cooldown=1.0
Boost=1.3
BoostSeconds=0.6
AllowInCombat=0

[Collision]
Enabled=0             ; Tier 2/3 runtime; il Tier 1 (2DA/PWK) si installa con build.py
SoftFactorFriendly=0.5
PlayerPassThroughParty=0
PartyYield=1
PartyYieldDelay=0.4
SlideIterations=4     ; Tier 3
StepTolerance=0.35    ; Tier 3b

[Debug]
Banner=0
LogTransitions=1
```

## Appendice D — Checklist per sessione 🎮

**Smoke (ogni sessione)**: banner `K2SE 0.2.0 active`; log `fingerprint OK`, `callsite 3/3 OK`, `TEST 1..21 PASS`; nessuna riga `REFUSED`.

**S1 Sprint esperimento**: `AlwaysOn=1 Factor=2.0` → corsa più veloce visibile; animazione senza pattinamento; camera segue; attraversare 3 porte; 10 min senza crash; annotare se i compagni restano indietro.

**S2 Sprint tasto**: premere/rilasciare Shift durante la corsa ×20; rampa fluida; cambiare direzione in sprint; walk (B) + Shift → walk vince; menu aperto con Shift premuto → nessun effetto; entrare in combattimento → `sprint OFF (combat)`.

**S3 Sprint interazioni**: Force Speed + sprint (cap); sprint in Ebon Hawk (stile camera stretto); Dxun pendenze; save/load con sprint premuto.

**S4 Crouch**: toggle Alt → postura `stealth`; camminare/fermarsi (`pausestl`); `IsStealthed`=0 (banner); nessuna trasparenza; velocità ridotta; Shift → esce dal crouch.

**S5 Crouch robustezza**: dialogo in crouch → dopo il dialogo stato coerente; transizione area; save/load ×3; combattimento → esce (se `ExitOnCombat=1`).

**S6 Roll + salto sul posto**: Alt → `diveroll` mentre si corre, cooldown, nessun attraversamento porte chiuse, in combattimento non parte; Space da fermo → il PC si alza ~1 m e riscende, camera senza scatti, nessun ritorno a terra a metà arco.

**S7 Salto in avanti**: in corsa Space → arco e atterraggio ~2.5 m avanti sullo stesso pavimento; verso un muro → abort e ritorno; su trigger di transizione → comportamento deciso.

**S8 Ostacoli**: cassa bassa a Peragus superata; parete non attraversata; sporgenza ≤ 1 m raggiunta; discesa ≤ 3 m; recovered su atterraggio fallito forzato.

**S9 Animazione e taratura**: animazione `jump` autoriale con spade/fucili/robe; `AR_ERROR.LOG` pulito; NPC non saltano; valori di altezza/distanza scelti.

**S10 Collisioni Tier 0**: banner raggi PC/party; log `stuck at …` quando ci si incastra di proposito.

**S11 Collisioni Tier 1**: Peragus/Ebon Hawk: passare accanto ai compagni nei corridoi; combattimento in mischia normale; casse/console non bloccano oltre il modello.

**S12 Collisioni Tier 2**: Nar Shaddaa: scivolare attorno agli NPC; ostili bloccano; compagni cedono senza ping-pong.

**S13 Ambiente e pavimento (Tier 3/3b)**: spigoli di Peragus/Telos senza aggancio; pareti sottili non attraversate; diagonale contro un muro scorre; scale di Telos/Nar Shaddaa senza blocchi; nessun sussulto sui bordi; piedi a terra.

**Regressione release**: 30 min di gioco normale, tutte le feature ON: combattimento, dialoghi, pazaak, swoop, transizioni, save/load, cutscene; FPS vs baseline.

## Appendice E — Glossario

**K2SE** script extender K2 (DLL proxy `version.dll`) · **routine** funzione NWScript identificata da un ID (877+ = estese) · **call-site redirection** riscrittura del `rel32` di una `call E8` · **RK4** integratore Runge-Kutta usato dal controller · **overlay** animazione sovrapposta al movimento · **creperspace/perspace** raggi di collisione/pathfinding di `appearance.2da` · **PWK/DWK/WOK** walkmesh di placeable/porte/stanze · **marker file** file vuoto che abilita un'opzione · **probe** verifica byte a un indirizzo prima di fidarsi.

## Appendice F — Fonti

- Studio: `docs/2026-09-02-studio-movimento-collisioni.md`; disassembly: `k2-jump-crouch-sprint/docs/re/`.
- K2SE: `K2SE/DESIGN.md`, `README.md`, `docs/*.md`, `data/k2se_addresses.csv`.
- k2-directional-movement: `README.md` (controller, turn rate).
- reone `libs/game/object/area.cpp` (`Area::moveCreature`), `libs/game/player.cpp`; KotOR.js `src/engine/CollisionManager.ts`, `src/module/ModuleCreature.ts`.
- Kotor-Patch-Manager (Desktop): `Patches/ExpandedKeyboardControl`, `Patches/Post-Combat Movement Fix`, `Patches/ScriptExtender/Extensions/clientCreatures.cpp`, `AddressDatabases/kotor1_0_3.db`.
- Skyrim (design): catalogo `docs/2026-09-02-catalogo-mod-skyrim-riferimenti.md` — True Directional Movement, Better Jumping AE, SkyParkour V3, Dynamic Collision Adjustment, StepUpOnto SKSE, Sprint Stuttering Fix, Dialogue Movement Enabler.
- Quake III Arena `bg_slidemove.c` (`PM_SlideMove`) come riferimento per il Tier 3.
- personal-resources: `12-SOFTWARE-ENGINEERING-EXTRA/04_Security_Cryptography/07_Reverse_Engineering_Binary_Analysis.md`, `11-GODOT-ENGINE/*`.
