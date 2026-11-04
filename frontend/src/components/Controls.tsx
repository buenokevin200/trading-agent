import React, { useState } from 'react';
import { Play, Pause, Zap, OctagonAlert, Sliders, RotateCcw } from 'lucide-react';
import { Instrument, SystemStatus } from '../types';

interface ControlsProps {
  status: SystemStatus;
  selectedInstrument: Instrument;
  onSelectInstrument: (inst: Instrument) => void;
  onStatusChange: (newStatus: SystemStatus) => void;
}

export const Controls: React.FC<ControlsProps> = ({
  status,
  selectedInstrument,
  onSelectInstrument,
  onStatusChange,
}) => {
  const [loadingCycle, setLoadingCycle] = useState(false);
  const [frequency, setFrequency] = useState<number>(status.cycle_frequency_sec || 5);
  const [showEmergencyModal, setShowEmergencyModal] = useState(false);

  const handleRunCycle = async () => {
    setLoadingCycle(true);
    try {
      const res = await fetch('/api/cycle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instrument: selectedInstrument }),
      });
      const data = await res.json();
      if (data?.status) onStatusChange(data.status);
    } finally {
      setLoadingCycle(false);
    }
  };

  const handleTogglePause = async () => {
    const endpoint = status.paused ? '/api/resume' : '/api/pause';
    const res = await fetch(endpoint, { method: 'POST' });
    const data = await res.json();
    if (data) onStatusChange(data);
  };

  const handleInstrumentChange = async (inst: Instrument) => {
    onSelectInstrument(inst);
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ instrument: inst }),
    });
    const data = await res.json();
    if (data) onStatusChange(data);
  };

  const handleFrequencyChange = async (val: number) => {
    setFrequency(val);
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ frequency_sec: val }),
    });
    const data = await res.json();
    if (data) onStatusChange(data);
  };

  const confirmEmergencyStop = async (reset = false) => {
    const res = await fetch('/api/emergency-stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reason: 'Activado manualmente desde el panel de control del operador',
        reset,
      }),
    });
    const data = await res.json();
    if (data) onStatusChange(data);
    setShowEmergencyModal(false);
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-4 flex flex-col gap-3.5">
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2.5">
        <Sliders className="w-4 h-4 text-sky-400" />
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
          Controles de Operación
        </h3>
      </div>

      {/* Instrument Selector */}
      <div className="space-y-1.5">
        <label className="text-[11px] font-mono text-slate-400 block">
          INSTRUMENTO SINTÉTICO
        </label>
        <div className="grid grid-cols-2 gap-2">
          {(['SYNTH/BTC', 'SYNTH/ETH'] as Instrument[]).map((inst) => (
            <button
              key={inst}
              type="button"
              onClick={() => handleInstrumentChange(inst)}
              className={`py-2 px-3 rounded text-xs font-mono font-bold border transition ${
                selectedInstrument === inst
                  ? 'bg-sky-500/20 border-sky-400 text-sky-300 shadow-sm'
                  : 'bg-slate-950/70 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {inst}
            </button>
          ))}
        </div>
      </div>

      {/* Cycle Frequency Slider */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-[11px] font-mono">
          <span className="text-slate-400">FRECUENCIA DE CICLO</span>
          <span className="text-sky-400 font-bold">{frequency}s</span>
        </div>
        <input
          type="range"
          min={1}
          max={60}
          value={frequency}
          onChange={(e) => handleFrequencyChange(Number(e.target.value))}
          className="w-full accent-sky-400 cursor-pointer"
        />
        <div className="flex justify-between text-[10px] font-mono text-slate-500">
          <span>1s (Rápido)</span>
          <span>30s</span>
          <span>60s (Lento)</span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="space-y-2 pt-1">
        <button
          type="button"
          onClick={handleRunCycle}
          disabled={loadingCycle || status.emergency_stop}
          className="w-full py-2.5 px-3 rounded bg-sky-500 hover:bg-sky-400 disabled:opacity-50 text-slate-950 font-mono font-bold text-xs flex items-center justify-center gap-2 transition cursor-pointer"
        >
          <Zap className="w-4 h-4" />
          {loadingCycle ? 'EJECUTANDO CICLO...' : 'EJECUTAR CICLO MANUAL'}
        </button>

        <button
          type="button"
          onClick={handleTogglePause}
          className={`w-full py-2 px-3 rounded font-mono font-bold text-xs flex items-center justify-center gap-2 border transition cursor-pointer ${
            status.paused
              ? 'bg-emerald-500/20 hover:bg-emerald-500/30 border-emerald-500/40 text-emerald-300'
              : 'bg-amber-500/20 hover:bg-amber-500/30 border-amber-500/40 text-amber-300'
          }`}
        >
          {status.paused ? (
            <>
              <Play className="w-4 h-4" /> REANUDAR CICLOS
            </>
          ) : (
            <>
              <Pause className="w-4 h-4" /> PAUSAR CICLOS
            </>
          )}
        </button>

        {!status.emergency_stop ? (
          <button
            type="button"
            onClick={() => setShowEmergencyModal(true)}
            className="w-full py-2.5 px-3 rounded bg-rose-600/25 hover:bg-rose-600/40 border border-rose-500/50 text-rose-300 font-mono font-bold text-xs flex items-center justify-center gap-2 transition cursor-pointer"
          >
            <OctagonAlert className="w-4 h-4" />
            EMERGENCY STOP
          </button>
        ) : (
          <button
            type="button"
            onClick={() => confirmEmergencyStop(true)}
            className="w-full py-2.5 px-3 rounded bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/50 text-amber-300 font-mono font-bold text-xs flex items-center justify-center gap-2 transition cursor-pointer"
          >
            <RotateCcw className="w-4 h-4" />
            REARMAR EMERGENCY STOP
          </button>
        )}
      </div>

      {/* Confirmation Modal */}
      {showEmergencyModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-rose-500/50 rounded-lg max-w-md w-full p-5 shadow-2xl space-y-4">
            <div className="flex items-center gap-2.5 text-rose-400">
              <OctagonAlert className="w-6 h-6 shrink-0" />
              <h4 className="text-base font-bold font-mono">
                Confirmar Interruptor de Emergencia
              </h4>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              ¿Estás seguro de activar el <strong>Emergency Stop</strong>? Esta acción pausará el
              loop automático y bloqueará inmediatamente cualquier nueva exposición con el código{' '}
              <code className="text-rose-300">ERR_01_EMERGENCY_STOP</code>, manteniendo la
              vigilancia de las protecciones activas.
            </p>
            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={() => setShowEmergencyModal(false)}
                className="px-3.5 py-2 rounded text-xs font-mono bg-slate-800 hover:bg-slate-700 text-slate-200 cursor-pointer"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => confirmEmergencyStop(false)}
                className="px-4 py-2 rounded text-xs font-mono font-bold bg-rose-600 hover:bg-rose-500 text-white cursor-pointer"
              >
                Sí, Activar Emergency Stop
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
