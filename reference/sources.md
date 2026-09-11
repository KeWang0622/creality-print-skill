# Sources

Everything in this repo traces to one of these. Version-specific claims name the version.

## Creality Print
- Download / release notes — https://www.creality.com/pages/creality-print-software (V7.2.2.5483, 2026-09-06)
- Source (AGPL-3.0, fork of Orca → Bambu Studio → PrusaSlicer) — https://github.com/CrealityOfficial/CrealityPrint
- CLI option definitions — https://github.com/CrealityOfficial/CrealityPrint/blob/master/src/libslic3r/PrintConfig.cpp
- CLI main incl. version gate (~L1505) — https://github.com/CrealityOfficial/CrealityPrint/blob/master/src/CrealityPrint.cpp
- 3MF reader/writer — https://github.com/CrealityOfficial/CrealityPrint/blob/master/src/libslic3r/Format/bbs_3mf.cpp
- "too close to others" (by-object clearance) — https://github.com/CrealityOfficial/CrealityPrint/blob/master/src/libslic3r/Print.cpp
- CLI multi-colour crash report — https://github.com/CrealityOfficial/CrealityPrint/issues/574
- Open Project vs Import Model — https://wiki.creality.com/en/software/update-released/Basic-introduction/Quick-Start
- K2 Plus multi-colour / CFS guide — https://wiki.creality.com/en/k2-flagship-series/k2-plus/multi-color-printing-guide
- Colour painting tool — https://wiki.creality.com/en/software/update-released/toolbar-introduction/color
- Bambu Studio CLI wiki (same flags) — https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage

## 3MF
- Core specification — https://github.com/3MFConsortium/spec_core/blob/master/3MF%20Core%20Specification.md
- Production extension (p:UUID, p:path) — https://github.com/3MFConsortium/spec_production/blob/master/3MF%20Production%20Extension.md
- Bambu 3MF compatibility note — https://wiki.bambulab.com/en/software/bambu-studio/3mf-compatibility
- Bambu Studio bbs_3mf.cpp — https://github.com/bambulab/BambuStudio/blob/master/src/libslic3r/Format/bbs_3mf.cpp
- Community write-ups — https://printago.io/blog/3mf-file-format · https://dev.to/bubudong/why-prusaslicer-cant-open-your-bambu-3mf-and-how-i-flattened-the-3mf-production-extension-in-the-3p36 · https://github.com/m-esm/bambu-3mf-export

## Blender
- 3MF Import/Export extension (ThreeMF_io 2.7.7, Blender ≥ 4.2) — https://extensions.blender.org/add-ons/threemf-io/ · source https://github.com/Clonephaze/3MF-Blender-Add-on---Maintained (fork of https://github.com/Ghostkeeper/Blender3mfFormat)
- Extension command line — https://docs.blender.org/manual/en/latest/advanced/command_line/extension_arguments.html
- Extension module naming — https://docs.blender.org/manual/en/latest/advanced/extensions/addons.html
- `bpy.ops.wm.stl_export` — https://docs.blender.org/api/current/bpy.ops.wm.html (new in 4.1: https://developer.blender.org/docs/release_notes/4.1/pipeline_assets_io/)

## Printers (official)
- K2 Plus — https://www.creality.com/support/creality-k2-plus-cfs-combo
- K2 / K2 Pro — https://www.creality.com/products/k2-series
- K1 / K1C / K1 Max / K1 SE — https://www.creality.com/support/creality-k1-3d-printer and sibling support pages
- Hi — https://www.creality.com/products/creality-hi-combo
- CFS-C — https://www.creality.com/products/cfs-c-smart-filament-system
- CFS announcement — https://www.creality.com/blog/creality-announces-pre-sale-of-the-k2-plus-x-cfs-combo-its-first-multi-color-3d-printing-solution
- Bed sizes in `data/printers.json` are generated from the vendor profiles shipped inside Creality Print (`scripts/gen_printer_table.py`).

## Design rules
- Prusa: Modeling with 3D printing in mind — https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135
- Prusa: Layers and perimeters — https://help.prusa3d.com/article/layers-and-perimeters_1748
- Prusa: Wipe tower / purging volumes — https://help.prusa3d.com/article/wipe-tower_125010 · https://help.prusa3d.com/article/purging-volumes-mmu_125097
- Hubs: thin walls / FDM — https://www.hubs.com/knowledge-base/dfm-tips-for-3d-printed-parts-with-thin-walls/ · https://www.hubs.com/knowledge-base/what-is-fdm-3d-printing/
- HLH: FDM design guide — https://hlhrapid.com/knowledge/design-guide-fdm-3d-printing/
- Bambu: prime tower, flushing, multi-colour, split to parts, assemble — https://wiki.bambulab.com/en/software/bambu-studio/parameter/prime-tower · https://wiki.bambulab.com/en/software/bambu-studio/reduce-wasting-during-filament-change · https://wiki.bambulab.com/en/software/bambu-studio/multi-color-printing · https://wiki.bambulab.com/en/software/bambu-studio/split-to-objects-parts · https://wiki.bambulab.com/en/bambu-studio/assemble-tool

## Prior art (what this repo does not redo)
- codeofaxel/Kiln — MCP server; multi-part 3MF verified on Bambu Studio, Creality/CFS marked hardware-unverified — https://github.com/codeofaxel/Kiln
- DMontgomery40/bambu-printer-mcp — template-cloning 3MF builder, Bambu only — https://github.com/DMontgomery40/bambu-printer-mcp
- woliveiras/k2-3d-printing-skill — K2 GUI procedures, read-only 3MF inspector — https://github.com/woliveiras/k2-3d-printing-skill
- Fei2-Labs/skill-genie `3mf-print-editor` — hand-editing Bambu 3MF — https://github.com/Fei2-Labs/skill-genie
- ahujasid/blender-mcp — live Blender control, no 3MF — https://github.com/ahujasid/blender-mcp
