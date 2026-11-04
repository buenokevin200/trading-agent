export type Instrument = 'SYNTH/BTC' | 'SYNTH/ETH';

export type SignalType = 'BUY' | 'SELL' | 'NO_OPERATION';

export interface CandleBar {
  time: number; // Unix timestamp in seconds
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface PriceUpdateEvent {
  instrument: Instrument;
  price: number;
  bid: number;
  ask: number;
  volume: number;
  timestamp: string;
  candle: CandleBar;
}

export interface SignalEvent {
  signal_id: string;
  signal_type: SignalType;
  instrument: Instrument;
  entry_price: number;
  stop_loss: number | null;
  take_profit: number | null;
  rules_triggered: string[];
  timestamp: string;
  chart_time?: number;
}

export interface RiskDecisionEvent {
  decision_id: string;
  signal_id: string;
  instrument: Instrument;
  approved: boolean;
  rejection_code: string | null;
  rejection_reason: string | null;
  approved_quantity: number;
  risk_amount: number;
  timestamp: string;
}

export interface OrderItem {
  order_id: string;
  instrument: Instrument;
  side: 'BUY' | 'SELL';
  quantity: number;
  status: 'filled' | 'rejected' | 'pending';
  fill_price: number;
  commission: number;
  timestamp: string;
  stop_loss?: number | null;
  take_profit?: number | null;
  reason?: string | null;
}

export interface PositionItem {
  instrument: Instrument;
  side: 'LONG' | 'SHORT';
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  is_protected: boolean;
  stop_loss?: number | null;
  take_profit?: number | null;
  opened_at?: string;
}

export interface RiskLimits {
  reference_capital: number;
  risk_per_trade: number;
  max_exposure: number;
  max_daily_loss: number;
  max_drawdown: number;
  max_positions: number;
  allowed_instruments?: string[];
  limits_configured?: boolean;
}

export interface AuditEvent {
  timestamp: string;
  event_type: string;
  agent: string;
  data: Record<string, unknown>;
  prev_hash?: string;
  hash?: string;
}

export interface SystemStatus {
  mode: string;
  system_source?: string;
  cycle_count: number;
  paused: boolean;
  emergency_stop: boolean;
  limits_configured: boolean;
  active_instrument: Instrument;
  cycle_frequency_sec: number;
  positions: PositionItem[];
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  total_orders: number;
  risk_limits: RiskLimits;
  last_risk_decision?: RiskDecisionEvent | null;
}
