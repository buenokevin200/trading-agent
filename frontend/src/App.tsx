import React, { useState } from 'react';
import { ShieldAlert, Cpu, Menu } from 'lucide-react';
import { useWebSocket } from './hooks/useWebSocket';
import { Instrument, SidebarSection, SignalEvent } from './types';
import { Sidebar } from './components/Sidebar';
import { BudgetDisplay } from './components/BudgetDisplay';
import { SystemStatus } from './components/SystemStatus';
import { Controls } from './components/Controls';
import { TradingChart } from './components/TradingChart';
import { SignalsPanel } from './components/SignalsPanel';
import { RiskPanel } from './components/RiskPanel';
import { OrdersPanel } from './components/OrdersPanel';
import { PositionsPanel } from './components/PositionsPanel';
import { AuditLog } from './components/AuditLog';
import { ConfigPanel } from './components/ConfigPanel';

export function App() {
  const {
    connected,
    status,
    setStatus,
    balance,
    fetchBalance,
    positions,
    orders,
    signals,
    riskDecision,
    auditEvents,
    candlesByInstrument,
    latestQuote,
  } = useWebSocket();

  const [activeSection, setActiveSection] = useState<SidebarSection>('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const [selectedInstrument, setSelectedInstrument] = useState<Instrument>('SYNTH/BTC');
  const [selectedSignal, setSelectedSignal] = useState<SignalEvent | null>(null);

  const handleSelectSignal = (sig: SignalEvent) => {
    setSelectedInstrument(sig.instrument);
    setSelectedSignal(sig);
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex">
      {/* Left Collapsible Navigation Sidebar (SPEC-002) */}
      <Sidebar
        activeSection={activeSection}
        onSelectSection={setActiveSection}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((prev) => !prev)}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
        counts={{
          positions: positions.length,
          signals: signals.length,
          orders: orders.length,
          audit: auditEvents.length,
          emergencyStop: status.emergency_stop,
        }}
      />

      {/* Main Content Wrapper with smooth margin transition matching sidebar state */}
      <div
        className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ease-in-out ${
          sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'
        }`}
      >
        {/* Top Global Header with Always-Visible BudgetDisplay on Top-Right */}
        <header className="sticky top-0 z-30 bg-slate-950/95 backdrop-blur border-b border-slate-800 px-3 lg:px-5 py-2.5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            {/* Mobile Hamburger Button to open Drawer */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Abrir menú de navegación"
              className="lg:hidden p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 cursor-pointer"
            >
              <Menu className="w-5 h-5" />
            </button>

            <div className="hidden sm:flex p-1.5 rounded bg-sky-500/15 border border-sky-500/30 text-sky-400">
              <Cpu className="w-5 h-5" />
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-sm md:text-base font-bold font-mono tracking-tight text-white">
                  MULTI-AGENT TRADING SYSTEM
                </h1>
                <span className="px-2 py-0.5 text-[10px] font-mono font-bold uppercase bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded">
                  MODO {status.mode || 'SIMULATION'} — SIN BROKER REAL
                </span>
                {status.emergency_stop && (
                  <span className="px-2.5 py-0.5 rounded bg-rose-600/25 border border-rose-500 text-rose-300 text-[10px] font-mono font-bold flex items-center gap-1 animate-pulse">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    EMERGENCY STOP
                  </span>
                )}
              </div>
              <p className="hidden md:block text-[11px] font-mono text-slate-400">
                Research → Strategy (SMA Cross) → Risk (20 Reglas) → Execution → Reconciliation
              </p>
            </div>
          </div>

          {/* Top-Right Always-Visible Budget Display (SPEC-002) */}
          <div className="ml-auto">
            <BudgetDisplay balance={balance} onRefresh={fetchBalance} />
          </div>
        </header>

        {/* Active Section Workspace */}
        <main className="flex-1 p-3 lg:p-4 flex flex-col gap-3.5 max-w-[1920px] w-full mx-auto">
          {activeSection === 'dashboard' && (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5">
                <div className="lg:col-span-3 flex flex-col gap-3.5">
                  <SystemStatus status={status} connected={connected} />
                  <Controls
                    status={status}
                    selectedInstrument={selectedInstrument}
                    onSelectInstrument={setSelectedInstrument}
                    onStatusChange={setStatus}
                  />
                </div>

                <div className="lg:col-span-5 xl:col-span-6 min-h-[480px] flex flex-col">
                  <TradingChart
                    instrument={selectedInstrument}
                    candles={candlesByInstrument[selectedInstrument] || []}
                    signals={signals}
                    selectedSignal={selectedSignal}
                    latestQuote={latestQuote[selectedInstrument]}
                  />
                </div>

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
            </>
          )}

          {activeSection === 'positions' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
              <div className="lg:col-span-8">
                <PositionsPanel
                  positions={positions}
                  realizedPnl={status.realized_pnl}
                  unrealizedPnl={status.unrealized_pnl}
                />
              </div>
              <div className="lg:col-span-4 flex flex-col gap-4">
                <SystemStatus status={status} connected={connected} />
                <OrdersPanel orders={orders} />
              </div>
            </div>
          )}

          {activeSection === 'signals' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-[540px]">
              <div className="lg:col-span-8 min-h-[480px] flex flex-col">
                <TradingChart
                  instrument={selectedInstrument}
                  candles={candlesByInstrument[selectedInstrument] || []}
                  signals={signals}
                  selectedSignal={selectedSignal}
                  latestQuote={latestQuote[selectedInstrument]}
                />
              </div>
              <div className="lg:col-span-4 flex flex-col gap-4">
                <SignalsPanel
                  signals={signals}
                  selectedSignal={selectedSignal}
                  onSelectSignal={handleSelectSignal}
                />
                <Controls
                  status={status}
                  selectedInstrument={selectedInstrument}
                  onSelectInstrument={setSelectedInstrument}
                  onStatusChange={setStatus}
                />
              </div>
            </div>
          )}

          {activeSection === 'risk' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
              <div className="lg:col-span-5">
                <RiskPanel
                  decision={riskDecision}
                  limits={status.risk_limits}
                  emergencyStop={status.emergency_stop}
                  onStatusChange={setStatus}
                />
              </div>
              <div className="lg:col-span-4">
                <SystemStatus status={status} connected={connected} />
              </div>
              <div className="lg:col-span-3">
                <Controls
                  status={status}
                  selectedInstrument={selectedInstrument}
                  onSelectInstrument={setSelectedInstrument}
                  onStatusChange={setStatus}
                />
              </div>
            </div>
          )}

          {activeSection === 'orders' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
              <div className="lg:col-span-7">
                <OrdersPanel orders={orders} />
              </div>
              <div className="lg:col-span-5">
                <PositionsPanel
                  positions={positions}
                  realizedPnl={status.realized_pnl}
                  unrealizedPnl={status.unrealized_pnl}
                />
              </div>
            </div>
          )}

          {activeSection === 'audit' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
              <div className="lg:col-span-8">
                <AuditLog events={auditEvents} />
              </div>
              <div className="lg:col-span-4">
                <SystemStatus status={status} connected={connected} />
              </div>
            </div>
          )}

          {activeSection === 'config' && (
            <ConfigPanel
              status={status}
              balance={balance}
              selectedInstrument={selectedInstrument}
              onSelectInstrument={setSelectedInstrument}
              onStatusChange={setStatus}
              onRefreshBalance={fetchBalance}
            />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
