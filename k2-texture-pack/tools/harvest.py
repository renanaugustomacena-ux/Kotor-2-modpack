#!/usr/bin/env python3
# harvest.py - mechanical texture harvest from Skyrim mod folders.
# Read-only on source. Writes only into the raw/ target folder.
import os
import sys
import csv
import shutil
import struct
import argparse
import time

SRC = r"D:\mods"
DST = r"C:\Users\Renan Macena\Documents\KOTOR2-Modding\k2-texture-pack\raw"

EXTS = (".dds", ".png", ".tga", ".tif", ".tiff")
MAX_FILE_BYTES = 6291456           # 6 MB
CAP_BYTES = 21474836480            # 20 GB
MIN_FREE_BYTES = 42949672960       # 40 GB must stay free on C:
FREE_DRIVE = "C:\\"

INCLUDE = ["architecture", "dungeons", "dwemer", "clutter", "furniture", "landscape", "terrain",
"rocks", "rock", "road", "dirt", "grass", "sand", "snow", "metal", "iron", "steel", "brass",
"copper", "wood", "stone", "brick", "marble", "cloth", "leather", "rope", "fabric", "rug",
"carpet", "tapestry", "banner", "glass", "crystal", "panel", "pipe", "grate", "door", "gate",
"wall", "floor", "ceiling", "pillar", "column", "stair", "crate", "barrel", "chest", "sack",
"box", "container", "bottle", "cup", "plate", "pot", "urn", "vase", "lantern", "lamp",
"candle", "torch", "brazier", "table", "chair", "bench", "bed", "shelf", "cabinet",
"machinery", "gear", "cog", "lever", "valve", "imperial", "riften", "whiterun", "solitude",
"markarth", "windhelm", "winterhold", "falkreath", "morthal", "dawnstar", "farmhouse",
"ships", "ship", "shipwreck", "docks", "dock", "mines", "mine", "caves", "cave", "ruins",
"nordic", "forts", "fort", "decals", "decal", "sign", "signs", "book", "books", "potion",
"food"]

EXCLUDE = ["actors", "actor", "character", "characters", "armor", "armour", "weapons",
"weapon", "clothes", "clothing", "face", "faces", "hair", "eyes", "eye", "skin", "body",
"bodies", "creature", "creatures", "dragon", "dragons", "effects", "effect", "fx",
"interface", "menus", "menu", "cubemaps", "cubemap", "sky", "clouds", "cloud", "lod",
"water", "blood", "plants", "trees", "tree", "flora", "animals"]

CAT_INDUSTRIAL = ["dwemer", "machinery", "gear", "cog", "pipe", "panel", "grate", "lever",
"valve", "metal", "iron", "steel", "brass", "copper"]
CAT_ARCHITECTURE = ["architecture", "dungeons", "ruins", "forts", "fort", "nordic", "imperial",
"wall", "floor", "ceiling", "pillar", "column", "stair", "door", "gate", "riften", "whiterun",
"solitude", "markarth", "windhelm", "winterhold", "falkreath", "morthal", "dawnstar",
"farmhouse", "mines", "mine", "caves", "cave", "ships", "ship", "shipwreck", "docks", "dock"]
CAT_CLUTTER = ["clutter", "furniture", "crate", "barrel", "chest", "sack", "box", "container",
"bottle", "cup", "plate", "pot", "urn", "vase", "lantern", "lamp", "candle", "torch",
"brazier", "table", "chair", "bench", "bed", "shelf", "cabinet", "sign", "signs", "book",
"books", "potion", "food", "banner", "rug", "carpet", "tapestry"]
CAT_MATERIALS = ["wood", "stone", "brick", "marble", "cloth", "leather", "rope", "fabric",
"glass", "crystal", "decals", "decal"]

CAT_ORDER = ["industrial", "architecture", "clutter", "materials", "landscape"]


def hit(rel, words):
    for w in words:
        if w in rel:
            return w
    return None


def category(rel):
    if hit(rel, CAT_INDUSTRIAL):
        return "industrial"
    if hit(rel, CAT_ARCHITECTURE):
        return "architecture"
    if hit(rel, CAT_CLUTTER):
        return "clutter"
    if hit(rel, CAT_MATERIALS):
        return "materials"
    return "landscape"


def longpath(p):
    if p.startswith("\\\\?\\"):
        return p
    if p.startswith("\\\\"):
        return "\\\\?\\UNC\\" + p[2:]
    return "\\\\?\\" + p


def strip_long(p):
    if p.startswith("\\\\?\\UNC\\"):
        return "\\\\" + p[8:]
    if p.startswith("\\\\?\\"):
        return p[4:]
    return p


def dds_info(path):
    # returns (width, height, fourcc) for DDS, else empty strings
    try:
        with open(longpath(path), "rb") as f:
            head = f.read(88)
    except OSError:
        return ("", "", "")
    if len(head) < 88 or head[:4] != b"DDS ":
        return ("", "", "")
    try:
        height = struct.unpack_from("<I", head, 12)[0]
        width = struct.unpack_from("<I", head, 16)[0]
    except struct.error:
        return ("", "", "")
    fourcc = head[84:88].decode("latin-1", "replace").replace("\x00", "").strip()
    return (width, height, fourcc)


def scan():
    rows = []
    stats = {
        "mods_scanned": 0,
        "texture_files": 0,
        "skip_no_keyword": 0,
        "skip_excluded": 0,
        "skip_too_big": 0,
        "skip_parallax": 0,
        "skip_duplicate": 0,
        "errors": [],
    }
    seen = {}   # (lowercase filename, size) -> first mod folder name
    root_l = longpath(SRC)
    try:
        mods = sorted(
            [e.name for e in os.scandir(root_l) if e.is_dir(follow_symlinks=False)],
            key=lambda s: s.lower(),
        )
    except OSError as e:
        stats["errors"].append("scandir %s: %s" % (SRC, e))
        return rows, stats

    t0 = time.time()
    for mi, mod in enumerate(mods, 1):
        stats["mods_scanned"] += 1
        modroot = os.path.join(root_l, mod)
        for dirpath, dirnames, filenames in os.walk(
                modroot, onerror=lambda e: stats["errors"].append(str(e))):
            parts = strip_long(dirpath)[len(SRC) + 1:].split("\\")
            tex_i = None
            for i, p in enumerate(parts):
                if p.lower() == "textures":
                    tex_i = i
                    break
            if tex_i is None:
                continue
            base = "/".join(parts[tex_i + 1:])
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in EXTS:
                    continue
                stats["texture_files"] += 1
                rel = (base + "/" + fn) if base else fn
                rel_l = rel.lower()
                if hit(rel_l, EXCLUDE):
                    stats["skip_excluded"] += 1
                    continue
                if not hit(rel_l, INCLUDE):
                    stats["skip_no_keyword"] += 1
                    continue
                if fn.lower().endswith("_p.dds"):
                    stats["skip_parallax"] += 1
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    size = os.path.getsize(full)
                except OSError as e:
                    stats["errors"].append("stat %s: %s" % (strip_long(full), e))
                    continue
                if size > MAX_FILE_BYTES:
                    stats["skip_too_big"] += 1
                    continue
                key = (fn.lower(), size)
                first = seen.get(key)
                if first is not None and first != mod:
                    stats["skip_duplicate"] += 1
                    rows.append({
                        "mod": mod, "relpath": rel, "bytes": size,
                        "width": "", "height": "", "fourcc": "",
                        "category": category(rel_l), "copied": 0,
                        "reason": "duplicate of " + first,
                        "_src": strip_long(full), "_dup": 1,
                    })
                    continue
                if first is None:
                    seen[key] = mod
                if ext == ".dds":
                    w, h, fcc = dds_info(full)
                else:
                    w, h, fcc = ("", "", "")
                rows.append({
                    "mod": mod, "relpath": rel, "bytes": size,
                    "width": w, "height": h, "fourcc": fcc,
                    "category": category(rel_l), "copied": 0, "reason": "",
                    "_src": strip_long(full), "_dup": 0,
                })
        if mi % 200 == 0 or mi == len(mods):
            print("  scanned %d/%d mods, %d rows, %.0fs"
                  % (mi, len(mods), len(rows), time.time() - t0), flush=True)
    return rows, stats


def do_copy(rows, stats):
    live = [r for r in rows if not r["_dup"]]
    live.sort(key=lambda r: (CAT_ORDER.index(r["category"]),
                             r["mod"].lower(), r["relpath"].lower()))
    total = 0
    n = 0
    capped = False
    for r in live:
        if capped:
            r["copied"] = 0
            r["reason"] = "cap"
            continue
        dest = os.path.join(DST, r["mod"], r["relpath"].replace("/", "\\"))
        destl = longpath(dest)
        try:
            if os.path.exists(destl) and os.path.getsize(destl) == r["bytes"]:
                r["copied"] = 1
                r["reason"] = ""
                total += r["bytes"]
                n += 1
                continue
        except OSError:
            pass
        free = shutil.disk_usage(FREE_DRIVE).free
        if total + r["bytes"] > CAP_BYTES or free - r["bytes"] < MIN_FREE_BYTES:
            capped = True
            r["copied"] = 0
            r["reason"] = "cap"
            continue
        try:
            os.makedirs(longpath(os.path.dirname(dest)), exist_ok=True)
            shutil.copy2(longpath(r["_src"]), destl)
        except OSError as e:
            r["copied"] = 0
            r["reason"] = "error: %s" % e
            stats["errors"].append("copy %s: %s" % (r["_src"], e))
            continue
        r["copied"] = 1
        r["reason"] = ""
        total += r["bytes"]
        n += 1
        if n % 2000 == 0:
            print("  copied %d files, %.2f GB" % (n, total / 1073741824.0), flush=True)
    stats["copied_files"] = n
    stats["copied_bytes"] = total
    stats["skip_cap"] = sum(1 for r in live if r["reason"] == "cap")
    stats["skip_error"] = sum(1 for r in live if r["reason"].startswith("error:"))
    return stats


def write_outputs(rows, stats, mode):
    os.makedirs(longpath(DST), exist_ok=True)
    man = os.path.join(DST, "MANIFEST.csv")
    with open(longpath(man), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["mod", "relpath", "bytes", "width", "height", "fourcc",
                    "category", "copied", "reason"])
        for r in rows:
            w.writerow([r["mod"], r["relpath"], r["bytes"], r["width"], r["height"],
                        r["fourcc"], r["category"], r["copied"], r["reason"]])

    cand = len(rows)
    live = [r for r in rows if not r["_dup"]]
    mods_with = len(set(r["mod"] for r in rows))
    cats = {}
    for r in rows:
        c = cats.setdefault(r["category"], {"files": 0, "bytes": 0, "copied": 0})
        c["files"] += 1
        c["bytes"] += r["bytes"]
        c["copied"] += 1 if r["copied"] else 0
    permod = {}
    for r in rows:
        d = permod.setdefault(r["mod"], {"files": 0, "bytes": 0, "copied": 0, "cbytes": 0})
        d["files"] += 1
        d["bytes"] += r["bytes"]
        if r["copied"]:
            d["copied"] += 1
            d["cbytes"] += r["bytes"]

    cb = stats.get("copied_bytes", 0)
    cf = stats.get("copied_files", 0)
    L = []
    L.append("# INVENTORY - k2-texture-pack raw harvest")
    L.append("")
    L.append("mode: %s" % mode)
    L.append("source: %s (read only, no archive opened)" % SRC)
    L.append("rule: candidate = loose .dds/.png/.tga/.tif/.tiff under a folder named textures,")
    L.append("include keyword hit, no exclude keyword, <= 6 MB, not _p.dds.")
    L.append("")
    L.append("## TOTALS")
    L.append("")
    L.append("- mods scanned: %d" % stats["mods_scanned"])
    L.append("- mods with candidates: %d" % mods_with)
    L.append("- texture files seen (ext + textures folder): %d" % stats["texture_files"])
    L.append("- candidates: %d" % cand)
    L.append("- candidate GB: %.2f" % (sum(r["bytes"] for r in rows) / 1073741824.0))
    L.append("- copied files: %d" % cf)
    L.append("- copied GB: %.2f" % (cb / 1073741824.0))
    L.append("")
    L.append("## SKIPPED BY REASON")
    L.append("")
    L.append("| reason | files |")
    L.append("|---|---:|")
    L.append("| no include keyword | %d |" % stats["skip_no_keyword"])
    L.append("| exclude keyword | %d |" % stats["skip_excluded"])
    L.append("| bigger than 6 MB | %d |" % stats["skip_too_big"])
    L.append("| parallax _p.dds | %d |" % stats["skip_parallax"])
    L.append("| duplicate (name+size, earlier mod) | %d |" % stats["skip_duplicate"])
    L.append("| cap (20 GB or C: free below 40 GB) | %d |" % stats.get("skip_cap", 0))
    L.append("| copy error | %d |" % stats.get("skip_error", 0))
    if mode == "inventory":
        L.append("| not copied (inventory mode) | %d |" % len(live))
    L.append("")
    L.append("## CATEGORY")
    L.append("")
    L.append("| category | files | MB | copied |")
    L.append("|---|---:|---:|---:|")
    for c in CAT_ORDER:
        d = cats.get(c, {"files": 0, "bytes": 0, "copied": 0})
        L.append("| %s | %d | %.1f | %d |"
                 % (c, d["files"], d["bytes"] / 1048576.0, d["copied"]))
    L.append("")
    L.append("## TOP 30 MODS BY CANDIDATE MB")
    L.append("")
    L.append("| # | mod | files | MB |")
    L.append("|---:|---|---:|---:|")
    top = sorted(permod.items(), key=lambda kv: -kv[1]["bytes"])[:30]
    for i, (m, d) in enumerate(top, 1):
        L.append("| %d | %s | %d | %.1f |" % (i, m, d["files"], d["bytes"] / 1048576.0))
    L.append("")
    if stats["errors"]:
        L.append("## ERRORS (%d)" % len(stats["errors"]))
        L.append("")
        for e in stats["errors"][:50]:
            L.append("- %s" % e)
        L.append("")
    inv = os.path.join(DST, "INVENTORY.md")
    with open(longpath(inv), "w", encoding="utf-8") as f:
        f.write("\n".join(L))

    P = []
    P.append("Raw material for k2-texture-pack. Every file belongs to its Skyrim mod author. "
             "Personal use only. Redistribution needs each author's permission. "
             "Bethesda game archives were not extracted.")
    P.append("")
    if mode == "inventory":
        P.append("(inventory mode - nothing copied yet)")
        P.append("")
    for m, d in sorted([(m, d) for m, d in permod.items() if d["copied"]],
                       key=lambda kv: kv[0].lower()):
        P.append("%s - %d files - %.1f MB" % (m, d["copied"], d["cbytes"] / 1048576.0))
    prov = os.path.join(DST, "PROVENANCE.md")
    with open(longpath(prov), "w", encoding="utf-8") as f:
        f.write("\n".join(P) + "\n")

    return cand, mods_with, cf, cb, cats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", action="store_true")
    ap.add_argument("--copy", action="store_true")
    a = ap.parse_args()
    if a.inventory == a.copy:
        print("pick exactly one: --inventory or --copy")
        return 2
    mode = "copy" if a.copy else "inventory"
    t0 = time.time()
    print("scan start: %s" % SRC, flush=True)
    rows, stats = scan()
    print("scan done in %.0fs" % (time.time() - t0), flush=True)
    if a.copy:
        print("copy start -> %s" % DST, flush=True)
        do_copy(rows, stats)
    else:
        stats["copied_files"] = 0
        stats["copied_bytes"] = 0
        for r in rows:
            if not r["_dup"]:
                r["reason"] = "inventory"
    cand, mods_with, cf, cb, cats = write_outputs(rows, stats, mode)
    print("")
    print("MODE            %s" % mode)
    print("mods scanned    %d" % stats["mods_scanned"])
    print("mods w/ cand    %d" % mods_with)
    print("texture files   %d" % stats["texture_files"])
    print("candidates      %d" % cand)
    print("cand GB         %.2f" % (sum(r["bytes"] for r in rows) / 1073741824.0))
    print("copied files    %d" % cf)
    print("copied GB       %.2f" % (cb / 1073741824.0))
    print("skip nokeyword  %d" % stats["skip_no_keyword"])
    print("skip excluded   %d" % stats["skip_excluded"])
    print("skip too big    %d" % stats["skip_too_big"])
    print("skip parallax   %d" % stats["skip_parallax"])
    print("skip duplicate  %d" % stats["skip_duplicate"])
    print("skip cap        %d" % stats.get("skip_cap", 0))
    print("copy errors     %d" % stats.get("skip_error", 0))
    for c in CAT_ORDER:
        d = cats.get(c, {"files": 0, "bytes": 0, "copied": 0})
        print("cat %-12s %7d files %10.1f MB  copied %d"
              % (c, d["files"], d["bytes"] / 1048576.0, d["copied"]))
    print("errors          %d" % len(stats["errors"]))
    for e in stats["errors"][:10]:
        print("  ERR %s" % e)
    print("elapsed         %.0fs" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
