"""Tests for creality3mf (stdlib unittest). Run: python3 -m unittest discover -s tests"""
import json
import os
import re
import struct
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import creality3mf as c3  # noqa: E402


def box(x0, y0, z0, x1, y1, z1):
    """Closed axis-aligned box as (vertices, triangles), outward-facing."""
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    t = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return v, t


def write_binary_stl(path, verts, tris):
    with open(path, "wb") as f:
        f.write(b"\0" * 80 + struct.pack("<I", len(tris)))
        for a, b, c in tris:
            f.write(struct.pack("<3f", 0, 0, 0))
            for i in (a, b, c):
                f.write(struct.pack("<3f", *verts[i]))
            f.write(b"\0\0")


def write_ascii_stl(path, verts, tris):
    with open(path, "w") as f:
        f.write("solid t\n")
        for a, b, c in tris:
            f.write(" facet normal 0 0 0\n  outer loop\n")
            for i in (a, b, c):
                f.write("   vertex %g %g %g\n" % verts[i])
            f.write("  endloop\n endfacet\n")
        f.write("endsolid t\n")


class ReaderTests(unittest.TestCase):
    def test_binary_and_ascii_stl_agree(self):
        v, t = box(0, 0, 0, 10, 20, 3)
        with tempfile.TemporaryDirectory() as d:
            write_binary_stl(f"{d}/b.stl", v, t)
            write_ascii_stl(f"{d}/a.stl", v, t)
            vb, tb = c3.read_stl(f"{d}/b.stl")
            va, ta = c3.read_stl(f"{d}/a.stl")
        self.assertEqual(len(vb), 8)
        self.assertEqual(len(tb), 12)
        self.assertEqual(sorted(vb), sorted(va))
        self.assertEqual(len(ta), 12)

    def test_obj_reader_fan_triangulates_quads(self):
        with tempfile.TemporaryDirectory() as d:
            with open(f"{d}/q.obj", "w") as f:
                f.write("v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3 4\n")
            v, t = c3.read_obj(f"{d}/q.obj")
        self.assertEqual(len(v), 4)
        self.assertEqual(t, [(0, 1, 2), (0, 2, 3)])

    def test_binary_stl_whose_header_starts_with_solid(self):
        v, t = box(0, 0, 0, 1, 1, 1)
        with tempfile.TemporaryDirectory() as d:
            write_binary_stl(f"{d}/s.stl", v, t)
            with open(f"{d}/s.stl", "r+b") as f:
                f.write(b"solid facet binary export")
            self.assertEqual(len(c3.read_stl(f"{d}/s.stl")[1]), 12)

    def test_obj_negative_indices_and_invalid_faces(self):
        with tempfile.TemporaryDirectory() as d:
            with open(f"{d}/n.obj", "w") as f:
                f.write("v 0 0 0\nv 1 0 0\nv 0 1 0\nf -3 -2 -1\nf 1 1 2\n")
            self.assertEqual(c3.read_obj(f"{d}/n.obj")[1], [(0, 1, 2)])
            with open(f"{d}/bad.obj", "w") as f:
                f.write("v 0 0 0\nf 1 2 3\n")
            with self.assertRaises(ValueError):
                c3.read_obj(f"{d}/bad.obj")

    def test_part_spec_with_windows_drive_letter(self):
        from unittest import mock
        with mock.patch.object(c3, "read_mesh", return_value=box(0, 0, 0, 1, 1, 1)):
            part = c3.load_part(r"C:\models\plate.stl:2:Plate")
            bare = c3.load_part(r"C:\models\plate.stl")
        self.assertEqual((part.extruder, part.name), (2, "Plate"))
        self.assertEqual((bare.extruder, bare.name), (1, "plate"))

    def test_unsupported_extension(self):
        with self.assertRaises(ValueError):
            c3.read_mesh("thing.step")


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.bed = c3.Bed(300, 300, 300, "Test Printer", "Test Printer 0.4 nozzle")
        pv, pt = box(0, 0, 0, 100, 60, 3)
        lv, lt = box(10, 10, 3, 40, 30, 4)
        self.parts = [c3.Part("Plate", pv, pt, 1), c3.Part("Logo", lv, lt, 2)]
        self.tmp = tempfile.mkdtemp()

    def build(self, **kw):
        out = os.path.join(self.tmp, "t.3mf")
        return out, c3.build_3mf(self.parts, out, self.bed, title="t", **kw)

    def test_single_object_multi_part_structure(self):
        out, _ = self.build()
        with zipfile.ZipFile(out) as z:
            names = set(z.namelist())
            for required in ("[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model",
                             "3D/_rels/3dmodel.model.rels", "3D/Objects/object_2.model",
                             "Metadata/model_settings.config", "Metadata/creality.config"):
                self.assertIn(required, names)
            top = z.read("3D/3dmodel.model").decode()
            sub = z.read("3D/Objects/object_2.model").decode()
            ms = z.read("Metadata/model_settings.config").decode()
            for doc in (top, sub, ms):
                ET.fromstring(doc)  # well-formed XML
        comp_ids = re.findall(r'<component [^>]*objectid="(\d+)"', top)
        sub_ids = re.findall(r'<object id="(\d+)"', sub)
        part_ids = re.findall(r'<part id="(\d+)"', ms)
        self.assertEqual(comp_ids, sub_ids)
        self.assertEqual(comp_ids, part_ids)
        self.assertEqual(len(re.findall(r'<item ', top)), 1, "exactly one build item (one object)")
        self.assertEqual(re.findall(r'key="extruder" value="(\d)"', ms), ["1", "1", "2"])
        self.assertIn('p:UUID="00000001-61cb-4c03-9d28-80fed5dfa1dc"', top)
        self.assertIn('p:UUID="00010001-b206-40ff-9872-83e8017abed1"', top)
        self.assertIn('p:UUID="00010001-81cb-4c03-9d28-80fed5dfa1dc"', sub)
        self.assertNotIn("Metadata/project_settings.config", names)

    def test_centred_on_bed_and_dropped_to_z0(self):
        out, res = self.build()
        self.assertAlmostEqual((res.bbox_min[0] + res.bbox_max[0]) / 2, 150)
        self.assertAlmostEqual((res.bbox_min[1] + res.bbox_max[1]) / 2, 150)
        self.assertAlmostEqual(res.bbox_min[2], 0)
        obj = c3.inspect_3mf(out)["objects"][0]
        self.assertEqual(obj["bbox_min"], [100.0, 120.0, 0.0])
        self.assertEqual(obj["bbox_max"], [200.0, 180.0, 4.0])
        self.assertEqual([p["extruder"] for p in obj["parts"]], ["1", "2"])

    def test_keep_position(self):
        out, res = self.build(center=False, drop_to_bed=False)
        self.assertEqual(res.bbox_min, (0, 0, 0))
        self.assertEqual(c3.inspect_3mf(out)["objects"][0]["bbox_max"], [100.0, 60.0, 4.0])

    def test_rejects_models_that_do_not_fit(self):
        with self.assertRaises(ValueError):
            c3.build_3mf(self.parts, os.path.join(self.tmp, "x.3mf"), c3.Bed(50, 50, 50))

    def test_rejects_zero_based_extruder(self):
        bad = [c3.Part("x", *box(0, 0, 0, 1, 1, 1), 0)]
        with self.assertRaises(ValueError):
            c3.build_3mf(bad, os.path.join(self.tmp, "x.3mf"), self.bed)

    def test_project_settings_and_filament_arrays(self):
        template = {"printer_settings_id": "Test 0.4 nozzle", "filament_colour": ["#FFFFFF"],
                    "filament_type": ["PLA"], "filament_settings_id": ["Generic PLA @Test"],
                    "filament_diameter": ["1.75"], "nozzle_temperature": ["220"], "layer_height": "0.2"}
        out, res = self.build(filaments=[{"colour": "#000000"}, {"colour": "#ff0000", "type": "PETG"}],
                              project_settings=template)
        self.assertEqual(res.warnings, [])
        info = c3.inspect_3mf(out)
        self.assertEqual([f["colour"] for f in info["filaments"]], ["#000000", "#FF0000"])
        self.assertEqual([f["type"] for f in info["filaments"]], ["PLA", "PETG"])
        with zipfile.ZipFile(out) as z:
            ps = json.loads(z.read("Metadata/project_settings.config"))
        self.assertEqual(ps["filament_diameter"], ["1.75", "1.75"], "per-filament vectors are padded")
        self.assertEqual(ps["filament_settings_id"], ["Generic PLA @Test"] * 2)
        self.assertEqual(ps["layer_height"], "0.2")

    def test_warns_when_colours_given_without_project(self):
        _, res = self.build(filaments=[{"colour": "#000000"}, {"colour": "#FFFFFF"}])
        self.assertTrue(any("project" in w for w in res.warnings))

    def test_rejects_extruder_beyond_project_filaments(self):
        with self.assertRaises(ValueError):
            self.build(filaments=[{"colour": "#000000"}], project_settings={"filament_colour": ["#fff"]})
        with self.assertRaises(ValueError):
            self.build(project_settings={"filament_colour": ["#fff"], "filament_type": ["PLA"]})


class CheckTests(unittest.TestCase):
    def test_watertight_box_is_ok(self):
        r = c3.mesh_report(c3.Part("b", *box(0, 0, 0, 10, 10, 10)))
        self.assertTrue(r["watertight"] and r["winding_consistent"])
        self.assertEqual(r["size_mm"], [10, 10, 10])

    def test_missing_face_and_flipped_face_are_reported(self):
        v, t = box(0, 0, 0, 10, 10, 10)
        holed = c3.Part("h", v, t[:-1])
        self.assertFalse(c3.mesh_report(holed)["watertight"])
        flipped = c3.Part("f", v, t[:-1] + [tuple(reversed(t[-1]))])
        r = c3.mesh_report(flipped)
        self.assertTrue(r["watertight"])
        self.assertFalse(r["winding_consistent"])

    def test_findings_cover_units_overlap_slots_and_bed(self):
        tiny = c3.Part("tiny", *box(0, 0, 0, 0.1, 0.1, 0.1), 1)
        a = c3.Part("a", *box(0, 0, 0, 10, 10, 10), 1)
        b = c3.Part("b", *box(5, 5, 5, 15, 15, 15), 3)
        msgs = [str(f) for f in c3.check_parts([tiny, a, b], c3.Bed(12, 12, 12, "Bed"), slots=2)]
        self.assertTrue(any("metres or inches" in m for m in msgs))
        self.assertTrue(any("overlap" in m and "a+b" in m for m in msgs))
        self.assertTrue(any("❌ b: extruder 3" in m for m in msgs))
        self.assertTrue(any("❌ assembly" in m and "does not fit" in m for m in msgs))

    def test_check_cli_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            write_binary_stl(f"{d}/p.stl", *box(0, 0, 0, 20, 20, 2))
            self.assertEqual(c3.main(["check", f"{d}/p.stl:1", "--printer", "Creality K2 Pro", "--slots", "2"]), 0)
            self.assertEqual(c3.main(["check", f"{d}/p.stl:3", "--slots", "2"]), 1)


class CliTests(unittest.TestCase):
    def test_build_and_inspect_via_cli(self):
        with tempfile.TemporaryDirectory() as d:
            write_binary_stl(f"{d}/plate.stl", *box(0, 0, 0, 50, 50, 2))
            write_binary_stl(f"{d}/top.stl", *box(5, 5, 2, 45, 45, 3))
            rc = c3.main(["build", "-o", f"{d}/o.3mf", "--printer", "Creality K2 Pro",
                          "--part", f"{d}/plate.stl:1", "--part", f"{d}/top.stl:2:Top"])
            self.assertEqual(rc, 0)
            self.assertEqual(c3.main(["inspect", f"{d}/o.3mf"]), 0)
            info = c3.inspect_3mf(f"{d}/o.3mf")
        self.assertEqual(info["objects"][0]["parts"][1]["name"], "Top")

    def test_unknown_printer_and_bad_zip_are_clean_errors(self):
        import contextlib
        import io
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(c3.main(["build", "-o", os.devnull, "--printer", "Nope", "--part", "x.stl"]), 1)
            self.assertEqual(c3.main(["inspect", __file__]), 1)
        self.assertIn("unknown printer", err.getvalue())
        self.assertIn("not a 3MF", err.getvalue())

    def test_printer_table_has_cfs_flagships(self):
        printers = c3.load_printers()
        self.assertEqual(printers["Creality K2 Plus"]["bed_mm"], [350.0, 350.0])
        self.assertEqual(printers["Creality K2 Pro"]["height_mm"], 300.0)


if __name__ == "__main__":
    unittest.main()
