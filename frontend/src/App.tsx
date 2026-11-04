import React, { useState } from 'react';
import { ShieldAlert, Cpu } from 'lucide-react';
import { useWebSocket } from './hooks/useWebSocket';
import { Instrument, SignalEvent } from './types';
import { SystemStatus } from './components/SystemStatus';
import { Controls } from './components/Controls';
import { TradingChart } from './components/TradingChart';
import { SignalsPanel } from './components/SignalsPanel';
import { RiskPanel } from './components/RiskPanel';
import { OrdersPanel } from './components/OrdersPanel';
import { PositionsPanel } from './components/PositionsPanel';
import { AuditLog } from './components/AuditLog';

export function App() {
  const {
    connected,
    status,
    setStatus,
    positions,
    orders,
    signals,
    riskDecision,
    auditEvents,
    candlesByInstrument,
    latestQuote,
  } = useWebSocket();

  const [selectedInstrument, setSelectedInstrument] = useState<Instrument>('SYNTH/BTC');
  const [selectedSignal, setSelectedSignal] = useState<SignalEvent | null>(null);

  const handleSelectSignal = (sig: SignalEvent) => {
    setSelectedInstrument(sig.instrument);
    setSelectedSignal(sig);
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col">
      {/* Top Global Simulation Banner & Header */}
      <header className="bg-slate-950/90 border-b border-slate-800 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded bg-sky-500/15 border border-sky-500/30 text-sky-400">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm md:text-base font-bold font-mono tracking-tight text-white">
                MULTI-AGENT TRADING SYSTEM DASHBOARD
              </h1>
              <span className="px-2 py-0.5 text-[10px] font-mono font-bold uppercase bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded">
                MODO SIMULACIÓN — SIN BROKER REAL
              </span>
            </div>
            <p className="text-[11px] font-mono text-slate-400">
              Flujo Determinista: Research → Strategy (SMA Cross) → Risk (20 Reglas) → Execution → Reconciliation
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          {status.emergency_stop && (
            <div className="px-3 py-1 rounded bg-rose-600/25 border border-rose-500 text-rose-300 font-bold flex items-center gap-1.5 animate-pulse">
              <ShieldAlert className="w-4 h-4" />
              INTERRUPTOR DE EMERGENCIA ACTIVO
            </div>
          )}
          <div className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
            DATOS SINTÉTICOS • CREDENCIALES: DESHABILITADAS
          </div>
        </div>
      </header>

      {/* Main Responsive Grid Layout */}
      <main className="flex-1 p-3 lg:p-4 flex flex-col gap-3.5 max-w-[1920px] w-full mx-auto">
        {/* Upper Workspace: Left Sidebar + Center TradingView Chart + Right Panels */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5">
          {/* Left Sidebar (3 cols on xl, 3 on lg) */}
          <div className="lg:col-span-3 flex flex-col gap-3.5">
            <SystemStatus status={status} connected={connected} />
            <Controls
              status={status}
              selectedInstrument={selectedInstrument}
              onSelectInstrument={setSelectedInstrument}
              onStatusChange={setStatus}
            />
          </div>

          {/* Center Area: Live TradingView Lightweight Chart (6 cols on lg) */}
          <div className="lg:col-span-5 xl:col-span-6 min-h-[480px] flex flex-col">
            <TradingChart
              instrument={selectedInstrument}
              candles={candlesByInstrument[selectedInstrument] || []}
              signals={signals}
              selectedSignal={selectedSignal}
              latestQuote={latestQuote[selectedInstrument]}
            />
          </div>

          {/* Right Panel: Signals, Risk, Orders (4 cols on lg, 3 on xl) */}
          <div className="lg:col-span-4 xl:col-span-3 flex flex-col gap-3.5">
            <SignalsPanel
              signals={signals}
              selectedSignal={selectedSignal}
              onSelectSignal={handleSelectSignal}
            />
            <RiskPanel
              decision={riskDecision}
              limits={status.risk_limits}
              emergencyStop={status.emergency_stop}
              onStatusChange={setStatus}
            />
            <OrdersPanel orders={orders} />
          </div>
        </div>

        {/* Bottom Panel: Open Positions with PnL + Real-Time Append-Only Audit Log */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5">
          <div className="lg:col-span-7">
            <PositionsPanel
              positions={positions}
              realizedPnl={status.realized_pnl}
              unrealizedPnl={status.unrealized_pnl}
            />
          </div>
          <div className="lg:col-span-5">
            <AuditLog events={auditEvents} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
