# Material Maker CLI and MCP

## Goal

Let pi export a material as a PBR texture set and optionally pass that set through one reusable hotspot-conversion `.ptex`.

Example user requests:

> Make a dark scratched metal texture at 1024×1024.

> Convert this material to the hotspot atlas layout.

Expected output:

- Generated working `.ptex` project
- Albedo PNG
- OpenGL normal PNG
- ORM PNG (`R = AO`, `G = roughness`, `B = metallic`)
- When requested, hotspot-atlas versions of those three maps

The first version uses curated source-material `.ptex` templates, materials downloaded from materialmaker.org, and the supplied `hotspot/converter.ptex` hotspot converter. Pi interprets natural language; the CLI remains deterministic and structured.

## MVP scope

### Included

- macOS and the installed Material Maker 1.7 app
- One CLI executable with `list`, `search`, `download`, `generate`, and `convert-hotspot` subcommands
- Searching and downloading static PBR materials from materialmaker.org
- Curated metal templates based on the included examples
- Friendly parameters defined per template, such as scale, colors, roughness, wear, and seed
- Resolution selection
- Godot 4 ORM texture export
- Output validation
- A reusable hotspot-conversion `.ptex` that accepts albedo, OpenGL normal, ORM, and the fixed mask
- Hotspot-atlas albedo, normal, and ORM export

### Not included

- Arbitrary text-to-node-graph generation
- Creating or UV-mapping meshes
- DreamUV automation as a CLI or MCP command (the Blender step is scripted in `blender_hotspot.py` and validated through Blender MCP, but is not part of `mm-material`)
- glTF/GLB export
- Godot, Blender, Unity, or Unreal project integration
- A separate daemon or database

Add these only after the template workflow proves too limiting.

## Proposed CLI

```sh
./mm-material generate metal \
  --output ./out/dark-metal \
  --size 1024 \
  --param color=#34383d \
  --param roughness=0.65 \
  --param scratch_scale=24
```

```sh
./mm-material convert-hotspot \
  --albedo ./metal/albedo.png \
  --normal ./metal/normal.png \
  --orm ./metal/orm.png \
  --output ./out/hotspot-metal
```

`generate ... --hotspot` may later combine these two operations as a convenience, without adding separate conversion logic.

Unsupported template names or parameters fail with a useful message. A `list` command can show available templates and their parameters if needed by pi.

## Implementation

Use one small Python script and the standard library.

For a normal material export:

1. Load the selected source-material `.ptex` as JSON.
2. Apply only that template's allowlisted friendly parameters.
3. Set the Material node's `size` parameter.
4. Save a working `.ptex` and export it with Material Maker.

For hotspot conversion:

1. Copy `hotspot/converter.ptex` into a working directory.
2. Patch its Image nodes to absolute paths: `image` = albedo, `image_2` = OpenGL normal, `image_3` = ORM, and `image_4` = `hotspot/mask.png`.
3. Set its Material node's resolution to match the input maps.
4. Export the converted albedo, normal, and ORM with Material Maker.

Finally, verify that all three outputs exist with matching dimensions and return their paths as JSON.

The conversion graph itself owns all seam, normal, and ORM operations. The CLI only replaces image paths and runs it; it must not recreate Material Maker node logic in Python. Keep source-template mappings in the script until their number makes that awkward.

## Material Maker 1.7 command

Validated locally with `materials/metal-noise.ptex` (then named `devil_metal.ptex`):

```sh
'/Applications/Material Maker.app/Contents/MacOS/Material Maker' \
  --export-material \
  -o /absolute/output/directory \
  /absolute/input/material.ptex
```

This produced:

- `devil_metal_albedo.png`
- `devil_metal_normal.png`
- `devil_metal_orm.png`
- `devil_metal.tres`

Known local constraints:

- Input paths must be absolute because the app changes its working directory.
- `--headless` currently crashes during export on this Mac; run with the normal renderer.
- Material Maker 1.7 always renders command-line exports at 2048×2048: `src/parse_args.gd` parses `--size` but passes a hardcoded 2048, which also overrides the Material node's `size`. The CLI resamples smaller sizes with `sips`; sizes above 2048 are not supported.
- The graph-level `seed_int` is not inherited by nodes. The CLI's `seed` parameter sets a derived seed on every unlocked node.
- The output directory must already exist.
- Ignore the extra `.tres` file for the texture-only MVP.

## Included source and reference assets

```text
materials/          source graphs: curated metal-noise.ptex and metal-scratched.ptex, plus downloads (<name>.ptex + <name>.json)
hotspot/
  converter.ptex    reusable converter: one material's three maps + the mask → atlas maps
  mask.png          2048×2048 panel mask exported from mask.ptex
  mask.ptex         layout.png → Image → Invert → Tones Step → Dilate/Erode → Invert
  layout.png        2048×2048 UV layout exported from layout.blend
  layout.blend      subdivided reference plane used by DreamUV
examples/           2048×2048 albedo, normal, orm texture sets
  metal-noise/      export of materials/metal-noise.ptex; hotspot/ holds its converted atlas maps
  metal-scratched/  export of materials/metal-scratched.ptex
  rust/             rusty source set for the clean/rust blend
blender_hotspot.py  DreamUV automation inside a running Blender
```

`layout.png` and `mask.ptex` are authoring assets used only to regenerate the mask; conversion needs only `mask.png`.

## Hotspot conversion

The hotspot converter is independent of the source material. It accepts any compatible tileable PBR texture set:

- Albedo
- OpenGL normal
- ORM
- `hotspot/mask.png`

It outputs atlas-compatible albedo, normal, and ORM maps. No source-material graph needs to contain hotspot logic.

`HOTSPOT_MATERIAL.md` documents how the converter modifies the three channels. DreamUV mapping uses the reference layout in `hotspot/layout.blend`; `blender_hotspot.py` scripts it inside a running Blender.

## Delivery phases

### Phase 1 — Validate the supplied converter — complete

- [x] Added the converter (`hotspot/converter.ptex`).
- [x] Connected the three `examples/metal-noise/` maps and `hotspot/mask.png`.
- [x] Exported hotspot albedo, normal, and ORM maps to `examples/metal-noise/hotspot/`.
- [x] Confirmed all three exported maps are 2048×2048.

The remaining work starts with CLI automation; Python does not need to construct the conversion graph.

### Phase 2 — Automate export and conversion — complete

- [x] `mm-material list`, `generate`, and `convert-hotspot`, in one stdlib-only Python script.
- [x] Curated materials `metal-scratched` and `metal-noise` in `materials/`, plus `seed` on every material.
- [x] Sizes 256, 512, 1024, and 2048.
- [x] Converting `examples/metal-noise/` reproduces `examples/metal-noise/hotspot/` byte for byte.
- [x] `check.sh` runs both commands at 256×256.
- [x] `convert-hotspot` accepts `edge_relief`, `edge_softness`, `edge_brightness`, and `edge_roughness`; softer converter defaults are documented in `HOTSPOT_MATERIAL.md` (Edge treatment), and `examples/metal-noise/hotspot/` was re-exported with them.

Original tasks:

- Implement `convert-hotspot` by patching only the converter's image paths and resolution.
- Implement `generate` around one included source-material `.ptex`.
- Expose only two or three useful, verified material parameters.
- Keep one small runnable low-resolution check for each command.

Done when the CLI can export a plain material and convert any supplied compatible texture set into hotspot-atlas maps.

### materialmaker.org downloads — complete

- [x] `search [words…] [--license CC0|CC-BY|CC-BY-SA]` filters the website's static materials (type `0`) by name, tags, description, and author, using `https://www.materialmaker.org/api/getMaterials`.
- [x] `download <id> [--name …]` fetches `api/getMaterial?id=<id>` and saves `materials/<name>.ptex` plus `<name>.json` with id, author, license, and page URL. CC-BY materials need attribution. Downloads accept only `seed`.
- [x] Tested exports for `material`, `material_export`, and `material_tesselated` Material nodes. Unlit materials are refused at download.
- [x] Material Maker skips the ORM map when AO, roughness, and metallic are all unconnected constants; `generate` then writes a flat ORM from those constants.

```sh
./mm-material search rust metal --license CC0
./mm-material download 121            # → materials/simple-rusted-metal.ptex
./mm-material generate simple-rusted-metal --output ./out/rust --size 1024
```

### Blender hotspot mapping — validated

- [x] `blender_hotspot.py` appends the atlas plane from `hotspot/layout.blend`, builds a Principled material from a hotspot texture set, and runs DreamUV Hotspot on a mesh.
- [x] Run through Blender MCP on Blender 5.2.1 with `examples/metal-noise/hotspot/` and a `convert-hotspot` output, on a cube and on a chamfered, inset test block.
- [x] DreamUV needed a one-line fix for Blender 5, documented in `HOTSPOT_MATERIAL.md`.

Possible later step: expose it as an `apply-hotspot` MCP tool that delegates to Blender MCP.

### Phase 3 — MCP wrapper

Expose the proven CLI operation as one structured MCP tool, for example:

```json
{
  "template": "metal",
  "output": "./out/dark-metal",
  "size": 1024,
  "hotspot": true,
  "parameters": {
    "color": "#34383d",
    "roughness": 0.65,
    "scratch_scale": 24
  }
}
```

The MCP server delegates to the CLI and returns its JSON result. It does not duplicate generation or export logic.

## Acceptance criteria

- `convert-hotspot` accepts arbitrary compatible albedo, OpenGL normal, and ORM images.
- It uses the fixed mask and supplied converter without reconstructing the graph in Python.
- Plain and hotspot output sets each contain albedo, normal, and ORM maps.
- Inputs and outputs may be outside the current working directory.
- All three input dimensions must match; mismatches fail clearly.
- Output dimensions match the inputs or requested `--size`.
- ORM channel order is documented and preserved.
- Invalid templates, parameters, values, or paths fail clearly.
- Pi can discover supported source templates and parameters without reading Python source.

## Inputs still needed

- The first two or three controls desired for the initial source-material template. If unspecified, start with scale, primary color, and roughness where supported.

## References

- Material Maker app: `/Applications/Material Maker.app`
- Material Maker source: <https://github.com/RodZill4/material-maker>
- Premade materials: <https://www.materialmaker.org/materials?type=material>
- Hotspot workflow: `HOTSPOT_MATERIAL.md`
- Tutorial: <https://www.youtube.com/watch?v=PdpS8jT7OPI>
- Example project: <https://github.com/profesorshader/example-hotspot-texturing>
