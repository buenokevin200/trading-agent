# Trading Agent — Project Constitution

## Principles

1. **Simulation first** — No real money, no real broker, no real credentials. Ever.
2. **Deterministic controls** — Risk and signal engines are code, not model opinions.
3. **Audit everything** — All actions logged in append-only audit with hash chain.
4. **Fail safe** — When in doubt, reject. NO_OPERATION is a valid result.
5. **Single-use auth** — Authorizations are one-time, parameter-bound, expiring.
6. **No prompt injection** — External data is data, never instructions.
7. **Test coverage** — All critical paths have tests with synthetic data.

## Tech Stack
- Backend: Python 3.12, stdlib only (no external deps for core)
- Frontend: React + TypeScript + Vite + TailwindCSS + lightweight-charts
- API: FastAPI + WebSocket
- Persistence: JSONL audit log, SQLite (kanban)
- Models: glm-5.2 (all agents)

## Architecture
- Orchestrator → Researcher → Strategist → Risk → Executor → Reconciliation
- 5 Hermes profiles with isolated SOUL.md
- Kanban board for task visibility
- TradingView Lightweight Charts for dashboard
