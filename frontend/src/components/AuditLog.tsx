import React, { useEffect, useRef, useState } from 'react';
import { Terminal, Pause, Play } from 'lucide-react';
import { AuditEvent } from '../types';

interface AuditLogProps {
  events: AuditEvent[];
}

export const AuditLog: React.FC<AuditLogProps> = ({ events }) => {
  const [autoScroll, setAutoScroll] = useState(true);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = 0;
    }
  }, [events, autoScroll]);

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-3.5 flex flex-col h-full">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5 mb-2.5">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-sky-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Audit Log Append-Only (Hash Chain — Últimos 20 Eventos)
          </h3>
        </div>

        <button
          type="button"
          onClick={() => setAutoScroll((prev) => !prev)}
          className={`px-2 py-1 rounded text-[11px] font-mono flex items-center gap-1 border transition cursor-pointer ${
            autoScroll
              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
              : 'bg-amber-500/15 border-amber-500/30 text-amber-300'
          }`}
        >
          {autoScroll ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
          {autoScroll ? 'Auto-Scroll ON' : 'Auto-Scroll PAUSADO'}
        </button>
      </div>

      <div
        ref={containerRef}
        className="overflow-y-auto max-h-[220px] space-y-1.5 pr-1 font-mono text-[11px]"
      >
        {events.slice(0, 20).map((ev, index) => {
          const timeStr = ev.timestamp
            ? new Date(ev.timestamp).toLocaleTimeString('es-ES', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })
            : '--:--:--';

          const agentColor =
            ev.agent === 'Orchestrator'
              ? 'text-sky-400'
              : ev.agent === 'Strategist'
              ? 'text-purple-400'
              : ev.agent === 'Risk'
              ? 'text-amber-400'
              : ev.agent === 'Executor'
              ? 'text-emerald-400'
              : 'text-cyan-300';

          return (
            <div
              key={`${ev.timestamp}-${index}`}
              className="p-2 rounded bg-slate-950/80 border border-slate-800/70 flex flex-col gap-1"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-slate-500">[{timeStr}]</span>
                  <span className={`font-bold ${agentColor}`}>{ev.agent}</span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-900 text-slate-200 font-semibold text-[10px]">
                    {ev.event_type}
                  </span>
                </div>
                {ev.hash && (
                  <span className="text-[10px] text-slate-600" title={`SHA-256: ${ev.hash}`}>
                    #{ev.hash.slice(0, 10)}
                  </span>
                )}
              </div>
              <div className="text-slate-400 truncate">
                {JSON.stringify(ev.data)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
