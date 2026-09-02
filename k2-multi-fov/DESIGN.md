# k2-multi-fov — design e studio del motore

*Letto dal disassemblato di `swkotor2.exe.pre-laa-backup` (capstone, script in
`K2SE/tools/re/`), 2026-09-02. Indirizzi con provenienza in `K2SE/data/k2se_addresses.csv`.*

## 1. Due oggetti, due ruoli

**`CSWBehaviorCamera`** (RTTI, vtable `0x009A1F94`, ctor `0x007DD380`): la camera
d'inseguimento del gioco. Carica `camerastyle.2da` con `LoadCameraStyle(int row)`
(`0x007E1CA0`, `ret 4`):

| Colonna 2DA | Campo | DEFAULT | EbonHawk | OutDoor |
| --- | --- | --- | --- | --- |
| DISTANCE | `+0x16C` (copia in `+0x88`) | 3.2 | 1.3 | 6.25 |
| SPEED | `+0x170` | 20 | 20 | 20 |
| PITCH | `+0x178` | 83 | 78 | 80 |
| HEIGHT | `+0x17C` | 0.45 | 0.15 | 2 |
| TILTSPEED | `+0x190` | 30 | 30 | 30 |
| VIEWANGLE | `+0x8C` **e** `Camera::SetFOV` | 55 | 60 | 55 |

Riga di stile in `+0x5C`. `[this+0x1C]` è un contenitore la cui `vtable[1]()` restituisce la
camera Aurora. Il caricamento avviene dal costruttore (via `0x007E1BD0`, che legge lo stile
dell'area: `clientApp → 0x0073F430() → +0x48 → +0xB8`), da `SetupFromDefinition`
(`0x007DDA10`, chiamata `0x007DDC52`) e da `ApplyPendingStyle` (`0x007DE740`, chiamata
`0x007DE7D6`, riga in attesa nella globale `0x00A108F8`: la via dello script
`SetCameraStyle`). Il posizionamento della camera legge `+0x16C` (`0x007E0D25`,
`0x007E22EF`, `0x007E23D2`), `+0x17C` (`0x007E152B`, `0x007E2339`, `0x007E2492`) e
`+0x178` (`0x007DD644`, `0x007DDD72`, `0x007DE199`, `0x007DE83A`).

**`Camera`** (Aurora, RTTI `.?AVCamera@@`, vtable `0x0098C45C`, 37 slot): la proiezione.
FOV verticale in gradi in `+0x204` (default 45, poi 55 dal camerastyle), near `+0x210`
(0.1), far `+0x214` (100), animazione del FOV in `+0x208` (zoom dei dialoghi). Slot 2
`ApplyProjection()` (`0x0047F320`, `ret`, nessun argomento) è **l'unica** chiamata a
`gluPerspective` dell'eseguibile (`E8 0x0047F6D7` → thunk `0x0093B436` → IAT
`0x00986028`) e subito dopo costruisce il frustum di culling da `tan(fov/2)`: il FOV va
cambiato nel campo, non nella chiamata GL, o gli oggetti ai bordi sparirebbero. Slot 17
`SetFOV(float)` (`0x0047F190`), slot 16 `SetNearFar`, slot 3 `Update(dt)` (`0x00480E40`):
**mai chiamato** per la camera di scena (sessione del 19:49: 0 chiamate), per questo il
primo tentativo di hook non ha prodotto nulla.

## 2. Gli hook

1. **Tre call site di `LoadCameraStyle`** (`0x007E1C0B`, `0x007DDC52`, `0x007DE7D6`)
   ridiretti (E8 rel32, byte verificati) a un pass-through che, dopo l'originale, ricorda
   l'oggetto e i valori appena caricati (lo "stile vanilla") e rimette sopra la visuale
   attiva. Copre ingresso area, script e costruzione.
2. **Slot 2 della vtable `Camera`** (`ApplyProjection`) scambiato: prima dell'originale il
   modulo FOV scrive `+0x204` (e `+0x210` in prima persona), così proiezione e culling
   vedono lo stesso valore. Valori che il modulo non ha scritto sono adottati come vanilla
   della camera; fuori dal gameplay vengono rimessi.
3. **Frame di gameplay** = il controller del giocatore (`movement::UpdateCount()`) ha fatto
   un tick negli ultimi 100 ms. `movement::HookUpdate` chiama `camera::OnGameplayFrame()`:
   tasto N, riscrittura dei campi distanza/altezza/pitch (il motore può risovrascriverli),
   banner.

## 3. Prima persona senza congelare il giocatore

Il free look del gioco (`camCtrl+0xC = 5`) disabilita il controller: si guarda ma non ci si
muove. La prima persona di K2SE resta in modalità inseguimento: distanza 0.05, altezza
1.65 (occhi), pitch 90 (orizzontale). Il corpo del personaggio, che sta attorno alla camera,
viene tagliato alzando il **piano vicino** a 0.35 m (`Camera+0x210`) — nessuna modifica al
modello. Da verificare in gioco: braccia visibili durante le animazioni, collisione della
camera con il personaggio, mira/click.

## 4. Configurazione, API, routine

Sezioni `[Camera]`, `[CameraNear]`, `[CameraFar]`, `[CameraFirstPerson]`, `[FOV]` (vedi
README). Routine: `896 int K2SE_SetCameraView(int)`, `897 int K2SE_GetCameraView()`,
`894 int K2SE_SetFOV(float, float)`, `895 float K2SE_GetFOV()`.

## 5. Da verificare in gioco (S1)

- [ ] `camera: game camera object 0x...` e `style row N loaded: ...` nel log all'ingresso
  in area (con i valori del 2DA: 3.2 / 20 / 83 / 0.45 / 55 per DEFAULT);
- [ ] `fov: camera #1`, `first gameplay frame: vanilla 55 -> ...`; contatore > 0 alla chiusura;
- [ ] N cicla vicina → lontana → prima persona, banner a schermo;
- [ ] la distanza cambia subito (o con lo smoothing del motore, SPEED 20);
- [ ] prima persona: niente testa a schermo, si cammina, si vede in giro;
- [ ] dialogo e menu: valori del gioco; uscita dal dialogo: la visuale torna;
- [ ] click su NPC/porte ai bordi con FOV 75: coerente;
- [ ] minigioco swoop/torretta: nessun effetto;
- [ ] `K2SE_SetCameraView(3)` da script.

## 6. Rischi noti e piano B

- Se il posizionamento usasse un valore lerp-ato interno oltre a `+0x16C`, la distanza
  potrebbe cambiare lentamente o non cambiare: in quel caso si scrive anche lo stato
  corrente (da individuare in `0x007E22xx`).
- Pitch 90 potrebbe non essere "orizzontale" (semantica da confermare: 83 default guarda
  leggermente dal basso in alto verso il personaggio). Si aggiusta dall'ini.
- Il piano vicino alto taglia anche oggetti reali molto vicini (muri a 30 cm): accettabile
  in prima persona, si regola con `NearPlane`.
- Se il rilevamento "gameplay" fallisse in qualche schermata, la visuale resterebbe attiva
  dove non dovrebbe: il log delle adozioni (`fov: camera ... vanilla a -> b (not gameplay)`)
  lo mostra.
