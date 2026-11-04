import React from 'react';
import { Activity, ShieldAlert, CheckCircle2, PauseCircle, PlayCircle, Wifi, WifiOff } from 'lucide-react';
import { SystemStatus as SystemStatusType } from '../types';

interface SystemStatusProps {
  status: SystemStatusType;
  connected: boolean;
}

export const SystemStatus: React.FC<SystemStatusProps> = ({ status, connected }) => {
  const totalPnl = status.total_pnl ?? status.realized_pnl + status.unrealized_pnl;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-4 flex flex-col gap-3.5">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-sky-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Estado del Sistema
          </h3>
        </div>
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono ${
            connected
              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
              : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
          }`}
        >
          {connected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
          {connected ? 'WS LIVE' : 'RECONECTANDO'}
        </span>
      </div>

      {/* Simulation Banner */}
      <div className="px-3 py-2 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-mono flex items-center justify-between">
        <span>MODO ACTIVO:</span>
        <span className="font-bold">SIMULACIÓN SINTÉTICA</span>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-2.5 text-xs font-mono">
        <div className="bg-slate-950/70 border border-slate-800/80 rounded p-2.5">
          <div className="text-slate-400 text-[11px]">CICLOS (cycle_count)</div>
          <div className="text-lg font-bold text-white mt-0.5">{status.cycle_count}</div>
        </div>

        <div className="bg-slate-950/70 border border-slate-800/80 rounded p-2.5">
          <div className="text-slate-400 text-[11px]">ÓRDENES TOTALES</div>
          <div className="text-lg font-bold text-sky-400 mt-0.5">{status.total_orders}</div>
        </div>
      </div>

      {/* Status Flags */}
      <div className="space-y-2 text-xs font-mono">
        <div className="flex items-center justify-between px-2.5 py-2 rounded bg-slate-950/60 border border-slate-800/70">
          <span className="text-slate-400">Estado Loop (paused):</span>
          {status.paused ? (
            <span className="inline-flex items-center gap-1 text-amber-400 font-semibold">
              <PauseCircle className="w-3.5 h-3.5" /> PAUSADO
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold">
              <PlayCircle className="w-3.5 h-3.5" /> EN EJECUCIÓN
            </span>
          )}
        </div>

        <div className="flex items-center justify-between px-2.5 py-2 rounded bg-slate-950/60 border border-slate-800/70">
          <span className="text-slate-400">Emergency Stop:</span>
          {status.emergency_stop ? (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/40 font-bold animate-pulse">
              <ShieldAlert className="w-3.5 h-3.5" /> ACTIVO
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-emerald-400">
              <CheckCircle2 className="w-3.5 h-3.5" /> INACTIVO
            </span>
          )}
        </div>

        <div className="flex items-center justify-between px-2.5 py-2 rounded bg-slate-950/60 border border-slate-800/70">
          <span className="text-slate-400">Límites Configurados:</span>
          {status.limits_configured ? (
            <span className="text-emerald-400 font-semibold">SÍ (ACTIVOS)</span>
          ) : (
            <span className="text-rose-400 font-semibold">NO (BLOQUEADO)</span>
          )}
        </div>
      </div>

      {/* PnL Summary */}
      <div className="border-t border-slate-800 pt-3 space-y-2 font-mono">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">PnL Realizado:</span>
          <span
            className={`font-bold ${
              status.realized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {status.realized_pnl >= 0 ? '+' : ''}${status.realized_pnl.toFixed(2)}
          </span>
        </div>

        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">PnL No Realizado:</span>
          <span
            className={`font-bold ${
              status.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {status.unrealized_pnl >= 0 ? '+' : ''}${status.unrealized_pnl.toFixed(2)}
          </span>
        </div>

        <div className="p-2.5 rounded bg-slate-950 border border-slate-800 flex items-center justify-between">
          <span className="text-xs text-slate-300 font-semibold">PnL Neto Total:</span>
          <span
            className={`text-base font-bold ${
              totalPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
};
