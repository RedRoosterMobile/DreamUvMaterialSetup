# Hotspot Material Workflow

Create a reusable panel-texture atlas in Material Maker, map it automatically with DreamUV's Hotspot tool in Blender, and optionally blend clean and rusty versions in Godot using vertex colors.

## Deliverables

- A reference Blender mesh defining the atlas rectangles
- A panel mask exported from Material Maker
- Clean-metal albedo, normal, and ORM textures
- Rusty-metal albedo, normal, and ORM textures
- A target mesh with hotspot UVs
- Optional red vertex-color mask for rust
- A GLB ready for Godot

## Tools

- Material Maker 1.6 or later
- Blender 5.0
- DreamUV Blender add-on with the Hotspot tool
- Godot 4

> The source workflow used Blender 5.0 because DreamUV did not work with Blender 5.1 at the time. Test newer versions before relying on them.

## 1. Prepare the source materials

Create or obtain two tileable PBR materials:

1. A clean or worn metal
2. A rusty metal

Each material needs:

- Albedo
- Normal map in OpenGL orientation
- ORM texture:
  - Red: ambient occlusion
  - Green: roughness
  - Blue: metallic

In Material Maker, export both materials with the **Godot 4 ORM** preset.

## 2. Define the atlas layout in Blender

1. Add a plane.
2. Enter Edit Mode.
3. Subdivide the plane into non-overlapping rectangular panels of several sizes and aspect ratios.
4. Keep every panel inside the plane's original square boundary.
5. Do not move the default UVs outside the `0–1` UV range.
6. Save this Blender file. DreamUV will later use the subdivided plane as its hotspot reference object.
7. In the UV Editor, select all UVs.
8. Export the UV layout with:
   - Size: `2048 × 2048`
   - All UVs selected
   - Opacity: `1.0`

The exported image must clearly show every rectangular panel boundary.

## 3. Convert the UV layout into a panel mask

Import the UV-layout image into Material Maker and build this node chain:

```text
Image → Invert → Tones Step → Dilate/Erode → Invert → panel_mask
```

Adjust the nodes as follows:

1. **Invert** the layout if necessary so the panel interiors and separator lines have the required polarity.
2. Use **Tones Step** to force the image to pure black and white.
3. Use **Dilate/Erode** to control separator width. Start near `5` and adjust visually.
4. Apply the final **Invert** so the mask has the polarity required by the following Blend nodes.

The final mask must have:

- Solid panel interiors
- Narrow, continuous separators
- No gray noise away from the separators
- No broken lines

Export this mask at the same resolution as the material textures.

## 4. Add panel detail to the albedo

For each source material:

1. Load the source albedo.
2. Duplicate it through a **Hue/Saturation/Value** node.
3. Reduce **Value** on the duplicate to create a darker version.
4. Blend the original and darkened versions with **Filter Blend**.
5. Use `panel_mask` as the blend mask.
6. Reverse the blend inputs or invert the mask if the panel faces become dark instead of the separators.
7. Pass the panel mask through **Smooth Curvature** to add a subtle highlight along panel edges.
8. Use a **Tones** node to control the final contrast without clipping large areas.

Expected result: panel separators are darker, while their edges receive a restrained highlight.

## 5. Add panel relief to the normal map

Build this node chain:

```text
panel_mask → Normal Map
source_normal ──────────┐
panel_normal ───────────┴→ Normal Map Blend → final_normal
```

1. Convert `panel_mask` to a normal map as if it were a height map.
2. Keep the relief subtle; the separators should read as shallow grooves, not deep cuts.
3. Convert maps to the same orientation before blending.
4. Blend the panel normal with the source material's normal using **Normal Map Blend**.
5. Export the result in the OpenGL orientation expected by Godot.

## 6. Modify the ORM texture at panel separators

Use the mask to alter the source ORM only around panel separators:

- Reduce ambient occlusion values to darken the recesses.
- Increase roughness by approximately `0.5`.
- Reduce metallic.

Suggested graph:

```text
panel_mask → Invert → Vector3 Math adjustment ─┐
source_orm ─────────────────────────────────────┴→ Vector3 Math (Clamp)
                                                   ↓
                                                Decompose
                                              ↙     ↓      ↘
                                            AO  Roughness  Metallic
```

Rules:

1. Leave **Clamp disabled** on the adjustment operation so intermediate values can exceed `0–1`.
2. Combine the adjustment with the source ORM in a second Vector3 Math node.
3. Enable **Clamp** on the final combination.
4. Decompose the RGB result into AO, roughness, and metallic.
5. Apply a small **Gaussian Blur** to AO so the recess is not razor-sharp.
6. Pass roughness and metallic through separate **Tones** nodes for final adjustment.
7. Recombine the channels as ORM if the export node does not do this automatically.

Check the channels before export: `R = AO`, `G = roughness`, `B = metallic`.

## 7. Export both atlas materials

Export complete Godot 4 ORM texture sets for:

- Clean metal with panel detail
- Rusty metal with the identical panel layout

Both materials must use the same:

- Resolution
- Panel mask
- UV layout
- Normal-map orientation
- ORM channel order

Reusing the same Material Maker graph should require replacing only the source albedo, normal, and ORM textures.

## 8. Apply hotspot UVs to a target mesh

1. Create or import the target environmental mesh.
2. Add seams where explicit UV breaks are required.
3. If DreamUV needs more topology, add a **Subdivision Surface** modifier:
   - Mode: Simple
   - Levels: `2`
4. Apply the modifier only if the extra geometry is acceptable.
5. Assign the clean atlas material to the target mesh.
6. Open DreamUV's **Hotspot** panel.
7. Set the saved subdivided plane as the hotspot reference object.
8. Set the atlas material or texture requested by DreamUV.
9. Select the target faces.
10. Run **Hotspot**.

DreamUV should match each selected UV island to a similarly proportioned rectangle in the atlas.

Inspect the result and rerun Hotspot on smaller face selections when:

- A panel spans an unwanted edge
- The chosen atlas rectangle has the wrong aspect ratio
- Adjacent faces need to remain one panel
- Visible stretching occurs

## 9. Paint an optional rust mask

Use vertex colors to specify where Godot should blend in the rusty material:

1. Switch to Vertex Paint mode.
2. Fill the entire mesh with black: `(0, 0, 0)`.
3. Paint rust areas red: `(1, 0, 0)`.
4. Use soft transitions rather than hard edges.
5. In the material's Blender shader graph, add and connect a **Color Attribute** node for the painted color layer.
6. Confirm that the vertex colors are visible before export.

Black means clean metal; red controls the amount of rusty metal.

## 10. Export the target mesh

Export as GLB/glTF with:

- Selected objects only
- Vertex colors enabled
- UVs enabled
- Materials enabled
- Animations disabled unless the asset actually uses them

Re-import the GLB into Blender or Godot once to verify that UVs and vertex colors survived export.

## 11. Blend the materials in Godot

1. Import the GLB and both texture sets.
2. Create a `ShaderMaterial` for the mesh.
3. Assign the clean and rusty albedo, normal, and ORM textures.
4. Read the mesh vertex color in the spatial shader.
5. Use the red vertex-color channel as the material-blend mask.
6. Multiply or reshape that mask with a seamless noise texture.
7. Expose these shader controls:
   - Noise scale
   - Rust threshold
   - Transition softness
8. Sample the noise at two different scales or offsets and combine the samples to reduce obvious repetition.
9. Use the final mask to blend all corresponding PBR values, not only albedo:
   - Albedo
   - Normal
   - AO
   - Roughness
   - Metallic

## Validation checklist

- [ ] The atlas contains several useful rectangular aspect ratios.
- [ ] All panel rectangles remain within the `0–1` UV range.
- [ ] Panel separators are continuous and narrow.
- [ ] Separator depth is subtle in the normal map.
- [ ] ORM channels are ordered as AO, roughness, metallic.
- [ ] Clean and rusty materials use exactly the same layout.
- [ ] Hotspot UVs show no obvious stretching.
- [ ] Vertex colors survive GLB export.
- [ ] Rust affects every PBR channel consistently.
- [ ] The noise texture is seamless and does not visibly repeat.

## Appropriate use

Use hotspot materials for reusable environmental and modular assets that need fast UV mapping. Do not use this as the default workflow for hero assets that require unique UVs and individually authored texture detail.
