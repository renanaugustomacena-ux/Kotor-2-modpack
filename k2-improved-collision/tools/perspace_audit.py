"""Audit of collision radii in KOTOR 2's appearance.2da (Tier 0/1 of K2 Improved Collision).

    python tools/perspace_audit.py            read appearance.2da from the game (override > BIF), print the audit
    python tools/perspace_audit.py --csv out.csv   also write one row per appearance

Groups appearances by category (PC, party, commoner/civilian, hostile-looking, droid, large)
using the `label` column, and reports the distribution of perspace / creperspace / hitradius /
hitdist / sizecategory per group, plus the rows a Tier 1 patch would touch.

Read-only: it never writes into the game folder.
"""

import argparse
import csv
import os
import subprocess
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "k2-directional-movement", "tools"))
import twoda  # noqa: E402

GAME = r"G:\SteamLibrary\steamapps\common\Knights of the Old Republic II"
OVERRIDE_2DA = os.path.join(GAME, "override", "appearance.2da")
K2SE_TOOLS = os.path.join(ROOT, "K2SE", "tools")
CACHE = os.path.join(HERE, "..", "stock", "appearance.2da")

RADIUS_COLS = ["perspace", "creperspace", "hitradius", "hitdist", "cameraspace", "height", "sizecategory"]


def load_table():
    """Prefer the copy the game actually uses (override), else extract the shipped one once."""
    if os.path.exists(OVERRIDE_2DA):
        print("source: override/appearance.2da (a mod ships this file)")
        return twoda.load(OVERRIDE_2DA)
    if not os.path.exists(CACHE):
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        tool = os.path.join(K2SE_TOOLS, "kotor_res.py")
        subprocess.check_call([sys.executable, tool, "extract", "appearance", "2da", CACHE])
    print("source: shipped BIF copy (cached at %s)" % os.path.relpath(CACHE, HERE))
    return twoda.load(CACHE)


def category(label):
    l = label.lower()
    if l.startswith("p_"):
        return "PC"
    if l.startswith("party_npc") or any(k in l for k in ("atton", "kreia", "bao_dur", "baodur", "hk47", "t3m4", "g0t0", "mira", "hanharr", "visas", "disciple", "handmaiden", "mandalore")):
        return "party"
    if any(k in l for k in ("commoner", "czerka", "civilian", "merchant", "refugee", "twilek", "duros", "bith", "ithorian", "rodian", "sullustan", "aqualish", "quarren", "gran", "nikto", "trandoshan", "wookie", "zabrak", "ext_")):
        return "civilian-ish"
    if any(k in l for k in ("droid", "hk_", "hk5", "assassin_droid", "war_droid", "sentry", "protocol")):
        return "droid"
    if any(k in l for k in ("sith", "dark_jedi", "mercenary", "gand", "boma", "cannok", "maalraas", "kinrath", "laigrek", "zakkeg", "drexl", "rakghoul", "assassin", "swoop_gang", "bounty", "exchange", "thug", "gamorrean", "gammorean")):
        return "hostile-ish"
    return "other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="write per-row audit here")
    args = ap.parse_args()

    t = load_table()
    cols = [c for c in RADIUS_COLS if c.lower() in [x.lower() for x in t.columns]]
    groups = defaultdict(list)
    rows = []
    for r in range(t.rows):
        label = t.get(r, "label")
        cat = category(label)
        if "sizecategory" in cols and t.get(r, "sizecategory") in ("4", "5"):
            cat = "large(size4-5)"
        vals = {c: t.get(r, c) for c in cols}
        groups[cat].append((r, label, vals))
        rows.append((r, label, cat, vals))

    print("\nrows: %d   columns audited: %s\n" % (t.rows, ", ".join(cols)))
    for cat in ["PC", "party", "civilian-ish", "hostile-ish", "droid", "large(size4-5)", "other"]:
        items = groups.get(cat, [])
        if not items:
            continue
        print("== %s: %d rows" % (cat, len(items)))
        for c in cols:
            cnt = Counter(v[c] for _, _, v in items)
            print("   %-13s %s" % (c, ", ".join("%s x%d" % kv for kv in cnt.most_common(6))))

    # Tier 1 proposal: PC + party only, moderate values.
    print("\n== Tier 1 proposal (PC + party): creperspace -> 0.25, perspace -> 0.25 ==")
    touched = [it for cat in ("PC", "party") for it in groups.get(cat, [])]
    print("   rows touched: %d" % len(touched))
    for r, label, v in touched[:12]:
        print("   %4d %-28s perspace %s -> 0.25   creperspace %s -> 0.25" % (r, label, v.get("perspace"), v.get("creperspace")))
    if len(touched) > 12:
        print("   ... (%d more)" % (len(touched) - 12))

    if args.csv:
        with open(args.csv, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["row", "label", "category"] + cols)
            for r, label, cat, v in rows:
                w.writerow([r, label, cat] + [v[c] for c in cols])
        print("\nwrote %s" % args.csv)


if __name__ == "__main__":
    main()
