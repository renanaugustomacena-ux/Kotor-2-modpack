# KOTOR 2 Modpack

Mod per **Star Wars: Knights of the Old Republic II — The Sith Lords**, build
Aspyr/Steam 1.0.2.0, costruite sopra [**K2SE**](https://github.com/renanaugustomacena-ux/K2SE),
un script extender che si aggancia al motore tramite una DLL proxy.

L'obiettivo non è solo rifare texture e modelli: è dare al gioco un movimento
moderno e mappe che sembrino vive, con più oggetti, più NPC e più varietà.

---

## Le mod

| Mod | Cosa fa | Stato |
|-----|---------|-------|
| [k2-jump-crouch-sprint](k2-jump-crouch-sprint/) | Sprint (Shift), accovacciamento a interruttore (C), capriola (Alt), salto funzionale (Spazio) | Sprint, capriola e accovacciamento **confermati in gioco**; salto visibile da fermo, da rifinire in corsa |
| [k2-multi-fov](k2-multi-fov/) | Tre visuali della camera d'inseguimento — vicina, lontana, prima persona — con un tasto (N), più campo visivo per situazione | **Confermato in gioco**; il movimento resta attivo anche in prima persona, a differenza del free look nativo |
| [k2-directional-movement](k2-directional-movement/) | Movimento a 8 direzioni relativo alla camera con WASD | **Confermato in gioco** dopo aver spostato il passo laterale su A/D dalle opzioni |
| [k2-improved-collision](k2-improved-collision/) | Raggi di collisione più onesti, scivolamento lungo i muri, collisioni con ambiente e pavimento | In progettazione; audit dei raggi funzionante |
| [k2-texture-pack](k2-texture-pack/) | Spawner di oggetti e NPC per area, varietà degli NPC generici, e in seguito texture e modelli | Spawner e varietà NPC **costruiti**, primo test in corso |
| [k2-tesselation](k2-tesselation/), [k2-high-polygon-ebon-hawk](k2-high-polygon-ebon-hawk/) | Idee non ancora iniziate | — |

Le funzioni di movimento, camera, spawner e varietà NPC vivono tutte dentro
K2SE e si accendono dal file `k2se_movement.ini`. Le mod qui documentano il
progetto, il reverse engineering e i dati; il codice sta nel sottomodulo.

---

## Come si installa

1. Serve KOTOR 2 nella build Steam/Aspyr **1.0.2.0**. Gli indirizzi sono
   verificati contro quell'eseguibile: su altre build K2SE si rifiuta di
   agganciarsi invece di rischiare.
2. Compila la DLL: `cd K2SE && .\build_direct.ps1` (serve MSVC; il percorso è
   configurabile nello script).
3. Installa: `python K2SE\tools\deploy_movement.py --install --enable sprint,roll,crouch,jump,fov,camera,spawner,npcvariety --banner`
   Lo strumento verifica ogni indirizzo contro il tuo eseguibile, controlla che
   la tabella delle routine e il compilatore di script siano d'accordo, e si
   rifiuta di scrivere mentre il gioco è aperto.
4. In gioco, da **Opzioni → Tastiera**, sposta Pausa via da Spazio e la
   rotazione della camera via da A e D. Il gioco riscrive il suo ini all'uscita,
   quindi le modifiche fatte da fuori non sopravvivono: vanno fatte dal menu.
5. Per disinstallare: `python K2SE\tools\deploy_movement.py --clean`.

Il registro di ogni sessione finisce in `%LOCALAPPDATA%\K2SE\k2se.log` ed è il
posto dove guardare quando qualcosa non si vede a schermo.

---

## Documenti

- [PIANO-DAZIONE-2026-09-02.md](PIANO-DAZIONE-2026-09-02.md) — il piano
  completo: fasi, criteri di accettazione, checklist di test.
- [DOSSIER.md](DOSSIER.md) — indagine sui crash della partita moddata
  (memoria a 32 bit, driver OpenGL AMD) e la scala dei rimedi.
- [docs/2026-09-02-studio-movimento-collisioni.md](docs/2026-09-02-studio-movimento-collisioni.md)
  — studio del movimento e delle collisioni nel motore Odyssey, con ogni
  affermazione marcata come verificata, presa da KOTOR 1 o ipotesi.
- [K2SE/docs/](https://github.com/renanaugustomacena-ux/K2SE/tree/master/docs)
  — le note di reverse engineering: catene di chiamate, offset, cosa il gioco
  ha risposto in ogni sessione di prova.

---

## Cosa non c'è in questa repo, e perché

- **Le texture grezze di Skyrim** (`k2-texture-pack/raw/`): 41 000 file per
  12 GB, raccolti in locale come materiale di studio. Ogni file appartiene
  all'autore della sua mod: uso personale sì, ridistribuzione no. Nella repo
  restano l'inventario, l'elenco delle provenienze e lo strumento che li ha
  raccolti, così chiunque può rifare la raccolta dalla propria collezione.
- **I file di dati originali del gioco** (`stock/*.2da`): appartengono a
  Obsidian, LucasArts e Aspyr. Le mod distribuiscono le **modifiche**, e gli
  script di build rigenerano i file a partire dalla tua installazione.
- **I disassemblati di `swkotor2.exe`**: le scoperte (indirizzi, strutture,
  punti di aggancio) stanno nei documenti di design; i dump grezzi derivano da
  un binario protetto e restano in locale.
- **Copie di progetti altrui** tenute come riferimento:
  [reone](https://github.com/seedhartha/reone) e
  [KotOR.js](https://github.com/KobaltBlu/KotOR.js).

## Crediti

Motore Odyssey di BioWare, gioco di Obsidian Entertainment, porting di Aspyr.
Il lavoro di reverse engineering ha usato come riferimento i progetti open
source reone e KotOR.js e il database di indirizzi di Kotor-Patch-Manager.
Questa è una mod non ufficiale, non affiliata né sostenuta da nessuno di loro.
