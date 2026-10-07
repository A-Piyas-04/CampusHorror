# Setup and implementation plan

Status: documentation prepared; installation and gameplay progress unverified.

## Phase 1 — environment

1. Confirm OS and hardware relevant to installation/rendering.
2. Install stable Godot 4 standard build, Node.js LTS and Git.
3. Create one Godot project and open its folder in Cursor.
4. Save an initial Git checkpoint.
5. Install one local Godot MCP add-on and configure Cursor.
6. Verify read-only project inspection, then a temporary visible test scene.
7. Record exact working versions and add a Cursor project rule.

Completion: the agent can inspect the correct open project and a test scene runs.

## Phase 2 — design agreements

1. Choose overhead versus slightly angled top-down perspective.
2. Choose pixel art versus clean stylized art.
3. Set tile scale, palette, proportions and export settings.
4. Gather campus layout references and assign zone IDs.
5. Create a small custom asset sample.
6. Adopt or revise the proposed blueprint.

Completion: a small compatible asset kit and documented zone/scene conventions exist.

## Phase 3 — working foundation

| Milestone | Deliverable | User check |
|---|---|---|
| A | Player movement, camera, walls | Movement feels usable; collision works |
| B | Reusable interaction | Prompt and action work within range |
| C | Two zones with doors/spawn markers | Travel both ways; one player remains |
| D | Persistent state and test pickup | Pickup stays collected across zones |
| E | Versioned save/load | Restart restores position and state |
| F | Lighting proof | Chosen renderer supports intended night/light visuals |
| G | Small campus patch and one room | Custom art, collision and doors fit together |
| H | Desktop export | Export opens and the basic loop works |

Commit after each checked milestone. Install matching export templates for H.

## Phase 4 — later story and mechanics

After the foundation works, select one mechanic or story beat at a time. Implement only what the next playable scenario needs. No detailed mechanics order is confirmed yet.

Use this content card:

```text
Title:
Zone ID:
Placed objects/characters:
Trigger:
Required flags/items:
Player action:
Outcome:
Persistence requirements:
Existing systems to reuse:
New behavior needed:
Acceptance checks:
```

## Cursor task template

```text
Read project instructions, blueprint and status.
Implement only [task]. Inspect existing scenes first.
Preserve manually placed map objects and use reusable Inspector settings.
Do not add paid dependencies or unrelated systems.
Acceptance criteria: [specific checks].
Run the affected scene and inspect errors.
Report actual checks and remaining manual checks.
Update status and show the diff before the checkpoint commit.
```

## Work not started

Full campus production, completed storyline, enemies, complete puzzle systems, lantern rules, underwater mechanics and final art/audio. Their presence in the idea does not mean they exist in the project.
