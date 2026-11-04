import { useEffect, useRef, useState, useCallback } from 'react';
import {
  AuditEvent,
  BalanceInfo,
  CandleBar,
  Instrument,
  OrderItem,
  PositionItem,
  PriceUpdateEvent,
  RiskDecisionEvent,
  SignalEvent,
  SystemStatus,
} from '../types';

const DEFAULT_STATUS: SystemStatus = {
  mode: 'SIMULATION',
  cycle_count: 0,
  paused: false,
  emergency_stop: false,
  limits_configured: true,
  active_instrument: 'SYNTH/BTC',
  cycle_frequency_sec: 5,
  positions: [],
  realized_pnl: 0,
  unrealized_pnl: 0,
  total_pnl: 0,
  total_orders: 0,
  risk_limits: {
    reference_capital: 100000,
    risk_per_trade: 0.01,
    max_exposure: 0.5,
    max_daily_loss: 0.03,
    max_drawdown: 0.06,
    max_positions: 4,
  },
  last_risk_decision: null,
};

const DEFAULT_BALANCE: BalanceInfo = {
  broker: 'binance',
  mode: 'simulation',
  source: 'synthetic_config',
  testnet: true,
  connected: true,
  currency: 'USDT',
  reference_capital: 100000,
  available_capital: 100000,
  used_capital: 0,
  total_capital: 100000,
  realized_pnl: 0,
  unrealized_pnl: 0,
  refresh_sec: 5,
  warning: null,
  updated_at: new Date().toISOString(),
};

export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<SystemStatus>(DEFAULT_STATUS);
  const [balance, setBalance] = useState<BalanceInfo>(DEFAULT_BALANCE);
  const [positions, setPositions] = useState<PositionItem[]>([]);
  const [orders, setOrders] = useState<OrderItem[]>([]);
  const [signals, setSignals] = useState<SignalEvent[]>([]);
  const [riskDecision, setRiskDecision] = useState<RiskDecisionEvent | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [candlesByInstrument, setCandlesByInstrument] = useState<Record<Instrument, CandleBar[]>>({
    'SYNTH/BTC': [],
    'SYNTH/ETH': [],
  });
  const [latestQuote, setLatestQuote] = useState<Record<Instrument, PriceUpdateEvent | null>>({
    'SYNTH/BTC': null,
    'SYNTH/ETH': null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);

  const fetchBalance = useCallback(async () => {
    try {
      const res = await fetch('/api/balance');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data) setBalance(data);
    } catch {
      setBalance((prev) => ({
        ...prev,
        connected: false,
        available_capital: null,
        used_capital: null,
        total_capital: null,
        warning: 'Sin respuesta del servicio de balance (Binance / Backend desconectado)',
      }));
    }
  }, []);

  const fetchInitialRestFallback = useCallback(async () => {
    try {
      const [statusRes, balRes, posRes, ordRes, sigRes, audRes, btcRes, ethRes] = await Promise.all([
        fetch('/api/status').then((r) => r.json()),
        fetch('/api/balance').then((r) => r.json()),
        fetch('/api/positions').then((r) => r.json()),
        fetch('/api/orders').then((r) => r.json()),
        fetch('/api/signals?limit=50').then((r) => r.json()),
        fetch('/api/audit?limit=20').then((r) => r.json()),
        fetch('/api/candles?instrument=SYNTH/BTC&limit=120').then((r) => r.json()),
        fetch('/api/candles?instrument=SYNTH/ETH&limit=120').then((r) => r.json()),
      ]);
      if (statusRes) {
        setStatus(statusRes);
        if (statusRes.last_risk_decision) {
          setRiskDecision(statusRes.last_risk_decision);
        }
      }
      if (balRes) setBalance(balRes);
      if (posRes?.positions) setPositions(posRes.positions);
      if (ordRes?.orders) setOrders(ordRes.orders);
      if (sigRes?.signals) setSignals(sigRes.signals);
      if (audRes?.events) setAuditEvents(audRes.events);
      setCandlesByInstrument({
        'SYNTH/BTC': btcRes?.candles || [],
        'SYNTH/ETH': ethRes?.candles || [],
      });
    } catch {
      // Handled by WebSocket retry & balance poll
    }
  }, []);

  useEffect(() => {
    fetchInitialRestFallback();

    // Poll /api/balance every 5 seconds as a backup to WebSocket balance_update
    const balanceInterval = window.setInterval(fetchBalance, 5000);

    let unmounted = false;
    const connect = () => {
      if (unmounted) return;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = import.meta.env.VITE_WS_URL || `${protocol}//${window.location.host}/ws`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!unmounted) setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          const { type, data } = msg;

          if (type === 'initial_state' && data) {
            if (data.status) {
              setStatus(data.status);
              if (data.status.last_risk_decision) {
                setRiskDecision(data.status.last_risk_decision);
              }
            }
            if (data.balance) setBalance(data.balance);
            if (data.positions) setPositions(data.positions);
            if (data.orders) setOrders(data.orders);
            if (data.signals) setSignals(data.signals);
            if (data.audit) setAuditEvents(data.audit);
            if (data.candles) {
              setCandlesByInstrument({
                'SYNTH/BTC': data.candles['SYNTH/BTC'] || [],
                'SYNTH/ETH': data.candles['SYNTH/ETH'] || [],
              });
            }
          } else if (type === 'balance_update' && data) {
            setBalance(data);
          } else if (type === 'price_update' && data) {
            const inst = data.instrument as Instrument;
            setLatestQuote((prev) => ({ ...prev, [inst]: data }));
            if (data.candle) {
              setCandlesByInstrument((prev) => {
                const list = [...(prev[inst] || [])];
                const last = list[list.length - 1];
                if (last && last.time === data.candle.time) {
                  list[list.length - 1] = data.candle;
                } else if (!last || data.candle.time > last.time) {
                  list.push(data.candle);
                }
                return { ...prev, [inst]: list.slice(-250) };
              });
            }
          } else if (type === 'signal' && data) {
            setSignals((prev) => [data, ...prev.filter((s) => s.signal_id !== data.signal_id)].slice(0, 60));
          } else if (type === 'risk_decision' && data) {
            setRiskDecision(data);
          } else if (type === 'order_fill' && data) {
            setOrders((prev) => [data, ...prev.filter((o) => o.order_id !== data.order_id)].slice(0, 100));
          } else if (type === 'position_update' && data) {
            if (data.positions) setPositions(data.positions);
            setStatus((prev) => ({
              ...prev,
              positions: data.positions || prev.positions,
              realized_pnl: data.realized_pnl ?? prev.realized_pnl,
              unrealized_pnl: data.unrealized_pnl ?? prev.unrealized_pnl,
              total_pnl: data.total_pnl ?? prev.total_pnl,
            }));
          } else if (type === 'cycle_complete' && data) {
            if (data.status) setStatus(data.status);
            if (data.audit) setAuditEvents(data.audit);
          }
        } catch (err) {
          console.error('Error parsing WebSocket payload:', err);
        }
      };

      ws.onclose = () => {
        if (!unmounted) {
          setConnected(false);
          reconnectTimerRef.current = window.setTimeout(connect, 2000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    return () => {
      unmounted = true;
      clearInterval(balanceInterval);
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [fetchInitialRestFallback, fetchBalance]);

  return {
    connected,
    status,
    setStatus,
    balance,
    setBalance,
    fetchBalance,
    positions,
    orders,
    signals,
    riskDecision,
    auditEvents,
    candlesByInstrument,
    latestQuote,
    refreshAll: fetchInitialRestFallback,
  };
}
