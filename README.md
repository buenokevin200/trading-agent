# Trading Agent

Multi-agent trading system with simulation, risk management, and dashboard.

## Mode: SIMULATION ONLY
No real money, no real broker, no real credentials.

## Structure
- `src/` — Core system (schemas, engines, services, orchestrator)
- `tests/` — 16 automated tests (all passing)
- `config/` — Example configuration (no secrets)
- `profiles/` — 5 SOUL.md for Hermes agent profiles
- `docs/` — Documentation, threat model, acceptance report
- `demo.py` — End-to-end synthetic demonstration

## Agents (all glm-5.2)
- trading-orchestrator — coordinates the flow
- trading-researcher — fetches data with provenance
- trading-strategist — evaluates signals deterministically
- trading-risk — reviews with veto power
- trading-executor — executes authorized intents

## Quick Start
```bash
python3 tests/test_all.py   # 16/16 tests
python3 demo.py             # synthetic demo
```

## Pending Decisions
- Market and broker/exchange
- Instruments, currency, reference capital
- Quantifiable strategy
- Risk limits (per trade, exposure, daily loss, drawdown)
- Timezone and daily cutoff
- Alert channel
