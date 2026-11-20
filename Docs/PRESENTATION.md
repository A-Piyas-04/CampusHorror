# Presentation contract

Snapshot: 21 November 2026 • **Status: CONFIRMED and APPLIED** (decisions D1–D4, `Docs/DECISIONS.md`; applied in roadmap batch H2)

Audience: any AI session or person creating assets, zones, camera, movement or rendering code.

This replaces the "Still undecided" presentation items in `Docs/ART_STYLE.md` and
`Docs/CONVENTIONS.md`. §1–2 were **applied on 21 November 2026** (batch H2) and are asserted by
`GameSessionCheck` on every run (`Docs/TESTING.md`). §3–5 were **applied and measured in Phase I
(I1–I5, 21 November 2026)**; the suites in `scenes/tests/feel/` assert them.

The goal behind every number here is the owner's top priority: **clean, crisp and smooth**. Nothing
should ever look magnified, and nothing should ever stutter.

---

## 1. Resolution and scaling (D1)

| Setting | Value | Why |
|---|---|---|
| Base viewport | **1920 × 1080** | The most common desktop display, so the reference case draws 1:1. (Before H2 nothing was set and Godot fell back to 1152 × 648.) |
| Windowed size | **1600 × 900** override | A 1080p laptop can't fit a 1920 × 1080 window plus title bar. `canvas_items` scales the canvas to 0.83, which mipmapped art minifies cleanly. Fullscreen and resolution choice arrive with the settings menu (K6). |
| Stretch mode | **`canvas_items`** | The world is drawn at the window's real resolution, so mipmapped, oversampled sprites stay sharp on larger screens. `viewport` mode would render at base resolution and upscale (blurry), which suits pixel art, not rendered art. |
| Aspect | **`expand`** | Wider monitors see more world instead of black bars. Zone camera limits stop the extra width from revealing unfinished edges. |
| Scale mode | **Fractional** | Rendered art has no pixel grid to protect. Integer scaling would waste screen or force bars. |
| Texture filter | **Linear with mipmaps on everything**, including ground tiles once they are re-rendered (§2) | Correct for rendered art. Nearest filtering is for pixel art only. |
| Pixel snap | **Off** for transforms and vertices | Sub-pixel motion is what makes slow movement look smooth instead of stepping. |
| Physics interpolation | **On** (`physics/common/physics_interpolation`) | Physics runs at 60 Hz. Without interpolation, a camera following the player judders on 120/144 Hz screens. `Player.teleport()` calls `reset_physics_interpolation()` (zone entry, load, respawn), so the player is never seen sliding to the new spot. **Every `Camera2D` must use `process_callback = 0` (physics)**: with interpolation on, Godot forces cameras into physics mode anyway and prints a warning for any camera left on idle. The pipeline's preview cameras and the player camera are set. **Still to verify by eye on a 120/144 Hz display (I1/I4).** |
| Vsync | **On** for shipping builds | Tests turn it off only to measure. |

## 2. Texel density and camera zoom (D2)

**Default camera zoom: 2.0.** Zones may set their own value between 1.5 (open exteriors) and 2.5
(tense interiors).

At 1080p and zoom 2, the view shows about **30 m of ground across and 26 m deep**, and the 1.8 m
character is **about 88 px tall** (8 % of screen height; today it is 44 px, 7 % of a 648 px window).
That is intimate enough for horror while keeping roughly a building's width of context.

What zoom 2 needs from the art: an asset stays crisp as long as it has at least one texel per screen
pixel at the *effective* zoom, which is camera zoom × window scale. Measured on 20 November 2026:

| Asset class | Render density | Texels per game px | 1080p (eff. 2.0) | 1440p (eff. 2.67) | 4K (eff. 4.0) |
|---|---|---|---|---|---|
| Props, vegetation, architecture modules, Main Gate | 220.69 px/m | **6.90** | ✅ | ✅ | ✅ |
| CDS landmark sections | 110.34 px/m | **3.45** | ✅ | ✅ | ≈ (0.86, mild) |
| Player character | 96 px/m | **3.00** | ✅ | ✅ | ≈ (0.75, mild) |
| **Ground tiles (4)** | 32 px/m, drawn 1:1 | **1.00** | ❌ soft | ❌ soft | ❌ soft |

**Only the ground is under-density.** Every sprite was already oversampled 3–7× and mipmapped down.
That explains the "soft tiles" note in `Docs/STATUS.md`. It also corrects the earlier assumption in
`Docs/PROJECT_REVIEW_2026-11.md` R1 that the whole library needed re-rendering.

**Done in H2 (21 November 2026): the 4 ground tiles were re-rendered at 4× density** (256 × 256 px
per 2 m tile, 128 px/m, 4 texels per game px, sharp up to effective zoom 4) and are shown at quarter
scale, so the world size of every cell is unchanged:

- TileSet `tile_size` 256, and the `Ground/Tiles` `TileMapLayer` gets scale 0.25. Cell coordinates
  don't change.
- The `Ground/EdgeStrips` polygons get `texture_scale` 4 so their repeat still matches the tiles.
- Mipmaps are on for the tiles. The pipeline now derives this: a tile gets mipmaps exactly when it is
  oversampled.
- Results: all 4 tiles pass the pipeline (142/142: seamless in both axes, no lighting gradient, the worn
  border matching grass within 0.071 mean RGB). Downsampled back to 64 px, each new tile matches the
  old one within 0.85–2.07 / 255 at offset (0, 0), against 4.8–16.5 for a half-tile shift, so it is
  the same pattern in the same phase, only sharper. The zone validator's ground lattice (316,575
  samples) is unchanged, and its snapshot changed in exactly the 21 intended nodes. Before/after
  screenshots at effective zoom 2 and 4 show crisp paver joints, no seam where strips meet tiles, and
  the plaza grid continuous with the path.

The 4K column shows a small shortfall on the CDS and the character. That is acceptable for launch.
If a 4K pass is wanted later, it is a `px_per_m` change per config. It was **proven layout-neutral**
on 20 November 2026: doubling the bench's density changed the PNG from 461 × 283 to 922 × 566 and
halved the sprite scale (0.145 → 0.0725). The footprint (57.6 game px), the collision rectangle
(57.6 × 12.34152) and the origin stayed byte-identical, and all 37/37 checks passed. Memory cost
grows 4× per doubling, so do it per asset class, not across the board.

## 3. Camera — applied (I4)

`scripts/player/player_camera.gd` on `Player/Camera`; per-zone values in each `ZoneProfile`
(`data/zones/profiles/<zone_id>.tres`).

- Zoom from the profile: `main_gate_exterior` 2.0, `cds_veranda` 2.2 (tighter, enclosed).
- Limits from the profile. The validator requires that they contain the playable area plus half a
  1920 × 1080 view at the profile's zoom, which is the exact condition for never showing the void.
  CameraCheck confirms it at every corner, centre and spawn of both zones.
- Eased follow (position smoothing 6). Look-ahead up to the profile's `look_ahead_px` (48 px outdoors, 40
  in the veranda) at a sprint, scaled by speed, eased at 2.5/s. Measured: 47 px lead at a sprint,
  settling to 0 within 3 s of stopping.
- A teleport snaps the camera: no smoothing drift, no leftover lead or shake.
- `shake(amount)`: trauma-based, decays within 1 s (for Phase J).

## 4. Movement (D4) — applied (I1, I2)

The world scale stays at **32 game px = 1 m**. Nothing about layout changes.

| Mode | Speed | Real-world equivalent | Animation |
|---|---|---|---|
| Sneak | **32 px/s** (1.0 m/s) | Careful, quiet creep | New crouched cycle (I2) |
| Walk (default) | **62 px/s** (1.95 m/s) | Brisk walk | **The existing walk cycle, which needs no change** |
| Sprint | **154 px/s** (4.8 m/s) | Running hard, limited by stamina | New run cycle (I2) |

Today: one speed, 200 px/s (6.25 m/s). That is faster than the new sprint, and it is why the feet
slide.

How the numbers were chosen:

- The existing walk cycle (8 frames at 12 fps, 0.667 s) covers about 1.3 m, which is **1.95 m/s**.
  Walk is set to exactly that, so the current animation plants its feet with no re-render.
- **As built:** every cycle's speed is *measured* in Blender (planted-foot travel per frame), and its fps
  is derived from that: walk 1.40 m per cycle at 11.1 fps, run 2.37 m at 16.2 fps, sneak (12 frames)
  1.19 m at 10.0 fps. MovementCheck measures 0.0 % foot slide in all three gaits, motion on the same tick
  as the input, 0 → walk in 0.100 s, walk → sprint in 0.233 s, and stop in 0.067 s.
- Sneak and sprint are too far from 1.95 m/s for the walk cycle simply to play slower or faster
  (sneak would play at 0.5× and look like slow motion; sprint at 2.5× and look comic). Each gets its
  own cycle in I2. Within a mode, the playback rate follows the actual speed
  (`speed_scale = speed / cycle_speed`) so acceleration never slides either. Clamp it to 0.75–1.25.
- Acceleration (I1 starting values, tune by feel): 0 to walk in about 0.10 s, walk to sprint in
  about 0.25 s, stopping in about 0.08 s. Responsive, with a sense of weight.
- Crossing time, as a check on backtracking: `main_gate_exterior` is about 124 m wide between its
  west and east prototype edges (x −1700..2280). That is about 64 s at a walk and 26 s at a sprint,
  comfortable for exploration. Long backtracks are shortened by
  unlockable shortcuts (`GAME_DESIGN.md` §9), not by raising speed.
- 8-direction facing (today: 4).

## 5. Smoothness budgets

These are acceptance criteria from Phase H onward, the same as geometry checks.

| Budget | Target | Measured today |
|---|---|---|
| Frame time, worst case, dev machine at 1080p | ≤ 6.9 ms (144 Hz) | Stress test: 3.24 ms CPU+GPU. FeelProbe (real play, vsync, 144 Hz, 3 runs): median 6.94 ms, p99 ≈ 9 ms, worst visible 10–14 ms. About 1 % of frames miss one 144 Hz refresh; open item for Phase N frame pacing |
| Frame time on the minimum-spec target | ≤ 16.7 ms (60 Hz) | Not measured. The minimum spec is defined in Phase N |
| Visible stall on a zone change | 0 frames (the loading happens behind a fade) | **Met.** The zone swaps at alpha 1.000; the swap stall (24–26 ms) is entirely behind black; door to control in 0.62 s |
| Input to motion | ≤ 1 physics tick | **Met.** 10.3 px/s after the first tick |
| Single-frame spikes during play | none over 2× the median frame time | **Met** in 3 FeelProbe runs (worst 1.96× in one run) |

The reusable frame-time probe is `scenes/tests/feel/FeelProbe.tscn` (windowed only; `Docs/TESTING.md`).
`RendererStressTest` stays as the lighting cost probe.
