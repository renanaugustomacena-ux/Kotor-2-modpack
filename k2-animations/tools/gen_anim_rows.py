"""Give the unreachable animations a row, so K2SE can play them.

    python tools/gen_anim_rows.py --plan
    python tools/gen_anim_rows.py --build --out build/override

The census found 40 animations that exist in the supermodels but have no
animations.2da row. The engine addresses animations by ROW, so motion that is
already authored, already skinned to the right skeleton and already shipping in
the game is simply unreachable. Adding a row costs nothing and risks nothing:
existing rows keep their indices, so no save game and no script changes meaning.

The one that matters most is `walkback` -- a real walk-backwards clip. The
directional movement mod currently plays the forward walk while moving
backwards, which is exactly the moonwalk it looks like.

Most of the other orphans are cutscene clips (cut0xx) and weapon-stance
variants (b11*, g9*); they are included because a row is cheap and finding a
use for them is easier than re-authoring them, but the ones worth trying first
are listed in USEFUL.
"""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import anim_census as census  # noqa: E402

# Orphans worth reaching for, with the flag set that suits how they move.
# (name, description, stationary, walking, running, looping, fireforget, overlay)
USEFUL = [
    ("walkback",     "Walk_Backwards",      "0", "1", "0", "1", "0", "0"),
    ("sitstand",     "Stand_Up_From_Sit",   "1", "0", "0", "0", "1", "0"),
    ("idlepose",     "Idle_Pose",           "1", "0", "0", "1", "0", "0"),
    ("shrug2",       "Shrug_Variant",       "1", "0", "0", "0", "1", "1"),
    ("hshakestun",   "Head_Shake_Stunned",  "1", "0", "0", "0", "1", "1"),
    ("hshakeweary",  "Head_Shake_Weary",    "1", "0", "0", "0", "1", "1"),
    ("emotions",     "Emotion_Blend",       "1", "0", "0", "0", "1", "1"),
]


def build_rows(game):
    """Every orphan, USEFUL ones first so their rows are easy to remember."""
    rows, table = census.animation_rows(game)
    named = {v.lower() for v in rows.values()}

    present = {}
    for model in census.SUPERMODELS:
        blob = game.get(model, census.RES_MDL)
        if not blob:
            continue
        for name, length, _t in census.read_animations(blob):
            present.setdefault(name.lower(), length)

    orphans = sorted(set(present) - named)
    useful_names = [u[0] for u in USEFUL]
    ordered = [n for n in useful_names if n in orphans]
    ordered += [n for n in orphans if n not in useful_names]
    return ordered, present, table


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--game", default=None)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "override"))
    ap.add_argument("--useful-only", action="store_true",
                    help="add rows only for the handful worth trying first")
    args = ap.parse_args()

    game = census.Game(args.game)
    ordered, present, table = build_rows(game)
    if args.useful_only:
        ordered = [n for n in ordered if n in [u[0] for u in USEFUL]]

    first_new = table.rows
    print("animations.2da has %d rows; %d orphan animations to add." % (table.rows, len(ordered)))
    print("New rows start at %d.\n" % first_new)
    flags = {u[0]: u for u in USEFUL}
    for i, name in enumerate(ordered):
        marker = "  <- worth trying" if name in flags else ""
        print("  row %3d  %-28s %5.2fs%s" % (first_new + i, name, present[name], marker))

    if not args.build:
        return 0

    for name in ordered:
        table.cells.append(["" for _ in table.columns])
        table.labels.append(str(table.rows))
        index = table.rows - 1
        for column in table.columns:
            table.set(index, column, "0")
        table.set(index, "name", name)
        entry = flags.get(name)
        if entry:
            (_n, description, stationary, walking, running, looping, fireforget,
             overlay) = entry
            table.set(index, "description", description)
            table.set(index, "stationary", stationary)
            table.set(index, "walking", walking)
            table.set(index, "running", running)
            table.set(index, "looping", looping)
            table.set(index, "fireforget", fireforget)
            table.set(index, "overlay", overlay)
        else:
            # Unknown clips are fire-and-forget overlays: the safest way to try
            # something is to play it once on top of whatever the body is doing.
            table.set(index, "description", "K2SE_recovered")
            table.set(index, "stationary", "1")
            table.set(index, "fireforget", "1")
            table.set(index, "overlay", "1")

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "animations.2da")
    with open(path, "wb") as fh:
        fh.write(table.write())
    print("")
    print("wrote %s (%d rows, was %d)" % (path, table.rows, first_new))
    print("Copy it into the game's override folder, then in the K2SE console:")
    print("  k2se> anim %d          # walkback" % first_new)
    return 0


if __name__ == "__main__":
    sys.exit(main())
