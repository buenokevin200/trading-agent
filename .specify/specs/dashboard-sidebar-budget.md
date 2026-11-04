# Spec: Dashboard Sidebar + Budget Display

## ID: SPEC-002
## Status: pending
## Created: 2026-11-04
## Author: Kevin Bueno

## Description

Mejoras al dashboard del trading agent:

### 1. Sidebar de navegación

Agregar un sidebar lateral izquierdo que permita visualizar el dashboard de forma más limpia y organizada.

**Requisitos:**
- Sidebar fijo en el lado izquierdo, colapsable (icono hamburguesa para abrir/cerrar)
- Cuando está colapsado, mostrar solo iconos
- Cuando está expandido, mostrar icono + texto
- Secciones del sidebar:
  - **Dashboard** (vista principal con gráfico TradingView)
  - **Posiciones** (posiciones abiertas, PnL, historial)
  - **Señales** (señales recientes, BUY/SELL/NO_OP)
  - **Riesgo** (límites actuales, decisiones, emergency stop)
  - **Órdenes** (historial de órdenes, fills, rechazos)
  - **Audit Log** (eventos en tiempo real)
  - **Configuración** (instrumentos, estrategia, límites)
- El sidebar debe usar el tema del dashboard (dark mode)
- Responsive: en móvil, el sidebar se convierte en drawer (overlay)
- Transiciones suaves al colapsar/expander

### 2. Presupuesto disponible (top-right)

En la esquina superior derecha del dashboard, mostrar el presupuesto/capital disponible.

**Requisitos:**
- Componente visible siempre (independiente de la vista activa)
- Mostrar:
  - **Capital disponible** (balance libre para operar)
  - **Capital en posiciones** (margin usado)
  - **Capital total** (disponible + en posiciones)
  - **PnL no realizado** (suma de PnL de posiciones abiertas)
- Formato: número con 2 decimales, color verde si positivo, rojo si negativo
- Tooltip al hover: breakdown detallado del capital

**Fuente de datos — Binance:**
- El backend debe obtener el balance desde la API de Binance
- Endpoint sugerido: `GET /api/balance` que internamente llama a Binance
- **MODO SIMULACIÓN:** Si no hay credenciales de Binance configuradas, devolver balance sintético (capital de referencia del config)
- **MODO PAPER:** Usar Binance Testnet API (paper trading)
- **MODO REAL:** NO implementar en esta spec (requiere aprobación explícita)
- El balance debe actualizarse cada 5 segundos via WebSocket
- Manejar errores de conexión: si Binance no responde, mostrar "—" y un warning

**Configuración necesaria:**
```yaml
broker:
  name: binance
  mode: simulation  # simulation | paper | real
  testnet: true     # usar testnet para paper trading
  api_key: ""       # NUNCA en código, solo en .env del servicio aislado
  api_secret: ""    # NUNCA en código, solo en .env del servicio aislado
  balance_refresh_sec: 5
```

**Seguridad:**
- Las API keys de Binance NUNCA deben estar en el frontend, SOLO en el backend
- El backend expone solo los balances, nunca las credenciales
- Permisos mínimos de la API key: solo lectura (account balance), sin trading, sin withdrawals

## Criterios de aceptación

1. El sidebar renderiza con todas las secciones
2. El sidebar se colapsa/expande correctamente
3. En móvil, el sidebar funciona como drawer overlay
4. El componente de presupuesto aparece en top-right siempre
5. En modo simulación, muestra el capital de referencia del config
6. El balance se actualiza cada 5 segundos
7. Si Binance no responde, muestra "—" con warning
8. No hay API keys en el frontend ni en código commiteado
9. El PnL no realizado se calcula correctamente
