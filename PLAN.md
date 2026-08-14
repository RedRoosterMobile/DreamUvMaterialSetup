# Material Maker CLI and MCP

## Goal

Let pi turn a structured material request into a known-good Material Maker project and exported PBR texture set.

Example user request:

> Make a dark scratched metal texture at 1024×1024.

Expected output:

- Generated `.ptex` project
- Albedo PNG
- OpenGL normal PNG
- ORM PNG (`R = AO`, `G = roughness`, `B = metallic`)

The first version uses curated `.ptex` templates with allowlisted parameters. Pi interprets natural language; the CLI remains deterministic and structured.

## MVP scope

### Included

- macOS and the installed Material Maker 1.7 app
- One CLI command
- Curated metal and brick templates
- Friendly parameters defined per template, such as scale, colors, roughness, wear, and seed
- Resolution selection
- Godot 4 ORM texture export
- Output validation
- Atlas texture export from a supplied hotspot `.ptex` template and panel mask

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
./mm-material generate brick \
  --output ./out/red-brick \
  --size 2048 \
  --param brick_color=#8b382d \
  --param mortar_color=#b8aa91
```

Unsupported template names or parameters fail with a useful message. A `list` command can show available templates and their parameters if needed by pi.

## Implementation

Use one small Python script and the standard library:

1. Load the selected `.ptex` template as JSON.
2. Apply only that template's allowlisted friendly parameters to known node/parameter paths.
3. Set the Material node's `size` parameter from the requested power-of-two resolution.
4. Save the generated `.ptex` into the output directory.
5. Run Material Maker with absolute input and output paths.
6. Verify that albedo, normal, and ORM PNGs exist and have the requested dimensions.
7. Return the generated file paths as JSON so pi and a future MCP wrapper can consume them.

Keep template mappings in the script until their number makes that awkward. Do not build a generic Material Maker schema or graph editor for the MVP.

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

## Hotspot materials

For the MVP, “hotspot” means only an atlas-compatible PBR texture set. The user supplies a known-good panel layout/mask through a curated `.ptex` template. DreamUV mapping remains manual.

`HOTSPOT_MATERIAL.md` documents the authoring and Blender workflow. `metal02_hotspot.ptex` currently has scratched-metal nodes but no image or panel-mask node, so it is not sufficient as the atlas template described there.

## Delivery phases

### Phase 1 — One end-to-end template

- Implement the CLI around `devil_metal.ptex`.
- Expose two or three useful, verified parameters.
- Export and validate a requested resolution.
- Keep one small runnable test using a low resolution.

Done when one command reliably creates a generated `.ptex`, albedo, normal, and ORM map.

### Phase 2 — Useful template library

- Add one known-good brick `.ptex`.
- Add the actual hotspot atlas `.ptex` and its panel-mask asset.
- Add only parameters that are useful in real prompts.

Done when metal, brick, and hotspot-atlas requests export without manual graph editing.

### Phase 3 — MCP wrapper

Expose the proven CLI operation as one structured MCP tool, for example:

```json
{
  "template": "metal",
  "output": "./out/dark-metal",
  "size": 1024,
  "parameters": {
    "color": "#34383d",
    "roughness": 0.65,
    "scratch_scale": 24
  }
}
```

The MCP server delegates to the CLI and returns its JSON result. It does not duplicate generation or export logic.

## Acceptance criteria

- A single CLI command generates all expected files.
- Inputs and outputs may be outside the current working directory.
- Supported parameters visibly affect the exported maps.
- Output texture dimensions match `--size`.
- ORM channel order is documented and preserved.
- Invalid templates, parameters, values, or output paths fail clearly.
- Pi can discover supported templates/parameters without reading Python source.

## Inputs still needed

- A known-good brick `.ptex` template.
- The real hotspot atlas `.ptex` plus its panel-mask image, if already created.
- The first two or three controls desired for each template. If unspecified, start with scale, primary color, and roughness where the graph supports them.

## References

- Material Maker app: `/Applications/Material Maker.app`
- Material Maker source: <https://github.com/RodZill4/material-maker>
- Premade materials: <https://www.materialmaker.org/materials?type=material>
- Hotspot workflow: `HOTSPOT_MATERIAL.md`
- Tutorial: <https://www.youtube.com/watch?v=PdpS8jT7OPI>
- Example project: <https://github.com/profesorshader/example-hotspot-texturing>
