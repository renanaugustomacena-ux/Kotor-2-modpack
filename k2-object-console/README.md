# k2-object-console — una console vera per piazzare oggetti

Prima F10 accodava la posizione del giocatore a `_captured.txt`. Si poteva
registrare un punto, ma non vedere cosa poteva starci sopra, e non metterci
niente senza editare un ini e riavviare.

Ora F10 apre **una finestra di console**, il gioco continua a girare, e si
sfoglia il catalogo di tutti gli oggetti del gioco.

```
k2se> list plant
  #1  placeable plc_plant1      Plant1_alien_potted    model PLC_Plant1   bif
  #2  placeable plc_plant2      Plant2_alien_potted    model PLC_Plant2   bif
  ...
  11 matches. Place one with `spawn <resref>` or `spawn #<n>`.

k2se> spawn #1
  placing plc_plant1 at 12.40 -3.11 0.00 facing 214 (entry 1) -- give it a moment

k2se> save
  1 entry written to k2se_spawns\262TEL.ini
```

## Comandi

| | |
|---|---|
| `list <testo>` | cerca nel catalogo (1348 oggetti) |
| `spawn <resref>` / `spawn #<n>` | piazza dove sei |
| `npc <resref>` | piazza una creatura |
| `here` | modulo, area, posizione, direzione |
| `placed` / `undo` / `save` | gestisci quello che hai messo |
| `anim <riga>` | suona una riga di `animations.2da` sul personaggio |
| `eyes` | il punto occhio misurato del tuo personaggio |
| `view <0-3>` | visuale camera: gioco / vicina / lontana / prima persona |

## Il catalogo

Costruito **offline**, non a runtime: cos'e' che esiste nel gioco e' una domanda
sui dati, non sul codice.

```bash
python K2SE/tools/gen_catalog.py --summary
python K2SE/tools/gen_catalog.py --grep lantern
```

```
catalogo: 1348 righe
  door                 360
  door-model           123
  placeable            842
  placeable-model       23
  con un nome leggibile: 1346
  provenienti dai moduli: 715
```

Legge i BIF, **tutti i 246 archivi dei moduli** (la maggior parte dei prop
esiste solo dentro il modulo che li usa) e `dialog.tlk`, cosi' una riga dice
"Footlocker" e non "strref 12345". RIM, ERF e GFF sono letti direttamente, con
reone come oracolo dei formati.

Verdetto utile emerso dal catalogo: il gioco ha piante, tavoli, statue,
footlocker e casse — **niente vasi, lanterne, piatti o forchette**. Da li' e'
nato [k2-decor-variety](../k2-decor-variety/).

## Come e' fatto dentro

Il vincolo che decide il design e' il threading: una console ha bisogno di una
lettura bloccante, e il thread del gioco non puo' bloccarsi. Quindi il thread
lettore fa **una cosa sola** — mettere la riga digitata in una coda protetta da
una critical section — e non tocca **mai** un oggetto di gioco. `Drain()` gira
sul thread del gioco, dove toccare oggetti e' legale, ed e' l'unico posto dove i
comandi vengono eseguiti.

Le posizioni entrano nella passata di spawn gia' esistente
(`spawner::AddRuntimeEntry`), non in un secondo meccanismo. Sono ancorate
all'area in cui le hai messe: `Area` vuota significa "ovunque nel modulo" e
farebbe seguire l'oggetto al giocatore.

## Accenderlo

```ini
[Spawner]
Enabled=1             ; obbligatorio: e' lui che crea gli oggetti
[Console]
Enabled=1
KeyToggle=F10
```

```bash
python K2SE/tools/gen_catalog.py
python K2SE/tools/deploy_movement.py --install --enable camera,console,spawner
```

**Serve il gioco in finestra o borderless**: a schermo intero esclusivo non si
riesce ad alt-tab sulla console senza minimizzare il gioco.
