# ManageSim

Discord-based multi-agent management system. Each project gets its own channel with OpenClaw bots backed by agent teams. A central Asset Base manages all knowledge across a 4-level hierarchy.

## Architecture

```
Server (Discord) → Department (Channel) → Team (Bot) → Agent (Worker)
```

**Key components:**
- **Gateway** — OpenClaw Discord interface with personal assistant + project bots
- **Pipeline** — Edict-inspired task state machine with enforced transitions, review gates, permission matrix
- **Knowledge** — Easybase + Mem0 unified store with provenance and visibility filtering
- **Asset Base** — Comprehensive knowledge hub (tasks, skills, agents, stats) via FastAPI
- **Evolution** — Evolver-inspired agent evolution (Genes, PersonalityState, Capsule sharing)
- **Creators** — Easy department/agent creation via Discord commands
- **Skills** — Online skill discovery from curated repos + ClawHub

## Quick Start

```bash
# 1. Install dependencies
make setup

# 2. Create personal config (Discord IDs, API keys)
./scripts/init-personal.sh

# 3. Edit your config
$EDITOR config/managesim.yaml
$EDITOR .env

# 4. Bootstrap Easybase hierarchy
./scripts/init-hierarchy.sh

# 5. Start services
docker-compose up
```

## Config

- `config/managesim.example.yaml` — Template (generic, no personal data)
- `config/managesim.yaml` — Your config (gitignored)
- `config/pipelines/` — Task pipeline definitions
- `config/templates/` — Team templates

## Pipeline CLI

```bash
# Create task
python -m pipeline.cli create --project my-app --title "Build login page"

# Transition state (validated)
python -m pipeline.cli transition TASK-001 Triage "Initial triage"

# Report progress
python -m pipeline.cli progress TASK-001 "Working on auth" "1.Design:done|2.Implement:active|3.Test"

# Complete task
python -m pipeline.cli done TASK-001 "Login page implemented with OAuth"
```

## Manual Steps

1. Create Discord channels (one per project + `#asset-base` + `#logs`)
2. Create Discord bots (personal assistant + one per project + asset base)
3. Copy Guild ID and Channel IDs to `config/managesim.yaml`
4. Set bot tokens in `.env`

## License

MIT
