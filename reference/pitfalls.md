# Pitfalls — what actually went wrong, and the fix  /  踩坑记录

Every row was hit while producing a real two-colour K2 Pro print (black plate, white body,
white lettering) with Blender 5.1 + Creality Print 7.2.1 on macOS, 2026-09.

| # | Symptom / 现象 | Root cause / 原因 | Fix / 解决 |
|---|---|---|---|
| 1 | Blender 5.x has no 3MF import/export | 3MF is an extension, not built in | `blender --command extension install ThreeMF_io` |
| 2 | Headless script: `bpy.ops.import_mesh.threemf … could not be found` | extensions are not enabled in `-b` runs unless prefs say so | `addon_utils.enable("bl_ext.blender_org.ThreeMF_io", default_set=True)` |
| 3 | Imported model is 0.178 × 0.100 units | importer converts mm → m (object scale 0.001) | work in metres, export STL with `global_scale=1000` |
| 4 | Plate made in metres, car in mm-with-0.001-scale → exporter wrote scale 1000 on some items | mixed conventions in one scene | one convention; `creality3mf.py` bakes to mm anyway |
| 5 | Creality Print: "laid over the boundary of the plate" | Blender exporter centres the scene at (0,0); K2 bed is 0..300 | `build` centres on the bed |
| 6 | Objects render grey/dark in the viewport | they are outside the build volume (`is_outside` → OUTSIDE_COLOR) | same as 5 |
| 7 | Lettering object not shown; plate shows an empty pocket | text was a separate 3MF object; GUI dropped it | one object, N parts |
| 8 | Warning "Base_Black is too close to others; collisions" | by-object clearance check between separate objects (`Print.cpp` L1008) | one object, N parts |
| 9 | Inlaid (flush) lettering looked like a dark slot | white part coincident with the pocket faces; visually ambiguous | raise lettering 1 mm instead (same as the original model's "PORSCHE 959") |
| 10 | CLI: `Version Check: File Version 2.3.0.0 not supported by current cli version 7.2.1.5476` | Blender exporter stamps `Application=BambuStudio-2.3.0`; CLI compares major versions | stamp `Creality_Print V7.2.1.5476` (`--app-version`) or `--allow-newer-file` |
| 11 | CLI: `loaded_filament_ids size 3 should be the same with input files size 1` | `--load-filament-ids` is per input file | put slots in the 3MF parts, not on the CLI |
| 12 | CLI: `setup params error` | `--filament_colour` is not a CLI option; colours belong in filament JSON / project settings | `--project-from` + `--filament` |
| 13 | CLI exit 139 on `--info` for a file that passed minutes earlier | Creality Print GUI was open (local observation; not in source) | quit the GUI, rerun |
| 14 | Headless `--slice` crashes on a multi-colour file | known: CrealityPrint#574 | validate with `--info`; slice in the GUI |
| 15 | Original file had `enable_prime_tower=1` on a single-colour print | leftover from a multi-colour template | harmless; single colour never builds the tower |
| 16 | `MultiExtruder` mode in `custom_gcode_per_layer.xml` on a 1-colour file | plate mode flag, not a colour change | check `T`/`M620` count in gcode, or `slice_info` filament list |
| 17 | `extruder_colour=#FCE94F` looked like a yellow print | that is the UI colour of the physical extruder; `filament_colour` is the material | ignore `extruder_colour` |
| 18 | Text converted from a font is non-manifold | duplicate vertices at cap/side seams | `remove_doubles` (Blender) — Creality still repairs, but do it |
| 19 | Cycles/EEVEE render: black material shows mid-grey | area lights ×100 too bright → exposure; unrelated to print | reduce light energy (not a print issue, but it wastes time) |
| 20 | Creality Print `printable_area` in vendor JSON is a string `"0x0,300x0,…"` | not an array | `scripts/gen_printer_table.py` handles both |
