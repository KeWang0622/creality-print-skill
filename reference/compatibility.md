# Compatibility matrix

"Verified" = a file produced by `creality3mf.py` was opened and inspected on that version.
"Expected" = same loader code path, not yet exercised. Please add rows via PR.

| Consumer | Version | One object / N parts with per-part `extruder` | Project settings | Status |
|---|---|---|---|---|
| Creality Print (macOS) | 7.2.1.5476 | ✅ `--info` lists all parts, manifold, sizes | ✅ | verified (CLI) |
| Creality Print GUI | 7.2.1 | ✅ colours shown per part | ✅ | verified with a 3-part K2 Pro file |
| Creality Print | 6.3.x | expected (same bbs_3mf.cpp) | ✅ (source template was 6.3) | expected |
| Bambu Studio | 1.10 – 2.x | expected | ✅ | expected |
| OrcaSlicer | 2.x | expected | ✅ | expected |
| PrusaSlicer | 2.8 | geometry only (no `Slic3r_PE_model.config`) | ✗ | expected |
| Cura | 5.x | geometry only | ✗ | expected |

Printers: any Creality FDM machine in `data/printers.json` (55 models from vendor profiles
v26.08.04.20). Multi-colour requires CFS (K2 series) or CFS-C (K1 / K1C / K1 Max / K1 SE /
Ender-3 V3-series CFS bundles); without CFS the slicer prints the file single-colour.

Python: 3.9 – 3.13, no third-party packages. Blender: 4.2 – 5.1 for the Blender scripts only.
