# Multi-Agent Trading System Dashboard (SIMULACIÓN SINTÉTICA)

Dashboard full-stack en tiempo real para visualizar y operar el sistema multiagente de trading en **modo simulación local** (`Research → Strategy → Risk → Execution → Reconciliation`).

> **IMPORTANTE**: Todo el flujo utiliza **datos sintéticos** y un **simulador determinista local**. No existen credenciales reales ni conexión a ningún broker real.

---

## Arquitectura y Estructura

```text
trading-dashboard/
├── trading-system/          # Motor multiagente Python stdlib (fallback si /home/champa/trading-system no está montado)
│   └── src/
│       ├── orchestrator.py
│       ├── engines/
│       │   ├── signal_engine.py
│       │   └── risk_engine.py
│       ├── services/
│       │   ├── simulator.py
│       │   ├── data_adapter.py
│       │   └── audit.py
│       └── schemas/
├── backend/                 # FastAPI + WebSocket (/ws) + Background Cycle Runner (Puerto 8000)
│   ├── main.py
│   ├── ws_manager.py
│   ├── cycle_runner.py
│   └── requirements.txt
├── frontend/                # React + TypeScript + Vite + TailwindCSS + TradingView Lightweight Charts (Puerto 5173)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── TradingChart.tsx
│   │   │   ├── SignalsPanel.tsx
│   │   │   ├── RiskPanel.tsx
│   │   │   ├── PositionsPanel.tsx
│   │   │   ├── OrdersPanel.tsx
│   │   │   ├── AuditLog.tsx
│   │   │   ├── SystemStatus.tsx
│   │   │   └── Controls.tsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   └── main.tsx
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── .env
├── docker-compose.yml
└── README.md
```

---

## Ejecución Rápida

### 1. Backend (FastAPI + WebSocket — Puerto 8000)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

El backend busca automáticamente `/home/champa/trading-system/src/` (configurable mediante `TRADING_SYSTEM_PATH`) y, si no existe en el host actual, utiliza `./trading-system/src/`.

### 2. Frontend (React + Vite + Lightweight Charts — Puerto 5173)

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173` en tu navegador.
