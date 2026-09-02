# k2-multi-fov — tre visuali: vicina, lontana, prima persona (KOTOR 2, Steam/Aspyr 1.0.2.0)

Modulo di **K2SE** (`K2SE/src/camera.cpp` + `K2SE/src/fov.cpp`). Con un tasto (default **N**)
si cicla tra tre visuali della camera d'inseguimento, ognuna con la sua distanza, altezza,
inclinazione e campo visivo (FOV):

| Visuale | Distanza | Altezza | Pitch | FOV vert. | Note |
| --- | --- | --- | --- | --- | --- |
| Vicina | 2.2 | 0.6 | 83 | 60° | il gioco: 3.2 / 0.45 / 83 / 55° |
| Lontana | 5.5 | 1.4 | 80 | 52° | |
| Prima persona | 0.05 | 1.65 | 90 | 75° | piano vicino 0.35 per tagliare il corpo |

A differenza del **free look** del gioco (CapsLock), che congela il personaggio, qui la
camera resta quella d'inseguimento: si cammina, si combatte, si clicca. Fuori dal gameplay
(menu, dialoghi, filmati, minigiochi) tornano i valori del gioco.

## Stato (2026-09-02, sera)

- Studio completo (DESIGN.md): classe `CSWBehaviorCamera` con i valori di camerastyle.2da,
  classe Aurora `Camera` con il FOV.
- Codice scritto e installato alle 20:03, **da provare in gioco**. Cose da verificare:
  il tasto N cicla e il banner compare; la distanza cambia davvero; la prima persona non
  mostra la testa; il FOV cambia (55 → 60/52/75); nei dialoghi torna tutto normale; il click
  sugli oggetti ai bordi è coerente.

## Configurazione (`k2se_movement.ini` accanto a `swkotor2.exe`)

```ini
[Camera]
Enabled=1
KeyCycle=N            ; cicla vicina -> lontana -> prima persona
StartView=1           ; 1 vicina, 2 lontana, 3 prima persona, 0 stile del gioco
IncludeGameStyle=0    ; 1 = nel ciclo entra anche lo stile del gioco
Banner=1

[CameraNear]
Distance=2.2
Height=0.6
Pitch=83
FOV=60

[CameraFar]
Distance=5.5
Height=1.4
Pitch=80
FOV=52

[CameraFirstPerson]
Distance=0.05
Height=1.65
Pitch=90
FOV=75
NearPlane=0.35

[FOV]                 ; usato quando nessuna visuale e' attiva; SprintAdd e i tasti Numpad valgono sempre
Enabled=1
Exploration=60
Combat=55
SprintAdd=5
KeyIncrease=ADD
KeyDecrease=SUBTRACT
KeyReset=MULTIPLY
```

Installazione: `python K2SE/tools/deploy_movement.py --install --enable sprint,roll,crouch,jump,fov,camera`.

Script (NWScript, `nss/k2se.nss`): `K2SE_SetCameraView(int)` / `K2SE_GetCameraView()`
(896/897), `K2SE_SetFOV(float gradi, float secondi)` / `K2SE_GetFOV()` (894/895).

## Conversione FOV verticale ↔ orizzontale

Il motore usa il FOV **verticale**. Orizzontale = 2·atan(tan(v/2)·aspetto).
A 16:9: 45° → 73°, 55° → 84°, 60° → 90°, 75° → 108°.
