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

## Install

One line to download and set up ManageSim:

```bash
curl -sSL https://raw.githubusercontent.com/superyicheng/ManageSim/main/scripts/install-managesim | bash
```

Or install to a specific directory:

```bash
curl -sSL https://raw.githubusercontent.com/superyicheng/ManageSim/main/scripts/install-managesim | bash -s ~/projects
```

This clones the repo, installs all dependencies, and adds the `update-managesim` command to your PATH.

## Update

One line to update ManageSim to the latest version (run from anywhere):

```bash
update-managesim
```

This pulls the latest code, updates dependencies, and re-initializes the hierarchy. Your personal config (`config/managesim.yaml`), API keys (`.env`), and stored data (`data/`) are never touched.

## Quick Start

After installing:

```bash
cd ~/ManageSim

# 1. Create personal config (Discord IDs, API keys)
./scripts/init-personal.sh

# 2. Edit your config
$EDITOR config/managesim.yaml
$EDITOR .env

# 3. Bootstrap Easybase hierarchy
./scripts/init-hierarchy.sh

# 4. Start services
docker-compose up
```

## Department Structure

Every project channel gets 5 teams automatically:

```
Leader (Main Team) — builds the work
├── QA Team            — validates individual deliverables
├── Error-Learning     — traces root causes, stores lessons
├── Test Team          — writes & runs full test plans (integration, regression, e2e)
└── Error Feedback     — collects reports from all teams, tracks patterns, ensures fixes
```

Each team has auto-created lead agents. Leaders receive a **Leader Guide** with the project structure, decision framework, communication standards, and first actions checklist.

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
