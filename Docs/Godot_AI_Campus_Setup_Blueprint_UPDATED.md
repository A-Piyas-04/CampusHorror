# AI-driven campus game: setup and reusable blueprint

Updated 7 October 2026 • Beginner guide • Godot 4 • Cursor Agent

## What this guide prepares

A custom 2D top-down university game with outdoor areas, buildings, rooms, a hospital, underground areas and underwater areas. Later, you will add mystery, puzzles, enemies, a lantern and day/night behavior.

Your first deliverable is a **small, working development foundation**: Cursor can inspect and modify the project, you can arrange custom assets in Godot, and new story content can reuse existing systems. This guide is documentation; the proposed game framework has not been built or tested on your computer.

You will still test movement, inspect visuals and decide layouts. AI can write most code, but a blueprint cannot make every future mechanic automatic. Each new behavior still needs implementation and testing.

## 1. Set the cost boundary first

Use your existing Cursor and ChatGPT subscriptions. Add no paid APIs, generation services or subscriptions.

**Correction to the earlier advice:** Cursor's paid plan has included usage limits; free MCP software does not remove those limits. Keep on-demand spending disabled in your account settings, where available, and check your usage dashboard. If you exhaust included usage, wait for renewal or do layout/design work. This workflow cannot promise unlimited cloud AI assistance. See [Cursor pricing and usage documentation](https://cursor.com/docs/models-and-pricing).

Do not supply an API key to an asset tool. Use ChatGPT through your existing app for planning, reference discussion and prompt preparation; treat image generation as optional, since it is not an unlimited production pipeline.

## 2. Install the minimum tools

Download from the official sites. Windows and macOS both work; follow the MCP configuration for your operating system below.

| Tool | Install now? | Job |
|---|---|---|
| [Godot](https://godotengine.org/download/) | Yes | Engine and visual level editor |
| Cursor | Already owned | Code, project files, AI agent |
| [Node.js LTS](https://nodejs.org/) | Yes | Runs the selected local MCP server |
| [Git](https://git-scm.com/downloads) | Yes | Recoverable project checkpoints |
| [Pixelorama](https://pixelorama.org/) | Yes, when making pixel assets | Adjust tiles and sprites; free/open-source |
| [Blender](https://www.blender.org/download/) | Later | Generate custom building sprites using scripted geometry |
| [Krita](https://krita.org/en/download/) | Optional | Paint or clean up larger images |

Choose Godot's **standard build**, using GDScript. You do not need the .NET build or C#. Pick a current stable Godot 4 release and record its exact version. Keep that version throughout the first prototype; avoid preview builds.

After installing Node.js and Git, restart Cursor. In its terminal run separately:

```sh
node --version
npm --version
git --version
```

**Pass condition:** all three print versions. If a command is missing, fix installation/PATH before continuing.

## 3. Create one Godot project

1. Open Godot's Project Manager and choose Create/New Project.
2. Name it `CampusMystery` and choose a dedicated folder.
3. Start with the **Compatibility** renderer for this simple 2D prototype. Test your intended lighting on it before committing to final visuals.
4. Choose Git version-control metadata if offered; create the project.
5. In Cursor, open that same folder containing `project.godot`.
6. Keep Godot and Cursor open on this same project.

Do not keep multiple Godot projects open while configuring this MCP.

Ask Cursor:

```text
Inspect this empty Godot project. Record its exact Godot version and
renderer in docs/SETUP.md. Initialize Git if necessary. Ignore .godot/
and exported builds, but retain source assets, .tscn, .tres, .gd and
.uid files. Do not create gameplay yet. Show the initial Git diff.
```

In Cursor's Source Control panel, review and commit the initial project. If Git requests your name/email, configure your own identity.

**Pass condition:** a clean project opens in both tools, with an initial commit.

## 4. Connect Cursor to Godot

Use **one integration**: [tomyud1/godot-mcp](https://github.com/tomyud1/godot-mcp), listed in Godot AssetLib as **Godot AI Assistant tools MCP**. It is community software; capabilities and compatibility should be verified in your project.

### Install the editor add-on

1. In Godot, open AssetLib.
2. Search for `Godot AI Assistant tools MCP`; check its repository matches the link above.
3. Install its add-on into your project.
4. Open Project → Project Settings → Plugins and enable Godot MCP.

### Configure Cursor

Create `.cursor/mcp.json` inside the project. Cursor supports project-local configuration there; see [official MCP documentation](https://cursor.com/docs/mcp). Menu labels may change; look for MCP under Settings or Customize.

**Windows:**

```json
{
  "mcpServers": {
    "godot": {
      "type": "stdio",
      "command": "cmd",
      "args": ["/c", "npx", "-y", "godot-mcp-server"]
    }
  }
}
```

**macOS/Linux:**

```json
{
  "mcpServers": {
    "godot": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "godot-mcp-server"]
    }
  }
}
```

Restart Cursor and the Godot project. Allow the local MCP server to start. The first launch needs internet to fetch the package. These setup commands follow the repository's quick start; the explicit `type` field follows Cursor's current configuration documentation.

### Verify the connection before building

Send this to Cursor Agent:

```text
Use the Godot MCP to report the open project, engine version and scene
tree. Do not edit anything. If a tool is unavailable, report that
instead of claiming success.
```

Then:

```text
Create a temporary Node2D scene named MCPCheck with a visible colored
rectangle. Save it, run it, inspect errors, and capture the viewport
if screenshot tools are available. Stop the game and report the result.
```

**Pass condition:** the rectangle appears in Godot and the agent can inspect the project. Screenshot/play capabilities are optional until confirmed. Record tested add-on/server versions in `docs/SETUP.md`; pin compatible versions after the connection works rather than upgrading automatically.

## 5. Give the agent permanent project instructions

Create `.cursor/rules/godot-project.mdc`. Cursor recognizes `.mdc` project rules with frontmatter; see [Cursor rules](https://cursor.com/docs/rules).

Paste:

```text
---
description: CampusMystery Godot development rules
alwaysApply: true
---
Read docs/SETUP.md, docs/BLUEPRINT.md and docs/STATUS.md before work.
Use this project's recorded Godot 4 version and typed GDScript.
Use CharacterBody2D and TileMapLayer where appropriate; avoid Godot 3 APIs.
Use only local/free tools. No paid APIs or extra subscriptions.
Work on one requested milestone at a time.
Inspect existing scenes and resources before creating replacements.
Preserve manually placed map objects and existing node names.
Use reusable scenes, exported Inspector properties and stable content IDs.
Keep story content separate from reusable behavior.
Do not add an AI service dependency to the shipped game.
Use Godot MCP for editor inspection when available.
If editing scene files directly, save editor changes first and verify reload.
Run the affected scene and inspect errors after each change.
Report what was actually tested and what still needs human testing.
Update docs/STATUS.md with changed files, checks and next task.
Do not silently change the architecture or add unrequested systems.
```

Keep the rule short. Put evolving details in documentation rather than repeating your whole game concept in every chat.

## 6. Establish the blueprint documents

Ask Cursor to create these **before generating gameplay**:

| File | What it records |
|---|---|
| `docs/SETUP.md` | OS, exact tool versions, MCP setup, run instructions |
| `docs/BLUEPRINT.md` | Scene ownership, reusable components, persistence contracts |
| `docs/ART_STYLE.md` | Perspective, tile scale, palette, lighting and export rules |
| `docs/CAMPUS_MAP.md` | Zone IDs, campus references and doorway connections |
| `docs/CONTENT.md` | Story flags, clue IDs, item IDs and chapter definitions |
| `docs/STATUS.md` | Working features, known bugs, latest checks, next task |
| `docs/ASSET_REGISTER.md` | Asset source, editable source file, export and usage notes |

Start `BLUEPRINT.md` with the architecture in Step 7. Mark undecided values explicitly. Start `CONTENT.md` empty except for conventions; you have not finalized your story yet.

**Pass condition:** a new Cursor chat can understand the project by reading these files.

## 7. Use this reusable game architecture

These are proposed design choices, not built-in Godot frameworks.

### Project folders

| Folder | Contents |
|---|---|
| `assets/source/` | Editable artwork and Blender sources |
| `assets/sprites/`, `assets/tiles/`, `assets/audio/` | Game-ready files |
| `scenes/core/` | Main game container and transition UI |
| `scenes/player/` | Player scene |
| `scenes/components/` | Interactions, doors, pickups, spawn markers |
| `scenes/world/` | Campus and interior zone scenes |
| `scenes/ui/` | HUD, menus, dialogue view |
| `scenes/tests/` | Small development rooms |
| `scripts/core/`, `scripts/components/` | Shared behavior |
| `data/zones/`, `data/items/`, `data/story/` | Custom Resource definitions and instances |
| `docs/` | Your project memory |

### Ownership rules

`Main.tscn` owns the world container, one Player instance and UI. A zone occupies the world container. Changing zones replaces the zone, moves the existing player to a spawn marker and preserves shared game state.

Every zone supplies a stable `zone_id`, spawn markers, scenery and placed objects. It must not include a second player or reset the global clock.

Use a small persistent `GameState` autoload for story flags, inventory IDs and time. A `SaveService` autoload reads/writes that state. Keep transition logic in Main or its controller initially; avoid creating a global manager for every feature.

| Reusable unit | Set through Godot's Inspector |
|---|---|
| Zone | `zone_id`, lighting profile, outdoor/indoor classification |
| Door | `destination_zone_id`, `destination_spawn_id`, optional required flag |
| Spawn marker | Unique `spawn_id` within its zone |
| Interactable | Prompt text, interaction behavior |
| Pickup/clue | Stable `item_id` or `clue_id`, persistence ID |
| Puzzle, later | `puzzle_id`, required conditions, completion flag |
| Enemy spawner, later | Enemy definition, spawn conditions |

A stable ID is a name like `hospital_basement_key`, retained even if its node moves or is renamed. Never save a transient node path as an object's identity.

### Save contract

Plan a versioned save containing: `save_version`, current zone/spawn, player position, inventory IDs, story flags, world time and persistent object states. Save data to Godot's `user://` location. Define when position overrides a spawn marker: loading a save restores position; entering a door uses its destination marker.

Later, opened doors, collected clues and solved puzzles use stable object IDs. Save gameplay state; reconstruct visuals from that state after loading.

**Example:** solving `hospital_fuse_puzzle` sets `hospital_power_restored`. A door reads that flag, dialogue reads it, and the save file retains it. Neither door nor dialogue needs to understand the fuse puzzle's internal code.

## 8. Prepare places for your future mechanics

Specify the connection points now; implement the behavior only when needed.

| Future feature | Foundation to reserve now | Add later |
|---|---|---|
| Day/night | Persistent clock; zone lighting profile | Cycle speed, schedules, night-only events |
| Lantern | Player attachment point and input action | Light, fuel, recharge, reveal effects |
| Enemies | Collision conventions and stable spawn IDs | Patrol, detection, combat, chase |
| Puzzles | Interaction system and story flags | Particular puzzle rules and presentation |
| Mystery | Clue IDs and dialogue/content data | Chapters, journal, revelations |
| Multiple scenes | Zone registry, doors and spawn markers | Additional buildings and floors |
| Underground | Separate zone with local lighting | Hazards, sound and secret connections |
| Underwater | Zone/environment profile | Swimming, oxygen and special controls |

For day/night and lantern visuals, Godot has `CanvasModulate`, `PointLight2D` and `LightOccluder2D`. They provide visual tools; they do not automatically implement enemy detection or puzzle logic. See [Godot 2D lighting](https://docs.godotengine.org/en/stable/tutorials/2d/2d_lights_and_shadows.html).

Keep enemies' perception separate from decorative lighting. Decide later whether a lantern affects detection, reveals symbols, or both.

## 9. Set one consistent custom-art pipeline

Before requesting assets, decide in this order:

1. **Perspective:** straight overhead or slightly angled top-down. Keep it consistent.
2. **Visual style:** pixel art, clean stylized/vector-like 2D, or rendered 2D sprites.
3. **Target platform:** decide whether the first real release target is desktop-only or whether mobile/web must also be supported. This decision may affect renderer choice, resolution, UI scale, lighting complexity, shaders and asset sizes.
4. **Prototype reference:** create one small visual mockup containing the player, path/ground, wall/door, tree and one recognizable campus building.
5. **Scale:** choose tile size / pixels-per-unit only after the visual direction is tested. Do not commit to 32 × 32 merely because it is common. If pixel art is chosen, 32 × 32 may be tested as one candidate.
6. **Style rules:** palette, outline treatment, shadow direction, player-to-door proportions and export conventions.
7. For pixel art, use nearest texture filtering and consistent integer scaling.

Write the adopted decisions in `ART_STYLE.md`. Values that are still being tested must be marked **Proposed** rather than **Confirmed**.

### Assets without drawing everything yourself

Do **not** choose the permanent production pipeline before a small comparison test.

**Route A: agent-generated SVG/vector shapes.** Cursor can create editable SVG tiles, props and simplified building art using a fixed palette and dimensions. These are useful for stylized prototypes and may become final assets if the chosen visual style supports them.

**Route B: scripted Blender → orthographic 2D renders.** Give campus photographs and approximate proportions to the agent. Ask for a Blender Python script that constructs a simplified building from geometric parts, uses a fixed orthographic camera and renders a transparent PNG. Reuse the same camera angle, scale and material rules.

**Route C: small manual corrections.** Use Pixelorama for pixel-art adjustments or Krita for larger raster/vector cleanup. The goal is correction and consistency, not drawing the entire campus from scratch.

For the **same test building**, try at least the two most promising routes (for example SVG and Blender render), import both into Godot beside the same player placeholder, and judge:

- recognizability,
- visual consistency,
- effort to reproduce,
- ease of editing,
- performance/import behavior,
- whether dozens of additional campus assets can follow the same style.

Only after this comparison should one route become the main production pipeline. A secondary route may still be used for special assets if it visually matches.

AI-generated Blender scripts still need visual review. Photos alone cannot reliably recover hidden building geometry. Supply missing proportions yourself.

**Pass condition:** one player placeholder, one tree/prop and one recognizable campus building look compatible at real gameplay scale, and the preferred repeatable asset route is documented. Do this before producing dozens of assets.

## 10. Turn your real campus into zones

1. Gather a rough campus layout, your photos and approximate building footprints.
2. Mark important roads, fields, entrances, water and landmarks.
3. Assign IDs such as `campus_gate`, `academic_floor_1`, `hospital_reception`.
4. Start with one outdoor zone and one room. Add interiors as separate scenes.
5. Record each connection in `CAMPUS_MAP.md`.

| From | Door | Destination | Spawn |
|---|---|---|---|
| `campus_gate` | `hospital_front_door` | `hospital_reception` | `main_entrance` |
| `hospital_reception` | `exit_door` | `campus_gate` | `outside_hospital` |

Use TileMapLayer for repeated ground/wall tiles and reusable scenes for doors, furniture and special props. Let the agent prepare tiles/collisions; you paint and arrange them. Large outdoor spaces can be split into connected zones if needed. Seamless streaming is a separate later feature.

Do not model every room immediately. Make the layout recognizable first.

## 11. Prevent AI over-engineering

Cursor must build only the smallest system required by the current milestone.

Do **not** allow the agent to create future managers, frameworks or abstractions simply because the project may need them later. A future mechanic listed in the blueprint is a reserved connection point, not permission to implement it now.

Examples:

- During player movement work, do not create inventory, quest, puzzle, enemy or dialogue managers.
- During interaction work, do not build a generic event framework unless the current interaction actually requires it.
- During zone-transition work, build only the registry/door/spawn behavior needed for the test zones.
- Create `GameState` only when persistent state is being tested.
- Create `SaveService` only when save/load is the active milestone.
- Add puzzle/enemy/dialogue systems only when a real playable scenario needs them.

Prefer a small working implementation that can be extended later over a large speculative architecture.

Add this rule to `.cursor/rules/godot-project.mdc`:

```text
Do not implement systems for future milestones. Build the smallest reusable
solution required by the current acceptance criteria. A planned connection
point is not permission to create a manager/framework early.
```

## 12. Build the foundation in small milestones

Do these in order. Commit only after you have personally checked each result.

| Milestone | Ask Cursor to build / define | Acceptance check |
|---|---|---|
| 0 | Project conventions: input names, collision layers/masks, visual ordering/Y-sort policy, character origin/feet convention, naming rules and initial resolution/stretch policy | Conventions are documented and a tiny test scene proves collisions/order behave as expected |
| A | Main container, placeholder player, movement, camera | Move in every direction; walls block movement |
| B | One reusable interaction prompt/action | Interact works only when within range |
| C | Two test zones, registry, door and spawn markers | Travel both ways; exactly one player remains |
| D | GameState and one persistent test pickup | Pickup remains collected after zone travel |
| E | SaveService with versioned save | Restart game and restore zone, item and position |
| F | Small lighting test with time/lantern attachment | Night tint and light work on the chosen renderer/target platform |
| G | One real custom outdoor patch and one real interior/building sample | Imported custom art, collision and doors work together at gameplay scale |
| H | Reopen project and make one desktop test export | Export launches and the basic loop works |

### Milestone 0 minimum conventions

Record these in `docs/BLUEPRINT.md` or a dedicated `docs/CONVENTIONS.md`:

- input action names such as `move_up`, `move_down`, `move_left`, `move_right`, `interact`, `lantern`, `pause`;
- collision-layer names for world, player, interactables, enemies and triggers;
- what determines top-down draw order / Y-sort;
- where a character's logical ground/feet point is;
- scene/node/file naming rules;
- initial project resolution, stretch mode and camera assumptions;
- which values are still provisional.

Do not over-design Milestone 0. Its purpose is consistency, not creating gameplay frameworks.

For H, install export templates matching your recorded Godot version. You do not need export templates for ordinary editor testing.

The foundation is complete when **0 and A–H** pass. Full enemies, puzzle systems and story chapters are subsequent work.

## 13. Use this prompt for each milestone

```text
Read the project rule, docs/BLUEPRINT.md and docs/STATUS.md.
Implement ONLY milestone [number/letter/name].
Inspect existing scenes before editing. State the small change plan.
Build the smallest reusable solution required by this milestone.
Do NOT create managers/frameworks for future mechanics or future milestones.
Use placeholder visuals and reusable scenes with Inspector properties where appropriate.
Preserve my manually arranged map objects.
Do not add paid services or unrelated features.
Run the affected scenes, inspect Godot errors, and check these criteria:
[paste the milestone's acceptance criteria]
Report changed files, checks performed, and checks I must perform manually.
Update docs/STATUS.md. Show the diff for review before the checkpoint commit.
```

If something fails, give Cursor the exact error plus expected and actual behavior. Have it fix the current milestone before moving on. Starting a new chat is fine: reference the same docs and latest commit.

## 14. Add story content later using a content card

For each new story beat, fill this out:

```text
Title:
Zone ID:
Placed objects / characters:
Trigger: proximity / interaction / time / existing flag
Required flags or items:
Player action:
Outcome: flags, items, dialogue, door access
Persistent after save/load?:
Reusable systems involved:
New behavior actually needed:
Acceptance checks:
```

Example: “At night, interact with a hospital noticeboard after collecting a letter. Reveal a clue and set `basement_location_known`.” That should reuse time, interaction and flags. A new lantern-shadow puzzle, however, needs a new puzzle behavior; document it before implementation.

This is how story becomes concrete, bounded work for the agent.

## 15. Troubleshooting and daily routine

| Problem | First action |
|---|---|
| `npx` missing | Verify Node installation; fully restart Cursor |
| MCP unavailable | Check JSON, plugin enabled and the correct Godot project open |
| MCP cannot reach editor | Close extra Godot instances; inspect server/plugin logs |
| Tools differ from screenshots | Use the installed add-on's README and actual tool list |
| Scene edits seem lost | Save editor changes, avoid simultaneous edits, then reload |
| AI invents unsupported APIs | Ask it to check your recorded engine version and docs |
| Art looks inconsistent | Return to the style sheet and fixed export settings |
| Included AI usage exhausted | Wait for renewal; continue mapping, testing or asset editing |

If MCP remains broken, Cursor can still edit GDScript and scene files. Run the game yourself and give it errors/screenshots. Continue the same architecture while troubleshooting the connection.

Each session: open one project in both apps → read status → choose one task → let Cursor implement → inspect/play → fix → update status → commit. Keep another copy of your project on a separate drive or backup location; local Git history alone does not protect against drive failure.

## Ready-to-start checklist

- [ ] Godot, Node.js and Git installed; versions recorded.
- [ ] Cursor and Godot open the same project.
- [ ] One local MCP connected and its inspection check passes.
- [ ] Project rule and blueprint docs exist.
- [ ] Target platform is chosen before renderer/art/lighting decisions become permanent.
- [ ] Perspective and visual style are tested with a small reference mockup.
- [ ] Preferred repeatable asset pipeline is selected after a small comparison test.
- [ ] Campus prototype zone IDs are recorded.
- [ ] Milestone 0 conventions are documented and tested.
- [ ] Milestones A–H pass with reviewed checkpoints.
- [ ] No paid API or additional subscription dependency.

Start with Steps 1–6. Then make the design decisions that affect the prototype, complete **Milestone 0**, and only then implement Milestone A. You do not need to finalize the entire mystery or every mechanic before getting this foundation working.

## Verification references

Installation instructions were checked against the selected integration's repository and official Cursor docs on 7 October 2026. This guide's architecture and milestones are recommendations tailored to your project.

- Godot download: https://godotengine.org/download/
- Selected MCP repository: https://github.com/tomyud1/godot-mcp
- Godot AssetLib listing: https://godotengine.org/asset-library/asset/4767
- Cursor MCP configuration: https://cursor.com/docs/mcp
- Cursor project rules: https://cursor.com/docs/rules
- Cursor usage limits: https://cursor.com/docs/models-and-pricing
- Godot 2D lights: https://docs.godotengine.org/en/stable/tutorials/2d/2d_lights_and_shadows.html
- Pixelorama: https://pixelorama.org/
