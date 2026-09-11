# Blender headless notes (4.2 – 5.1)

## Install / enable the 3MF extension
```bash
blender --command extension sync
blender --command extension install ThreeMF_io        # extensions.blender.org, GPL-3.0, Blender ≥ 4.2
```
Module id: `bl_ext.blender_org.ThreeMF_io`. In `-b` scripts:
```python
import addon_utils
addon_utils.enable("bl_ext.blender_org.ThreeMF_io", default_set=True, persistent=True)
bpy.ops.import_mesh.threemf(filepath="in.3mf")
```
The importer gives each 3MF object a material named `3MF_Extruder_N` and scales mm → m.

## Units
Scene unit scale 1.0 + metres is Blender's default; 1 mm = 0.001 BU. Export:
`bpy.ops.wm.stl_export(filepath, export_selected_objects=True, global_scale=1000 * scene.unit_settings.scale_length, apply_modifiers=True)`
(`wm.stl_export` replaced `export_mesh.stl` in 4.1).

## Text that prints
```python
cu = bpy.data.curves.new("t", type="FONT"); cu.body = "HELLO"
cu.font = bpy.data.fonts.load("/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf")
cu.extrude = 0.0005          # ±0.5 mm → 1 mm thick
cu.fill_mode = "BOTH"; cu.size = 0.014
obj = bpy.data.objects.new("Lettering", cu); scene.collection.objects.link(obj)
bpy.ops.object.convert(target="MESH")      # then remove_doubles, then position on the plate top
```
Bold/rounded faces keep strokes ≥ 0.9 mm at 12–15 mm cap height. Script faces do not.

## Splitting an existing single-colour model into parts
`bpy.ops.mesh.separate(type='LOOSE')` then group shells by bounding box (e.g. z < 0.5 mm = base).
Re-join per colour with `bpy.ops.object.join()`. Replace a non-manifold base with a fresh cube
of the same footprint rather than repairing it.

## Marking slots
Material name `E1_Black`, `E2_White` (regex `(?:e|extruder|slot)[_-]?(\d+)`) or object custom
property `obj["extruder"] = 2`. `scripts/blender_export_parts.py` reads both.

## Why not export 3MF straight from Blender?
The extension writes valid Bambu-style files (per-object extruder from material names, project
settings copied from the imported file) but: every object becomes a separate 3MF object, the
scene is re-centred at (0,0), and the `Application` stamp trips Creality's CLI version gate.
Use it to *read* 3MF; use `creality3mf.py` to *write*.
