# Prompt para Antigravity: Dashboard web del sistema multiagente de trading

## Contexto

Existe un sistema multiagente de trading en `/home/champa/trading-system/` (Python 3.12, solo stdlib). Opera en modo **simulación** — no hay dinero real ni broker real. El sistema tiene:

- **Orquestador** (`src/orchestrator.py`) con método `run_cycle(instrument)` que ejecuta: Research → Strategy → Risk → Execution → Reconciliation
- **Simulador** (`src/services/simulator.py`) con precios sintéticos, posiciones, órdenes y PnL
- **Motor de señales** (`src/engines/signal_engine.py`) con estrategia SMA cross que produce señales BUY/SELL/NO_OPERATION con `entry_price`, `stop_loss`, `take_profit`
- **Motor de riesgo** (`src/engines/risk_engine.py`) que aprueba/rechaza con 20 códigos de rechazo
- **Audit log** (`src/services/audit.py`) append-only con hash chain
- **DataAdapter** (`src/services/data_adapter.py`) que genera observaciones sintéticas con precio, bid, ask, volume, timestamp
- **Esquemas** (`src/schemas/`) para Observation, Signal, RiskDecision, OrderEvent, Position, Intent, Authorization, Incident

### API disponible del backend (Python)

```python
# Orchestrator
orch.run_cycle(instrument="SYNTH/BTC") -> dict  # ejecuta un ciclo completo
orch.get_status() -> dict  # cycle_count, paused, positions, realized_pnl, total_orders, emergency_stop, limits_configured
orch.pause() / orch.resume()

# Simulator
sim.get_price(instrument) -> float
sim.positions -> list[Position]  # instrument, side, quantity, entry_price, current_price, unrealized_pnl, is_protected
sim.realized_pnl -> float
sim.reconcile() -> dict  # positions, realized_pnl, total_orders, filled_orders, rejected_orders
sim.check_protection() -> list[(instrument, "stop_loss_hit"|"take_profit_hit")]

# Signal engine
signal_engine.evaluate(observations, task_id) -> Signal  # signal_type, entry_price, stop_loss, take_profit, rules_triggered

# Data adapter
data.fetch(instrument) -> Observation  # price, bid, ask, volume, observed_at, quality

# Audit
audit.read_all() -> list[dict]  # timestamp, event_type, agent, data
```

## Objetivo

Construir una **aplicación web full-stack** que sirva como dashboard de visualización del sistema de trading. Debe cumplir:

### 1.@ Backend: API WebSocket + REST

Crear un servidor (FastAPI o Flask) en `/home/champa/trading7-dashboard/backend/` que:

- **Importe y use** el sistema existente en `/home/champa/trading-system/src/`
- Exponga endpoints REST:
  - `GET /api/status` → estado del sistema (posiciones, PnL, cycle_count, emergency_stop)
  - `GET /api/positions` → posiciones abiertas con entry_price, current_price, unrealized_pnl, stop_loss, take_profit
  - `GET /api/orders` → historial de órdenes (filled, rejected, pending)
  - `GET /api/signals` → señales recientes con entry_price, stop_loss, take_profit, signal_type
  - `GET /api/audit` → últimos N eventos del audit log
  - `POST /api/cycle` → ejecutar un ciclo manualmente
  - `POST /api/pause` / `POST /api/resume` → pausar/reanudar
  - `POST /api/emergency-stop` → activar interruptor de emergencia
- Exponga **WebSocket** `/ws` que emita en tiempo real:
  - `price_update` → {instrument, price, bid, ask, volume, timestamp} cada vez que el data adapter genera una observación
  - `signal` → {signal_type, instrument, entry_price, stop_loss, take_profit, rules_triggered} cuando se genera una señal
  - `risk_decision` → {approved, rejection_code, rejection_reason} cuando el motor de riesgo evalúa
  - `order_fill` → {order_id, instrument, side, quantity, fill_price, commission, status} cuando se ejecuta una orden
  - `position_update` → posiciones actuales con PnL no realizado
  - `cycle_complete` → resumen del ciclo
- El backend debe correr un **loop de ciclos** en background (configurable, default 5 segundos) que llama `orch.run_cycle()` y emite eventos por WebSocket
- Persistencia: usar el audit log existente (`data/audit.jsonl`)
- **Sin secretos, sin credenciales reales, sin broker real**

### 2.@ Frontend: Dashboard con TradingView

Crear el frontend en `/home/champa/trading-dashboard/frontend/` (React + TypeScript + Vite + TailwindCSS) que tenga:

#### Layout principal
- **Sidebar izquierdo**: estado del sistema (cycle_count, paused, emergency_stop, limits_configured, realized_pnl)
- **Área central**: gráfico de TradingView en vivo
- **Panel derecho**: señales recientes, decisiones de riesgo, órdenes
- **Bottom panel**: posiciones abiertas con PnL, audit log en tiempo real

#### Gráfico de TradingView en vivo
- Usar **TradingView Charting Library** (o Lightweight Charts como alternativa gratuita) embebida
- El gráfico debe mostrar:
  - **Velas/candlesticks** en tiempo real alimentadas por los datos sintéticos del simulador (precio, bid, ask, volume)
  - **Marcadores visuales** en los puntos donde se esperan entradas:
    - 🟢 Marcador verde con etiqueta "BUY" en el `entry_price` cuando hay una señal BUY
   678- 🔴 Marcador rojo con etiqueta "SELL" en el `entry_price` cuando hay una señal SELL
 "   - 🟡 Marcador amarillo con etiqueta "NO_OP" cuando no hay operación
  - **Líneas horizontales** para `stop_loss` (rojo punteado) y `take_profit` (verde punteado) de la señal activa
  - **Zona sombreada** entre stop_loss y take_profit mostrando el rango de la operación
  - Los datos llegan por WebSocket en tiempo real y se actualizan sin recargar
  - Si no hay datos reales de mercado, mostrar claramente "DATOS SINTÉTICOS — SIMULACIÓN" como watermark

#### Panel de señales
- Lista de últimas señales con: timestamp, instrumento, tipo (BUY/SELL/NO_OP), entry_price, stop_loss, take_profit, rules_triggered
- Click en una señal → centra el gráfico en ese punto

#### Panel de riesgo
- Última decisión: aprobado/rechazado, código de rechazo, razón
- Límites actuales: risk_per_trade, max_exposure, max_daily_loss, max_drawdown, max_positions
- Interruptor de emergencia con botón de activación (requiere confirmación)

#### Panel de posiciones
- Tabla con: instrumento, side (LONG/SHORT), quantity, entry_price, current_price, unrealized_pnl, is_protected
- PnL total (realizado + no realizado) en grande con color verde/rojo
- Si una posición no tiene protección (is_protected = false), mostrar warning

#### Panel de órdenes
- Historial con: order_id, instrument, side, quantity, status (filled/rejected/pending), fill_price, commission, timestamp
- Filtrar por status

#### Audit log en tiempo real
- Últimos 20 eventos del audit log
- Cada evento: timestamp, event_type, agent, data (resumido)
- Auto-scroll, pausable

#### Controles
- Botón "Ejecutar ciclo" (manual)
- Botón "Pausar" / "Reanudar"
- Botón "Emergency Stop" (con confirmación modal)
- Selector de instrumento (SYNTH/BTC, SYNTH/ETH)
- Slider de frecuencia del ciclo (1-60 segundos)

### 3.@ Integración TradingView

Usar **lightweight-charts** (https://tradingview.github.io/lightweight-charts/) — es gratuito y open source de TradingView:

```bash
npm install lightweight-charts
```

Features necesarias:
- `chart.addCandlestickSeries()` para velas OHLC
- `series.setMarkers()` para los puntos de entrada (BUY/SELL)
- `series.createPriceLine()` para stop_loss y take_profit
- Datos en tiempo real via `series.update()` con datos del WebSocket
- Volume en serie separada

### 4.@ Configuración

- Backend: puerto 8000 (FastAPI + uvicorn)
- Frontend: puerto 5173 (Vite dev server), proxy a 8000 para /api y /ws
- Docker Compose opcional para producción
- `.env` con `BACKEND_URL`, `WS_URL`, `CYCLE_FREQUENCY_SEC=5`

### 5.@ Restricciones

- **No inventar datos de mercado reales** — todo es sintético, debe verse claramente etiquetado
- **No conectar broker real** — el sistema es simulación
- **No incluir credenciales** en ningún archivo
- El frontend debe ser responsive (desktop-first, pero funcional en tablet)
- Usar TailwindCSS para styling
- Código limpio, tipado con TypeScript

### 6.@ Estructura de archivos esperada

```
/home/champa/trading-dashboard/
├── backend/
│   ├── main.py          # FastAPI app
│   ├── ws_manager.py    # WebSocket manager
│   ├── cycle_runner.py  # Background cycle loop
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── TradingChart.tsx    # TradingView lightweight-charts
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
├── docker-compose.yml
└── README.md
```

### 7.@ Criterios de aceptación

1. El backend importa y usa el sistema existente en `/home/champa/trading-system/src/`
2. El WebSocket emite eventos en tiempo real cuando se ejecutan ciclos
3. El gráfico de TradingView muestra velas en vivo con datos sintéticos
4. Los marcadores de entrada (BUY/SELL) aparecen en el gráfico cuando hay señales
5. Las líneas de stop_loss y take_profit se dibujan correctamente
6. El panel de posiciones muestra PnL en tiempo real
7. El audit log se actualiza en tiempo real
8. Los controles (pausa, ciclo manual, emergency stop) funcionan
9. Todo está claramente etiquetado como SIMULACIÓN
10. No hay credenciales ni broker real en ningún lugar
