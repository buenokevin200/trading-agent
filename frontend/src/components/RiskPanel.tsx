import React, { useState } from 'react';
import { ShieldCheck, ShieldX, OctagonAlert } from 'lucide-react';
import { RiskDecisionEvent, RiskLimits, SystemStatus } from '../types';

interface RiskPanelProps {
  decision: RiskDecisionEvent | null;
  limits: RiskLimits;
  emergencyStop: boolean;
  onStatusChange: (status: SystemStatus) => void;
}

export const RiskPanel: React.FC<RiskPanelProps> = ({
  decision,
  limits,
  emergencyStop,
  onStatusChange,
}) => {
  const [confirmingStop, setConfirmingStop] = useState(false);

  const triggerEmergencyStop = async () => {
    const res = await fetch('/api/emergency-stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reason: 'Activado desde el Panel de Riesgo',
        reset: false,
      }),
    });
    const data = await res.json();
    if (data) onStatusChange(data);
    setConfirmingStop(false);
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-3.5 flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          {decision?.approved ? (
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          ) : (
            <ShieldX className="w-4 h-4 text-amber-400" />
          )}
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Motor Determinista de Riesgo
          </h3>
        </div>
        <span className="text-[10px] font-mono text-slate-400">20 CÓDIGOS DE CONTROL</span>
      </div>

      {/* Latest Risk Decision */}
      <div className="bg-slate-950/80 border border-slate-800 rounded p-2.5 text-xs font-mono space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Última Decisión:</span>
          {decision ? (
            <span
              className={`px-2 py-0.5 rounded font-bold text-[11px] ${
                decision.approved
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
              }`}
            >
              {decision.approved ? 'APROBADO' : 'RECHAZADO'}
            </span>
          ) : (
            <span className="text-slate-500">SIN DATOS</span>
          )}
        </div>

        {decision && !decision.approved && (
          <div className="pt-1 space-y-1">
            <div className="text-rose-400 font-semibold text-[11px]">
              Código: {decision.rejection_code || 'REJECTED'}
            </div>
            <div className="text-slate-300 text-[11px] leading-snug">
              {decision.rejection_reason}
            </div>
          </div>
        )}

        {decision && decision.approved && (
          <div className="pt-1 text-[11px] text-emerald-300 flex items-center justify-between">
            <span>Cant. Aprobada: {decision.approved_quantity}</span>
            <span>Riesgo: ${decision.risk_amount?.toFixed(2)}</span>
          </div>
        )}
      </div>

      {/* Configured Risk Limits */}
      <div className="space-y-1.5">
        <div className="text-[11px] font-mono text-slate-400 font-semibold">
          LÍMITES CONFIGURADOS
        </div>
        <div className="grid grid-cols-2 gap-1.5 text-[11px] font-mono">
          <div className="bg-slate-950/60 border border-slate-800/80 rounded px-2 py-1.5 flex justify-between">
            <span className="text-slate-400">risk_per_trade:</span>
            <span className="text-white font-semibold">{(limits.risk_per_trade * 100).toFixed(1)}%</span>
          </div>
          <div className="bg-slate-950/60 border border-slate-800/80 rounded px-2 py-1.5 flex justify-between">
            <span className="text-slate-400">max_exposure:</span>
            <span className="text-white font-semibold">{(limits.max_exposure * 100).toFixed(0)}%</span>
          </div>
          <div className="bg-slate-950/60 border border-slate-800/80 rounded px-2 py-1.5 flex justify-between">
            <span className="text-slate-400">max_daily_loss:</span>
            <span className="text-white font-semibold">{(limits.max_daily_loss * 100).toFixed(1)}%</span>
          </div>
          <div className="bg-slate-950/60 border border-slate-800/80 rounded px-2 py-1.5 flex justify-between">
            <span className="text-slate-400">max_drawdown:</span>
            <span className="text-white font-semibold">{(limits.max_drawdown * 100).toFixed(1)}%</span>
          </div>
          <div className="col-span-2 bg-slate-950/60 border border-slate-800/80 rounded px-2 py-1.5 flex justify-between">
            <span className="text-slate-400">max_positions:</span>
            <span className="text-sky-300 font-semibold">{limits.max_positions} posiciones simultáneas</span>
          </div>
        </div>
      </div>

      {/* Emergency Stop Switch in Risk Panel */}
      <div className="pt-1">
        {!confirmingStop ? (
          <button
            type="button"
            disabled={emergencyStop}
            onClick={() => setConfirmingStop(true)}
            className="w-full py-1.5 px-3 rounded bg-rose-500/15 hover:bg-rose-500/25 disabled:opacity-40 border border-rose-500/40 text-rose-300 text-xs font-mono font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer"
          >
            <OctagonAlert className="w-3.5 h-3.5" />
            {emergencyStop ? 'INTERRUPTORES BLOQUEADOS (STOP ACTIVO)' : 'Activar Interruptor de Emergencia'}
          </button>
        ) : (
          <div className="p-2 rounded bg-rose-950/40 border border-rose-500/50 space-y-2 text-xs font-mono">
            <div className="text-rose-200 text-[11px]">
              ¿Confirmar bloqueo inmediato de nuevas exposiciones?
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={triggerEmergencyStop}
                className="flex-1 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white font-bold text-[11px] cursor-pointer"
              >
                Confirmar
              </button>
              <button
                type="button"
                onClick={() => setConfirmingStop(false)}
                className="flex-1 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] cursor-pointer"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
