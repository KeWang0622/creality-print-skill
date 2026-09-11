#!/usr/bin/env python3
"""Regenerate data/printers.json from the Creality Print profiles installed on this machine.

Source of truth: <Creality Print.app>/Contents/Resources/profiles/Creality/machine/*.json
(Windows: %APPDATA% / Program Files equivalents). Run:  python3 scripts/gen_printer_table.py
"""
import glob, json, os, re, sys

CANDIDATES = [
    "/Applications/Creality Print.app/Contents/Resources/profiles/Creality",
    os.path.expandvars(r"C:\Program Files\Creality\Creality Print\resources\profiles\Creality"),
]

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def resolve(machine_dir, name, seen=None):
    """Flatten a profile by following `inherits` (child keys win)."""
    seen = seen or set()
    path = os.path.join(machine_dir, name + ".json")
    if name in seen or not os.path.exists(path):
        return {}
    seen.add(name)
    d = load(path)
    base = resolve(machine_dir, d["inherits"], seen) if d.get("inherits") else {}
    return {**base, **d}

def main():
    root = next((c for c in CANDIDATES if os.path.isdir(c)), None)
    if not root:
        sys.exit("Creality Print profiles not found; install Creality Print or pass a path")
    machine_dir = os.path.join(root, "machine")
    vendor = load(root + ".json")
    version = vendor.get("version")
    rows = {}
    for path in sorted(glob.glob(os.path.join(machine_dir, "* nozzle.json"))):
        d = resolve(machine_dir, os.path.basename(path)[:-5])
        model = d.get("printer_model") or re.sub(r"\s+[\d.]+ nozzle$", "", d["name"])
        if not d.get("printable_area"):
            continue
        area = d["printable_area"]
        area = area.split(",") if isinstance(area, str) else area   # vendor JSON stores it as "0x0,300x0,..."
        try:
            pts = [tuple(map(float, p.split("x"))) for p in area if p]
        except ValueError:
            continue
        if len(pts) < 3:
            continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        row = rows.setdefault(model, {
            "printer_model": model,
            "bed_mm": [max(xs) - min(xs), max(ys) - min(ys)],
            "height_mm": float(d.get("printable_height", 0)),
            "nozzles": [],
            "presets": {},
            "cfs_variant": "CFS" in model,
            "extruder_clearance_radius": float(d.get("extruder_clearance_radius", 0)),
        })
        nz = d["nozzle_diameter"]
        nz = str(nz[0] if isinstance(nz, list) else nz).split(",")[0]
        row["nozzles"].append(nz)
        row["presets"][nz] = {
            "printer_settings_id": d["name"],
            "default_print_profile": d.get("default_print_profile"),
            "default_filament_profile": (d.get("default_filament_profile") or [None])[0],
        }
    out = {"source": "Creality Print vendor profiles", "profiles_version": version, "printers": rows}
    dst = os.path.join(os.path.dirname(__file__), "..", "data", "printers.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"wrote {len(rows)} printers -> {os.path.relpath(dst)} (profiles v{version})")

if __name__ == "__main__":
    main()
