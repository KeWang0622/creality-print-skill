# Multi-colour FDM design rules (0.4 mm nozzle, 0.2 mm layers)

| Rule | Value | Source |
|---|---|---|
| Extrusion width | 0.45 mm; walls thinner than one perimeter are not printable | Prusa KB "Modeling with 3D printing in mind" |
| Minimum wall / stroke | two perimeters ≈ 0.9 mm | Prusa KB "Layers and perimeters"; Hubs DFM (0.8 mm) |
| Embossed height | ≥ 0.3 mm printable; **0.8–1.0 mm** for crisp colour lettering (4–5 layers) | HLH design guide; derived |
| Engraved depth | ≥ 0.5 mm | HLH design guide |
| Smallest island | ≥ 2 mm | Hubs DFM |
| Text | cap height ≥ 10 mm, bold sans / rounded; centre on a flat top face | derived from stroke minimum |
| Plate | ≥ 2.4 mm (12 layers) under raised text; 3 mm for ≥150 mm plates | practice |
| Purge | every colour change flushes filament; dark→light needs more; prime tower auto-enabled | Bambu wiki (prime tower, flushing), Prusa purging volumes |
| Slot order | slot 1 = largest / darkest part when possible | reduces purge volume |
| Overlap | parts should touch, not overlap (overlap = double walls); Bambu "Assemble" unions parts | Bambu wiki assemble tool |

CFS specifics: one CFS = 4 slots; K2 series chains up to 4 units (16 slots); K1-series CFS-C is
one unit, 4 slots, no chaining. Multi-colour files print single-colour if CFS is disabled.
TPU/PVA are not supported through CFS.
