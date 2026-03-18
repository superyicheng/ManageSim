# ManageSim — AI Development Guide

## Project Overview
ManageSim is a Discord-based multi-agent management system. Each project gets its own Discord channel with OpenClaw bots backed by agent teams. A central Asset Base manages knowledge across a 4-level hierarchy: Server → Department → Team → Agent.

## Architecture
- **gateway/** — OpenClaw Discord gateway (Node.js/TypeScript)
- **pipeline/** — Edict-inspired task pipeline with enforced state machine (Python)
- **knowledge/** — Easybase + Mem0 unified knowledge bridge (Python)
- **asset_base/** — Comprehensive knowledge hub API (Python/FastAPI)
- **evolution/** — Evolver-inspired agent evolution system (Node.js)
- **creators/** — Easy department/agent creation (Python)
- **skills/** — Online skill/tool discovery (Python)
- **orchestrator/** — Paperclip + Ruflo bridge (Node.js/TypeScript)
- **tools/** — External tool integrations (Python)

## Key Patterns
- All task operations go through `managesim-task` CLI (`pipeline/cli.py`)
- Every Easybase chunk carries provenance: `stored_by`, `visibility`, `channel_origin`
- Visibility levels: public (default) > project > team > agent > private
- State machine transitions are code-enforced (invalid transitions rejected)
- Agent soul.md/CLAUDE.md stored as Easybase chunks at appropriate tree_path

## Config
- `config/managesim.example.yaml` — template (generic, no personal data)
- `config/managesim.yaml` — personal config (gitignored)
- Pipeline definitions in `config/pipelines/*.yaml`

## Testing
```bash
python3 scripts/health-check.py          # Validate config
python3 -m pytest pipeline/ -v           # Pipeline tests
managesim-task create --project test --title "Test task"
```
