# User constraints and working style

## Confirmed constraints

- The user already has paid Cursor access and ChatGPT Plus, described as the $20 package.
- No additional payments or premium subscriptions are acceptable.
- Additional tools must be genuinely free to use for the intended workflow, without generation credits or a trial that stops after a few uses.
- The user expects Cursor to produce essentially all game code, with very little manual coding.
- The user can design layouts and place assets through drag-and-drop.
- The user cannot create complete visual assets from scratch through traditional drawing.
- The user has made simple Python games but has never developed with a game engine.
- Custom recognizable campus assets are needed; unrelated random web assets do not satisfy that need.
- Detailed game mechanics and story design are postponed until the setup/blueprint is ready.

## Practical implications

Prefer free local software and reproducible scripts. Avoid workflows requiring paid API keys, cloud rendering credits, paid asset generation or extra subscriptions.

Do not equate a free MCP server with free unlimited inference. Cursor's subscription has usage limits. The project can have no additional tool costs, but continuous unlimited cloud AI assistance is not guaranteed. Keep extra usage spending disabled where account settings permit it.

A local AI model could avoid provider quotas, but hardware suitability and quality are unknown. It is an optional later route, not an established solution for this user.

## Suggested teaching style

Use ordered steps, concrete completion checks and copyable Cursor prompts. Teach only enough Godot concepts to enable layout, inspection and testing: scene, node, resource, script, signal, collision, camera and TileMapLayer.

The user does not want a full traditional programming course as a prerequisite. Nevertheless, they must be able to judge what the agent built and report problems.

## Scope discipline

Do not implement every mentioned mechanic at setup time. Establish reusable connections, then implement each behavior in a bounded milestone. AI assistance does not eliminate testing or the learning involved in operating the engine.
