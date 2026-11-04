import React from 'react';
import { Radio, Crosshair } from 'lucide-react';
import { SignalEvent } from '../types';

interface SignalsPanelProps {
  signals: SignalEvent[];
  selectedSignal: SignalEvent | null;
  onSelectSignal: (sig: SignalEvent) => void;
}

export const SignalsPanel: React.FC<SignalsPanelProps> = ({
  signals,
  selectedSignal,
  onSelectSignal,
}) => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-3.5 flex flex-col h-full max-h-[340px]">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2.5">
        <div className="flex items-center gap-2">
          <Radio className="w-4 h-4 text-sky-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Señales Recientes
          </h3>
        </div>
        <span className="text-[11px] font-mono text-slate-400">
          {signals.length} eventos
        </span>
      </div>

      <div className="overflow-y-auto space-y-2 pr-1 flex-1">
        {signals.length === 0 ? (
          <div className="text-xs font-mono text-slate-500 py-8 text-center">
            Esperando señales del Strategist...
          </div>
        ) : (
          signals.slice(0, 25).map((sig) => {
            const isSelected = selectedSignal?.signal_id === sig.signal_id;
            const badgeStyle =
              sig.signal_type === 'BUY'
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                : sig.signal_type === 'SELL'
                ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                : 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40';

            const label =
              sig.signal_type === 'BUY'
                ? '🟢 BUY'
                : sig.signal_type === 'SELL'
                ? '🔴 SELL'
                : '🟡 NO_OP';

            const timeStr = sig.timestamp
              ? new Date(sig.timestamp).toLocaleTimeString('es-ES', {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                })
              : '--:--:--';

            return (
              <div
                key={sig.signal_id}
                onClick={() => onSelectSignal(sig)}
                className={`p-2.5 rounded border text-xs font-mono cursor-pointer transition ${
                  isSelected
                    ? 'bg-sky-950/50 border-sky-500/60'
                    : 'bg-slate-950/70 border-slate-800/80 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className={`px-1.5 py-0.5 rounded border text-[11px] font-bold ${badgeStyle}`}>
                      {label}
                    </span>
                    <span className="font-bold text-slate-200">{sig.instrument}</span>
                  </div>
                  <div className="flex items-center gap-1 text-[11px] text-slate-400">
                    <Crosshair className="w-3 h-3 text-sky-400" />
                    <span>{timeStr}</span>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-1.5 mt-2 text-[11px]">
                  <div className="bg-slate-900/80 px-1.5 py-1 rounded">
                    <span className="text-slate-400 block text-[10px]">ENTRY</span>
                    <span className="text-white font-semibold">${sig.entry_price?.toFixed(2)}</span>
                  </div>
                  <div className="bg-slate-900/80 px-1.5 py-1 rounded">
                    <span className="text-slate-400 block text-[10px]">STOP LOSS</span>
                    <span className="text-rose-400 font-semibold">
                      {sig.stop_loss != null ? `$${sig.stop_loss.toFixed(2)}` : '—'}
                    </span>
                  </div>
                  <div className="bg-slate-900/80 px-1.5 py-1 rounded">
                    <span className="text-slate-400 block text-[10px]">TAKE PROFIT</span>
                    <span className="text-emerald-400 font-semibold">
                      {sig.take_profit != null ? `$${sig.take_profit.toFixed(2)}` : '—'}
                    </span>
                  </div>
                </div>

                {sig.rules_triggered && sig.rules_triggered.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {sig.rules_triggered.map((rule, i) => (
                      <span
                        key={i}
                        className="px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 text-[10px]"
                      >
                        {rule}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
