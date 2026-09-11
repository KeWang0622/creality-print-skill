#!/usr/bin/env python3
"""Two-colour name plate, no Blender required: black plate + raised white pixel lettering.

    python3 examples/nameplate.py "HELLO" --printer "Creality K2 Pro" -o examples/out/nameplate.3mf

Open the result in Creality Print (File > Open Project). It loads as ONE object with two
parts: `Plate` on filament slot 1 and `Lettering` on slot 2. Pixel letters are 2 mm
squares raised 1.0 mm, which prints cleanly with a 0.4 mm nozzle.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import creality3mf as c3  # noqa: E402

# 5x7 pixel font (uppercase, digits, a few symbols). Rows top->bottom, '1' = pixel.
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "01010", "00100", "00100", "00100", "01010", "10001"],
    "Y": ["10001", "01010", "00100", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "00000", "00100"],
    "!": ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
    "♥": ["01010", "11111", "11111", "11111", "01110", "00100", "00000"],
    " ": ["00000"] * 7,
}
GLYPH_W, GLYPH_H, ADVANCE = 5, 7, 6


def add_box(mesh, x0, y0, z0, x1, y1, z1):
    """Append a closed, outward-facing box to (vertices, triangles)."""
    verts, tris = mesh
    base = len(verts)
    verts += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
              (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    tris += [(base + a, base + b, base + c) for a, b, c in
             ((0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
              (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7))]


def lettering(text, pixel, height, z0, x0, y0):
    """Raised pixel letters as one mesh. Adjacent pixels overlap by a hair so the slicer unions them."""
    mesh = ([], [])
    eps = pixel * 0.02
    for i, ch in enumerate(text.upper()):
        rows = FONT.get(ch)
        if rows is None:
            raise ValueError(f"no glyph for {ch!r}; supported: {''.join(sorted(FONT))}")
        for r, row in enumerate(rows):
            for cidx, bit in enumerate(row):
                if bit == "1":
                    px = x0 + (i * ADVANCE + cidx) * pixel
                    py = y0 + (GLYPH_H - 1 - r) * pixel
                    add_box(mesh, px - eps, py - eps, z0 - eps, px + pixel + eps, py + pixel + eps, z0 + height)
    return mesh


def make_nameplate(text, pixel=2.0, plate_t=3.0, letter_h=1.0, margin=6.0):
    text_w = (len(text) * ADVANCE - 1) * pixel
    text_h = GLYPH_H * pixel
    plate_w, plate_d = text_w + 2 * margin, text_h + 2 * margin
    plate = ([], [])
    add_box(plate, 0, 0, 0, plate_w, plate_d, plate_t)
    letters = lettering(text, pixel, letter_h, plate_t, margin, margin)
    return [c3.Part("Plate", plate[0], plate[1], extruder=1),
            c3.Part("Lettering", letters[0], letters[1], extruder=2)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("text", nargs="?", default="HELLO")
    ap.add_argument("-o", "--output", default=os.path.join(os.path.dirname(__file__), "out", "nameplate.3mf"))
    ap.add_argument("--printer", default="Creality K2 Pro")
    ap.add_argument("--pixel", type=float, default=2.0, help="pixel size in mm (>= 2 for a 0.4 nozzle)")
    ap.add_argument("--project-from", help="existing Creality Print 3MF/JSON to take slicer settings from")
    ap.add_argument("--colours", nargs=2, default=["#000000", "#FFFFFF"], metavar=("PLATE", "LETTERS"))
    a = ap.parse_args(argv)

    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    parts = make_nameplate(a.text, pixel=a.pixel)
    settings = c3.load_project_settings(a.project_from) if a.project_from else None
    res = c3.build_3mf(parts, a.output, c3.Bed.from_printer(a.printer), title=f"nameplate {a.text}",
                       filaments=[{"colour": a.colours[0]}, {"colour": a.colours[1]}] if settings else (),
                       project_settings=settings)
    w, d, h = (res.bbox_max[i] - res.bbox_min[i] for i in range(3))
    print(f"wrote {res.path}: {w:.0f} x {d:.0f} x {h:.0f} mm, {len(parts)} parts "
          f"(slot 1 = plate, slot 2 = lettering)")
    for warning in res.warnings:
        print("note:", warning)
    return 0


if __name__ == "__main__":
    sys.exit(main())
