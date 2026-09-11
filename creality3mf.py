#!/usr/bin/env python3
"""creality3mf — build and inspect Creality Print–compatible multi-part, multi-colour 3MF files.

Zero dependencies (Python ≥ 3.9). One file so agents and humans can vendor it anywhere.
The same 3MF dialect is read by Bambu Studio and OrcaSlicer (Creality Print is a fork).

    python3 creality3mf.py build  -o out.3mf --printer "Creality K2 Pro" \
        --part plate.stl:1 --part logo.stl:2 --filament "#000000" --filament "#FFFFFF"
    python3 creality3mf.py inspect out.3mf
    python3 creality3mf.py printers

Format notes (verified against CrealityPrint's bbs_3mf.cpp, a Bambu Studio fork):
  * ONE object, N <part>s. Each part carries <metadata key="extruder" value="N"/> in
    Metadata/model_settings.config; the loader copies unknown part metadata into the
    volume config, and keeps per-part extruders only when the object has >1 volume.
  * Creality Print centres every object around its origin on import (Model::center_around_origin)
    and keeps placement in the <build><item> transform; this tool writes files already in that form.
  * p:UUID values follow Creality's own scheme: object "%08X-61cb-…", sub-mesh
    "%08X-81cb-…", component "%08X-b206-…", build item "%08X-b1ec-…".
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import struct
import sys
import zipfile
from dataclasses import dataclass, field
from typing import Iterable, Sequence

__version__ = "0.1.0"

HERE = os.path.dirname(os.path.abspath(__file__))
PRINTERS_JSON = os.path.join(HERE, "data", "printers.json")

NS_CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
NS_PROD = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
NS_BBS = "http://schemas.bambulab.com/package/2021"

OBJECT_UUID_SUFFIX = "-61cb-4c03-9d28-80fed5dfa1dc"
SUB_OBJECT_UUID_SUFFIX = "-81cb-4c03-9d28-80fed5dfa1dc"
COMPONENT_UUID_SUFFIX = "-b206-40ff-9872-83e8017abed1"
BUILD_ITEM_UUID_SUFFIX = "-b1ec-4553-aec9-835e5b724bb4"
BUILD_UUID = "2c7c17d8-22b5-4d84-8835-1976022ea369"

DEFAULT_APP_VERSION = "7.2.1.5476"
TOP_OBJECT_ID = 2          # Creality Print numbers the first object 2 (id 1 is reserved)
EPS = 1e-6

Vec3 = tuple[float, float, float]
Tri = tuple[int, int, int]


# ----------------------------------------------------------------------------- meshes
@dataclass
class Part:
    """One colour region of the print. `extruder` is the 1-based filament slot."""
    name: str
    vertices: list[Vec3]
    triangles: list[Tri]
    extruder: int = 1

    def bbox(self) -> tuple[Vec3, Vec3]:
        xs, ys, zs = zip(*self.vertices)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def _is_ascii_stl(head: bytes) -> bool:
    return head.lstrip().lower().startswith(b"solid") and b"facet" in head


def read_stl(path: str) -> tuple[list[Vec3], list[Tri]]:
    """Read binary or ASCII STL; vertices are de-duplicated (exact match after rounding)."""
    with open(path, "rb") as f:
        data = f.read()
    binary_count = struct.unpack_from("<I", data, 80)[0] if len(data) >= 84 else -1
    looks_binary = binary_count >= 0 and 84 + binary_count * 50 == len(data)
    if _is_ascii_stl(data[:1024]) and not looks_binary:   # binary files may also start with "solid"
        raw = [tuple(map(float, m.groups()))
               for m in re.finditer(rb"vertex\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)", data)]
    else:
        if len(data) < 84:
            raise ValueError(f"{path}: not an STL file")
        count = binary_count
        if 84 + count * 50 > len(data):
            raise ValueError(f"{path}: truncated binary STL")
        raw = []
        for i in range(count):
            rec = struct.unpack_from("<12f", data, 84 + i * 50)
            raw.extend((rec[3:6], rec[6:9], rec[9:12]))
    return _index_triangles(raw)  # type: ignore[arg-type]


def read_obj(path: str) -> tuple[list[Vec3], list[Tri]]:
    """Read a Wavefront OBJ (v / f lines only); polygons are fan-triangulated."""
    verts: list[Vec3] = []
    tris: list[Tri] = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                x, y, z = (float(t) for t in line.split()[1:4])
                verts.append((x, y, z))
            elif line.startswith("f "):
                idx = [int(tok.split("/")[0]) for tok in line.split()[1:]]
                if 0 in idx:
                    raise ValueError(f"{path}: OBJ indices are 1-based; found 0")
                idx = [i - 1 if i > 0 else len(verts) + i for i in idx]   # negative = relative
                if any(i < 0 or i >= len(verts) for i in idx):
                    raise ValueError(f"{path}: OBJ face references a missing vertex")
                for k in range(1, len(idx) - 1):
                    tri = (idx[0], idx[k], idx[k + 1])
                    if len(set(tri)) == 3:
                        tris.append(tri)
    return verts, tris


def read_mesh(path: str) -> tuple[list[Vec3], list[Tri]]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".stl":
        return read_stl(path)
    if ext == ".obj":
        return read_obj(path)
    raise ValueError(f"{path}: unsupported mesh format {ext!r} (use .stl or .obj)")


def _index_triangles(raw: Sequence[Vec3]) -> tuple[list[Vec3], list[Tri]]:
    index: dict[Vec3, int] = {}
    verts: list[Vec3] = []
    tris: list[Tri] = []
    for i in range(0, len(raw), 3):
        ids = []
        for v in raw[i:i + 3]:
            key = (round(v[0], 6), round(v[1], 6), round(v[2], 6))
            if key not in index:
                index[key] = len(verts)
                verts.append(key)
            ids.append(index[key])
        if len({*ids}) == 3:
            tris.append((ids[0], ids[1], ids[2]))
    return verts, tris


def load_part(spec: str, default_extruder: int = 1) -> Part:
    """Parse `path[:extruder[:name]]` into a Part (Windows drive letters are safe)."""
    m = re.fullmatch(r"(.*\.(?:stl|obj))(?::(\d*))?(?::(.*))?", spec, re.I)
    if not m:
        raise ValueError(f"bad --part {spec!r}; expected MESH.stl[:EXTRUDER[:NAME]]")
    path, extruder_s, name = m.group(1), m.group(2), m.group(3) or ""
    extruder = int(extruder_s) if extruder_s else default_extruder
    verts, tris = read_mesh(path)
    if not tris:
        raise ValueError(f"{path}: no triangles")
    stem = re.split(r"[\\/]", path)[-1].rsplit(".", 1)[0]     # basename on any OS
    return Part(name or stem, verts, tris, extruder)


# ----------------------------------------------------------------------------- printers
def load_printers() -> dict:
    if not os.path.exists(PRINTERS_JSON):
        raise FileNotFoundError(f"{PRINTERS_JSON} missing — keep data/printers.json next to creality3mf.py, "
                                "or pass --bed W D --height H instead of --printer")
    with open(PRINTERS_JSON, encoding="utf-8") as f:
        return json.load(f)["printers"]


@dataclass
class Bed:
    width: float
    depth: float
    height: float
    printer_model: str = ""
    printer_settings_id: str = ""

    @classmethod
    def from_printer(cls, model: str, nozzle: str = "0.4") -> "Bed":
        printers = load_printers()
        if model not in printers:
            near = [k for k in printers if model.lower() in k.lower()]
            hint = f" Did you mean: {near[:5]}" if near else ""
            raise KeyError(f"unknown printer {model!r}.{hint} Run `printers` to list.")
        p = printers[model]
        preset = p["presets"].get(nozzle) or next(iter(p["presets"].values()))
        return cls(p["bed_mm"][0], p["bed_mm"][1], p["height_mm"], model, preset["printer_settings_id"])


# ----------------------------------------------------------------------------- build
@dataclass
class BuildResult:
    path: str
    parts: list[Part]
    bbox_min: Vec3
    bbox_max: Vec3
    centre: Vec3
    warnings: list[str] = field(default_factory=list)


def _fmt(x: float) -> str:
    s = f"{x:.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _group_bbox(parts: Iterable[Part]) -> tuple[Vec3, Vec3]:
    boxes = [p.bbox() for p in parts]
    lo = tuple(min(b[0][i] for b in boxes) for i in range(3))
    hi = tuple(max(b[1][i] for b in boxes) for i in range(3))
    return lo, hi  # type: ignore[return-value]


def _translate(parts: list[Part], d: Vec3) -> list[Part]:
    return [Part(p.name, [(v[0] + d[0], v[1] + d[1], v[2] + d[2]) for v in p.vertices], p.triangles, p.extruder)
            for p in parts]


def _check_fits(lo: Vec3, hi: Vec3, bed: Bed) -> list[str]:
    problems = []
    if lo[0] < -EPS or lo[1] < -EPS or hi[0] > bed.width + EPS or hi[1] > bed.depth + EPS:
        problems.append(f"model footprint X[{lo[0]:.1f},{hi[0]:.1f}] Y[{lo[1]:.1f},{hi[1]:.1f}] mm "
                        f"exceeds bed {bed.width:g}x{bed.depth:g} mm")
    if hi[2] > bed.height + EPS:
        problems.append(f"model height {hi[2]:.1f} mm exceeds printable height {bed.height:g} mm")
    if lo[2] < -1e-3:
        problems.append(f"model extends below the bed (min z {lo[2]:.3f} mm); drop it to z=0")
    return problems


def _submodel_xml(parts: list[Part], centre: Vec3) -> str:
    out = [f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" xmlns="{NS_CORE}" '
           f'xmlns:BambuStudio="{NS_BBS}" xmlns:p="{NS_PROD}" requiredextensions="p">\n'
           ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources>\n']
    for k, part in enumerate(parts):
        pid = 2 * k + 1
        out.append(f'  <object id="{pid}" p:UUID="{(1 << 16) + k + 1:08X}{SUB_OBJECT_UUID_SUFFIX}" type="model">\n'
                   '   <mesh>\n    <vertices>\n')
        out.extend(f'     <vertex x="{_fmt(x - centre[0])}" y="{_fmt(y - centre[1])}" z="{_fmt(z - centre[2])}"/>\n'
                   for x, y, z in part.vertices)
        out.append('    </vertices>\n    <triangles>\n')
        out.extend(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n' for a, b, c in part.triangles)
        out.append('    </triangles>\n   </mesh>\n  </object>\n')
    out.append(' </resources>\n <build/>\n</model>\n')
    return "".join(out)


def _top_model_xml(parts: list[Part], centre: Vec3, title: str, app_version: str) -> str:
    comps = "".join(
        f'    <component p:path="/3D/Objects/object_{TOP_OBJECT_ID}.model" objectid="{2 * k + 1}" '
        f'p:UUID="{(1 << 16) + k + 1:08X}{COMPONENT_UUID_SUFFIX}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n'
        for k in range(len(parts)))
    t = " ".join(_fmt(c) for c in centre)
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" xmlns="{NS_CORE}" '
            f'xmlns:BambuStudio="{NS_BBS}" xmlns:p="{NS_PROD}" requiredextensions="p">\n'
            f' <metadata name="Application">Creality_Print V{app_version} Release</metadata>\n'
            ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
            f' <metadata name="Title">{_xml(title)}</metadata>\n'
            ' <resources>\n'
            f'  <object id="{TOP_OBJECT_ID}" p:UUID="{1:08X}{OBJECT_UUID_SUFFIX}" type="model">\n'
            f'   <components>\n{comps}   </components>\n  </object>\n </resources>\n'
            f' <build p:UUID="{BUILD_UUID}">\n'
            f'  <item objectid="{TOP_OBJECT_ID}" p:UUID="{TOP_OBJECT_ID:08X}{BUILD_ITEM_UUID_SUFFIX}" '
            f'transform="1 0 0 0 1 0 0 0 1 {t}" printable="1"/>\n </build>\n</model>\n')


def _model_settings_xml(parts: list[Part], centre: Vec3, title: str) -> str:
    t = " ".join(_fmt(c) for c in centre)
    body = [f'<?xml version="1.0" encoding="UTF-8"?>\n<config>\n  <object id="{TOP_OBJECT_ID}">\n'
            f'    <metadata key="name" value="{_xml(title)}"/>\n    <metadata key="extruder" value="1"/>\n']
    for k, part in enumerate(parts):
        body.append(f'    <part id="{2 * k + 1}" subtype="normal_part">\n'
                    f'      <metadata key="name" value="{_xml(part.name)}"/>\n'
                    '      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
                    f'      <metadata key="extruder" value="{part.extruder}"/>\n    </part>\n')
    body.append('  </object>\n  <plate>\n    <metadata key="plater_id" value="1"/>\n'
                '    <metadata key="plater_name" value=""/>\n    <metadata key="locked" value="false"/>\n'
                f'    <model_instance>\n      <metadata key="object_id" value="{TOP_OBJECT_ID}"/>\n'
                '      <metadata key="instance_id" value="0"/>\n'
                f'      <metadata key="identify_id" value="{TOP_OBJECT_ID}"/>\n    </model_instance>\n  </plate>\n'
                f'  <assemble>\n   <assemble_item object_id="{TOP_OBJECT_ID}" instance_id="0" '
                f'transform="1 0 0 0 1 0 0 0 1 {t}" offset="0 0 0" />\n  </assemble>\n</config>\n')
    return "".join(body)


CONTENT_TYPES = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
                 ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
                 ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
                 ' <Default Extension="png" ContentType="image/png"/>\n'
                 ' <Default Extension="gcode" ContentType="text/x.gcode"/>\n</Types>\n')
ROOT_RELS = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
             ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" '
             'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n</Relationships>\n')
MODEL_RELS = ('<?xml version="1.0" encoding="UTF-8"?>\n'
              '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
              f' <Relationship Target="/3D/Objects/object_{TOP_OBJECT_ID}.model" Id="rel-1" '
              'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n</Relationships>\n')


def _creality_config(app_version: str, date: str) -> str:
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n'
            '    <metadata key="Company" value="Creality"/>\n    <metadata key="Application" value="Creality_Print"/>\n'
            f'    <metadata key="AppVersion" value="{app_version}"/>\n    <metadata key="AppStage" value="Release"/>\n'
            '    <metadata key="FileVersion" value="1.0"/>\n    <metadata key="FileType" value="Undefined"/>\n'
            f'    <metadata key="CreationDate" value="{date}"/>\n</config>\n')


def load_project_settings(source: str) -> dict:
    """Read a project_settings.config dict from a .3mf (Creality/Bambu/Orca) or a bare .json."""
    if source.lower().endswith(".3mf"):
        with zipfile.ZipFile(source) as z:
            if "Metadata/project_settings.config" not in z.namelist():
                raise ValueError(f"{source}: model-only 3MF, it carries no project settings")
            return json.loads(z.read("Metadata/project_settings.config"))
    with open(source, encoding="utf-8") as f:
        return json.load(f)


def apply_filaments(settings: dict, filaments: Sequence[dict]) -> dict:
    """Return a copy of `settings` whose per-filament arrays match `filaments` (colour/type/preset)."""
    out = dict(settings)
    n = len(filaments)
    template_preset = (settings.get("filament_settings_id") or ["Generic PLA"])[0]
    out["filament_colour"] = [f.get("colour", "#FFFFFF").upper() for f in filaments]
    out["filament_type"] = [f.get("type", "PLA") for f in filaments]
    out["filament_settings_id"] = [f.get("preset", template_preset) for f in filaments]
    # every other per-filament vector must have the same length or the slicer rejects the project
    replaced = {"filament_colour", "filament_type", "filament_settings_id"}
    for key, val in settings.items():
        if key in replaced or not (isinstance(val, list) and val and key.startswith("filament")):
            continue
        if len(val) != n:
            out[key] = (val + [val[-1]] * n)[:n]
    return out


def _slot_count(settings: dict | None) -> int:
    if not settings:
        return 0
    for key in ("filament_colour", "filament_settings_id", "filament_type"):
        val = settings.get(key)
        if isinstance(val, list) and val:
            return len(val)
    return 0


def build_3mf(parts: list[Part], out_path: str, bed: Bed, *, title: str = "model",
              filaments: Sequence[dict] = (), project_settings: dict | None = None,
              center: bool = True, drop_to_bed: bool = True,
              app_version: str = DEFAULT_APP_VERSION, date: str = "") -> BuildResult:
    """Write a single-object, multi-part 3MF. Raises ValueError if the model does not fit the bed."""
    if not parts:
        raise ValueError("no parts")
    if any(p.extruder < 1 for p in parts):
        raise ValueError("extruder ids are 1-based")
    lo, hi = _group_bbox(parts)
    shift = [0.0, 0.0, 0.0]
    if center:
        shift[0] = bed.width / 2 - (lo[0] + hi[0]) / 2
        shift[1] = bed.depth / 2 - (lo[1] + hi[1]) / 2
    if drop_to_bed:
        shift[2] = -lo[2]
    placed = _translate(parts, (shift[0], shift[1], shift[2])) if any(shift) else parts
    lo, hi = _group_bbox(placed)
    problems = _check_fits(lo, hi, bed)
    if problems:
        raise ValueError("; ".join(problems))
    centre: Vec3 = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)
    warnings: list[str] = []
    max_ext = max(p.extruder for p in placed)
    slot_count = len(filaments) or _slot_count(project_settings)
    if slot_count and max_ext > slot_count:
        # the loader resets such extruders to 0 (object default) — the colour would silently vanish
        raise ValueError(f"parts reference extruder {max_ext} but the project defines only {slot_count} filaments")
    date = date or datetime.date.today().isoformat()

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", ROOT_RELS)
        z.writestr("3D/_rels/3dmodel.model.rels", MODEL_RELS)
        z.writestr("3D/3dmodel.model", _top_model_xml(placed, centre, title, app_version))
        z.writestr(f"3D/Objects/object_{TOP_OBJECT_ID}.model", _submodel_xml(placed, centre))
        z.writestr("Metadata/model_settings.config", _model_settings_xml(placed, centre, title))
        z.writestr("Metadata/creality.config", _creality_config(app_version, date))
        if project_settings is not None:
            ps = apply_filaments(project_settings, filaments) if filaments else dict(project_settings)
            ps.setdefault("version", app_version)
            z.writestr("Metadata/project_settings.config", json.dumps(ps, indent=4, ensure_ascii=False))
        elif filaments:
            warnings.append("filament colours live in project settings; pass --project-from to embed them "
                            "(without it this is a model-only 3MF and colours come from the slicer's current slots)")
    return BuildResult(out_path, placed, lo, hi, centre, warnings)


# ----------------------------------------------------------------------------- inspect
def inspect_3mf(path: str) -> dict:
    """Summarise a Creality/Bambu-flavour 3MF: printer, filaments, objects/parts/extruders, placement."""
    import xml.etree.ElementTree as ET
    info: dict = {"file": path, "objects": [], "sliced": False}
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        info["sliced"] = any(n.endswith(".gcode") for n in names)
        if "Metadata/project_settings.config" in names:
            ps = json.loads(z.read("Metadata/project_settings.config"))
            info["printer"] = ps.get("printer_settings_id") or ps.get("printer_model")
            info["print_profile"] = ps.get("print_settings_id")
            info["filaments"] = [{"slot": i + 1, "colour": c, "type": t} for i, (c, t) in enumerate(
                zip(ps.get("filament_colour", []), ps.get("filament_type", [])))]
            info["print_sequence"] = ps.get("print_sequence")
            info["printable_area"] = ps.get("printable_area")
        root = ET.fromstring(z.read("3D/3dmodel.model"))
        info["application"] = next((m.text for m in root.iter(f"{{{NS_CORE}}}metadata")
                                    if m.get("name") == "Application"), None)
        parts_meta: dict[str, dict] = {}
        if "Metadata/model_settings.config" in names:
            cfg = ET.fromstring(z.read("Metadata/model_settings.config"))
            for obj in cfg.iter("object"):
                meta = {m.get("key"): m.get("value") for m in obj.findall("metadata")}
                parts = []
                for part in obj.findall("part"):
                    pm = {m.get("key"): m.get("value") for m in part.findall("metadata")}
                    parts.append({"id": part.get("id"), "name": pm.get("name"), "extruder": pm.get("extruder")})
                parts_meta[obj.get("id")] = {"name": meta.get("name"), "extruder": meta.get("extruder"), "parts": parts}
        objects = {o.get("id"): o for o in root.iter(f"{{{NS_CORE}}}object")}
        build = root.find(f"{{{NS_CORE}}}build")
        for item in (build if build is not None else []):
            oid = item.get("objectid")
            t = [float(x) for x in item.get("transform", "1 0 0 0 1 0 0 0 1 0 0 0").split()]
            entry = {"object_id": oid, **parts_meta.get(oid, {"name": None, "extruder": None, "parts": []}),
                     "translation": t[9:12]}
            entry["bbox_min"], entry["bbox_max"] = _object_world_bbox(z, objects, oid, t)
            info["objects"].append(entry)
        if "Metadata/slice_info.config" in names:
            si = z.read("Metadata/slice_info.config").decode("utf-8", "replace")
            for key in ("prediction", "weight"):
                m = re.search(rf'key="{key}" value="([^"]+)"', si)
                if m:
                    info[key] = float(m.group(1))
    return info


def _object_world_bbox(z, objects, oid, t):
    import xml.etree.ElementTree as ET
    obj = objects.get(oid)
    if obj is None:
        return None, None
    pts = []
    comps = obj.find(f"{{{NS_CORE}}}components")
    if comps is not None:
        for c in comps:
            path = c.get(f"{{{NS_PROD}}}path", "").lstrip("/")
            ct = [float(x) for x in c.get("transform", "1 0 0 0 1 0 0 0 1 0 0 0").split()]
            sub = ET.fromstring(z.read(path)) if path else obj
            for so in sub.iter(f"{{{NS_CORE}}}object"):
                if so.get("id") == c.get("objectid"):
                    pts.extend(_apply(ct, _verts(so)))
    else:
        pts = _verts(obj)
    pts = _apply(t, pts)
    if not pts:
        return None, None
    return ([round(min(p[i] for p in pts), 3) for i in range(3)],
            [round(max(p[i] for p in pts), 3) for i in range(3)])


def _verts(obj):
    return [(float(v.get("x")), float(v.get("y")), float(v.get("z"))) for v in obj.iter(f"{{{NS_CORE}}}vertex")]


def _apply(t, pts):
    # 3MF transform = 3x3 row-major matrix followed by translation (12 numbers)
    return [(t[0] * x + t[3] * y + t[6] * z + t[9], t[1] * x + t[4] * y + t[7] * z + t[10],
             t[2] * x + t[5] * y + t[8] * z + t[11]) for x, y, z in pts]


# ----------------------------------------------------------------------------- CLI
def _cmd_build(a: argparse.Namespace) -> int:
    bed = Bed.from_printer(a.printer, a.nozzle) if a.printer else Bed(a.bed[0], a.bed[1], a.height)
    parts = [load_part(s) for s in a.part]
    types = (a.filament_type + ["PLA"] * len(a.filament))[:len(a.filament)]
    filaments = [{"colour": c, "type": t} for c, t in zip(a.filament, types)]
    settings = load_project_settings(a.project_from) if a.project_from else None
    res = build_3mf(parts, a.output, bed, title=a.title or os.path.splitext(os.path.basename(a.output))[0],
                    filaments=filaments, project_settings=settings, center=not a.keep_position,
                    drop_to_bed=not a.keep_position, app_version=a.app_version)
    print(f"wrote {res.path}")
    for p in res.parts:
        lo, hi = p.bbox()
        print(f"  part {p.name:<24} extruder {p.extruder}  {len(p.triangles):>8} tris  "
              f"X[{lo[0]:.1f},{hi[0]:.1f}] Y[{lo[1]:.1f},{hi[1]:.1f}] Z[{lo[2]:.2f},{hi[2]:.2f}]")
    print(f"  footprint {res.bbox_max[0]-res.bbox_min[0]:.1f} x {res.bbox_max[1]-res.bbox_min[1]:.1f} x "
          f"{res.bbox_max[2]-res.bbox_min[2]:.1f} mm on {bed.printer_model or 'custom bed'} "
          f"({bed.width:g}x{bed.depth:g}x{bed.height:g})")
    for w in res.warnings:
        print(f"  warning: {w}")
    return 0


def _cmd_inspect(a: argparse.Namespace) -> int:
    info = inspect_3mf(a.file)
    if a.json:
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return 0
    print(f"{info['file']}\n  application: {info.get('application')}   sliced: {info['sliced']}")
    if "printer" in info:
        print(f"  printer: {info['printer']}   profile: {info.get('print_profile')}   "
              f"sequence: {info.get('print_sequence')}")
    for f in info.get("filaments", []):
        print(f"  filament {f['slot']}: {f['colour']} {f['type']}")
    for o in info["objects"]:
        print(f"  object {o['object_id']} {o.get('name')!r} extruder={o.get('extruder')} "
              f"bbox {o['bbox_min']} -> {o['bbox_max']}")
        for p in o.get("parts", []):
            print(f"      part {p['id']} {p['name']!r} extruder={p['extruder']}")
    if "prediction" in info:
        print(f"  sliced estimate: {info['prediction']/3600:.2f} h, {info.get('weight')} g")
    return 0


def _cmd_printers(a: argparse.Namespace) -> int:
    for name, p in sorted(load_printers().items()):
        if a.filter and a.filter.lower() not in name.lower():
            continue
        print(f"{name:<32} {p['bed_mm'][0]:>5g} x {p['bed_mm'][1]:<5g} x {p['height_mm']:<5g} mm  "
              f"nozzles {','.join(p['nozzles'])}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="creality3mf", description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="assemble parts into one multi-colour 3MF object")
    b.add_argument("-o", "--output", required=True)
    b.add_argument("--part", action="append", required=True, metavar="MESH[:EXTRUDER[:NAME]]",
                   help="STL/OBJ in millimetres; extruder is the 1-based filament slot")
    b.add_argument("--printer", help='e.g. "Creality K2 Pro" (see `printers`)')
    b.add_argument("--nozzle", default="0.4")
    b.add_argument("--bed", nargs=2, type=float, metavar=("W", "D"), help="custom bed size in mm")
    b.add_argument("--height", type=float, default=250.0, help="custom printable height in mm")
    b.add_argument("--filament", action="append", default=[], metavar="#RRGGBB", help="slot colours, in order")
    b.add_argument("--filament-type", action="append", default=[], help="per slot, default PLA")
    b.add_argument("--project-from", metavar="FILE", help="3MF or JSON whose project settings to embed")
    b.add_argument("--title")
    b.add_argument("--keep-position", action="store_true", help="do not centre on bed / drop to z=0")
    b.add_argument("--app-version", default=DEFAULT_APP_VERSION)
    b.set_defaults(fn=_cmd_build)

    i = sub.add_parser("inspect", help="summarise any Creality/Bambu-flavour 3MF")
    i.add_argument("file")
    i.add_argument("--json", action="store_true")
    i.set_defaults(fn=_cmd_inspect)

    p = sub.add_parser("printers", help="list known Creality printers and bed sizes")
    p.add_argument("filter", nargs="?")
    p.set_defaults(fn=_cmd_printers)

    a = ap.parse_args(argv)
    if a.cmd == "build" and not a.printer and not a.bed:
        ap.error("build needs --printer or --bed W D")
    try:
        return a.fn(a)
    except zipfile.BadZipFile as e:
        print(f"error: not a 3MF (zip) file: {e}", file=sys.stderr)
        return 1
    except (ValueError, KeyError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
