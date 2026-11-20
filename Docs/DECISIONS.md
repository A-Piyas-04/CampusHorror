# Decisions ledger

Audience: the project owner, and any AI session building on these decisions.

This is the one place to check whether something is decided. **Confirmed** means the owner has
decided it, or explicitly handed the decision over ("do what is necessary to achieve the best
outcome") and it was then settled with evidence. A Confirmed decision changes only through a new
row here, never by being quietly edited in another document.

Answered 20 November 2026. The questions themselves are in `Docs/NEXT_ACTIONS.md` §1.

---

## Scope and design (decided by the owner)

| # | Decision | Confirmed value | Where it is applied |
|---|---|---|---|
| D0 | Game shape | **A finishable 2–4 hour horror game**, with enough exploration and backtracking area | `GAME_DESIGN.md` §2, §9; `ROADMAP.md` scope table |
| D5 | Premise | **An underground bio-organism research facility beneath the campus.** Its experiments have produced horrifying mutated human and animal creatures. **Horror, not action**: the player never fights. | `GAME_DESIGN.md` §2 |
| D6 | Lantern model | **Light reveals, hides and attracts** (the full three-way cost model) | `GAME_DESIGN.md` §3 |
| D7 | Composure / fear system | **In** | `GAME_DESIGN.md` §4 |
| D8 | Mirror Campus | **The spine of the game, appearing as a late-game area.** Read as: built and played in the back half, foreshadowed from the start (see `GAME_DESIGN.md` §2 "How the Mirror Campus is both late and the spine") | `GAME_DESIGN.md` §2, `ROADMAP.md` Phase M |
| D9 | Enemies | **Start with one, build more later**, on one reusable AI framework | `GAME_DESIGN.md` §5, `ROADMAP.md` J4 |
| D10 | Campus-knowledge puzzles | **Real IUT students get an advantage and privileges and solve them faster. Players who don't know the campus always get enough in-game information to solve every puzzle.** | `GAME_DESIGN.md` §7 |
| D11 | Language | **English only** (in-world Bengali signage stays as authentic environment art) | `GAME_DESIGN.md` §7, `ROADMAP.md` Phase N |
| D12 | Title | **The Quiet Hours** (owner asked Claude to choose; see the reasoning below) | Everywhere |

**D12 reasoning.** "Quiet hours" is a real campus and hall-of-residence rule. It is also what this
game is about: the hours after lights-out, when the campus goes silent and something below it does
not. The title promises atmosphere rather than action, and that matches D5. It does not collide with
a major horror property. Runners-up: *Specimen Hall* (hall of residence plus lab specimens; sharper,
but risks reading as a B-movie) and *Lower Campus* (understated, literal for the facility).
Ruled out: *Vivarium*, because the 2019 horror film of that name is about being trapped in a replica
neighbourhood, which is too close to the Mirror Campus.

---

## Presentation and technology (delegated to Claude, settled by measurement)

Full contract and numbers: `Docs/PRESENTATION.md`. Summary:

| # | Decision | Confirmed value | Evidence |
|---|---|---|---|
| D1 | Base resolution and stretch | **1920 × 1080 base, `canvas_items` stretch, `expand` aspect, fractional scaling, no pixel snap**, plus 2D physics interpolation | Reasoning in `PRESENTATION.md` §1. Cost at 1080p measured: 2.62 ms per frame |
| D2 | Texel density and camera zoom | **Default camera zoom 2.0** (per-zone range 1.5–2.5). Every sprite is already dense enough. **Only the 4 ground tiles are re-rendered, at 4× density.** | Measured density of all 22 assets (`PRESENTATION.md` §2). Bench experiment: doubling `px_per_m` left footprint, collision and origin byte-identical, 37/37 |
| D3 | Renderer | **Stay on Compatibility** | Stress test, below |
| D4 | Movement speeds | **Sneak 32 px/s (1.0 m/s) · Walk 62 px/s (1.95 m/s) · Sprint 154 px/s (4.8 m/s)**, replacing the single 200 px/s (6.25 m/s) | Stride arithmetic in `PRESENTATION.md` §4 |

### D3 evidence: renderer stress test, 20 November 2026

`scenes/tests/renderer_stress/RendererStressTest.tscn`: the real `main_gate_exterior` at night, with
30 shadow-casting PCF5 lights spread across the zone plus N low-energy lights stacked on one brick
point. Vsync off, 90 warm-up frames, 300 measured frames, RTX 3050 Laptop GPU, default
1152 × 648 window unless noted.

**Correctness.** This is the question that mattered: does Compatibility's default
`max_lights_per_object = 8` silently drop lights? The figure is luminance under the stacked lights.

| Stacked lights | Compatibility | Forward+ |
|---|---|---|
| 8 | 0.4716 | 0.4717 |
| 12 | 0.5248 | 0.5248 |
| 16 | 0.5341 | 0.5340 |
| 24 | 0.5341 | 0.5340 |
| 48 | 0.5341 | 0.5340 |

The two renderers agree to four decimal places at every count. Brightness rises past 8 lights, so
there is no per-object cap in 2D, and both flatten at 16 lights because the brick's colour saturates.
A first run at higher light energy saturated even at 8 lights and proved nothing; it was discarded
and the energy lowered.

**Cost.**

| Renderer | Average | p99 | Worst frame |
|---|---|---|---|
| Compatibility (12 stacked + 30) | 1.45 ms | 1.58 ms | 1.77 ms |
| Compatibility (48 stacked + 30) | 1.52 ms | 1.73 ms | 1.87 ms |
| Compatibility at **1920 × 1080** (12 + 30) | **2.62 ms** | 3.03 ms | 3.24 ms |
| Forward+ (12 stacked + 30) | 1.04 ms | 1.39 ms | 1.39 ms |
| Forward+ (first run) | 1.07 ms | 1.39 ms | **12.19 ms** spike |

**Why Compatibility.** The lighting is identical, so correctness does not decide it. Compatibility's
steadier frame pacing does (its worst frame stayed under 2.1 ms in every run). It also has the
broadest hardware support of Godot's renderers (OpenGL 3.3, including integrated GPUs, which matters
for an audience of students on laptops), needs no migration, and keeps every existing light-mask
convention valid. Forward+ is about 0.4 ms faster on
average, which is irrelevant against a 16.7 ms (60 Hz) or 6.9 ms (144 Hz) budget. Its one 12 ms spike
is the kind of hitch the smoothness priority rules out.

**Retires review risk R2.** Revisit only if a needed feature turns out to be Forward+-only.
