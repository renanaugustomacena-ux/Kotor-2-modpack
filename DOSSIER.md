# KOTOR 2 — Dossier completo: crash, Workshop, engine e progetto remaster

*Analisi del 25/08/2026 — gioco: Steam/Aspyr 1.0.2.0, `G:\SteamLibrary\steamapps\common\Knights of the Old Republic II`*
*Sistema: Ryzen 9 9950X, RX 9070 XT (driver atioglxx 32.0.31035.1003 del 24/07/2026), 3440x1440@165, Windows 10*

---

## 1. Stato interventi (cosa è già stato fatto)

| Intervento | Stato | Note |
|---|---|---|
| Patch LAA/4GB su `swkotor2.exe` | ✅ applicata | Flag PE `0x0103 → 0x0123`. Backup: `swkotor2.exe.pre-laa-backup` nella cartella del gioco. **"Verifica integrità file" di Steam la annulla** |
| Flag compatibilità `HIGHDPIAWARE` | ✅ impostato | Registro HKCU AppCompatFlags, come gli altri tuoi giochi legacy |
| `FixTaskbar.bat` sul Desktop | ✅ creato | Doppio click = riavvia explorer e la taskbar torna (niente logout) |
| `swkotor2.ini` | ⛔ NON toccato | Volutamente: vedi §2.3 — la riga VBO è giusta così |
| Mod / cartelle Workshop | ⛔ NON toccate | Solo analisi |

---

## 2. I crash di viaggio: diagnosi e scala dei fix

### 2.1 Le evidenze raccolte

- `swkotor2.exe` è 32-bit e **non era Large Address Aware** → max 2 GB di memoria indirizzabile (verificato nel PE header, ora corretto). Con ~16 GB di texture pack in TGA **non compresso** (975 file personaggi + 728 ambienti), il caricamento di un'area satura lo spazio → il classico "Runtime Error" (abort del C runtime, infatti non lascia traccia nel registro eventi).
- Registro eventi Windows: 1 **access violation in `atioglxx.dll`** (driver OpenGL AMD) il 25/08 alle 00:33 + **4 AppHang** (14/08, 18/08, 24/08, 25/08 17:54). I freeze c'erano **dal giorno 1** della run moddata (install 13/08); le 9 mod aggiunte il 24/08 sera hanno peggiorato.
- Il pack ambienti **Unlimited World Texture Mod ha crash di transizione documentati** dagli utenti (Peragus, zone di Telos), risolti rimuovendolo: https://steamcommunity.com/sharedfiles/filedetails/comments/1834699399
- Il driver OpenGL AMD riscritto (da Adrenalin 22.7.1, luglio 2022) **rompe i giochi OpenGL 1.x come KOTOR**, con segnalazioni specifiche su RX 9070 XT (stessa firma: `atioglxx.dll` + `0xc0000005`). Fix community: wrapper Mesa (§2.4, punto 5).
- Due meccanismi indipendenti e **non mutuamente esclusivi**: (a) esaurimento memoria 32-bit, (b) fragilità del driver AMD su OpenGL legacy.

### 2.2 La scala dei fix (in ordine — UNA modifica alla volta, poi test)

1. ✅ **Patch LAA** (fatta). Testa il viaggio da Dantooine.
2. Se crasha ancora → **Frame Buffer Effects = OFF e Soft Shadows = OFF** (Opzioni grafiche avanzate in gioco). È il fix documentato per il "data overflow" al caricamento aree E il fix storico per i crash AMD. Si può rifare ON dopo la transizione incriminata.
3. Emergenza per sbloccarsi subito: in `swkotor2.ini` sezione `[Game Options]` aggiungi `EnableCheats=1`, in gioco premi ` (backtick) e usa `warp 003ebo` (Ebon Hawk) o direttamente il modulo di destinazione (es. `warp 301nar` per Nar Shaddaa, `warp 501ond` Onderon, `warp 401dxn` Dxun, `warp 701kor` Korriban) — salta la transizione che crasha.
4. Se crasha ancora → **togli Unlimited World Texture Mod** (unsubscribe da Steam): è l'unico con crash documentati, ed è solo texture = **zero rischio per i salvataggi**.
5. Se crasha ancora (pista driver AMD) → **wrapper Mesa**: scarica da https://github.com/mmozeiko/build-mesa/releases/latest il pacchetto **d3d12 x86** (NON x64: il gioco è 32-bit), metti `opengl32.dll` accanto a `swkotor2.exe`. Bypassa completamente `atioglxx.dll`. Su RX 9000 è il fix che funziona per KOTOR 1 (stesso engine). Alternativa: build `zink`. **Incompatibile con ReShade** (entrambi usano opengl32.dll).
6. Per i **freeze** (AppHang): l'engine ha il famoso bug sopra i ~90 FPS (freeze dopo i combattimenti ecc.). Con V-Sync=0 su 165 Hz vai a centinaia di FPS → Adrenalin → Gaming → profilo swkotor2 → **Frame Rate Target Control = 90**.
7. Fix definitivo consigliato (a gioco chiuso, con calma): **3C-FD Patcher v4.1.2** (feb 2026) — https://deadlystream.com/files/file/2734-fog-fix-more-3c-fd-patcher/ — ripara i bug della build Aspyr (**nebbia rotta** su Dxun & co., riflessi, musica dialoghi) E applica il 4GB/LAA. ⚠️ **Richiede l'exe NON modificato**: prima ripristina `swkotor2.exe.pre-laa-backup` → poi lancia 3C-FD con l'opzione 4GB. Sostituisce la mia patch manuale in meglio.

### 2.3 ⚠️ Il falso amico: `DisableVertexBufferObjects`

Nel tuo ini c'è `DisableVertexBufferObjects=1` **senza spazi**: è il default che la build Steam/Aspyr scrive da sola ed è **la forma stabile**. Il consiglio che gira online di "correggerla" in `Disable Vertex Buffer Objects=1` (con spazi) vale per KOTOR 1 / build vecchie: sulla build Aspyr dà +20-30 FPS ma **causa crash semi-casuali nei moduli** (documentato: superficie di Telos). Fonte: https://deadlystream.com/topic/4923-full-workaround-for-disablevertexbufferoptions-in-tsl-steam-update/ e PCGamingWiki. **Non toccarla.**

---

## 3. Taskbar che sparisce

- Non è Explorer che crasha (zero eventi nel registro): è il gioco fullscreen esclusivo che, morendo o uscendo durante un cambio di modalità video, lascia la shell in stato rotto — aggravato dal mismatch DPI noto di questa macchina (cambi scaling senza sign-out).
- **Fix immediato**: doppio click su `FixTaskbar.bat` (Desktop) — riavvia `explorer.exe`. Niente più logout.
- Mitigazione: `HIGHDPIAWARE` ora impostato sull'exe. La cura vera è eliminare i crash (§2).

---

## 4. Il Workshop di KOTOR 2: come funziona davvero

Meccanica (fonti: Deadly Stream, guida Workshop di Leonard, dev TSLRCM):

- Ogni iscrizione = una cartella in `G:\SteamLibrary\steamapps\workshop\content\208580\<ID>` con dentro `override/`, `modules/`, `dialog.tlk` ecc. Il gioco le legge **tutte**.
- **Quando due mod portano lo stesso file, ne vince UNA sola e l'altra viene ignorata in silenzio.** Priorità di fatto: **vince la installata più di recente** (DarthParametric), quindi con 23 iscrizioni l'esito è imprevedibile e cambia se una mod si ri-scarica. → Ecco il tuo "non tutte funzionano".
- Regola community: **sul Workshop SOLO TSLRCM** (o TSLRCM+M4-78EP combinata); tutte le altre mod installate **a mano dentro la cartella Workshop di TSLRCM** (`...\208580\485537937\override`), perché è lì che vive il dialog.tlk. I mod build seri dicono addirittura: Workshop mai, tutto da Deadly Stream in locale.
- Il tuo TSLRCM Workshop è **1.8.6** (l'etichetta sulla pagina dice 1.8.5 ma il contenuto è aggiornato — verificato nel readme locale).
- Log del gioco: esiste solo `AR_ERROR.LOG` (warning sui modelli, non-fatali). Il tuo `Names Differ: PMBMN pmbnm` è un warning noto e **innocuo** (refuso di naming in un modello di TSLRCM/vanilla).

### 4.1 Le tue 23 mod, identificate una per una

| ID | Mod | Verdetto |
|---|---|---|
| 485537937 | **TSLRCM 1.8.6** (contenuti tagliati + bugfix) | ✅ Tieni. Base di tutto |
| 2282938060 | **Ultimate Character Overhaul REDUX** (11,2 GB, tutti i personaggi 4x) | ⚠️ Tieni se ami i personaggi HD, ma è metà del carico memoria; doppia 5 altre mod (HK47, Sion, Bao-Dur, Twi'lek, Mandalorian). L'autore stesso: con tante mod, meglio install manuale |
| 1834699399 | **Unlimited World Texture Mod** (4,7 GB ambienti 4x) | 🔴 **Primo indiziato crash** (crash di transizione documentati). Include un `opengl32.dll` (fix trasparenze) che nel Workshop è **inerte** — andrebbe accanto all'exe. Save-safe da togliere |
| 2312186259 | **High Quality Skyboxes II** (Kexikus) | ✅ Tieni: il miglior skybox mod. Ma dichiara: va installato DOPO TSLRCM (ordine non garantito sul Workshop) e **incompatibile con ogni altra mod skybox** → vedi le due sotto |
| 820840616 | **TSL Backdrop Improvements** (Kexikus, fondali spazio) | 🔴 Copia Workshop del 2017 (vecchia); con TSLRCM richiede copia manuale di `222TEL15.mdl/.mdx` nella cartella TSLRCM (mai fatta → scene spazio Telos a rischio); in conflitto skybox con HQSII |
| 489036533 | **High Quality Stars and Nebulas** (Kexikus) | 🟡 Ridondante: 10 file sovrapposti a Backdrop Improvements, superata da HQSII. Da togliere alla prossima pulizia (texture, safe) |
| 639641660 | **Widescreen UI (Stretch fix)** | ✅ Tieni: raddrizza la GUI in widescreen (file .gui) |
| 602245011 | **Animated Galaxy Map** (Sith Holocron) | ✅ OK (texture animata; versione più aggiornata su Deadly Stream) |
| 602247806 | **Malachor Lightning Retexture** | ✅ OK (il file .dds incluso è inerte: il gioco non legge DDS) |
| 511658857 | **Fixed Lightsaber Colors** | ✅ OK, texture pure |
| 583257486 | **Stealth HK47** | 🟡 OK ma collide con UCO (chi vince: imprevedibile) |
| 1151110927 | **Effixian's Bao-Dur** | 🟡 OK; l'autore la dichiara incompatibile con altre mod che cambiano Bao-Dur → collide con UCO |
| 1834631667 | **High Quality Blasters** (Sithspecter) | ✅ OK (modelli+texture armi) |
| 1834662234 | **Sion Retexture** | 🟡 OK, collide con UCO |
| 2316663650 | **Effixian's Twi'leks Females** (teste PC) | 🟡 OK (sub/unsub sicuro anche a metà run, parola dell'autore); **36 file sovrapposti a UCO** |
| 2648839547 | **Effixian's Mandalorian Reskins** | 🟡 OK, collide con UCO |
| 2841720165 | **Effixian's Grass Improvements** | 🟡 OK; 13 file sovrapposti a UWTM |
| 2190629790 / 2190644196 | **Upscaled Shock / Fire Effects** (John Doom) | ✅ OK |
| 2193435092 | **Better Credit Rewards** (script) | ⚠️ Logica di gioco: **NON togliere a metà run** |
| 3360204869 | **Better/Fixed Czerka Salvager** (script Telos) | ⚠️ Script di modulo: non togliere (zona comunque già superata) |
| 2853389296 | **Effixian's Carth Jacket** (.uti + p_atton.utc) | ⚠️ Oggetto nell'inventario = "cotto" nel save: non togliere a metà run |
| 3360211849 | **Plasteel Cylinder Reskin** | ✅ OK |

### 4.2 Setup consigliato

**Per QUESTA run**: non aggiungere/togliere nulla se non per la scala fix §2.2 (le rimozioni lì indicate sono solo texture = safe). A fine run:

**Per la PROSSIMA run (setup pulito, "remaster" serio):**
1. Unsubscribe da tutto il Workshop.
2. Base locale da Deadly Stream: **TSLRCM 1.8.6** + **K2 Community Patch 1.6.2** (https://deadlystream.com/files/file/1280-kotor-2-community-patch/) + **3C-FD Patcher** (nebbia/LAA) + Water Restoration + Stutter Fix.
3. Segui il **KOTOR 2 Full Mod Build** (aggiornato 27/07/2026, ~15,5 GB): https://kotor.neocities.org/modding/mod_builds/k2/full — installazione batch con **KOTORModSync**. Include HQSII, Backdrop Improvements v1.4, gli upscale "Ultimate", effetti JC, PartySwap, ecc. già verificati compatibili e nell'ordine giusto.
4. Nuova partita (TSLRCM & co. vogliono un new game).

---

## 5. Com'è fatto KOTOR 2 (per il tuo occhio da modder Skyrim)

### 5.1 Engine

**Odyssey Engine**: BioWare Infinity → Aurora (NWN, 2002) → Odyssey (KOTOR 2003), licenziato a Obsidian per K2 (2004). Renderer **OpenGL 1.4 fixed-function** (niente pipeline shader per i modder: gli effetti texture passano da flag TXI). Scripting **NWScript** compilato in bytecode **NCS**, eseguito da una VM nell'exe con tabella di ~850 funzioni engine hardcodata.

**Precedenza risorse** (dal più debole al più forte) — l'equivalente del load order di Skyrim:
`chitin.key + data\*.bif` (asset base) → `TexturePacks\swpc_tex_tpa/b/c.erf` (texture hi/med/low) → `modules\*.rim/.mod` (un `.mod` batte i RIM appaiati) → **cartella `override`** (file sciolti, vince quasi sempre) → cartelle Workshop (sopra il vanilla, tra loro: vince l'installata più di recente).

**Anatomia di un'area** (il "cell/worldspace" di KOTOR):
- `modules\<nome>.rim` → `module.ifo` (entry point), `<nome>.are` (proprietà area: **nebbia, luci, script**), `<nome>.git` (istanze: creature/placeable/porte/trigger/suoni)
- `<nome>_s.rim` → blueprint (UTC/UTP/UTI...) + script compilati NCS; K2 separa i dialoghi in `<nome>_dlg.erf`
- **LYT** = elenco dei modelli-stanza e posizioni; **VIS** = da ogni stanza, quali altre stanze si vedono (il culling!); ogni stanza = modello **MDL/MDX** + walkmesh **WOK**

### 5.2 Formati file

| Formato | Cos'è | Editor |
|---|---|---|
| 2DA | Tabelle regole di gioco (feat, appearance...) | Holocron Toolset / KotorTool |
| TLK | `dialog.tlk`: tutte le stringhe per StrRef | TalkEd/TLKEd |
| GFF (UTC/UTP/UTI/DLG/ARE/GIT/IFO) | Container ad albero: creature, placeable, oggetti, dialoghi, aree | K-GFF, DLGEditor, Holocron Toolset |
| ERF / RIM / MOD | Archivi risorse | ERFEdit, Holocron Toolset |
| MDL/MDX | Modelli binari (nodi/animazioni + dati vertex) | MDLEdit / MDLOps ↔ KotorBlender |
| TPC / TXI / TGA | Texture DXT con "shader hints" in coda (envmap, bumpmap, animazioni) / hints in file testo / TGA non compresso | tga2tpc; TXI = editor di testo |
| NCS / NSS | Bytecode / sorgente NWScript | nwnnsscomp (KOTOR Scripting Tool); decompiler DeNCS/NCSDecomp |
| WOK / LYT / VIS | Walkmesh / layout stanze / visibilità stanze | KotorBlender; LYT e VIS sono testo semplice |
| LIP | Lip-sync per battuta | Pipeline storica semi-morta |

### 5.3 Toolchain 2026 (l'equivalente di CK+Nifskope+xEdit)

- **Holocron Toolset / PyKotor** — l'all-in-one moderno, ATTIVO (repo OpenKotOR/PyKotor, commit mag 2026): https://deadlystream.com/files/file/1982-holocron-toolset/
- **KotorBlender** (fork seedhartha) — Blender 3.6–4.4, import/export MDL+WOK+LYT, bake lightmap (agg. apr 2025): https://deadlystream.com/files/file/1853-kotorblender-for-blender-36-and-42/
- **MDLEdit** (bead-v) — MDL binario↔ASCII: https://deadlystream.com/files/file/1150-mdledit/
- **tga2tpc** (ndix UR): https://deadlystream.com/files/file/1152-tga2tpc/
- **K-GFF** / **DLGEditor** (tk102) — editor GFF/dialoghi
- **KOTOR Scripting Tool** (nwnnsscomp): https://deadlystream.com/files/file/191-kotor-scripting-tool-2021/ ; decompiler: NCSDecomp / ncs2nss
- **HoloPatcher** (successore moderno di TSLPatcher) + **KOTORModSync** (installer batch di mod build)
- Sorgenti script vanilla decompilati: https://github.com/KOTORCommunityPatches/Vanilla_KOTOR_Script_Source

### 5.4 Fattibilità remaster, punto per punto

- **Texture** ✅ Maturo: pipeline TGA→TPC (DXT + TXI hints). Standard community = **2K** (i 4K esistono ma sono per lo più sprecati); il limite vero non è il formato ma la memoria del processo 32-bit → LAA obbligatorio. La tua idea di ritexturare è fattibilissima OGGI.
- **Modelli 3D** ✅ Maturo: KotorBlender/MDLEdit; limite **65.535 vertici-texture per mesh part** (indici 16-bit) — si aggira spezzando in più part. Remodel high-poly di teste/armi/stanze sono routine.
- **LOD** ❌ Non esiste un sistema LOD a distanza: solo **culling per stanze via VIS**. Le aree sono piccole per design. Non c'è un "LOD da migliorare" alla Skyrim — un LOD vero è territorio da script extender/engine reimplementation.
- **Fog / draw distance** ✅/⚠️ La nebbia è **per-area nei file ARE**: campi `SunFogOn`, `SunFogNear`, `SunFogFar`, `SunFogColor` — editabili oggi con K-GFF/Holocron Toolset (una mod "atmosfere riviste" è fattibile subito). Bonus: la build Aspyr ha la nebbia BUGGATA (Dxun ecc.), riparata dal 3C-FD Patcher. Non esiste invece un vero controllo draw-distance: la profondità è fatta di fog + skybox/backdrop.
- **Skybox** ✅ HQSII dimostra il massimo possibile: ri-render in Terragen + sostituzione dei modelli skybox.
- **Shader/lighting** ❌ Fixed-function: niente shader modding. ReShade funziona (OpenGL) ma è incompatibile col wrapper Mesa (§2.2 p.5) — scegli uno dei due.
- **UI ultrawide** ⚠️ A 3440x1440 il rendering è nativo ma la UI 21:9 non è perfetta; il tuo Widescreen UI fix sistema lo stretch; esiste un fix dialoghi/letterbox 21:9 ma testato su exe GOG/UniWS, non garantito su Aspyr.
- **Engine reimplementation** (la via per il "vero" remaster): **KotOR.js** (TS/three.js, MOLTO attivo — commit agosto 2026, include la suite "KotOR Forge"), **reone** (C++/GL3.3, il più completo architetturalmente ma dormiente da apr 2025), NorthernLights/Unity (fermo 2022), xoreos (K2 non giocabile). **Nessuno permette ancora di finire K2.**

---

## 6. Il progetto "K2SE" — script extender per KOTOR 2

> **➡️ Superato da un documento dedicato:** `K2SE\DESIGN.md` (26/08/2026) contiene il design completo, con gli indirizzi della VM verificati byte per byte, l'architettura scelta, il piano di reverse engineering e le milestone. Quanto segue resta come inquadramento iniziale.

### Stato dell'arte (verificato ad agosto 2026)

- **Per K2 NON esiste un SKSE-equivalente maturo.** La nicchia è aperta.
- **K1SE — KotOR Script Extender** (2025, solo KOTOR 1): proxy di `binkw32.dll` che inietta nuove funzioni chiamabili da NWScript (feat permanenti, scrittura skill/saving throw, storage chiave-valore...). **Il progetto da studiare riga per riga.** Nexus: https://www.nexusmods.com/kotor/mods/1852 — GitHub: https://github.com/Brotaku-Vengeant/Kotor-Script-Extender-Public-
- **Kotor Patch Manager** (LaneDibello, beta): framework di **patching runtime via DLL injection per K1 E K2** (hook simple/replace/detour/static, exe su disco mai modificato), con tra gli esempi un embrione di script extender: https://github.com/LaneDibello/Kotor-Patch-Manager
- Letteratura: **NWNX** (l'extender di Neverwinter Nights, stesso ceppo Aurora) = vent'anni di architettura collaudata per "hookare la VM e registrare nuove funzioni".
- Know-how exe: 3C-FD Patcher, "KOTOR Editable Executable" (https://deadlystream.com/files/file/1320-kotor-editable-executable/).

### Perché K2 è un bersaglio favorevole

1. **Un solo exe, congelato dal 2015** (1.0.2.0) → una tabella di indirizzi hardcodata vale per sempre (niente rincorsa alle patch come SKSE).
2. **32-bit, `RELOCS_STRIPPED`, niente ASLR** → image base fissa, ogni funzione a indirizzo noto (verificato nel PE header).
3. **Vettore di iniezione banale e già dimostrato**: il gioco carica DLL dalla propria cartella (`opengl32.dll` wrapper già usato dalle mod; `binkw32.dll`/`mss32.dll` le alternative classiche).

### Architettura di riferimento (il modello K1SE/NWNX)

```
proxy DLL (binkw32/opengl32) accanto all'exe
  → all'avvio: hook della dispatch table della VM NWScript
     (le "azioni" numerate definite in nwscript.nss)
  → registra nuovi routine ID oltre le ~850 vanilla
  → pubblica un nwscript.nss esteso per i mod author
  → i modder chiamano le nuove funzioni da NWScript puro
     (zero gimmick lato utente: è "il linguaggio del gioco")
```

Strumenti: Ghidra (RE dell'exe — la community ha già mappe parziali dei simboli, vedi PyKotor/xoreos/reone come documentazione dei formati e KPM per gli offset), MinHook/Detours per l'hooking x86, e il corpus di script vanilla decompilati come test suite.

### MVP suggeriti (sinergia diretta col tuo remaster)

1. Controllo runtime di **fog/far plane per-area** (leggi/scrivi i valori ARE in memoria) → il "fog of war/draw distance" che volevi.
2. **Camera/FOV API** (oggi il FOV non è modificabile pulito).
3. Storage persistente chiave-valore per i modder (il "co-save" di SKSE).
4. Hook `OnModuleLoad`/`OnHeartbeat` estesi + console comandi custom.
5. Gestione cache texture (mitiga i limiti di memoria per i pack 4K).

---

## 7. Link rapidi

- PCGamingWiki K2: https://www.pcgamingwiki.com/wiki/Star_Wars:_Knights_of_the_Old_Republic_II_-_The_Sith_Lords
- FAQ community: https://kotor.neocities.org/faq/k2 — Mod build: https://kotor.neocities.org/modding/mod_builds/k2/full
- Deadly Stream (l'hub del modding KOTOR): https://deadlystream.com
- TSLRCM: https://deadlystream.com/files/file/578-tsl-restored-content-mod/ — K2CP: https://deadlystream.com/files/file/1280-kotor-2-community-patch/ — 3C-FD: https://deadlystream.com/files/file/2734-fog-fix-more-3c-fd-patcher/
- Mesa builds per il fix AMD: https://github.com/mmozeiko/build-mesa/releases/latest (x86!) — mesa-dist-win: https://github.com/pal1000/mesa-dist-win
- Guida Workshop storica: https://steamcommunity.com/sharedfiles/filedetails/?id=488641307
