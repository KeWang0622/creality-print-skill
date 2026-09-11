# Anatomy of a Creality / Bambu-flavour 3MF

A 3MF is an OPC (ZIP) package. Creality Print, Bambu Studio and OrcaSlicer share one loader
(`src/libslic3r/Format/bbs_3mf.cpp`); Creality adds one file. Minimal, verified layout:

```
[Content_Types].xml                 OPC content types (rels/model/png/gcode)
_rels/.rels                         → /3D/3dmodel.model
3D/3dmodel.model                    object tree + <build><item transform> placement
3D/_rels/3dmodel.model.rels         → /3D/Objects/object_2.model
3D/Objects/object_2.model           meshes: one <object id=1|3|5…> per part
Metadata/model_settings.config      names, per-part extruder, plate instance, assemble
Metadata/project_settings.config    (optional) printer/process/filament presets as JSON
Metadata/creality.config            (Creality) Company/Application/AppVersion/CreationDate
Metadata/slice_info.config          (only after slicing) time, weight, filament usage
Metadata/plate_1.gcode              (only after slicing) — stale as soon as geometry changes
```

## 3D/3dmodel.model

```xml
<model unit="millimeter" xmlns="…/core/2015/02" xmlns:BambuStudio="…/package/2021"
       xmlns:p="…/production/2015/06" requiredextensions="p">
 <metadata name="Application">Creality_Print V7.2.1.5476 Release</metadata>
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <resources>
  <object id="2" p:UUID="00000001-61cb-4c03-9d28-80fed5dfa1dc" type="model">
   <components>
    <component p:path="/3D/Objects/object_2.model" objectid="1" p:UUID="00010001-b206-…" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>
    <component p:path="/3D/Objects/object_2.model" objectid="3" p:UUID="00010002-b206-…" transform="…"/>
   </components>
  </object>
 </resources>
 <build p:UUID="2c7c17d8-22b5-4d84-8835-1976022ea369">
  <item objectid="2" p:UUID="00000002-b1ec-…" transform="1 0 0 0 1 0 0 0 1 150 150 2" printable="1"/>
 </build>
</model>
```

- Production extension: `p:path` points at a sub-model file; `objectid` then refers to an
  object **inside that file**. Meshes never live in the root model.
- `transform` is 12 numbers: 3×3 row-major matrix then translation. The writer stores mesh
  vertices centred on the object origin and puts the placement in the build item — the reader
  calls `center_around_origin` anyway, so absolute vertices also load, but do it the native way.
- UUID scheme (constants in bbs_3mf.cpp L263–268): object `%08X-61cb-4c03-9d28-80fed5dfa1dc`,
  sub-model object `%08X-81cb-…`, component `%08X-b206-40ff-9872-83e8017abed1`, build item
  `%08X-b1ec-4553-aec9-835e5b724bb4`, build `2c7c17d8-22b5-4d84-8835-1976022ea369`. The hex
  prefix encodes an index (`index + (backup_id << 16)`), it is not random.
- Object ids start at 2 in files Creality Print writes; sub-model objects use odd ids 1,3,5….

## Metadata/model_settings.config

```xml
<config>
  <object id="2">
    <metadata key="name" value="nameplate"/>
    <metadata key="extruder" value="1"/>
    <part id="1" subtype="normal_part">
      <metadata key="name" value="Plate"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="extruder" value="1"/>
    </part>
    <part id="3" subtype="normal_part"> … <metadata key="extruder" value="2"/> </part>
  </object>
  <plate>
    <metadata key="plater_id" value="1"/> …
    <model_instance><metadata key="object_id" value="2"/><metadata key="instance_id" value="0"/>
                    <metadata key="identify_id" value="2"/></model_instance>
  </plate>
  <assemble><assemble_item object_id="2" instance_id="0" transform="… 150 150 2" offset="0 0 0"/></assemble>
</config>
```

- `part id` **must equal** the component's `objectid`.
- Any `<metadata key>` on a part that is not `name/matrix/source_*/mesh_stat` is deserialised
  straight into the volume config (`bbs_3mf.cpp` ~L5757) — that is how `extruder` works.
- On load (~L2787–2807): an object with exactly one volume has the volume extruder erased and
  the object extruder used; with >1 volumes each volume keeps its own extruder if it is within
  `1..max_filament_id`, else it is reset to 0 (= object default). So **part colours only exist on
  multi-part objects**, and a part extruder beyond the filament count silently becomes "default".
- Objects with no volumes or no instances are deleted at the end of import (~L2910, ~L4175).
- `subtype` values: `normal_part`, `negative_part`, `modifier_part`, `support_blocker`,
  `support_enforcer`.

## Metadata/project_settings.config

Flat JSON of every slicer option. The vectors indexed by filament slot **must have the same
length** (`filament_colour`, `filament_type`, `filament_settings_id`, `filament_diameter`, …);
`creality3mf.py apply_filaments()` pads them. Keys the GUI keys off: `printer_settings_id`,
`printer_model`, `print_settings_id`, `filament_settings_id`, `version`. Without this file the
3MF is "model only" and inherits whatever printer/filaments the user has selected.

## Metadata/creality.config

```xml
<config>
    <metadata key="Company" value="Creality"/>
    <metadata key="Application" value="Creality_Print"/>
    <metadata key="AppVersion" value="7.2.1.5476"/>
    <metadata key="AppStage" value="Release"/>
    <metadata key="FileVersion" value="1.0"/>
    <metadata key="FileType" value="Undefined"/>
    <metadata key="CreationDate" value="2026-09-11"/>
</config>
```
Read at import (`CREALITY_CONFIG_FILE`, bbs_3mf.cpp L177/L673). Bambu/Orca ignore it.
