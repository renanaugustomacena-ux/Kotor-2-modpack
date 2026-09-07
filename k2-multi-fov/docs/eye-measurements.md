# Dove sono davvero gli occhi — misure dei modelli PC

Misurato l'08/09/2026 con `K2SE/tools/model_measure.py`, direttamente dagli MDL
dentro `models.bif`. Nessun numero qui è stimato o ricordato: ognuno esce dal
file del modello.

## La domanda

La prima persona di k2-multi-fov metteva la camera a un'altezza fissa:

```cpp
// K2SE/src/camera.cpp
{"first person", 0.05f, 1.65f, 90.0f, 75.0f, 0.35f},
//                      ^^^^^ altezza, uguale per tutti
```

Quel numero non era misurato. La domanda era: **dove sono esattamente gli occhi
del modello del personaggio?**

## Come sono strutturati i modelli

Un personaggio KOTOR è due modelli separati, non uno:

```
corpo (PMBAM)                    testa (PMHC01)
  rootdummy                        head
    torso_g                          head_g
      ...                              eyeLA   <- bone occhio sinistro
      headhook  <-------- la testa      eyeRA   <- bone occhio destro
      camerahook          si attacca    eyeLlid / eyeRlid
      FreeLookHook        qui
```

Il punto occhio si compone così:

```
occhio_mondo = trasformata_mondo(headhook nel corpo)  ∘  posizione(eyeLA/eyeRA nella testa)
punto camera = midpoint(occhio_sinistro, occhio_destro)
```

Il modello del corpo dipende dall'**armatura equipaggiata**: `appearance.2da`
riga di tipo `B` sceglie fra `modela`..`modeln`. Il modello della testa viene da
`normalhead` → `heads.2da`. Sistema di coordinate: metri, **Z in alto, Y in
avanti**.

## I numeri — PC maschio (PMBAM + PMHC01, vestiti normali)

| Nodo | X | Y (avanti) | Z (alto) |
|---|---:|---:|---:|
| `rootdummy` | 0.0000 | 0.0000 | 1.1256 |
| `headhook` | 0.0000 | −0.0180 | 1.5250 |
| `camerahook` (di BioWare) | 0.0003 | 0.0207 | 1.6339 |
| `FreeLookHook` | 0.0000 | 0.1200 | 1.6350 |
| **`eyeLA`** | **−0.0288** | **0.0583** | **1.6726** |
| **`eyeRA`** | **+0.0290** | **0.0583** | **1.6726** |
| **punto occhio (midpoint)** | **0.0001** | **0.0583** | **1.6726** |

Distanza interpupillare: **5.78 cm** — plausibile per un adulto, ed è la prova
che il parser legge bene l'albero dei nodi.

## I numeri — PC femmina (PFBAM + PFHC01, vestiti normali)

| Nodo | X | Y (avanti) | Z (alto) |
|---|---:|---:|---:|
| `camerahook` | 0.0006 | −0.0227 | 1.5382 |
| **punto occhio (midpoint)** | **−0.0001** | **0.0626** | **1.5886** |

## Le tre conclusioni che contano

### 1. Il valore fisso 1.65 era sbagliato per tutti

Su 105 righe PC di `appearance.2da` (51 maschili, 54 femminili, 35 teste
distinte):

| | altezza occhi media | min | max | errore di 1.65 |
|---|---:|---:|---:|---:|
| maschio | 1.6686 | 1.6616 | 1.6757 | **1.9 cm troppo basso** |
| femmina | 1.5903 | 1.5851 | 1.5968 | **6.0 cm troppo alto** |

Fra maschio e femmina ci sono **7.8 cm**: una costante sola non può
rappresentarli. Ecco perché la prima persona sembrava "sbagliata" in un modo
difficile da spiegare.

### 2. `camerahook` non è agli occhi, e non è nemmeno coerente

BioWare ha messo un nodo `camerahook` nello scheletro, ed è un ottimo ripiego,
ma non sta dove stanno gli occhi:

| | eye − camerahook (X, Y, Z) |
|---|---|
| maschio PMBAM + PMHC01 | (−0.0002, **+0.0376**, **+0.0387**) |
| femmina PFBAM + PFHC01 | (−0.0007, **+0.0853**, **+0.0504**) |

Cioè gli occhi stanno 3.9–5.0 cm **più in alto** e 3.8–8.5 cm **più avanti** del
camerahook. E peggio: con l'armatura il rapporto si rovescia.

### 3. L'armatura cambia l'altezza degli occhi

Corpo maschile, stessa testa, al variare della classe di armatura:

| slot | modello | occhi Z | camerahook Z |
|---|---|---:|---:|
| a–h, j | PMBAM… | 1.6726 | 1.6339 |
| i | PMBIM | 1.6970 | 1.6493 |
| m | PMBMM | 1.6712 | 1.6493 |
| n | PMBNM | 1.6926 | 1.6493 |
| **k** | **PMBKM** | **1.6976** | **1.7126** |

Con l'armatura pesante (slot k) il `camerahook` finisce **sopra** gli occhi
(1.7126 contro 1.6976). Un ancoraggio al camerahook cambierebbe altezza quando
cambi armatura, e a volte nel verso sbagliato. **I bone oculari no.**

## Copertura e casi limite

Passata completa su `appearance.2da` con tutte le varianti di armatura:

```
1359 coppie corpo+testa distinte
1281 misurate
   controllo di plausibilità: superato
   (altezze occhi 1.32–1.71 m, nodi oculari simmetrici in X entro 0.2 mm)
```

Le righe non misurate non sono errori del parser:

- **11 facce mascherate** — Visas, Darth Revan, i Dark Jedi incappucciati, il
  Sith Assassin. Questi modelli **non hanno nodi oculari** perché la faccia è
  coperta. Per loro il ripiego corretto è il `camerahook` del corpo.
- **6 modelli assenti** — righe avanzate da KOTOR 1 (Jolee, Mission, Juhani,
  Candarous) e righe di test. Non usate nel gioco.

Due convenzioni di nomi convivono nei file spediti: **109 teste su 125** usano
`eyeLA`/`eyeRA`, **6** usano `eyeL`/`eyeR`. Il tool prova entrambe.
Kreia, la Handmaiden e Atris non hanno una testa separata: i loro bone oculari
stanno dentro il modello del corpo, e vengono misurati lì.

## Verifica del parser

Il lettore MDL è scritto da zero (solo stdlib) seguendo
`ref/reone/src/libs/graphics/format/mdlmdxreader.cpp` come specifica. È stato
confrontato con PyKotor, un'implementazione indipendente:

```
$ python tools/model_measure.py --verify
cross-check vs PyKotor: 268 nodi, delta massimo di posizione locale 0.000e+00 m
cross-check passed
```

Accordo esatto su tutti i nodi di `pmbam`, `pmhc01`, `pfbam` e `s_male02`.
(PyKotor serve solo per questo controllo e **non** è una dipendenza del
progetto.)

Nota utile per chi legge gli MDL: `s_male02` contiene **due** nodi chiamati
`w_Longsword`. Una ricerca per nome ne prende uno solo, e due lettori diversi
possono prenderne uno diverso — sembra un disaccordo da 2.4 cm che non esiste.
Il confronto va fatto sull'albero, non sui nomi.

## Come rigenerare i dati

```bash
python tools/model_measure.py --report                       # la tabella
python tools/model_measure.py --report --armour              # con le armature
python tools/model_measure.py --armour --csv data/k2se_eye_offsets.csv
python tools/model_measure.py --nodes pmbam:camerahook,headhook
python tools/model_measure.py --verify                       # se PyKotor c'è
```

Output: `K2SE/data/k2se_eye_offsets.csv`, 1359 righe, una per coppia
corpo+testa, con punto occhio, camerahook, headhook e distanza interpupillare.

## Cosa ne fa la prima persona

Queste sono misure in **posa di riposo**. In gioco lo scheletro è animato: la
testa si muove a ogni passo. Il modulo `K2SE/src/fpcam.cpp` chiede la posizione
del nodo al motore **ogni frame**, e usa queste misure per:

1. sapere quale nodo cercare (`eyeLA`/`eyeRA`, o `headhook` + offset misurato,
   o `camerahook` per le facce mascherate);
2. validare quello che il motore restituisce — un punto occhio fuori dai
   1.3–1.8 m attesi significa che la ricerca ha risolto la cosa sbagliata;
3. dare un ripiego statico corretto per personaggio quando la ricerca a runtime
   non è disponibile.
