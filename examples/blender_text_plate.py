"""Blender headless example: plate + real-font raised text → parts → multi-colour 3MF.

    blender -b --python examples/blender_text_plate.py -- --text "To Lindsey" --out /tmp/plate --build \
        [--font "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"] [--printer "Creality K2 Pro"]

Design rules baked in for a 0.4 mm nozzle: text raised 1.0 mm, cap height 14 mm, bold face.
"""
import argparse
import json
import os
import subprocess
import sys

import bpy
from mathutils import Vector

MM = 0.001  # the scene works in metres with unit scale 1.0, so 1 mm = 0.001 Blender units


def bbox(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return (Vector([min(p[i] for p in pts) for i in range(3)]),
            Vector([max(p[i] for p in pts) for i in range(3)]))


def make_plate(width, depth, thickness):
    bpy.ops.mesh.primitive_cube_add(size=1)
    plate = bpy.context.object
    plate.name = "Plate"
    plate.scale = (width * MM, depth * MM, thickness * MM)
    plate.location = (0, 0, thickness / 2 * MM)
    bpy.ops.object.transform_apply(scale=True)
    plate.data.materials.append(bpy.data.materials.new("E1_Plate"))
    return plate


def make_text(text, font, height_mm, max_width_mm, raise_mm, z_mm):
    cu = bpy.data.curves.new("Lettering", type="FONT")
    cu.body = text
    if font and os.path.exists(font):
        cu.font = bpy.data.fonts.load(font)
    cu.align_x = "CENTER"
    cu.extrude = raise_mm / 2 * MM
    cu.fill_mode = "BOTH"
    cu.size = height_mm * MM
    obj = bpy.data.objects.new("Lettering", cu)
    bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    lo, hi = bbox(obj)
    width = (hi.x - lo.x) / MM
    if width > max_width_mm:                       # shrink to fit the plate
        s = max_width_mm / width
        obj.scale = (s, s, 1)
        bpy.ops.object.transform_apply(scale=True)
        lo, hi = bbox(obj)
    centre = (lo + hi) / 2
    obj.location += Vector((0, 0, z_mm * MM + raise_mm / 2 * MM)) - centre  # stand on the plate top
    bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="EDIT")            # weld seams left by the font converter
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-6)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.data.materials.append(bpy.data.materials.new("E2_Lettering"))
    return obj


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default="HELLO")
    ap.add_argument("--out", required=True)
    ap.add_argument("--font", default="")
    ap.add_argument("--printer", default="Creality K2 Pro")
    ap.add_argument("--plate", nargs=2, type=float, default=[120, 40], metavar=("W", "D"))
    ap.add_argument("--thickness", type=float, default=3.0)
    ap.add_argument("--text-height", type=float, default=14.0)
    ap.add_argument("--raise", dest="raise_mm", type=float, default=1.0)
    ap.add_argument("--build", action="store_true", help="also run creality3mf.py build")
    a = ap.parse_args(argv)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    make_plate(a.plate[0], a.plate[1], a.thickness)
    make_text(a.text, a.font, a.text_height, a.plate[0] - 12, a.raise_mm, a.thickness)

    here = os.path.dirname(os.path.abspath(__file__))
    exporter = os.path.join(here, "..", "scripts", "blender_export_parts.py")
    sys.argv = [sys.argv[0], "--", "--out", a.out]
    with open(exporter, encoding="utf-8") as f:
        exec(compile(f.read(), exporter, "exec"), {"__name__": "__main__"})

    if a.build:
        with open(os.path.join(a.out, "parts.json"), encoding="utf-8") as f:
            manifest = json.load(f)["parts"]
        cmd = ["python3", os.path.join(here, "..", "creality3mf.py"), "build",
               "-o", os.path.join(a.out, "model.3mf"), "--printer", a.printer, "--title", a.text]
        for m in manifest:
            cmd += ["--part", f"{os.path.join(a.out, m['file'])}:{m['extruder']}:{m['name']}"]
        print("running:", " ".join(cmd))
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
