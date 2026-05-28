# CBT Framework — Claude Code Guide

CBT Framework is a Node.js + Python backtesting system for trading strategies, operated through Claude Code slash commands. This project uses the Superpowers skills framework.

## Superpowers Skills

This project has the Superpowers plugin installed. At the start of every conversation, invoke the `using-superpowers` skill to load the skill-selection methodology before taking any action.

Available skills:

| Skill | When to use |
|---|---|
| `using-superpowers` | Meta-skill: load at start of every conversation |
| `brainstorming` | Before building any new feature or command |
| `writing-plans` | Create step-by-step plans from approved designs |
| `executing-plans` | Execute written plans in a separate session |
| `subagent-driven-development` | Execute plans with fresh subagent per task + review |
| `dispatching-parallel-agents` | Run 2+ independent tasks in parallel |
| `test-driven-development` | Red-green-refactor for all new code |
| `systematic-debugging` | Root cause investigation before any fix |
| `verification-before-completion` | Evidence before any completion claim |
| `requesting-code-review` | Request review before merging |
| `receiving-code-review` | Handle review feedback with technical rigor |
| `finishing-a-development-branch` | Structured branch completion (merge/PR/discard) |
| `using-git-worktrees` | Isolated workspace before executing plans |
| `writing-skills` | Author new reusable skills |

## Project Structure

```
commands/cbt/     — 22 slash command specs (/cbt:build, /cbt:run, etc.)
agents/           — 4 AI agent definitions (cbt-analyzer, cbt-builder, cbt-eda, cbt-researcher)
hooks/            — Claude Code hooks
bin/cbt-init.js   — npm installer (npx cbt-framework)
engine/           — Python backtest engine (metrics, Sharpe, Sortino, etc.)
templates/        — Strategy, config, and live trading templates
  standard/       — pandas-based (default, <1M rows)
  fast/           — Polars + NumPy + Numba (1M+ rows)
  live/           — Exchange bots (Bybit, Binance, Kraken, Hyperliquid)
  presets/        — Conservative/aggressive config presets
references/       — Reference docs (metrics, strategy types, MCP setup)
skills/           — Superpowers skill files
.claude-plugin/   — Plugin registration
```

## Key Slash Commands

| Command | Purpose |
|---|---|
| `/cbt:new <name>` | Create a new strategy |
| `/cbt:discover` | Define strategy edge via Q&A |
| `/cbt:research` | Research and validate the edge |
| `/cbt:eda` | Exploratory data analysis |
| `/cbt:build` | Generate strategy code |
| `/cbt:run` | Execute backtest |
| `/cbt:analyze` | Quick analysis |
| `/cbt:deep-analyze` | Forensic analysis |
| `/cbt:optimize` | Parameter sweep / walk-forward |
| `/cbt:iterate` | Guided improvement loop |
| `/cbt:report` | Auto-generate report |
| `/cbt:live` | Deploy to exchange |

## Development Conventions

- **Python 3.8+, Node.js 16+**
- Fast engine path uses Polars + NumPy + Numba — no pandas in hot path
- All credentials in `.env`, never hardcoded
- Paper trading is the default for live deployments
- One change per iteration when optimizing strategies
- Always `.shift(1)` indicators to prevent lookahead bias
- No automated test suite — validate by running a backtest and verifying output metrics

## Branch Workflow

- Active development branch: `claude/what-is-this-3XooA`
- Main branch: `main`
- Remote: `origin` (GitHub — Rohan273273273/cbt-framework)
