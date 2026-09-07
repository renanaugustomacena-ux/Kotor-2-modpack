# k2-animations — piu' animazioni per i mod di movimento

## La richiesta, e la risposta onesta

> "possiamo estrarre il movimento dello scheletro, riscrivere il suo codice per
> adattarlo ai nostri NPC, magari possiamo ricreare lo scheletro degli NPC 3D di
> kotor letteralmente basato su quelli di Skyrim"

**Ricreare lo scheletro non e' fattibile, e non lo consiglio in nessuna
variante.** Non e' una questione di difficolta': e' che romperebbe tutto il
gioco. Ogni modello di KOTOR e' skinnato allo scheletro Odyssey, e ogni
animazione e' definita su quello. I numeri, misurati qui:

```
S_Male02     5.077.166 byte   230 animazioni   466.3 s di movimento
S_Female02   2.171.130 byte    88 animazioni   138.6 s
S_Male01     1.562.813 byte    65 animazioni   101.0 s
S_Female01   1.958.397 byte    76 animazioni   114.3 s
```

Sono **459 animazioni, ~820 secondi di movimento**, piu' ogni mesh del gioco,
tutte legate a quello scheletro. Sostituirlo con quello di Skyrim invaliderebbe
tutte e 459 e ogni personaggio insieme a loro. Lo scheletro di Skyrim ha
gerarchia, nomi bone, proporzioni e convenzioni di rotazione diverse: non e' un
adattamento, e' una riscrittura di tutto il contenuto animato del gioco.

E c'e' una scorciatoia che nessuno aveva guardato.

## La scoperta: il gioco ha animazioni che non usa

```
righe in animations.2da:                        571
animazioni distinte nei supermodel:             456
  indirizzabili E presenti:                     416
  con una riga 2da ma assenti dai modelli:      107
  presenti ma SENZA riga 2da:                    40   <-- irraggiungibili
```

Il motore suona un'animazione **per numero di riga**. Quelle 40 esistono nei
supermodel — gia' autorate, gia' skinnate allo scheletro giusto, gia' spedite
col gioco — ma nessuna riga le indirizza, quindi il gioco non puo' suonarle.

La piu' importante:

| | durata | dove |
|---|---:|---|
| **`walkback`** | 1.33s | S_Female02 |

Una camminata all'indietro vera. Il mod di movimento direzionale finora suona
l'animazione in avanti mentre si va indietro — che e' esattamente il moonwalk
che sembra.

Le altre utili: `sitstand`, `idlepose`, `shrug2`, `hshakestun`, `hshakeweary`,
`emotions`. Le restanti 33 sono clip di cutscene (`cut0xx`) e varianti di posa
con arma (`b11*`, `g9*`).

## E cosa NON c'e'

Il censimento risponde anche alla domanda opposta, e serve saperlo:

- **nessuna animazione di salto.** Zero candidati. Il mod jump non ha nulla da
  suonare, ed e' per questo che usava il diveroll (che a Renan non piaceva).
- **nessuna camminata accovacciata.** `stealth` (riga 5) e `kneel` (riga 23)
  sono il massimo disponibile.

Queste due vanno autorate. Ora si puo': Blender e' installato.

## Cosa c'e' in questa cartella

```bash
python tools/anim_census.py --supermodels   # quante animazioni, quanti secondi
python tools/anim_census.py --census        # il conteggio incrociato con la 2da
python tools/anim_census.py --unused        # le 40 irraggiungibili
python tools/anim_census.py --suggest       # candidati per sprint/salto/crouch/rotolata
python tools/anim_census.py --model S_Male02

python tools/gen_anim_rows.py --plan
python tools/gen_anim_rows.py --build --out build/override
```

`gen_anim_rows.py` produce un `animations.2da` da 611 righe: le 571 originali
**byte per byte agli stessi indici** (verificato — salvataggi e script
indirizzano per riga, uno spostamento romperebbe tutto) piu' 40 righe nuove da
571 in poi.

## Provarle in gioco

La console K2SE (F10) ora suona qualsiasi riga:

```
k2se> anim 2      # run
k2se> anim 5      # stealth
k2se> anim 567    # diveroll
k2se> anim 571    # walkback, con l'override installato
```

E' il modo piu' rapido per capire come si muove una clip senza ricompilare
niente. Nessuna descrizione sostituisce il guardarla.

## Il passo dopo: autorare le clip mancanti

Con Blender installato, la strada e':

1. **KotorBlender** — importa `S_Male02.mdl` con scheletro e animazioni.
2. Autorare le clip mancanti **sullo scheletro Odyssey esistente**: salto
   (stacco/volo/atterraggio), camminata accovacciata, scatti direzionali.
3. Esportare, aggiungere le righe con `gen_anim_rows.py`, suonarle da K2SE.

Le pose chiave possono benissimo essere **ispirate** alle mod Skyrim che Renan
ha (Goetia, EVG Animation Variance, Leviathan, DOVAJUMP — tutte in `D:\mods`):
guardarle e rifarle sullo scheletro giusto e' lavoro d'animazione normale.
Quello che non funziona e' convertire gli HKX: sono legati allo scheletro di
Skyrim, e il retarget richiederebbe comunque di rifare a mano quasi tutto.

Nota: `MDL-SDK` di NVIDIA non serve — e' il Material Definition Language, un
altro formato che condivide solo il nome.

## Dettagli di formato

- L'array di animazioni sta nel model header a +88 (offset, count, count2),
  relativo a `kMdlDataOffset = 12`.
- Ogni voce e' un geometry header (nome a +8, 32 byte) seguito da `length` e
  `transitionTime` float a +80.
- Oracolo: `ref/reone/src/libs/graphics/format/mdlmdxreader.cpp`.
- `S_Male02` dichiara `S_Male01` come supermodel, `S_Female01` dichiara
  `S_Male02`: la catena di ereditarieta' e' incrociata, quindi un'animazione va
  cercata in tutti e quattro.
