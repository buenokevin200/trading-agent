import React, { useState } from 'react';
import { ListOrdered } from 'lucide-react';
import { OrderItem } from '../types';

interface OrdersPanelProps {
  orders: OrderItem[];
}

export const OrdersPanel: React.FC<OrdersPanelProps> = ({ orders }) => {
  const [statusFilter, setStatusFilter] = useState<'all' | 'filled' | 'rejected' | 'pending'>('all');

  const filteredOrders = orders.filter((o) =>
    statusFilter === 'all' ? true : o.status === statusFilter
  );

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-3.5 flex flex-col h-full max-h-[280px]">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2 mb-2.5">
        <div className="flex items-center gap-2">
          <ListOrdered className="w-4 h-4 text-sky-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Historial de Órdenes
          </h3>
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-1 text-[10px] font-mono">
          {(['all', 'filled', 'rejected', 'pending'] as const).map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => setStatusFilter(st)}
              className={`px-2 py-0.5 rounded uppercase transition cursor-pointer ${
                statusFilter === st
                  ? 'bg-sky-500/25 text-sky-300 border border-sky-500/40 font-bold'
                  : 'bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-y-auto flex-1 pr-1 space-y-1.5">
        {filteredOrders.length === 0 ? (
          <div className="text-xs font-mono text-slate-500 py-6 text-center">
            No hay órdenes con filtro "{statusFilter}".
          </div>
        ) : (
          filteredOrders.slice(0, 35).map((ord) => {
            const timeStr = ord.timestamp
              ? new Date(ord.timestamp).toLocaleTimeString('es-ES', {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                })
              : '--:--:--';

            return (
              <div
                key={ord.order_id}
                className="p-2 rounded bg-slate-950/70 border border-slate-800/80 text-[11px] font-mono flex flex-col gap-1"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        ord.side === 'BUY'
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : 'bg-rose-500/20 text-rose-300'
                      }`}
                    >
                      {ord.side}
                    </span>
                    <span className="font-bold text-slate-200">{ord.instrument}</span>
                    <span className="text-slate-500 text-[10px]">{ord.order_id}</span>
                  </div>

                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold ${
                      ord.status === 'filled'
                        ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                        : ord.status === 'rejected'
                        ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                        : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                    }`}
                  >
                    {ord.status}
                  </span>
                </div>

                <div className="flex items-center justify-between text-slate-400 text-[10px]">
                  <span>Qty: <strong className="text-slate-200">{ord.quantity}</strong></span>
                  <span>Fill: <strong className="text-slate-200">${ord.fill_price?.toFixed(2)}</strong></span>
                  <span>Fee: <strong className="text-slate-200">${ord.commission?.toFixed(2)}</strong></span>
                  <span>{timeStr}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
