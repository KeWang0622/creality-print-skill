---
name: creality-print
description: Author print-ready, multi-colour 3MF models for Creality (创想三维) FDM printers — K2 / K1 series with CFS — and for Bambu Studio / OrcaSlicer, which read the same 3MF dialect. Use when asked to prepare, colour, split, letter, resize or repair a model for Creality Print; to add raised text or logos to a print; to turn a Blender scene into a printable multi-colour file; or when a 3MF opens with no colours, missing parts, "outside the plate" or "too close to others" errors.
---

# Creality Print Skill

You are preparing a file that a human will open in **Creality Print** (or Bambu Studio / OrcaSlicer)
and send to a printer. The deliverable is a `.3mf` that opens as **one object with N parts, each part
on a filament slot**, sitting inside the bed, with no manual fixing required. Everything below is
verified against Creality Print 7.2.1 source (`bbs_3mf.cpp`, a Bambu Studio fork) and real files —
see `reference/sources.md` for citations and `reference/pitfalls.md` for what went wrong before.

## 1. When to use / when not

Use this skill when the user wants any of:
- a multi-colour print (CFS / AMS): "plate black, text white", "logo in a second colour"
- text, names, logos or dates added to an existing model
- an STL/OBJ/Blender scene turned into something Creality Print opens correctly
- a diagnosis of a 3MF that shows no colours, loses a part, or lands off the plate

Do **not** use it for: resin printers (Halot uses `.cxdlp`, no multi-colour), G-code editing
(never hand-edit G-code), texture/painted-surface colour (that is the slicer's paint tool, not
part assignment), or printers from other vendors that do not read Bambu-style 3MF.

## 2. Mental model (read once)

```
 geometry (STL/OBJ/Blender)  ──►  3MF container  ──►  sliced G-code (slicer's job)
 mm, z-up, watertight              ONE object,          you never produce this
                                   N <part>s,
                                   part.extruder = slot
```

- A 3MF is a ZIP. The parts that matter: `3D/3dmodel.model` (object tree, placement),
  `3D/Objects/object_2.model` (meshes), `Metadata/model_settings.config` (names + per-part
  `extruder`), optional `Metadata/project_settings.config` (printer/filament presets + colours).
- **Colour = filament slot, not RGB.** A part with `extruder="2"` prints with whatever is in slot 2.
  Colours in `project_settings.config` are only what the slicer shows; the CFS/AMS mapping at
  print time decides the real filament.
- **One object, many parts** — never N separate objects. Separate objects trigger "too close to
  others", can be dropped on load, and are re-arranged independently.
- **Model-only vs project 3MF.** Without `project_settings.config` the file opens with the
  user's current printer/filaments (portable, recommended for sharing). With it, the file carries
  a full preset (use `--project-from` on a 3MF the user's own Creality Print saved).

## 3. Workflow

1. **Inspect the input** — `python3 creality3mf.py inspect in.3mf` (or read the STL bbox).
   Note printer, bed, existing parts, whether it is already sliced (`sliced: True` means the
   gcode inside is stale the moment you change geometry).
2. **Confirm the printer** — `python3 creality3mf.py printers K2` → bed and height come from
   Creality's own vendor profiles (`data/printers.json`). Ask if unknown; never guess a bed size.
3. **Decide the parts** — one part per colour region. Typical: `Plate` (slot 1), `Body` (slot 2),
   `Lettering` (slot 2 or 3). Parts may touch; avoid overlapping volumes (double walls).
4. **Build geometry in millimetres** — pure Python (`examples/nameplate.py`) when the parts are
   boxes/cylinders/pixel text and Blender is not installed; Blender (`examples/blender_text_plate.py`)
   when you need real fonts, booleans, or to split/repair an existing mesh. Rules in §4. Raised features sit *on* a surface (z = top), inlays
   need a matching pocket; do not leave a part floating.
5. **Export parts** — Blender: `scripts/blender_export_parts.py` (STL, mm, manifest with slots).
6. **Assemble** — `python3 creality3mf.py build -o out.3mf --printer "Creality K2 Pro" \
   --part Plate.stl:1 --part Lettering.stl:2 [--filament "#000000" --filament "#FFFFFF" \
   --project-from users_own.3mf]`. The tool centres the group on the bed, drops it to z = 0,
   and refuses to write a file that does not fit. No `--project-from` at hand? Ship a model-only
   3MF (omit `--filament`); the user's current printer/filament presets apply and part slots still
   work. Ask the user for any 3MF their Creality Print saved if they want colours embedded.
7. **Verify** — `python3 creality3mf.py inspect out.3mf`: exactly one object, all parts listed
   with the intended extruder, bbox inside the bed. If Creality Print CLI is available *and the
   GUI is closed*, `CrealityPrint --info out.3mf` must exit 0 (see §6).
8. **Deliver** with instructions: *File → Open Project*, check the filament list shows N slots,
   load matching filament in CFS slots 1..N, slice. Say that a prime/purge tower is automatic
   and adds time/material.

## 4. Design rules for multi-colour FDM (0.4 mm nozzle)

| Feature | Minimum | Why |
|---|---|---|
| Wall / stroke width | 0.9 mm (2 perimeters at 0.45 mm) | thinner strokes are skipped or single-walled |
| Raised text height | 0.8–1.0 mm (4–5 layers at 0.2) | fewer layers look faint; 1 mm is crisp |
| Cap height for text | ≥ 10 mm, bold sans/rounded face | thin serifs fall below stroke minimum |
| Standalone island (dot of an i) | ≥ 2 mm | adhesion and purge quality |
| Plate under lettering | ≥ 2.4 mm thick | rigidity, no warping on a 200 mm plate |
| Colour change count | keep parts few and large | every colour swap purges ~30–60 mm of filament |

Dark-after-light transitions purge more than light-after-dark; put black on slot 1 when
possible. Prime tower is enabled automatically for >1 filament — do not disable it.

## 5. Blender (headless) recipe

```bash
blender --command extension install ThreeMF_io      # once; extensions.blender.org "3MF Import/Export"
blender -b --python examples/blender_text_plate.py -- --text "HELLO" --out /tmp/p --build
```
- Headless scripts must enable the extension themselves:
  `addon_utils.enable("bl_ext.blender_org.ThreeMF_io", default_set=True)`. Operators are
  `bpy.ops.import_mesh.threemf` / `bpy.ops.export_mesh.threemf`.
- Units: the importer scales mm → metres (object scale 0.001). Keep one convention per scene and
  export STL with `global_scale=1000 * scene.unit_settings.scale_length`.
- Text: `cu.extrude = h/2` gives total thickness `h`; convert to mesh, `remove_doubles`, then
  place its bottom on the plate top. Fonts on macOS: `/System/Library/Fonts/Supplemental/*.ttf`.
- Mark slots with material names `E1_…`, `E2_…` or an object custom property `extruder`.
- Blender's 3MF exporter writes per-object extruders from materials but centres the whole scene
  at (0,0) and makes every object a separate 3MF object → use it for import, use
  `creality3mf.py` for output.

## 6. Creality Print CLI

`/Applications/Creality Print.app/Contents/MacOS/CrealityPrint` (macOS) supports `--info`,
`--export-3mf`, `--export-stl(s)`, `--slice 0|N`, `--load-settings "machine.json;process.json"`,
`--load-filaments "f1.json;f2.json"`, `--arrange 0|1`, `--outputdir`, `--debug N --logfile F`.
- **Version gate**: the CLI refuses a 3MF whose major version differs from its own or whose minor
  is newer (`CrealityPrint.cpp` ~L1505). `--allow-newer-file` bypasses it. `creality3mf.py`
  stamps the file with `--app-version` (default 7.2.1.5476) so `--info` passes.
- `--load-filament-ids "1,2"` is **per input file**, not per part.
- Observed on macOS: the CLI segfaults (exit 139) whenever the GUI is running; close the GUI
  first. Not confirmed in source — treat as a local observation.
- Headless multi-colour *slicing* is unreliable (CrealityPrint#574). Validate with `--info`;
  let the human slice in the GUI.

## 7. Pitfalls (short form — full table in `reference/pitfalls.md`)

| Symptom | Cause | Fix |
|---|---|---|
| Model in the corner / "laid over the boundary" | coordinates centred at (0,0) | `build` centres on the bed |
| Grey/dark object in the viewport | outside the plate | same |
| Lettering missing, plate shows a pocket | text was a separate object and got dropped | one object, N parts |
| "too close to others; collisions" | separate objects within clearance radius | one object, N parts |
| Colours not applied | part extruder missing, or object has 1 volume | `inspect` shows `extruder=` per part |
| Only 1 filament in the list | no `project_settings`, or arrays length ≠ slots | `--project-from` + `--filament` ×N |
| CLI "File Version … not supported" | version gate | `--allow-newer-file` or matching `--app-version` |
| Blender renders every material grey | lights ×100 too strong → exposure, not materials | irrelevant to printing; lower light energy |

## 8. Compatibility

| Slicer | Reads one-object/N-part `extruder` | Notes |
|---|---|---|
| Creality Print 7.2.1 | ✅ verified (GUI + CLI `--info`) | primary target; adds `Metadata/creality.config` |
| Creality Print 6.x | expected | same loader; the source template for project settings was a 6.3 file |
| Bambu Studio 1.x–2.x | expected | same loader lineage; ignores `creality.config` — unverified |
| OrcaSlicer 2.x | expected | same — unverified |
| PrusaSlicer | ⚠️ | needs `Slic3r_PE_model.config` (not written) — import as plain 3MF |
| Cura | ⚠️ | reads geometry only; colours lost |

## 9. Delivery checklist

- [ ] `inspect` shows 1 object, N parts, expected extruders, bbox inside bed, `sliced: False`
- [ ] every part is watertight or the slicer repaired it (`--info` → `manifold = yes`)
- [ ] filaments listed = slots used; slot 1 holds the plate/base colour
- [ ] user told: Open Project (not Import), map CFS slots, prime tower expected
- [ ] source geometry (.blend/.py) handed over so the next edit does not start from a 3MF

## 中文速览

- 目标交付物：**一个物体、多个 part、每个 part 绑定一个耗材槽** 的 3MF，落在平台内，用户打开即切片。
- 颜色 = 耗材槽号，不是 RGB；文件里的颜色只是切片软件的显示，真正用哪卷料由 CFS 映射决定。
- 千万不要输出多个独立物体（会被判"太近"、可能被丢、会被分别摆放）。
- 流程：`inspect` 输入 → 确认机型（`printers`）→ 拆 part → Blender/Python 建几何（毫米）→
  导出 STL → `creality3mf.py build` → `inspect` 验证 → 交付并说明"打开工程、对应槽位、擦料塔"。
- 0.4 喷嘴规则：笔画 ≥ 0.9 mm，凸字 0.8–1.0 mm，字高 ≥ 10 mm 粗体，孤立小点 ≥ 2 mm。
- CLI 坑：版本门（`--allow-newer-file`）、`--load-filament-ids` 按文件不按 part、GUI 开着时 CLI 崩。
