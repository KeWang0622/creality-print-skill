# Geometry sources → `creality3mf.py build`

Anything that writes STL/OBJ in millimetres works. One STL per colour region, then
`build --part a.stl:1 --part b.stl:2`. Ranked by install weight.

| Source | Install | Text/emboss | Booleans | Notes |
|---|---|---|---|---|
| pure Python (`examples/nameplate.py`) | none | pixel font | no | boxes, cylinders, pixel lettering; always available |
| Blender ≥ 4.2 (`examples/blender_text_plate.py`) | app | any TTF | exact | repair/split existing meshes, renders |
| [OpenSCAD](https://openscad.org) | app / `brew install openscad` | `text()` + `linear_extrude` | yes | one `-D part=…` run per colour |
| [CadQuery](https://github.com/CadQuery/cadquery) 2.8 | `pip install cadquery` (OCP wheels, heavy) | `Workplane.text(..., combine=False, fontPath=)` | yes | parametric, STEP-native |
| [build123d](https://github.com/gumyr/build123d) 0.11 | `pip install build123d` (heavy) | `Text()` + `extrude` | yes | `Mesher` writes generic 3MF (no slots) |
| [trimesh](https://github.com/mikedh/trimesh) 5 | `pip install trimesh` (numpy only) | no | with `manifold3d` | load/repair/union, `is_watertight`, `fill_holes()` |
| [manifold3d](https://github.com/elalish/manifold) 3.5 | `pip install manifold3d` | no | guaranteed-manifold | union parts that must merge before slicing |
| [text-to-cad](https://github.com/earthtojake/text-to-cad) `$cad` | `npx skills add earthtojake/text-to-cad` | via CadQuery | yes | emits STL/3MF; this skill is the per-part-slot stage after it |

None of these write the per-part `extruder` dialect — that is the gap `creality3mf.py` fills
(trimesh's 3MF export is geometry-only; manifold's 3MF export exists only in its wasm binding;
build123d/OpenSCAD write generic material colours that slicers ignore).

## CadQuery

```python
import cadquery as cq
FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
plate = cq.Workplane().box(70, 26, 2.4, centered=(True, True, False))
text = (cq.Workplane().workplane(offset=2.4)
        .text("HELLO", 12, 1.0, combine=False, kind="bold", fontPath=FONT))   # 1.0 mm raised
cq.exporters.export(plate, "plate.stl")
cq.exporters.export(text, "text.stl")
# python3 creality3mf.py build -o hello.3mf --printer "Creality K2 Plus" --part plate.stl:1:Plate --part text.stl:2:Lettering
```

## OpenSCAD

```openscad
// plate.scad — run twice:  openscad -o plate.stl -D 'part="plate"' plate.scad ; openscad -o text.stl -D 'part="text"' plate.scad
part = "plate";
if (part == "plate") cube([70, 26, 2.4]);
if (part == "text") translate([35, 13, 2.4]) linear_extrude(1.0)
    text("HELLO", size = 12, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
```

## trimesh as a repair step

```python
import trimesh
m = trimesh.load("body.stl")
if not m.is_watertight:
    m.fill_holes(); m.fix_normals()
m.export("body_fixed.stl")
```
`creality3mf.py check` reports the same topology facts without numpy; use trimesh when you need the repair.

## build123d

```python
from build123d import *
with BuildPart() as plate: Box(70, 26, 2.4)
with BuildPart() as text:
    with BuildSketch(Plane.XY.offset(2.4)): Text("HELLO", 12, font_style=FontStyle.BOLD)
    extrude(amount=1.0)
export_stl(plate.part, "plate.stl"); export_stl(text.part, "text.stl")
```

Units: CadQuery/build123d/OpenSCAD/trimesh are unit-less and treated as millimetres by every
slicer; Blender needs the explicit ×1000 (see `reference/blender.md`). `check` flags parts whose
largest dimension is < 3 mm as a probable metre/inch mix-up.
