# Proposed technical blueprint

This architecture is a recommendation. No scenes or scripts described here have been implemented or tested.

## Engine direction

Godot 4 standard build, GDScript, 2D top-down. Start with a stable version and record/pin it during the first prototype. Compatibility renderer is a proposed starting point; confirm lighting and target hardware before finalizing.

## Scene ownership

- `Main.tscn` owns a world container, a single persistent player and UI.
- Each zone is a separate scene placed into the world container.
- Changing zones replaces the zone and moves the existing player to a named spawn marker.
- Zones contain terrain, scenery, spawn markers and placed interactive objects, not their own duplicate player.
- Zone changes preserve shared inventory, flags and world time.

Campus exteriors may be split into connected zones when necessary. Seamless streaming is not required for the initial foundation.

## Reusable units

| Unit | Configuration |
|---|---|
| Zone | Stable zone ID, environment/lighting profile |
| Door | Destination zone ID, spawn ID, optional required flag |
| Spawn marker | ID unique within its zone |
| Interactable | Prompt and local behavior |
| Clue/pickup | Content ID and persistent object ID |
| Puzzle, later | Puzzle ID, prerequisites and completion flag |
| Enemy spawner, later | Enemy definition and activation conditions |

Inspector properties should let the user arrange and configure instances without editing code.

## Persistent state

Start with a small `GameState` autoload for inventory IDs, story flags and world time. Use a `SaveService` autoload for reading/writing versioned saves to `user://`. Transition ownership can remain in Main's controller initially.

Save contract: format version, current zone/spawn, player position, inventory, flags, time and persistent object states. Loading restores saved position; a door transition uses its configured spawn marker.

Use stable IDs rather than transient node paths. A collected clue should remain collected after leaving its zone and restarting the game.

## Connection points for later mechanics

| Mechanic | Reserved foundation |
|---|---|
| Day/night | Persistent clock and per-zone lighting profile |
| Lantern | Player attachment point and input action |
| Enemies | Collision conventions and spawn IDs |
| Puzzles | Interaction interface and story flags |
| Mystery | Clue IDs, dialogue/content data |
| Underground | Separate zone and local lighting profile |
| Underwater | Environment profile; later swimming/oxygen behavior |

Godot lighting nodes provide visuals. Enemy perception and light-sensitive puzzle rules require explicit gameplay implementation.

## Suggested organization

- `assets/source/`: editable original assets.
- `assets/sprites/`, `assets/tiles/`, `assets/audio/`: game-ready assets.
- `scenes/core/`, `scenes/player/`, `scenes/components/`: shared foundation.
- `scenes/world/`, `scenes/ui/`, `scenes/tests/`: areas, interface and test rooms.
- `scripts/core/`, `scripts/components/`: reusable code.
- `data/zones/`, `data/items/`, `data/story/`: content definitions.
- `docs/`: canonical project memory.

## Example content relationship

A future hospital puzzle sets `hospital_power_restored`. Doors, dialogue and lights can read that flag without embedding the puzzle's internal logic. This is an example, not a confirmed story event.
