"""Build the K2 Directional Movement override.

    python build.py              build into Override/
    python build.py --install    ... and copy it into the game's Override folder
    python build.py --uninstall  remove it from the game's Override folder
    python build.py --show       print the shipped table and the built one

WHAT THIS CHANGES, AND WHY IT IS ONE NUMBER

KOTOR 2's player controller is CSWPlayerControlCamRelative, and -- contrary to
how the game feels on a keyboard -- it is genuinely camera-relative. It takes a
2D input vector, rotates it into camera space, converts it to a target heading,
and then turns the character toward that heading at a RATE LIMIT. The limit is
(disassembled at 0x00866057, in the update at 0x00865830):

    turnRate = minturnrate + (maxturnrate - minturnrate) * (1 - speed / maxSpeed)

Turn rate is inversely proportional to speed. Standing still you get
`maxturnrate` and the character spins freely; at a full run you get
`minturnrate`, which the shipped table sets to 150 deg/s almost everywhere. At
150 deg/s a 180-degree reversal takes 1.2 seconds, during which the character
arcs around like a vehicle. That is the "tank controls" feeling, and it is not a
control scheme -- it is two numbers in camerastyle.2da.

Setting minturnrate = maxturnrate removes the ramp: the turn rate no longer
depends on how fast you are moving, so the character reorients to the input
heading just as readily at a sprint as standing still.

The engine reads the row chosen by the current area's `CameraStyle` field in
its ARE, so every row has to be treated, not just DEFAULT.

EVIDENCE THAT THE MODEL IS RIGHT, BEFORE YOU EDIT ANYTHING

Row 1 (EbonHawk) already ships with minturnrate == maxturnrate == 500, while
DEFAULT and the outdoor rows ship 150. So the shipped data contains its own
control experiment: if turning while running feels noticeably crisper aboard the
Ebon Hawk than it does outdoors, the model above is confirmed on your install
with no files touched at all.
"""

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import twoda  # noqa: E402

GAME = r"G:\SteamLibrary\steamapps\common\Knights of the Old Republic II"
GAME_OVERRIDE = os.path.join(GAME, "override")
K2SE_TOOLS = r"C:\Users\Renan Macena\Documents\KOTOR2-Modding\K2SE\tools"

OUT_DIR = os.path.join(HERE, "Override")
OUT_2DA = os.path.join(OUT_DIR, "camerastyle.2da")
STOCK_2DA = os.path.join(HERE, "stock", "camerastyle.2da")

# How the turn rate is flattened.
#   "match_max"  minturnrate = maxturnrate, per row. Keeps each area's own
#                character (the Ebon Hawk stays tighter than open ground) while
#                removing the speed-dependent slowdown. This is the default and
#                the least opinionated change that fixes the feel.
#   a number     use this value for BOTH columns on every row. Blunt, uniform,
#                useful for A/B testing how fast is too fast.
MODE = "match_max"


def extract_stock():
    """Pull the shipped camerastyle.2da out of the game's BIFs, once."""
    if os.path.exists(STOCK_2DA):
        return STOCK_2DA
    os.makedirs(os.path.dirname(STOCK_2DA), exist_ok=True)
    tool = os.path.join(K2SE_TOOLS, "kotor_res.py")
    if not os.path.exists(tool):
        raise SystemExit(
            "cannot find K2SE's kotor_res.py at %s -- it is what reads the BIFs.\n"
            "Adjust K2SE_TOOLS at the top of this file." % tool)
    subprocess.check_call([sys.executable, tool, "extract", "camerastyle", "2da", STOCK_2DA])
    return STOCK_2DA


def show(table, title):
    print("\n%s" % title)
    print("  %-4s %-10s %12s %12s" % ("row", "name", "maxturnrate", "minturnrate"))
    for r in range(table.rows):
        print("  %-4d %-10s %12s %12s" % (
            r, table.get(r, "name"), table.get(r, "maxturnrate"), table.get(r, "minturnrate")))


def build():
    stock = twoda.load(extract_stock())
    show(stock, "SHIPPED camerastyle.2da")

    table = twoda.load(STOCK_2DA)
    for r in range(table.rows):
        target = table.get(r, "maxturnrate") if MODE == "match_max" else str(MODE)
        if MODE != "match_max":
            table.set(r, "maxturnrate", target)
        table.set(r, "minturnrate", target)

    os.makedirs(OUT_DIR, exist_ok=True)
    twoda.save(table, OUT_2DA)
    show(table, "BUILT Override/camerastyle.2da  (mode: %s)" % MODE)

    # Only the two turn columns may differ. camerastyle.2da also configures the
    # chase camera -- distance, pitch, height, framing -- and a stray edit there
    # would silently change how the whole game looks.
    changed = set()
    for r in range(table.rows):
        for c in table.columns:
            if stock.get(r, c) != table.get(r, c):
                changed.add(c)
    unexpected = changed - {"maxturnrate", "minturnrate"}
    if unexpected:
        raise SystemExit("REFUSING: unexpected columns changed: %s" % ", ".join(sorted(unexpected)))
    print("\n  columns changed: %s  (camera framing untouched)" % ", ".join(sorted(changed)))
    print("  wrote %s (%d bytes)" % (OUT_2DA, os.path.getsize(OUT_2DA)))
    return OUT_2DA


def install():
    src = build()
    if not os.path.isdir(GAME_OVERRIDE):
        raise SystemExit("game override folder not found: %s" % GAME_OVERRIDE)
    dst = os.path.join(GAME_OVERRIDE, "camerastyle.2da")
    shutil.copy(src, dst)
    print("\nINSTALLED -> %s" % dst)
    print("Uninstall with:  python build.py --uninstall   (or just delete that file)")


def uninstall():
    dst = os.path.join(GAME_OVERRIDE, "camerastyle.2da")
    if os.path.exists(dst):
        os.remove(dst)
        print("removed %s" % dst)
        print("The game falls back to the copy in its BIFs. Nothing else was touched.")
    else:
        print("nothing installed at %s" % dst)


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        uninstall()
    elif "--show" in sys.argv:
        show(twoda.load(extract_stock()), "SHIPPED camerastyle.2da")
    elif "--install" in sys.argv:
        install()
    else:
        build()
