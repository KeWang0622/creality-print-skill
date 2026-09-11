"""Blender (headless) → per-part STL + manifest for creality3mf.

    blender -b scene.blend --python scripts/blender_export_parts.py -- --out /tmp/parts [--all]

Every visible mesh object becomes one STL in millimetres. The filament slot for each
part comes from, in order of precedence:
  1. an object custom property  `extruder` (int, 1-based)
  2. the first material name matching  E<N>  /  extruder<N>  /  slot<N>  (e.g. "E2_White")
  3. default 1
The script writes `<out>/parts.json` and prints the exact `creality3mf.py build` command.

Tested on Blender 4.2 – 5.1. `bpy.ops.wm.stl_export` writes Blender units, so the scene's
unit scale is applied explicitly (a metre-based scene with unit scale 1.0 is exported x1000).
"""
import argparse
import json
import os
import re
import sys

import bpy

SLOT_RE = re.compile(r"(?:^|[^a-z])(?:e|extruder|slot)\s*[_-]?(\d+)", re.I)


def slot_for(obj) -> int:
    if "extruder" in obj:
        return int(obj["extruder"])
    for slot in obj.material_slots:
        if slot.material:
            m = SLOT_RE.search(slot.material.name)
            if m:
                return int(m.group(1))
    return 1


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--all", action="store_true", help="export hidden objects too")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)

    scene = bpy.context.scene
    scale = 1000.0 * scene.unit_settings.scale_length   # Blender unit -> mm
    manifest = []
    used = set()
    for obj in scene.objects:
        if obj.type != "MESH" or (not a.all and obj.hide_render):
            continue
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        safe = stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", obj.name)
        n = 2
        while safe.lower() in used:          # "Plate" and "Plate " must not overwrite each other
            safe, n = f"{stem}_{n}", n + 1
        used.add(safe.lower())
        path = os.path.join(a.out, f"{safe}.stl")
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, global_scale=scale,
                              apply_modifiers=True)
        manifest.append({"file": os.path.basename(path), "name": obj.name, "extruder": slot_for(obj)})
        print(f"exported {obj.name:<24} -> {path}  slot {manifest[-1]['extruder']}")

    with open(os.path.join(a.out, "parts.json"), "w", encoding="utf-8") as f:
        json.dump({"parts": manifest}, f, indent=2)
    parts = " ".join(f'--part "{os.path.join(a.out, m["file"])}:{m["extruder"]}:{m["name"]}"' for m in manifest)
    print('\nnext:\n  python3 creality3mf.py build -o model.3mf --printer "Creality K2 Pro" ' + parts)


if __name__ == "__main__":
    main()
