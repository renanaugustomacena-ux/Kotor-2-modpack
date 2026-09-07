# k2-graphics — rendere modificabile il renderer

## Cos'e' davvero questo motore

Prima di promettere qualsiasi cosa, il fatto misurato: KOTOR 2 e' **OpenGL 1.x a
funzione fissa piu' shader assembly ARB_fragment_program**. Non c'e' GLSL, non ci
sono framebuffer object, non c'e' un percorso vertex programmabile in uso.
L'exe importa 95 funzioni da `OPENGL32.dll` e 2 da `GLU32.dll`, e sono tutte
GL 1.1 tranne quello che risolve via `wglGetProcAddress`.

Quindi ci sono esattamente **due** modi onesti di estenderlo, e ci sono
entrambi.

## 1. Shader sostituibili — la parte che conta

Il motore passa ogni fragment program a `glProgramStringARB`, che K2SE gia'
intercettava per la nebbia. Ora:

```ini
[Render]
Enabled=1
DumpShaders=1
ReplaceShaders=1
```

Ogni programma del gioco finisce in `k2se_shaders\<hash>.fp`. Si apre con un
editor di testo, si modifica, e alla partita dopo il gioco usa il tuo. **Questo
e' cio' che trasforma un renderer chiuso in uno modificabile**, ed e' la base su
cui sta tutto il resto.

Dettagli che non sono arbitrari:

- Il nome e' un hash **FNV-1a del sorgente**, non un numero progressivo: cosi'
  un dump e la sua sostituzione restano allineati anche se l'ordine di
  caricamento cambia.
- Il dump avviene **prima** di qualsiasi riscrittura, altrimenti una copia
  modificata si porterebbe dentro la nostra `OPTION ARB_fog_linear` e alla
  partita dopo se ne impilerebbe una seconda.
- Una sostituzione da disco **sopprime** l'iniezione della nebbia: modificare di
  nascosto il programma di qualcun altro farebbe si' che il file su disco smetta
  di descrivere cio' che la GPU esegue.

## 2. Una passata di post-processing

Su `SwapBuffers` (slot IAT GDI32 `0x0098601C`) il frame finito e' ancora nel
back buffer. Viene copiato in una texture e ridisegnato con un quad a tutto
schermo attraverso un nostro fragment program.

```ini
PostProcess=1
Sharpen=0.25          ; su un gioco del 2004 anche 0.2 si vede
Saturation=0.9
Contrast=1.05
Brightness=1.0
TintR=1.02
TintG=1.0
TintB=0.96            ; leggermente piu' caldo
```

Nitidezza a cinque campioni, poi saturazione, contrasto, luminosita', tinta.
Pesi di luminanza Rec.709: desaturare con una media piatta 1/3 rende fangosi gli
interni caldi di KOTOR.

Nessuna estensione nuova richiesta: il motore importa gia'
`glCopyTexSubImage2D`, `glGenTextures`, `glPushAttrib`, `glOrtho` e il resto.
La texture di cattura e' un quadrato potenza di due, perche' su GL 1.x le NPOT
non sono garantite, e il frame ne occupa l'angolo.
`glPushAttrib`/`glPopAttrib` avvolge tutta la passata: senza, il primo sintomo
visibile e' la GUI che perde il blending.

## Cosa NON si puo' fare, detto chiaro

- **PBR, ray tracing, shadow map da depth pass.** Servono una pipeline vertex e
  render target che questo motore non ha. La strada onesta per arrivarci e' un
  renderer diverso ([reone](https://github.com/seedhartha/reone) lo e'), non un
  hook.
- **"Tecnologie fisiche".** Non c'e' un motore fisico da estendere: KOTOR ha una
  walkmesh e nient'altro. Aggiungere fisica significa scriverne una, ed e' un
  progetto a se' — imparentato con
  [k2-improved-collision](../k2-improved-collision/).

## Sicurezza

Tutto e' opt-in e spento di default. GL viene risolto pigramente al primo
`SwapBuffers`, non in `Install`: al momento di `DllMain` `opengl32` potrebbe non
essere ancora mappata, e gli entry point ARB richiedono comunque un contesto
corrente. La passata e' avvolta in SEH: se salta, si disabilita per la sessione
e il gioco continua.

La DLL importa **solo KERNEL32** (`tools/check_dll.py` lo verifica): ogni
funzione GL passa da `GetProcAddress`, mai da un link.
