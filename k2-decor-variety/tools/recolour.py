"""Make colour variants of KOTOR's own props, so maps stop repeating themselves.

    python tools/recolour.py --list                        what a placeable uses
    python tools/recolour.py --plan                        the whole variant plan
    python tools/recolour.py --build --out build/override  write the pack
    python tools/recolour.py --preview plc_planter         one texture, as PNG

The catalogue (K2SE/tools/gen_catalog.py) says the game ships plants, tables,
statues, footlockers and crates -- but no vases, lanterns, plates or forks. The
small clutter simply is not in KOTOR, and importing it needs a mesh pipeline.
What IS available immediately is variety: the same props, desaturated and
shifted slightly in hue, so a room can hold six subtly different planters
instead of six identical ones.

How it works, and why it needs no new meshes: a KOTOR model names its textures,
and a TGA in override/ beats the TPC shipped in the BIFs. So a variant is just a
recoloured texture written under a new name, plus a placeables.2da row pointing a
new appearance at the same model with that texture. The mesh is untouched.

TPC is decoded here rather than through a library: header at 0, pixels at 128,
DXT1 for RGB and DXT5 for RGBA when dataSize is non-zero, raw otherwise. The
format follows ref/reone/src/libs/graphics/format/tpcreader.cpp.
"""

import argparse
import colorsys
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(REPO, "K2SE", "tools"))
sys.path.insert(0, os.path.join(REPO, "k2-directional-movement", "tools"))

import kotor_res  # noqa: E402
from twoda import TwoDA  # noqa: E402

RES_2DA = 2017
RES_MDL = 2002
RES_TPC = 3007
RES_TGA = 3
RES_MDX = 3008
RES_PWK = 3009

ENC_GRAY, ENC_RGB, ENC_RGBA = 1, 2, 4

# The variants. Kept deliberately gentle: Renan asked for "desaturated, slightly
# different colours", and a prop that shouts is worse than a repeated one.
# (name suffix, saturation multiplier, hue shift in degrees, value multiplier)
VARIANTS = [
    ("_a", 0.55, -0.02, 1.00),
    ("_b", 0.45, 0.03, 0.92),
    ("_c", 0.65, 0.06, 1.06),
    ("_d", 0.35, -0.05, 0.88),
]


# --- TPC ---------------------------------------------------------------------

def _dxt_colours(block):
    """The four interpolated colours of a DXT colour block."""
    c0, c1 = struct.unpack_from("<HH", block, 0)

    def expand(c):
        r = (c >> 11) & 0x1F
        g = (c >> 5) & 0x3F
        b = c & 0x1F
        return (r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)

    a, b = expand(c0), expand(c1)
    if c0 > c1:
        third = tuple((2 * a[i] + b[i]) // 3 for i in range(3))
        fourth = tuple((a[i] + 2 * b[i]) // 3 for i in range(3))
    else:
        third = tuple((a[i] + b[i]) // 2 for i in range(3))
        fourth = (0, 0, 0)
    return [a, b, third, fourth]


def _decode_dxt(data, width, height, rgba):
    """DXT1 (rgba=False) or DXT5 (rgba=True) -> a flat RGBA bytearray."""
    stride = 16 if rgba else 8
    out = bytearray(width * height * 4)
    blocks_x = (width + 3) // 4
    blocks_y = (height + 3) // 4
    for by in range(blocks_y):
        for bx in range(blocks_x):
            offset = (by * blocks_x + bx) * stride
            if offset + stride > len(data):
                return out
            if rgba:
                a0, a1 = data[offset], data[offset + 1]
                alpha_bits = int.from_bytes(data[offset + 2:offset + 8], "little")
                # DXT5 alpha: six interpolated steps when a0 > a1, otherwise
                # four plus explicit 0 and 255. The weights run 6:1 down to 1:6
                # over 7 -- using 7:1 overflows past 255 and corrupts the alpha
                # of every texture that takes this path.
                if a0 > a1:
                    alphas = [a0, a1] + [((6 - i) * a0 + (1 + i) * a1) // 7 for i in range(6)]
                else:
                    alphas = ([a0, a1] +
                              [((4 - i) * a0 + (1 + i) * a1) // 5 for i in range(4)] + [0, 255])
                colour_block = data[offset + 8:offset + 16]
            else:
                alphas = None
                alpha_bits = 0
                colour_block = data[offset:offset + 8]

            palette = _dxt_colours(colour_block)
            bits = struct.unpack_from("<I", colour_block, 4)[0]
            for py in range(4):
                for px in range(4):
                    x, y = bx * 4 + px, by * 4 + py
                    if x >= width or y >= height:
                        continue
                    index = (bits >> (2 * (py * 4 + px))) & 3
                    r, g, b = palette[index]
                    if alphas is not None:
                        a = alphas[(alpha_bits >> (3 * (py * 4 + px))) & 7]
                    elif index == 3 and not rgba:
                        # DXT1's fourth slot is transparent only in the c0<=c1 mode.
                        a = 0 if struct.unpack_from("<HH", colour_block, 0)[0] <= \
                            struct.unpack_from("<HH", colour_block, 0)[1] else 255
                    else:
                        a = 255
                    o = (y * width + x) * 4
                    out[o:o + 4] = bytes((r, g, b, a))
    return out


def read_tpc(blob):
    """(width, height, RGBA bytearray) from a TPC, top mip only."""
    if len(blob) < 128:
        raise ValueError("too small for a TPC")
    data_size = struct.unpack_from("<I", blob, 0)[0]
    width, height = struct.unpack_from("<HH", blob, 8)
    encoding = blob[12]
    if width == 0 or height == 0:
        raise ValueError("zero-sized TPC")
    # A height that is six times the width is a cubemap; only the first face is
    # of any use for recolouring a prop.
    if height // max(width, 1) == 6:
        height = width

    pixels = blob[128:]
    if data_size > 0:
        rgba = (encoding == ENC_RGBA)
        return width, height, _decode_dxt(pixels, width, height, rgba)

    out = bytearray(width * height * 4)
    if encoding == ENC_GRAY:
        for i in range(width * height):
            v = pixels[i] if i < len(pixels) else 0
            out[i * 4:i * 4 + 4] = bytes((v, v, v, 255))
    elif encoding == ENC_RGB:
        for i in range(width * height):
            o = i * 3
            if o + 3 > len(pixels):
                break
            out[i * 4:i * 4 + 4] = bytes((pixels[o], pixels[o + 1], pixels[o + 2], 255))
    elif encoding == ENC_RGBA:
        n = min(len(pixels), width * height * 4)
        out[:n] = pixels[:n]
    else:
        raise ValueError("unknown TPC encoding %d" % encoding)
    return width, height, out


def write_tga(path, width, height, rgba, with_alpha=True):
    """Uncompressed TGA. The engine reads these from override/, and unlike TPC
    they are editable in anything."""
    depth = 32 if with_alpha else 24
    header = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, width, height, depth,
                         0x20 if with_alpha else 0x00)
    body = bytearray()
    # TGA is BGR(A); with bit 5 of the descriptor set the rows run top-down,
    # which is the order the decoder produced.
    for i in range(width * height):
        r, g, b, a = rgba[i * 4:i * 4 + 4]
        body += bytes((b, g, r, a)) if with_alpha else bytes((b, g, r))
    with open(path, "wb") as fh:
        fh.write(header)
        fh.write(body)


# --- recolouring --------------------------------------------------------------

def recolour(rgba, saturation, hue_shift, value):
    """Desaturate, nudge the hue, scale the brightness. Alpha is untouched:
    it is a cutout mask on these props, and shifting it eats the geometry."""
    out = bytearray(rgba)
    cache = {}
    for i in range(0, len(out), 4):
        key = bytes(out[i:i + 3])
        got = cache.get(key)
        if got is None:
            r, g, b = (c / 255.0 for c in key)
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            h = (h + hue_shift) % 1.0
            s = min(1.0, s * saturation)
            v = min(1.0, v * value)
            got = bytes(int(round(c * 255.0)) for c in colorsys.hsv_to_rgb(h, s, v))
            cache[key] = got
        out[i:i + 3] = got
    return out


# --- the game's data ----------------------------------------------------------

class Game(object):
    def __init__(self, game=None):
        if game:
            kotor_res.GAME = game
        self.game = kotor_res.GAME
        self.bifs, self.entries = kotor_res.read_key(os.path.join(self.game, "chitin.key"))
        self._packs = None

    def get(self, resref, restype):
        return kotor_res.extract(self.bifs, self.entries, resref, restype)

    def table(self, name):
        blob = self.get(name, RES_2DA)
        return TwoDA.parse(blob) if blob else None

    def _load_texture_packs(self):
        """Textures do not live in the BIFs: they are in TexturePacks/*.erf.
        tpa is the high-resolution pack and is what a modern install renders."""
        if self._packs is not None:
            return
        self._packs = {}
        packs_dir = os.path.join(self.game, "TexturePacks")
        for name in ("swpc_tex_tpa.erf", "swpc_tex_tpb.erf", "swpc_tex_tpc.erf"):
            path = os.path.join(packs_dir, name)
            if not os.path.isfile(path):
                continue
            with open(path, "rb") as fh:
                data = fh.read()
            count = struct.unpack_from("<I", data, 0x10)[0]
            off_keys, off_res = struct.unpack_from("<II", data, 0x18)
            for i in range(count):
                k = off_keys + i * 24
                r = off_res + i * 8
                if k + 24 > len(data) or r + 8 > len(data):
                    break
                resref = data[k:k + 16].split(b"\x00")[0].decode("ascii", "replace").lower()
                offset, size = struct.unpack_from("<II", data, r)
                # First pack wins: tpa before tpb before tpc, highest quality first.
                self._packs.setdefault(resref, (path, offset, size))

    def texture_blob(self, resref):
        self._load_texture_packs()
        got = self._packs.get(resref.lower())
        if not got:
            return None
        path, offset, size = got
        with open(path, "rb") as fh:
            fh.seek(offset)
            return fh.read(size)

    def texture(self, resref):
        """The decoded top mip of a texture, from the packs or from override."""
        override = os.path.join(self.game, "override", resref + ".tpc")
        if os.path.isfile(override):
            with open(override, "rb") as fh:
                return read_tpc(fh.read())
        blob = self.texture_blob(resref)
        if blob:
            return read_tpc(blob)
        return None


# MDL node layout, from ref/reone/.../mdlmdxreader.cpp. The node header is 80
# bytes; a mesh node's own header follows it, and texture1 sits 88 bytes into
# that -- past two function pointers, the face array, the bounding box, radius,
# average, diffuse, ambient and the transparency hint.
MDL_DATA_OFFSET = 12
NODE_HEADER_SIZE = 80
MESH_TEXTURE1 = 88
NODE_FLAG_MESH = 0x20


def model_textures(blob):
    """Texture names a model's mesh nodes actually reference.

    Read out of the mesh headers rather than guessed from strings in the file:
    a model's node names (PLC_Plant1_wg, ..._pwk) look exactly like texture
    names and are not, so name-shaped guessing finds four plausible candidates
    and none of them real.
    """
    if len(blob) < MDL_DATA_OFFSET + 200:
        return []
    base = MDL_DATA_OFFSET

    def u32(at):
        return struct.unpack_from("<I", blob, at)[0]

    names = []
    seen = set()
    stack = [u32(base + 40)]          # offRootNode
    visited = set()
    while stack:
        offset = stack.pop()
        if offset in visited or base + offset + NODE_HEADER_SIZE > len(blob):
            continue
        visited.add(offset)
        at = base + offset
        flags = struct.unpack_from("<H", blob, at)[0]
        if flags & NODE_FLAG_MESH:
            to = at + NODE_HEADER_SIZE + MESH_TEXTURE1
            if to + 32 <= len(blob):
                raw = blob[to:to + 32].split(b"\x00")[0]
                try:
                    name = raw.decode("ascii").strip()
                except UnicodeDecodeError:
                    name = ""
                key = name.lower()
                if name and key not in seen and key not in ("null", "****"):
                    seen.add(key)
                    names.append(name)
        child_offset = u32(at + 44)
        child_count = u32(at + 48)
        for i in range(child_count):
            co = base + child_offset + 4 * i
            if co + 4 <= len(blob):
                stack.append(u32(co))
    return names


def placeable_rows(game):
    """(row, label, model) for every placeable the game defines."""
    table = game.table("placeables")
    if table is None:
        raise SystemExit("placeables.2da not found")
    out = []
    for row in range(table.rows):
        model = table.get(row, "modelname").strip()
        if not model or model == "****":
            continue
        out.append((row, table.get(row, "label").strip(), model))
    return out, table


# Props worth varying: the ones a room has several of, where repetition shows.
# Everything else is left alone on purpose -- a unique quest object with four
# recoloured twins is worse than the original problem.
WORTH_VARYING = ("plant", "planter", "footlocker", "crate", "container", "table",
                 "chair", "bench", "barrel", "canister", "statue", "rug", "computer")


def plan(game):
    rows, _table = placeable_rows(game)
    chosen = []
    for row, label, model in rows:
        name = (label + " " + model).lower()
        if any(word in name for word in WORTH_VARYING):
            chosen.append((row, label, model))
    return chosen


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--game", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "override"))
    ap.add_argument("--preview", default=None, help="dump one texture as TGA and stop")
    ap.add_argument("--limit", type=int, default=0, help="stop after N props (for a trial run)")
    args = ap.parse_args()

    game = Game(args.game)

    if args.preview:
        got = game.texture(args.preview)
        if not got:
            raise SystemExit("no texture resource named %s" % args.preview)
        w, h, rgba = got
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, args.preview + ".tga")
        write_tga(path, w, h, rgba)
        print("wrote %s (%dx%d)" % (path, w, h))
        for suffix, sat, hue, val in VARIANTS:
            p2 = os.path.join(args.out, args.preview + suffix + ".tga")
            write_tga(p2, w, h, recolour(rgba, sat, hue, val))
            print("wrote %s" % p2)
        return 0

    if args.list:
        rows, _ = placeable_rows(game)
        print("%d placeable rows with a model" % len(rows))
        for row, label, model in rows[:60]:
            print("  %4d  %-34.34s %s" % (row, label, model))
        return 0

    chosen = plan(game)
    if args.plan or not args.build:
        print("props worth varying: %d of %d placeable rows"
              % (len(chosen), len(placeable_rows(game)[0])))
        print("each gets %d variants -> %d new appearance rows"
              % (len(VARIANTS), len(chosen) * len(VARIANTS)))
        for row, label, model in chosen[:40]:
            print("  %4d  %-34.34s %s" % (row, label, model))
        if not args.build:
            return 0

    return build_pack(game, chosen, args.out, args.limit)


def fixed_string(name, length):
    """A NUL-padded fixed-width field, as the MDL stores names."""
    raw = name.encode("ascii", "replace")[:length - 1]
    return raw + bytes(length - len(raw))


def patch_model(blob, old_texture, new_texture, new_model_name):
    """A variant model: the same mesh, pointing at a different texture.

    placeables.2da has no texture column -- only modelname -- so two rows using
    the same model can only ever look the same. The texture is named inside the
    MDL, in the mesh header's fixed 32-byte texture1 field, so a variant is a
    copy of the model with that field rewritten. Both names are fixed-width, so
    nothing moves and every offset in the file stays valid; this is a byte
    substitution, not a re-serialisation.
    """
    out = bytearray(blob)
    base = MDL_DATA_OFFSET

    def u32(at):
        return struct.unpack_from("<I", out, at)[0]

    # The geometry header's own name, so the engine caches the two separately.
    out[base + 8:base + 40] = fixed_string(new_model_name, 32)

    patched = 0
    stack = [u32(base + 40)]
    visited = set()
    while stack:
        offset = stack.pop()
        if offset in visited or base + offset + NODE_HEADER_SIZE > len(out):
            continue
        visited.add(offset)
        at = base + offset
        flags = struct.unpack_from("<H", out, at)[0]
        if flags & NODE_FLAG_MESH:
            to = at + NODE_HEADER_SIZE + MESH_TEXTURE1
            if to + 32 <= len(out):
                current = bytes(out[to:to + 32]).split(b"\x00")[0].decode("ascii", "replace")
                if current.lower() == old_texture.lower():
                    out[to:to + 32] = fixed_string(new_texture, 32)
                    patched += 1
        child_offset = u32(at + 44)
        child_count = u32(at + 48)
        for i in range(child_count):
            co = base + child_offset + 4 * i
            if co + 4 <= len(out):
                stack.append(u32(co))
    return bytes(out), patched


def build_pack(game, chosen, out_dir, limit):
    """Write the variant models, their textures and the extended placeables.2da."""
    os.makedirs(out_dir, exist_ok=True)
    rows, table = placeable_rows(game)

    made = 0
    skipped = []
    new_rows = []
    for row, label, model in (chosen[:limit] if limit else chosen):
        mdl = game.get(model, RES_MDL)
        mdx = game.get(model, RES_MDX)
        if not mdl or not mdx:
            skipped.append((label, "model or mdx missing from the BIFs"))
            continue
        textures = [t for t in model_textures(mdl) if game.texture_blob(t)]
        if not textures:
            skipped.append((label, "no texture of its own in the packs"))
            continue
        base_texture = textures[0]
        try:
            width, height, pixels = game.texture(base_texture)
        except ValueError as exc:
            skipped.append((label, str(exc)))
            continue

        # A resref is 16 characters; the suffix has to fit inside that.
        stem_model = model[:16 - 2]
        stem_texture = base_texture[:16 - 2]
        pwk = game.get(model, RES_PWK)

        for suffix, saturation, hue, value in VARIANTS:
            model_name = stem_model + suffix
            texture_name = stem_texture + suffix
            patched, count = patch_model(mdl, base_texture, texture_name, model_name)
            if count == 0:
                skipped.append((label + suffix, "texture field not found to patch"))
                continue
            with open(os.path.join(out_dir, model_name + ".mdl"), "wb") as fh:
                fh.write(patched)
            # The MDX is vertex data addressed by offsets the MDL carries; it is
            # copied byte for byte under the new name because nothing in it
            # refers to the texture.
            with open(os.path.join(out_dir, model_name + ".mdx"), "wb") as fh:
                fh.write(mdx)
            if pwk:
                # Without its walkmesh the placeable has no collision and the
                # player walks through it.
                with open(os.path.join(out_dir, model_name + ".pwk"), "wb") as fh:
                    fh.write(pwk)
            write_tga(os.path.join(out_dir, texture_name + ".tga"), width, height,
                      recolour(pixels, saturation, hue, value))
            new_rows.append((row, (label + suffix)[:32], model_name))
            made += 1
        print("  %-32.32s %-14s texture %-14s %dx%d -> %d variants"
              % (label, model, base_texture, width, height, len(VARIANTS)))

    # Each variant needs its own appearance row, cloned from the original and
    # differing only in label and modelname -- that is what lets the console
    # place it and a module list it.
    for row, label, model_name in new_rows:
        table.cells.append(list(table.cells[row]))
        table.labels.append(str(table.rows))
        index = table.rows - 1
        table.set(index, "label", label)
        table.set(index, "modelname", model_name)

    twoda_path = os.path.join(out_dir, "placeables.2da")
    with open(twoda_path, "wb") as fh:
        fh.write(table.write())

    print("")
    print("%d variants: %d models, %d textures, placeables.2da now %d rows (was %d)"
          % (made, made, made, table.rows, table.rows - len(new_rows)))
    if skipped:
        print("%d skipped:" % len(skipped))
        for name, why in skipped[:12]:
            print("  %-34.34s %s" % (name, why))
    print("")
    print("Install: copy the contents of %s into the game's override folder." % out_dir)
    print("Then place them in game with the K2SE console (F10): `list _a`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
