# Contributing

1. `git clone https://github.com/KeWang0622/creality-print-skill && cd creality-print-skill`
2. `bash scripts/dev.sh install` — checks Python ≥ 3.9 (no third-party packages)
3. `bash scripts/dev.sh example` — builds `examples/out/nameplate.3mf` and inspects it
4. `bash scripts/dev.sh test` — runs the unittest suite
5. Open a PR. If you verified a file on a real printer or slicer version, say which one in the
   PR body — every compatibility claim in `reference/` is tied to a version.

Bug reports about a 3MF that Creality Print / Bambu Studio / OrcaSlicer refuses to open are
most useful with the output of `python3 creality3mf.py inspect <file> --json` attached.
