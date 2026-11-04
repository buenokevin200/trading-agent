import React from 'react';
import { Wallet, AlertTriangle, Info, RefreshCw } from 'lucide-react';
import { BalanceInfo } from '../types';

interface BudgetDisplayProps {
  balance: BalanceInfo;
  onRefresh?: () => void;
}

function formatMoney(value: number | null | undefined, showSign = false): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—';
  }
  const formatted = Math.abs(value).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  if (showSign) {
    return value >= 0 ? `+$${formatted}` : `-$${formatted}`;
  }
  return `$${formatted}`;
}

function valueColor(value: number | null | undefined, neutralPositive = true): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'text-slate-400';
  }
  if (value > 0) return 'text-emerald-400';
  if (value < 0) return 'text-rose-400';
  return neutralPositive ? 'text-emerald-400' : 'text-slate-300';
}

export const BudgetDisplay: React.FC<BudgetDisplayProps> = ({ balance, onRefresh }) => {
  const isOffline = !balance.connected || balance.available_capital === null;

  return (
    <div className="relative group font-mono">
      {/* Main Top-Right Budget Pill / Bar */}
      <div
        className={`flex flex-wrap items-center gap-3 md:gap-4 px-3.5 py-2 rounded-lg border transition ${
          isOffline
            ? 'bg-rose-950/30 border-rose-500/50'
            : 'bg-slate-900/95 border-slate-800 hover:border-sky-500/40'
        }`}
      >
        {/* Broker + Mode Badge */}
        <div className="flex items-center gap-2 pr-2 border-r border-slate-800">
          <div
            className={`p-1.5 rounded ${
              isOffline
                ? 'bg-rose-500/20 text-rose-400'
                : 'bg-emerald-500/15 text-emerald-400'
            }`}
          >
            <Wallet className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                BINANCE ({balance.mode.toUpperCase()})
              </span>
              {isOffline && (
                <span className="inline-flex items-center gap-0.5 px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[10px] font-bold">
                  <AlertTriangle className="w-3 h-3 text-amber-400" />
                  WARNING
                </span>
              )}
            </div>
            <div className="text-[10px] text-slate-500 flex items-center gap-1">
              <span>Sync: {balance.refresh_sec || 5}s</span>
              <Info className="w-3 h-3 text-slate-500" />
            </div>
          </div>
        </div>

        {/* 1. Capital Disponible */}
        <div className="text-right">
          <div className="text-[10px] text-slate-400 uppercase">Disponible</div>
          <div
            className={`text-xs md:text-sm font-bold ${
              isOffline ? 'text-amber-400' : valueColor(balance.available_capital)
            }`}
          >
            {isOffline ? '—' : formatMoney(balance.available_capital)}
          </div>
        </div>

        {/* 2. Capital en Posiciones (Margin Usado) */}
        <div className="text-right pl-2 border-l border-slate-800/80">
          <div className="text-[10px] text-slate-400 uppercase">En Posiciones</div>
          <div
            className={`text-xs md:text-sm font-bold ${
              isOffline ? 'text-amber-400' : 'text-sky-300'
            }`}
          >
            {isOffline ? '—' : formatMoney(balance.used_capital)}
          </div>
        </div>

        {/* 3. Capital Total */}
        <div className="text-right pl-2 border-l border-slate-800/80">
          <div className="text-[10px] text-slate-400 uppercase">Capital Total</div>
          <div
            className={`text-xs md:text-sm font-extrabold ${
              isOffline ? 'text-amber-400' : valueColor(balance.total_capital)
            }`}
          >
            {isOffline ? '—' : formatMoney(balance.total_capital)}
          </div>
        </div>

        {/* 4. PnL No Realizado */}
        <div className="text-right pl-2 border-l border-slate-800/80">
          <div className="text-[10px] text-slate-400 uppercase">PnL No Realizado</div>
          <div className={`text-xs md:text-sm font-bold ${valueColor(balance.unrealized_pnl)}`}>
            {isOffline ? '—' : formatMoney(balance.unrealized_pnl, true)}
          </div>
        </div>

        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            title="Refrescar balance ahora"
            className="p-1.5 rounded bg-slate-950 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Hover Detailed Breakdown Tooltip */}
      <div className="pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-200 absolute right-0 top-full mt-2 z-50 w-80 p-3.5 rounded-lg bg-slate-950 border border-slate-700 shadow-2xl text-xs space-y-2">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <span className="font-bold text-white">Desglose de Presupuesto</span>
          <span className="px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 text-[10px] font-bold uppercase">
            {balance.broker} • {balance.mode}
          </span>
        </div>

        {balance.warning && (
          <div className="p-2 rounded bg-amber-500/15 border border-amber-500/40 text-amber-300 text-[11px] flex items-start gap-1.5">
            <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
            <span>{balance.warning}</span>
          </div>
        )}

        <div className="space-y-1.5 text-[11px]">
          <div className="flex justify-between">
            <span className="text-slate-400">Capital de Referencia (Config):</span>
            <span className="text-slate-200 font-semibold">
              {formatMoney(balance.reference_capital)} {balance.currency}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Capital Disponible (Libre):</span>
            <span className={`font-bold ${valueColor(balance.available_capital)}`}>
              {isOffline ? '—' : `${formatMoney(balance.available_capital)} ${balance.currency}`}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Capital en Posiciones (Margin):</span>
            <span className="text-sky-300 font-semibold">
              {isOffline ? '—' : `${formatMoney(balance.used_capital)} ${balance.currency}`}
            </span>
          </div>
          <div className="flex justify-between border-t border-slate-800/80 pt-1">
            <span className="text-slate-300 font-semibold">Capital Total:</span>
            <span className={`font-bold ${valueColor(balance.total_capital)}`}>
              {isOffline ? '—' : `${formatMoney(balance.total_capital)} ${balance.currency}`}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">PnL Realizado Acumulado:</span>
            <span className={`font-semibold ${valueColor(balance.realized_pnl)}`}>
              {formatMoney(balance.realized_pnl, true)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">PnL No Realizado (Abierto):</span>
            <span className={`font-semibold ${valueColor(balance.unrealized_pnl)}`}>
              {isOffline ? '—' : formatMoney(balance.unrealized_pnl, true)}
            </span>
          </div>
        </div>

        <div className="border-t border-slate-800 pt-1.5 flex items-center justify-between text-[10px] text-slate-500">
          <span>Fuente: {balance.source || 'synthetic_config'}</span>
          <span>
            {balance.updated_at
              ? new Date(balance.updated_at).toLocaleTimeString('es-ES')
              : '--:--:--'}
          </span>
        </div>
      </div>
    </div>
  );
};
