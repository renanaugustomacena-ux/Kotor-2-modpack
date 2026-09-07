"""What animations does KOTOR already have, and which does it never play?

    python tools/anim_census.py --supermodels
    python tools/anim_census.py --census
    python tools/anim_census.py --unused
    python tools/anim_census.py --suggest

Renan asked to port Skyrim's skeleton and animations onto KOTOR's NPCs. The
skeleton half of that is not possible -- see README.md -- but the question
underneath it is a good one, and it has a much cheaper answer than importing
anything: **the supermodels already contain animations the game never plays.**

s_male02 alone is 5 MB, almost all of it animation data. animations.2da lists
the rows the engine can address. K2SE can already play any row on demand
(anim::PlayRow, K2SE/src/anim.cpp). So before authoring a single new clip, it is
worth knowing exactly what is sitting there unused -- that is what this does.

The animation array hangs off the model header; each entry is a geometry header
(name at +8, 32 bytes) followed by length and transition time. Layout follows
ref/reone/src/libs/graphics/format/mdlmdxreader.cpp.
"""

import argparse
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(REPO, "K2SE", "tools"))
sys.path.insert(0, os.path.join(REPO, "k2-directional-movement", "tools"))

import kotor_res  # noqa: E402
from twoda import TwoDA  # noqa: E402

RES_MDL = 2002
RES_2DA = 2017

MDL_DATA_OFFSET = 12
OFF_ANIM_ARRAY = 88      # model header: ArrayDefinition{offset, count, count2}
OFF_SUPERMODEL = 136     # char[32]

# The supermodels every humanoid inherits from. Everything a PC or an NPC can do
# is defined in one of these.
SUPERMODELS = ["S_Male02", "S_Female02", "S_Male01", "S_Female01"]


def read_animations(blob):
    """[(name, length seconds, transition seconds)] declared by an MDL."""
    if len(blob) < MDL_DATA_OFFSET + 200:
        return []
    base = MDL_DATA_OFFSET

    def u32(at):
        return struct.unpack_from("<I", blob, at)[0]

    array_offset = u32(base + OFF_ANIM_ARRAY)
    count = u32(base + OFF_ANIM_ARRAY + 4)
    if count == 0 or count > 20000:
        return []

    out = []
    for i in range(count):
        entry = base + array_offset + 4 * i
        if entry + 4 > len(blob):
            break
        at = base + u32(entry)
        if at + 96 > len(blob):
            continue
        raw = blob[at + 8:at + 40].split(b"\x00")[0]
        try:
            name = raw.decode("ascii").strip()
        except UnicodeDecodeError:
            continue
        # Animation header sits right after the 80-byte geometry header.
        length, transition = struct.unpack_from("<ff", blob, at + 80)
        if name:
            out.append((name, length, transition))
    return out


def supermodel_of(blob):
    if len(blob) < MDL_DATA_OFFSET + OFF_SUPERMODEL + 32:
        return ""
    raw = blob[MDL_DATA_OFFSET + OFF_SUPERMODEL:
               MDL_DATA_OFFSET + OFF_SUPERMODEL + 32].split(b"\x00")[0]
    return raw.decode("ascii", "replace").strip()


class Game(object):
    def __init__(self, game=None):
        if game:
            kotor_res.GAME = game
        self.game = kotor_res.GAME
        self.bifs, self.entries = kotor_res.read_key(os.path.join(self.game, "chitin.key"))

    def get(self, resref, restype):
        return kotor_res.extract(self.bifs, self.entries, resref, restype)

    def table(self, name):
        blob = self.get(name, RES_2DA)
        return TwoDA.parse(blob) if blob else None


def animation_rows(game):
    """animations.2da: row -> name. These are what the engine can address."""
    table = game.table("animations")
    if table is None:
        raise SystemExit("animations.2da not found")
    column = "name" if "name" in [c.lower() for c in table.columns] else table.columns[0]
    rows = {}
    for row in range(table.rows):
        name = table.get(row, column).strip()
        if name and name != "****":
            rows[row] = name
    return rows, table


# Where K2SE's movement features could use a better clip than they have now.
# Each entry is (what it is for, substrings that would suit it).
WANTS = [
    ("sprint",       ("run", "sprint", "dash", "hurry")),
    ("jump start",   ("jump", "leap", "hop", "vault")),
    ("jump land",    ("land", "jumpland", "impact")),
    ("crouch idle",  ("crouch", "kneel", "duck", "stealth", "sneak")),
    ("crouch walk",  ("crouchwalk", "sneakwalk", "stealthwalk", "crawl")),
    ("dodge / roll", ("roll", "dodge", "dive", "evade", "tumble")),
    ("strafe left",  ("left", "sidestep", "strafe")),
    ("strafe right", ("right", "sidestep", "strafe")),
    ("walk back",    ("back", "reverse")),
    ("turn",         ("turn", "pivot")),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--game", default=None)
    ap.add_argument("--supermodels", action="store_true")
    ap.add_argument("--census", action="store_true")
    ap.add_argument("--unused", action="store_true")
    ap.add_argument("--suggest", action="store_true")
    ap.add_argument("--model", default=None, help="census one model instead")
    args = ap.parse_args()

    game = Game(args.game)

    if args.model:
        blob = game.get(args.model, RES_MDL)
        if not blob:
            raise SystemExit("no model %s" % args.model)
        anims = read_animations(blob)
        print("%s: supermodel %r, %d animations"
              % (args.model, supermodel_of(blob), len(anims)))
        for name, length, transition in anims:
            print("  %-28s %6.2fs  transition %.2fs" % (name, length, transition))
        return 0

    if args.supermodels:
        for name in SUPERMODELS:
            blob = game.get(name, RES_MDL)
            if not blob:
                print("%-14s not in the BIFs" % name)
                continue
            anims = read_animations(blob)
            total = sum(a[1] for a in anims)
            print("%-14s %8d bytes  %4d animations  %6.1f s of motion  supermodel %r"
                  % (name, len(blob), len(anims), total, supermodel_of(blob)))
        return 0

    rows, _table = animation_rows(game)
    in_models = {}
    for name in SUPERMODELS:
        blob = game.get(name, RES_MDL)
        if not blob:
            continue
        for anim, length, _t in read_animations(blob):
            in_models.setdefault(anim.lower(), []).append((name, length))

    named_rows = {v.lower() for v in rows.values()}

    if args.census:
        print("animations.2da rows: %d" % len(rows))
        print("distinct animations in the supermodels: %d" % len(in_models))
        both = named_rows & set(in_models)
        print("  addressable AND present: %d" % len(both))
        print("  in a 2da row but absent from the supermodels: %d"
              % len(named_rows - set(in_models)))
        print("  present but with NO 2da row: %d" % len(set(in_models) - named_rows))
        return 0

    if args.unused:
        orphans = sorted(set(in_models) - named_rows)
        print("%d animations exist in the supermodels but have no animations.2da row.\n"
              "The engine plays a row, so these need a row added before K2SE can\n"
              "reach them with anim::PlayRow -- but the motion is already authored.\n"
              % len(orphans))
        for anim in orphans:
            where = in_models[anim]
            print("  %-30s %.2fs  in %s" % (anim, where[0][1],
                                            ", ".join(w[0] for w in where)))
        return 0

    if args.suggest:
        print("Candidates already in the game for the movement features.\n"
              "'row' means K2SE can play it today with anim::PlayRow(row).\n")
        by_row = {v.lower(): k for k, v in rows.items()}
        for want, needles in WANTS:
            hits = []
            for anim in sorted(in_models):
                if any(n in anim for n in needles):
                    hits.append((anim, by_row.get(anim)))
            print("%-14s %d candidate(s)" % (want, len(hits)))
            for anim, row in hits[:8]:
                marker = ("row %d" % row) if row is not None else "NO ROW"
                print("    %-30s %-9s %.2fs" % (anim, marker, in_models[anim][0][1]))
            print("")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
