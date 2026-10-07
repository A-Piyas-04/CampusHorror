# Decision register and open questions

Snapshot: 7 October 2026.

## Confirmed by the user

| Topic | Decision |
|---|---|
| Engine | Godot |
| Game view | 2D top-down |
| Setting | A personally known university campus |
| Areas | Fields, buildings, hallways, rooms, underground, underwater, small hospital |
| Planned features | Day/night, enemies, puzzles, lantern, mystery, multiple scenes |
| Coding method | Heavy reliance on Cursor Agent; minimal manual coding |
| Other AI support | Existing ChatGPT Plus subscription |
| User activity | Design/layout and placing assets |
| Art constraint | Cannot draw all complete assets from scratch |
| Additional costs | No extra paid tools, subscriptions or quota-based generation pipeline |
| Current priority | Setup and blueprint before detailed story/mechanics |

## Proposed by the assistant; not explicitly adopted

- Godot standard build with typed GDScript.
- Compatibility renderer for the initial 2D prototype.
- One `tomyud1/godot-mcp` integration with Node.js.
- Persistent player owned by Main, with interchangeable zone scenes.
- Small GameState and SaveService autoloads.
- Inspector-configurable doors, interactions and content IDs.
- SVG placeholders and scripted Blender renders for custom assets.
- Pixelorama/Krita for adjustments.
- Git checkpoints and documented acceptance checks.
- 32 × 32 tiles if the user chooses pixel art.

## Ask when relevant to the next step

1. Which computer/OS will run Godot and Cursor? No OS is confirmed for this project.
2. What GPU/RAM is available, if discussing Blender performance or local AI?
3. Straight overhead or angled top-down?
4. Pixel art, stylized vector-like art, or rendered 2D sprites?
5. Which campus, and what references can the user provide?
6. Which small outdoor area/interior should be the prototype?
7. Desktop-only release or eventual mobile/web support?
8. What should the lantern do beyond illumination?
9. Will enemies involve avoidance, combat, or another interaction?
10. Is time continuous, event-driven, or chapter-controlled?

Do not ask all of these before helping with basic installation. Gather decisions as their consequences become relevant.

## Update policy

Move a recommendation to Confirmed only after the user adopts it. Record a feature as Verified only after actual test evidence. Retain the difference between planned scope and implemented scope.

Do not fabricate a game title, campus identity, plot or implementation status. `CampusMystery` and hospital puzzle examples are placeholders, not user-approved names or story facts.
