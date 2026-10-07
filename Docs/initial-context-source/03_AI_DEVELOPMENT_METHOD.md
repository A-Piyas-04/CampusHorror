# Proposed AI-assisted development method

Everything in this file is a recommendation unless also recorded as confirmed in the decisions file.

## Division of work

| Participant/tool | Responsibility |
|---|---|
| User | Campus references, map layout, ideas, visual approval and playtesting |
| ChatGPT | Planning, explanations, blueprint review, asset specifications and Cursor prompts |
| Cursor Agent | GDScript, scene files, reusable systems, integration and debugging |
| Godot editor | Visual placement, scene inspection and running the game |
| Local Godot MCP | Allow the agent to inspect/control supported editor operations |
| Free art tools | Edit or generate reproducible custom asset sources |

The shipped game should run independently of ChatGPT, Cursor and the MCP. These are development tools, not runtime requirements.

## Working loop

1. Read project documentation and current status.
2. Choose one small task with acceptance criteria.
3. Have Cursor inspect existing files and propose a bounded change.
4. Implement through scripts/files and available MCP operations.
5. Run the affected scene and inspect engine errors.
6. User checks layout, controls and visual result.
7. Fix the task, update status and review the diff.
8. Commit a working checkpoint in Git.

Do not simultaneously edit the same scene in Cursor and unsaved Godot editor tabs. Save and coordinate reloads.

## Proposed initial integration

Use one community integration: `tomyud1/godot-mcp`, listed as **Godot AI Assistant tools MCP**. Install its editor add-on and connect its local Node.js server to Cursor. Confirm actual available tools and compatibility rather than relying on advertised tool counts.

References: https://github.com/tomyud1/godot-mcp and https://cursor.com/docs/mcp

If MCP is unavailable, continue with Cursor editing project files, manually run in Godot and report exact errors/screenshots. The project's architecture should not depend on MCP availability.

## Custom asset method

1. Record a fixed perspective, palette, scale and export convention.
2. Produce a sample kit before expanding production.
3. Use agent-written SVG shapes for simple stylized placeholders or assets.
4. Use agent-written Blender Python scripts for geometric custom buildings, rendered with a consistent orthographic camera.
5. Use Pixelorama for pixel artwork adjustments, or Krita for larger raster edits.
6. Place repeated terrain through tiles and distinctive objects through reusable scenes.

Do not promise that SVG output is polished pixel art. Do not promise exact architecture from photos alone. The user must supply approximate footprints/proportions and inspect results.

Cloud image generation may help with references but cannot be the required production pipeline under the user's quota constraint. Local image generation is optional and hardware-dependent.

## Agent context

Keep a short always-applied Cursor project rule plus canonical docs for setup, blueprint, art style, campus zones, content and status. Update documents after decisions so a new agent chat can continue reliably.
