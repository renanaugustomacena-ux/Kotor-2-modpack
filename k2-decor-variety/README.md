# k2-decor-variety — varianti di colore dei prop di KOTOR

180 nuovi placeable, senza una singola mesh nuova.

## Il problema

Il catalogo costruito per la console (`K2SE/tools/gen_catalog.py`) dice una cosa
scomoda: **KOTOR ha 842 blueprint di placeable ma pochissima varieta'**. E, alla
lettera, il gioco contiene piante, tavoli, statue, footlocker e casse — ma
**niente vasi, lanterne, piatti o forchette**. La minuteria che Renan voleva
semplicemente non esiste in KOTOR, e importarla richiede una pipeline di mesh
(vedi "Cosa manca").

Quello che si puo' avere subito e' la varieta': gli stessi prop, desaturati e
spostati un po' di tonalita', cosi' che una stanza abbia sei fioriere
leggermente diverse invece di sei identiche.

## Come funziona (e perche' non servono mesh nuove)

Il vincolo che decide tutto il design:

> `placeables.2da` **non ha una colonna texture**. Ha solo `modelname`.

Quindi due righe che puntano allo stesso modello saranno sempre identiche: non
basta clonare una riga. La texture e' scritta **dentro l'MDL**, nel campo
`texture1` dell'header di mesh, largo 32 byte fissi.

Da qui la ricetta:

```
MDL originale ──► copia con texture1 riscritto ──► PLC_Bench_a.mdl
                  (campo a larghezza fissa: niente si sposta,
                   tutti gli offset del file restano validi)
MDX             ──► copiato identico (dati vertice, non nomina texture)
PWK             ──► copiato identico (senza, il prop non ha collisione)
TPC dai pack    ──► decodificato, ricolorato, scritto come TGA
placeables.2da  ──► riga clonata, con label e modelname nuovi
```

Non e' "scrivere un MDL": e' una sostituzione di byte a parita' di dimensione.
Verificato: modello patchato e originale hanno **la stessa dimensione, lo stesso
numero di nodi e la stessa geometria**, e differiscono solo nel nome texture.

## Uso

```bash
python tools/recolour.py --plan                      # cosa verrebbe fatto
python tools/recolour.py --preview PLC_FootLker      # una texture e le 4 varianti
python tools/recolour.py --build --out build/override
```

Poi copiare il contenuto di `build/override` nella cartella `override` del
gioco, e piazzare i prop in gioco con la console K2SE (F10):

```
k2se> list _a
k2se> spawn #3
k2se> save
```

## Risultato

```
180 varianti: 180 modelli, 180 texture, placeables.2da da 361 a 541 righe
45 prop di partenza x 4 varianti
2 saltati: Crate_wooden (texture non nei pack), RakataStatue (modello assente)
```

Le quattro varianti sono volutamente discrete — un prop che urla e' peggio di un
prop ripetuto:

| | saturazione | tonalita' | luminosita' |
|---|---:|---:|---:|
| `_a` | 0.55 | −0.02 | 1.00 |
| `_b` | 0.45 | +0.03 | 0.92 |
| `_c` | 0.65 | +0.06 | 1.06 |
| `_d` | 0.35 | −0.05 | 0.88 |

L'alfa non viene toccata: su questi prop e' una maschera di ritaglio, e
alterarla mangia la geometria.

## Dettagli di formato (per non riscoprirli)

- **Le texture non sono nei BIF.** Stanno in `TexturePacks/swpc_tex_tpa.erf`
  (alta risoluzione), poi `tpb`, `tpc`. Cercarle in `chitin.key` non trova nulla.
- **TPC**: header a 0, pixel a 128. `dataSize != 0` = compresso — DXT1 se
  encoding=2 (RGB), DXT5 se encoding=4 (RGBA); altrimenti raw grigio/RGB/RGBA.
- **Alfa DXT5**: i sei passi interpolati pesano da 6:1 a 1:6 su 7. Usare 7:1
  sfora oltre 255 e corrompe l'alfa di *ogni* texture DXT5 — errore commesso e
  corretto qui, non ripeterlo.
- **Nomi texture nell'MDL**: vanno letti dall'header di mesh (nodo con flag
  0x20, campo a +80+88), non indovinati dalle stringhe del file. I nomi dei nodi
  (`PLC_Plant1_wg`, `..._pwk`) sembrano identici a nomi di texture e non lo sono.
- **Un resref e' 16 caratteri**: il suffisso deve starci dentro.

## Cosa manca — la minuteria vera

Forchette, lanterne, vasi, piatti: non esistono in KOTOR e questa strada non li
crea. Servono mesh nuove, e ora la via e' aperta perche' Blender e' installato:

1. **KotorBlender** — l'addon che importa/esporta MDL+MDX nativamente. E' il
   pezzo indispensabile.
2. **MDLedit** — per verificare il binario prodotto.

Attenzione: `MDL-SDK` di NVIDIA (scaricato l'08/09/2026) e' il *Material
Definition Language* e non c'entra nulla con l'MDL di KOTOR nonostante il nome.

Con KotorBlender la conversione da NIF di Skyrim diventa
`NIF → Blender → MDL`, e non serve piu' scrivere un writer MDL da zero. Solo
prop statici: le mesh animate sono un problema diverso (vedi `k2-animations`).
