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

The first version uses curated source-material `.ptex` templates and the supplied `combined_orm_with_grid.ptex` hotspot converter. Pi interprets natural language; the CLI remains deterministic and structured.

## MVP scope

### Included

- macOS and the installed Material Maker 1.7 app
- One CLI executable with `generate` and `convert-hotspot` subcommands
- Curated metal templates based on the included examples
- Friendly parameters defined per template, such as scale, colors, roughness, wear, and seed
- Resolution selection
- Godot 4 ORM texture export
- Output validation
- A reusable hotspot-conversion `.ptex` that accepts albedo, OpenGL normal, ORM, and the fixed mask
- Hotspot-atlas albedo, normal, and ORM export

### Not included

- Arbitrary text-to-node-graph generation
- Downloading materials from materialmaker.org
- Creating or UV-mapping meshes
- DreamUV automation
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

1. Copy `combined_orm_with_grid.ptex` into a working directory.
2. Patch its Image nodes to absolute paths: `image` = albedo, `image_2` = OpenGL normal, `image_3` = ORM, and `image_4` = `hotspot_grid_nodes_invert.png`.
3. Set its Material node's resolution to match the input maps.
4. Export the converted albedo, normal, and ORM with Material Maker.

Finally, verify that all three outputs exist with matching dimensions and return their paths as JSON.

The conversion graph itself owns all seam, normal, and ORM operations. The CLI only replaces image paths and runs it; it must not recreate Material Maker node logic in Python. Keep source-template mappings in the script until their number makes that awkward.

## Material Maker 1.7 command

Validated locally with `devil_metal.ptex`:

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
- Material Maker 1.7's `--size` argument appears to be ignored; patch the Material node's `size` parameter before export instead.
- The output directory must already exist.
- Ignore the extra `.tres` file for the texture-only MVP.

## Included source and reference assets

- `devil_metal.ptex`: procedural metal source graph.
- `devil/`: example 2048×2048 albedo, OpenGL normal, and ORM exports from that material, plus Material Maker's reference glTF plane.
- `metal02_hotspot.ptex`: scratched-metal source graph.
- `metal_02/`: example 2048×2048 albedo, OpenGL normal, and ORM exports from that material, plus Material Maker's reference glTF plane.
- `hotspot_uv.png`: 2048×2048 UV-layout input.
- `hotspot_grid_nodes.ptex`: graph that converts `hotspot_uv.png` through Image → Invert → Tones Step → Dilate/Erode → Invert.
- `hotspot_grid_nodes_invert.png`: 2048×2048 exported hotspot panel mask produced by that graph.
- `combined_orm_with_grid.ptex`: reusable converter that consumes one material's three maps plus the mask and produces the final atlas maps.
- `devil/hotspot/`: successful 2048×2048 test export containing `devil_orm_albedo.png`, `devil_orm_normal.png`, `devil_orm_orm.png`, and the extra Godot `.tres` file.

The example glTF files document Material Maker's output but are not required or generated by the texture-only MVP. `hotspot_uv.png` and `hotspot_grid_nodes.ptex` are authoring assets used only to regenerate the mask; conversion needs only the exported mask PNG.

## Hotspot conversion

The hotspot converter is independent of the source material. It accepts any compatible tileable PBR texture set:

- Albedo
- OpenGL normal
- ORM
- `hotspot_grid_nodes_invert.png`

It outputs atlas-compatible albedo, normal, and ORM maps. No source-material graph needs to contain hotspot logic.

`HOTSPOT_MATERIAL.md` documents how the converter modifies the three channels. DreamUV mapping remains manual and requires a Blender reference layout matching the mask. Despite its filename, `metal02_hotspot.ptex` is only a possible source material, not the converter.

## Delivery phases

### Phase 1 — Validate the supplied converter — complete

- [x] Added `combined_orm_with_grid.ptex`.
- [x] Connected the three `devil/` material maps and `hotspot_grid_nodes_invert.png`.
- [x] Exported hotspot albedo, normal, and ORM maps to `devil/hotspot/`.
- [x] Confirmed all three exported maps are 2048×2048.

The remaining work starts with CLI automation; Python does not need to construct the conversion graph.

### Phase 2 — Automate export and conversion

- Implement `convert-hotspot` by patching only the converter's image paths and resolution.
- Implement `generate` around one included source-material `.ptex`.
- Expose only two or three useful, verified material parameters.
- Keep one small runnable low-resolution check for each command.

Done when the CLI can export a plain material and convert any supplied compatible texture set into hotspot-atlas maps.

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

- The matching Blender/DreamUV reference object, needed for later UV mapping but not by the CLI.
- The first two or three controls desired for the initial source-material template. If unspecified, start with scale, primary color, and roughness where supported.

## References

- Material Maker app: `/Applications/Material Maker.app`
- Material Maker source: <https://github.com/RodZill4/material-maker>
- Premade materials: <https://www.materialmaker.org/materials?type=material>
- Hotspot workflow: `HOTSPOT_MATERIAL.md`
- Tutorial: <https://www.youtube.com/watch?v=PdpS8jT7OPI>
- Example project: <https://github.com/profesorshader/example-hotspot-texturing>
