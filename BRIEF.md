# creality-print-skill — one file in, one printable multi-colour 3MF out, verified against Creality's own loader

**Angle:** the first agent skill that *writes* Creality/Bambu-dialect 3MF the way Creality Print writes it (one object, N parts, per-part extruder, native UUID scheme, bed-centred) — with the format rules cited to `bbs_3mf.cpp` line numbers and a pitfalls table from a real K2 Pro job.
**Closest incumbent:** https://github.com/codeofaxel/Kiln (multi-part 3MF, Bambu-verified, Creality/CFS "hardware-unverified", arrange paywalled)
**Structural advantage over it:** zero-dependency single file + Blender headless path + Creality-specific validation (`creality.config`, version gate, printer table from vendor profiles); Kiln cannot vendor into a skill folder and does not document the Creality loader.
**Why now (URL+date):** CrealityPrint#574 (2026-06) still open; Blender 3MF extension 2.7.7 (2026-09-02) made round-tripping possible; Creality Print 7.2.2 (2026-09-06).
**Target user:** someone with a K2/K1 + CFS who asks an agent "put my name on this and print it in two colours".
**Shareable artifact:** the `inspect` block showing 1 object / N parts / extruders / bbox, plus the photo of the print.
**Tech stack:** Python stdlib; optional Blender 4.2+; optional Creality Print CLI.
**Risks:** (1) a future Creality Print changes `model_settings` semantics; (2) users expect headless slicing, which Creality's CLI cannot do reliably.
**Out of scope:** slicing/G-code, resin printers, painted-texture colour, printer control.

> Reference repos used in research are craft samples, not a viral pattern.
