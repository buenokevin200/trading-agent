import React from 'react';
import { Briefcase, AlertTriangle, Shield } from 'lucide-react';
import { PositionItem } from '../types';

interface PositionsPanelProps {
  positions: PositionItem[];
  realizedPnl: number;
  unrealizedPnl: number;
}

export const PositionsPanel: React.FC<PositionsPanelProps> = ({
  positions,
  realizedPnl,
  unrealizedPnl,
}) => {
  const totalPnl = realizedPnl + unrealizedPnl;
  const hasUnprotected = positions.some((p) => !p.is_protected);

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-3.5 flex flex-col h-full">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2.5 mb-2.5">
        <div className="flex items-center gap-2">
          <Briefcase className="w-4 h-4 text-sky-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Posiciones Abiertas (Simulador)
          </h3>
          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px] font-mono">
            {positions.length}
          </span>
        </div>

        {/* Large Total PnL Display */}
        <div className="flex items-center gap-3 font-mono">
          <div className="text-right">
            <span className="text-[10px] text-slate-400 block uppercase">
              PnL Total (Realizado + No Realizado)
            </span>
            <span
              className={`text-lg font-extrabold ${
                totalPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {hasUnprotected && (
        <div className="mb-2.5 px-3 py-2 rounded bg-amber-500/15 border border-amber-500/40 text-amber-300 text-xs font-mono flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
          <span>
            ALERTA DE SEGURIDAD: Existe al menos una posición sin protección activa (is_protected = false).
          </span>
        </div>
      )}

      <div className="overflow-x-auto flex-1">
        <table className="w-full text-left border-collapse text-xs font-mono">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 text-[11px]">
              <th className="py-2 px-2">INSTRUMENTO</th>
              <th className="py-2 px-2">SIDE</th>
              <th className="py-2 px-2 text-right">QTY</th>
              <th className="py-2 px-2 text-right">ENTRY PRICE</th>
              <th className="py-2 px-2 text-right">CURRENT PRICE</th>
              <th className="py-2 px-2 text-right">SL / TP</th>
              <th className="py-2 px-2 text-right">UNREALIZED PNL</th>
              <th className="py-2 px-2 text-center">PROTECCIÓN</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {positions.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-slate-500">
                  No hay posiciones abiertas en el simulador en este instante.
                </td>
              </tr>
            ) : (
              positions.map((pos, idx) => (
                <tr key={`${pos.instrument}-${idx}`} className="hover:bg-slate-800/30">
                  <td className="py-2 px-2 font-bold text-white">{pos.instrument}</td>
                  <td className="py-2 px-2">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        pos.side === 'LONG'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                          : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                      }`}
                    >
                      {pos.side}
                    </span>
                  </td>
                  <td className="py-2 px-2 text-right text-slate-200">{pos.quantity}</td>
                  <td className="py-2 px-2 text-right text-slate-300">
                    ${pos.entry_price?.toFixed(2)}
                  </td>
                  <td className="py-2 px-2 text-right text-white font-semibold">
                    ${pos.current_price?.toFixed(2)}
                  </td>
                  <td className="py-2 px-2 text-right text-[11px]">
                    <span className="text-rose-400">
                      {pos.stop_loss != null ? `$${pos.stop_loss.toFixed(0)}` : '—'}
                    </span>
                    {' / '}
                    <span className="text-emerald-400">
                      {pos.take_profit != null ? `$${pos.take_profit.toFixed(0)}` : '—'}
                    </span>
                  </td>
                  <td
                    className={`py-2 px-2 text-right font-bold ${
                      pos.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {pos.unrealized_pnl >= 0 ? '+' : ''}${pos.unrealized_pnl?.toFixed(2)}
                  </td>
                  <td className="py-2 px-2 text-center">
                    {pos.is_protected ? (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400 text-[10px]">
                        <Shield className="w-3 h-3" /> PROTEGIDA
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[10px] font-bold">
                        <AlertTriangle className="w-3 h-3" /> SIN SL/TP
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
