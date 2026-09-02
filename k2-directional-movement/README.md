# K2 Directional Movement

KOTOR 2's movement feels like driving a tank. This fixes most of that by
changing **one column in one table**. No DLL, no engine patch, no script
extender — it is a single file in `Override/`, and deleting it undoes
everything.

## The finding

The obvious theory is that KOTOR 2 has tank controls and a modern game would
need a new movement system bolted on. That theory is wrong.

The PC build's only player controller is `CSWPlayerControlCamRelative`
(vtable `0x009A4818`), and it is exactly what its name says: it takes a 2D input
vector, rotates it into camera space, derives a target heading, and turns the
character toward it. `CSWPlayerControl` (`0x009A47E4`) is the abstract base and
is never instantiated — all twelve of its vtable slots are stubs, and its update
is literally `xor eax, eax; ret 4`.

So the camera-relative movement you want is already in the game. What makes it
*feel* like a tank is a rate limit applied to the turn, disassembled at
`0x00866057` inside the update at `0x00865830`:

```
turnRate = minturnrate + (maxturnrate - minturnrate) * (1 - speed / maxSpeed)
```

**The turn rate is inversely proportional to your speed.** Standing still you
get `maxturnrate` and spin freely. At a full run you get `minturnrate` — which
the shipped table sets to **150 deg/s** nearly everywhere. At 150 deg/s a
180-degree reversal takes **1.2 seconds**, and the character arcs around like a
vehicle instead of turning.

Both coefficients come from `camerastyle.2da`, indexed by the current area's
`CameraStyle` field:

| row | name | maxturnrate | minturnrate |
|---|---|---|---|
| 0 | DEFAULT | 1500 | **150** |
| 1 | EbonHawk | 500 | **500** |
| 2–7 | OutDoor, Manaan, E3test, Highview, Chess, QAVis | 480 | **150** |
| 8 | Combat | 800 | **200** |

## Prove it before you install anything

Row 1 is the giveaway. **`EbonHawk` already ships with `minturnrate` equal to
`maxturnrate`.** The shipped data contains its own control experiment.

Run in circles aboard the Ebon Hawk, then run in circles outdoors. If turning
while moving is noticeably crisper on the ship, the model above is confirmed on
your install, with no files touched.

## What this mod does

Sets `minturnrate = maxturnrate` on every row. The turn rate stops depending on
your speed, so the character reorients at a run as readily as standing still.

Each area keeps its own character — the Ebon Hawk's tighter 500 stays 500, open
ground stays 480, DEFAULT stays 1500 — because only the *ramp* is removed, not
the tuning.

Nothing else is touched. `camerastyle.2da` also configures the chase camera
(distance, pitch, height, framing), so `build.py` refuses to write the file if
any column other than the two turn-rate ones differs from stock.

## Use

```
python build.py              build into Override/
python build.py --install    build and copy into the game's Override folder
python build.py --uninstall  remove it from the game
python build.py --show       print the shipped table
```

**Restart the game after installing.** The 2DA cache is populated once at
startup (`C2DACache::LoadTables` at `0x006EA4C0`, `camerastyle` in slot `+0x78`),
so a running game will not pick it up.

## Tuning

`MODE` at the top of `build.py`:

- `"match_max"` (default) — per-row `minturnrate = maxturnrate`
- a number — force both columns to that value on every row, e.g. `MODE = 900`

If it feels *too* snappy, lower it. The turn is applied per frame with no
smoothing beyond this ramp, so very large values can pop the animation.

## What this does not do

- **Keyboard strafing.** `A`/`D` are bound to turn actions, not to the lateral
  input axis the controller consumes (`this+0x14`, written by the setter at
  `0x008653C0`). A gamepad's left stick feeds both axes, which is why the stick
  already moves in 360 degrees while WASD does not. Fixing that needs an input
  hook — a K2SE job, not a 2DA edit.
- **Sprint.** Wants `CSWSCreatureStats::SetMovementRate` (`0x006BA320`) and a
  key to hold. Also K2SE work.
- **Jump.** KOTOR has no jump: no animation, no vertical physics, no walkmesh
  support for leaving the ground. Not moddable at this layer, or realistically
  at any layer.

## Compatibility

Any other mod shipping `camerastyle.2da` conflicts — only one file can win in
`Override/`. If you use such a mod, apply the same `minturnrate` change to
*its* copy instead: `python build.py` after pointing `STOCK_2DA` at theirs.

## Credit

The offsets and the turn-rate formula were recovered by disassembling
`swkotor2.exe` (Steam/Aspyr 1.0.2.0) during work on
[K2SE](https://github.com/renanaugustomacena-ux/K2SE). No game code is
redistributed here — `build.py` extracts the stock table from your own
installation.
