import React, { useState } from 'react';
import { Settings, Save, WifiOff, CheckCircle2 } from 'lucide-react';
import { BalanceInfo, Instrument, SystemStatus } from '../types';

interface ConfigPanelProps {
  status: SystemStatus;
  balance: BalanceInfo;
  selectedInstrument: Instrument;
  onSelectInstrument: (inst: Instrument) => void;
  onStatusChange: (status: SystemStatus) => void;
  onRefreshBalance: () => void;
}

export const ConfigPanel: React.FC<ConfigPanelProps> = ({
  status,
  balance,
  selectedInstrument,
  onSelectInstrument,
  onStatusChange,
  onRefreshBalance,
}) => {
  const [brokerMode, setBrokerMode] = useState<'simulation' | 'paper'>(
    balance.mode === 'paper' ? 'paper' : 'simulation'
  );
  const [refCapital, setRefCapital] = useState<number>(
    status.risk_limits?.reference_capital || 100000
  );
  const [riskPerTrade, setRiskPerTrade] = useState<number>(
    (status.risk_limits?.risk_per_trade || 0.01) * 100
  );
  const [maxExposure, setMaxExposure] = useState<number>(
    (status.risk_limits?.max_exposure || 0.5) * 100
  );
  const [maxDailyLoss, setMaxDailyLoss] = useState<number>(
    (status.risk_limits?.max_daily_loss || 0.03) * 100
  );
  const [maxDrawdown, setMaxDrawdown] = useState<number>(
    (status.risk_limits?.max_drawdown || 0.06) * 100
  );
  const [maxPositions, setMaxPositions] = useState<number>(
    status.risk_limits?.max_positions || 4
  );
  const [simulateOffline, setSimulateOffline] = useState<boolean>(!balance.connected);
  const [savedBanner, setSavedBanner] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        instrument: selectedInstrument,
        broker_mode: brokerMode,
        reference_capital: Number(refCapital),
        simulate_binance_offline: simulateOffline,
        risk_per_trade: Number(riskPerTrade) / 100,
        max_exposure: Number(maxExposure) / 100,
        max_daily_loss: Number(maxDailyLoss) / 100,
        max_drawdown: Number(maxDrawdown) / 100,
        max_positions: Number(maxPositions),
      }),
    });
    const updatedStatus = await res.json();
    if (updatedStatus) onStatusChange(updatedStatus);
    onRefreshBalance();
    setSavedBanner(true);
    setTimeout(() => setSavedBanner(false), 3000);
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-5 max-w-4xl mx-auto space-y-6 font-mono">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <Settings className="w-5 h-5 text-sky-400" />
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-white">
              Configuración del Sistema y Broker (SPEC-002)
            </h2>
            <p className="text-xs text-slate-400">
              Instrumentos, estrategia determinista, límites de riesgo y fuente de balance Binance
            </p>
          </div>
        </div>
        {savedBanner && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-bold">
            <CheckCircle2 className="w-4 h-4" /> Configuración aplicada
          </span>
        )}
      </div>

      <form onSubmit={handleSave} className="space-y-6 text-xs">
        {/* Broker & Binance Balance Section */}
        <div className="p-4 rounded-lg bg-slate-950/70 border border-slate-800 space-y-4">
          <h3 className="text-xs font-bold uppercase text-sky-400">
            1. Fuente de Presupuesto — Broker Binance (Simulación / Paper Testnet)
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-400 mb-1">MODO DEL BROKER</label>
              <select
                value={brokerMode}
                onChange={(e) => setBrokerMode(e.target.value as 'simulation' | 'paper')}
                className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white"
              >
                <option value="simulation">simulation (Balance sintético de referencia)</option>
                <option value="paper">paper (Binance Testnet API / Fallback seguro)</option>
              </select>
              <p className="text-[11px] text-slate-500 mt-1">
                El modo <code>real</code> está deshabilitado por política de seguridad. Las API keys solo viven en <code>.env</code> del backend.
              </p>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">
                CAPITAL DE REFERENCIA (USDT)
              </label>
              <input
                type="number"
                step="100"
                min="100"
                value={refCapital}
                onChange={(e) => setRefCapital(Number(e.target.value))}
                className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white"
              />
            </div>
          </div>

          {/* Toggle to test Criterion 7: Binance unreachable warning */}
          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <WifiOff className="w-4 h-4 text-amber-400" />
              <div>
                <div className="text-slate-200 font-semibold">
                  Simular fallo de conexión con Binance (Prueba de resiliencia)
                </div>
                <div className="text-[11px] text-slate-400">
                  Verifica que el indicador de presupuesto superior derecho muestre "—" y un warning cuando Binance no responde.
                </div>
              </div>
            </div>
            <input
              type="checkbox"
              checked={simulateOffline}
              onChange={(e) => setSimulateOffline(e.target.checked)}
              className="w-4 h-4 accent-amber-400 cursor-pointer"
            />
          </div>
        </div>

        {/* Instrument & Strategy Section */}
        <div className="p-4 rounded-lg bg-slate-950/70 border border-slate-800 space-y-4">
          <h3 className="text-xs font-bold uppercase text-sky-400">
            2. Universo de Instrumentos y Estrategia Determinista
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-400 mb-1">INSTRUMENTO ACTIVO</label>
              <select
                value={selectedInstrument}
                onChange={(e) => onSelectInstrument(e.target.value as Instrument)}
                className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white"
              >
                <option value="SYNTH/BTC">SYNTH/BTC (Sintético Bitcoin)</option>
                <option value="SYNTH/ETH">SYNTH/ETH (Sintético Ethereum)</option>
              </select>
            </div>
            <div>
              <label className="block text-slate-400 mb-1">ESTRATEGIA ACTIVA</label>
              <input
                type="text"
                disabled
                value="SMA_CROSS_v1.0 (Fast SMA 4 / Slow SMA 9)"
                className="w-full px-3 py-2 rounded bg-slate-900/50 border border-slate-800 text-slate-400"
              />
            </div>
          </div>
        </div>

        {/* Risk Limits Section */}
        <div className="p-4 rounded-lg bg-slate-950/70 border border-slate-800 space-y-4">
          <h3 className="text-xs font-bold uppercase text-sky-400">
            3. Parámetros del Motor Determinista de Riesgo
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-slate-400 mb-1">Riesgo por Trade (%)</label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="20"
                value={riskPerTrade}
                onChange={(e) => setRiskPerTrade(Number(e.target.value))}
                className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1">Exposición Máxima (%)</label>
              <input
                type="number"
                step="1"
                min="5"
                max="100"
                value={maxExposure}
                onChange={(e) => setMaxExposure(Number(e.target.value))}
                className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1">Pérdida Diaria Máxima (%)</label>
              <input
                type="number"
                step="0.5"
                min="0.5"
                max="50"
                value={maxDailyLoss}
                onChange={(e) => setMaxDailyLoss(Number(e.target.value))}
                className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1">Drawdown Máximo (%)</label>
              <input
                type="number"
                step="0.5"
                min="1"
                max="50"
                value={maxDrawdown}
                onChange={(e) => setMaxDrawdown(Number(e.target.value))}
                className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1">Máximo de Posiciones</label>
              <input
                type="number"
                step="1"
                min="1"
                max="20"
                value={maxPositions}
                onChange={(e) => setMaxPositions(Number(e.target.value))}
                className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white"
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            className="px-5 py-2.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold flex items-center gap-2 transition cursor-pointer"
          >
            <Save className="w-4 h-4" />
            Guardar y Actualizar Balance
          </button>
        </div>
      </form>
    </div>
  );
};
