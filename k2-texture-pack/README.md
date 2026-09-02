# k2-texture-pack — materiale grezzo, object swapper, extender

Obiettivo (Renan, 2026-09-02): non solo texture e modelli migliori, ma **mappe più
vive**: più decorazione, più NPC e più varietà (vestiti, teste, comportamenti),
con collisioni corrette. Tre pezzi:

1. **Texture pack** — materiale grezzo in `raw/`, da convertire (TGA/TPC + TXI) e
   rimappare sugli asset di KOTOR 2.
2. **Object swapper** — scambio/aggiunta di placeable e modelli per area (GIT/LYT
   e, dove serve, lato K2SE a runtime), stile "Base Object Swapper" di Skyrim.
3. **Extender** — routine K2SE per spawn, varietà NPC e collisioni degli oggetti
   aggiunti (vedi `k2-improved-collision`).

## raw/ — raccolta del 2026-09-02

Copiato da `D:\mods` (solo file sciolti, nessun archivio aperto) con
`tools/harvest.py` (rieseguibile, salta i file già copiati):

| | |
|---|---|
| mod esaminate | 1957 |
| file candidati | 41 273 |
| file copiati | 41 118 (11,9 GB) |
| mod con file copiati | 130 |

Per categoria (MB): architettura 6249, paesaggio 2868, clutter 2458, industriale
(dwemer/metallo/tubi/pannelli) 690, materiali 285. Esclusi: personaggi, armature,
armi, volti, creature, effetti, interfaccia, cielo, LOD, acqua, piante.

File: `raw/MANIFEST.csv` (una riga per candidato: mod, percorso, byte, dimensioni,
formato, categoria, copiato, motivo), `raw/INVENTORY.md`, `raw/PROVENANCE.md`.

**Licenze**: ogni file appartiene all'autore della mod Skyrim di origine. Uso
personale. Qualsiasi distribuzione richiede il permesso di ciascun autore
(elenco in `raw/PROVENANCE.md`). Gli archivi del gioco Bethesda non sono stati toccati.

## Prossimi passi (da pianificare)

- Selezione: quali texture hanno senso per KOTOR 2 (industriale → Peragus/Telos/Ebon
  Hawk; pietra/sabbia → Dantooine/Korriban; legno/tessuti → Nar Shaddaa/Onderon).
- Pipeline di conversione DDS → TGA/TPC con TXI, controllo dimensioni (il DOSSIER
  ricorda che 16 GB di TGA non compressi hanno saturato i 2 GB del processo).
- Object swapper: formato dati, iniezione GIT, collisioni (PWK) e test per area.
- Varietà NPC: appearance.2da / heads.2da / vestiti, spawn aggiuntivi via script K2SE.

## Stato 2026-09-02 sera — spawner e varietà NPC costruiti

- **Spawner** (K2SE `spawner.cpp` + script `k2se_spawn.ncs`): oggetti e NPC da
  `k2se_spawns\<MODULO>.ini`, creati dal motore stesso (`CreateObject`), marcati e salvati
  con l'area; F10 cattura la posizione del giocatore. Vedi `K2SE/data/k2se_spawns/README.txt`.
- **Varietà NPC** (K2SE `npcvariety.cpp`): 7 famiglie di aspetti intercambiabili (cittadini
  M/F, ufficiali Czerka, soldati e ufficiali Repubblica M/F) — teste diverse, scelta stabile
  per NPC. Da estendere con altre famiglie (alieni, Sith, Onderon) dopo il primo test.
- Prossimo: modalità "swap" (nascondere un placeable esistente e crearne un altro), pool
  estesi, pipeline texture per i materiali ripetibili.
