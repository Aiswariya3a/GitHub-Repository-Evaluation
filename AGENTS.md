# AI Source Attribution

This project was developed with assistance from AI tools as part of the GSD workflow system.

## AI Tools Used

| Tool | Role | Configuration |
|------|------|---------------|
| OpenCode (deepseek-v4-flash-free) | GSD orchestrator, code generation | Planning, execution, test generation, documentation |
| gsd-executor subagent | Plan execution | Task-level code generation under orchestrator supervision |

## How AI Was Used

- **GSD workflow orchestration** — project planning, phase management, state tracking
- **Code generation** — evaluation pipeline agents (Ollama client, BaseAgent, capability agents, orchestrator, tests)
- **Documentation generation** — planning artifacts (STATE.md, ROADMAP.md, SUMMARY.md), VERIFICATION.md files
- **Test generation** — 102 unit tests across 6 test files

## Review Process

All AI-generated code was reviewed and validated by a human developer. All automated tests pass without AI inference.
