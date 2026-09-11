# Creality Print command line

Binary: `/Applications/Creality Print.app/Contents/MacOS/CrealityPrint` (macOS),
`C:\Program Files\Creality\Creality Print\CrealityPrint.exe` (Windows). Options are defined in
`src/libslic3r/PrintConfig.cpp` (underscores in source, hyphens on the command line).

| Option | Meaning (tooltip) |
|---|---|
| `--info` | Output the model's information (per object: size, manifold, parts, volume) |
| `--export-3mf out.3mf` | Export project as 3MF |
| `--export-stl` / `--export-stls DIR` | objects as one STL / one STL per object |
| `--slice 0` / `--slice N` | slice all plates / plate N |
| `--load-settings "machine.json;process.json"` | up to 1 machine + 1 process preset |
| `--load-filaments "a.json;b.json"` | filament presets, count ≤ filaments used |
| `--load-filament-ids "1,2"` | **per input file**, not per part |
| `--arrange 0|1` | disable / enable auto-arrange |
| `--allow-newer-file` | skip the 3MF version gate |
| `--outputdir DIR`, `--debug N`, `--logfile F` | output & logging (`--debug 2` = warning) |

Vendor presets live next to the binary: `…/Contents/Resources/profiles/Creality/{machine,process,filament}/*.json`
(`inherits` chains; `printable_area` is a string `"0x0,300x0,300x300,0x300"`).

## Version gate (`src/CrealityPrint.cpp` ~L1505)

```cpp
if (!allow_newer_file && ((cli_ver.maj() != file_version.maj()) || (cli_ver.min() < file_version.min())))
    // "Version Check: File Version %1% not supported by current cli version %2%"
```
`file_version` comes from the `Application` metadata / `creality.config`. `creality3mf.py`
writes `7.2.1.5476` by default; pass `--app-version` to match another install.

## Known limits

- Headless multi-colour slicing: crash reports (CrealityPrint#574) and reproduced locally
  (exit 139). Use the CLI for `--info` / `--export-3mf` validation and slice in the GUI.
- Observed: with the GUI open, every CLI invocation exits 139 on macOS. Close the GUI first.
- `--info` prints raw mesh sizes before the build transform; placement is not shown — use
  `creality3mf.py inspect` for world-space bounding boxes.
