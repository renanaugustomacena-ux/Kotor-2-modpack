"""Read and write KOTOR's binary 2DA format ("2DA V2.b").

Enough of the format to round-trip a table and change cells. Deliberately small:
this exists to edit camerastyle.2da, not to be a general modding library.

Layout, confirmed by round-tripping the shipped camerastyle.2da byte-for-byte:

    "2DA V2.b\\n"
    <column name>\\t ... <column name>\\t \\0
    uint32   row count
    <row label>\\t ... <row label>\\t
    uint16   cell offsets, row-major, rows*cols of them, into the data block
    uint16   data block size
    <data block: NUL-terminated strings>

Cells are STRINGS, not floats -- the engine calls atof on them when it reads a
numeric column (C2DA::GetFloatEntry @0x0071B670). So "1500" and "1500.0" are
both fine, and an empty cell is a real, distinct state.

Offsets are deduplicated in the shipping files: equal cell values share one
string. write() does the same, which keeps the output close in size to the
original and makes a diff of the two files legible.
"""

import struct


class TwoDA(object):
    def __init__(self, columns, labels, cells):
        self.columns = columns          # list[str]
        self.labels = labels            # list[str], one per row
        self.cells = cells              # list[list[str]], [row][col]

    # --- access ---------------------------------------------------------
    def col(self, name):
        """Column index by name, case-insensitively -- the engine resolves
        column names case-insensitively too, and the shipped tables are not
        consistent about case."""
        low = name.lower()
        for i, c in enumerate(self.columns):
            if c.lower() == low:
                return i
        raise KeyError("no such column: %s (have: %s)" % (name, ", ".join(self.columns)))

    def get(self, row, column):
        return self.cells[row][self.col(column)]

    def set(self, row, column, value):
        self.cells[row][self.col(column)] = str(value)

    @property
    def rows(self):
        return len(self.labels)

    # --- parse ----------------------------------------------------------
    @classmethod
    def parse(cls, blob):
        if blob[:8] != b"2DA V2.b":
            raise ValueError("not a binary 2DA (header was %r)" % blob[:9])
        i = 9                                        # past "2DA V2.b\n"

        end = blob.index(b"\x00", i)
        columns = [c.decode("ascii") for c in blob[i:end].split(b"\t") if c]
        i = end + 1

        nrows, = struct.unpack_from("<I", blob, i)
        i += 4

        labels = []
        for _ in range(nrows):
            k = blob.index(b"\t", i)
            labels.append(blob[i:k].decode("ascii"))
            i = k + 1

        ncells = nrows * len(columns)
        offsets = struct.unpack_from("<%dH" % ncells, blob, i)
        i += ncells * 2

        datasize, = struct.unpack_from("<H", blob, i)
        i += 2
        data = blob[i:i + datasize]

        def at(off):
            return data[off:data.index(b"\x00", off)].decode("ascii")

        cells = [[at(offsets[r * len(columns) + c]) for c in range(len(columns))]
                 for r in range(nrows)]
        return cls(columns, labels, cells)

    # --- serialise ------------------------------------------------------
    def write(self):
        out = bytearray(b"2DA V2.b\n")
        for c in self.columns:
            out += c.encode("ascii") + b"\t"
        out += b"\x00"
        out += struct.pack("<I", self.rows)
        for l in self.labels:
            out += l.encode("ascii") + b"\t"

        # Build the data block first, deduplicating equal values so the file
        # stays the size the engine's own tables are.
        data = bytearray()
        seen = {}
        offsets = []
        for r in range(self.rows):
            for c in range(len(self.columns)):
                v = self.cells[r][c]
                if v not in seen:
                    seen[v] = len(data)
                    data += v.encode("ascii") + b"\x00"
                offsets.append(seen[v])

        if len(data) > 0xFFFF:
            raise ValueError("data block too large for a uint16 size field")
        for o in offsets:
            out += struct.pack("<H", o)
        out += struct.pack("<H", len(data))
        out += data
        return bytes(out)


def load(path):
    with open(path, "rb") as fh:
        return TwoDA.parse(fh.read())


def save(table, path):
    with open(path, "wb") as fh:
        fh.write(table.write())
