"""Binance Balance Service (Simulation & Paper Testnet) — SPEC-002.

SECURITY RULES:
- API keys are read ONLY from environment variables in the backend.
- API keys are NEVER exposed to the frontend or committed to source control.
- Real trading mode ('real') is strictly blocked per SPEC-002.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class BinanceBalanceService:
    TESTNET_BASE_URL = "https://testnet.binance.vision"

    def __init__(self, default_reference_capital: float = 10000.0) -> None:
        self.broker_name: str = os.getenv("BROKER_NAME", "binance")
        self.mode: str = os.getenv("BROKER_MODE", "simulation").lower()  # simulation | paper
        self.testnet: bool = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
        self.refresh_sec: int = int(os.getenv("BALANCE_REFRESH_SEC", "5"))
        self.reference_capital: float = float(
            os.getenv("REFERENCE_CAPITAL", str(default_reference_capital))
        )
        self.simulate_offline: bool = False

    def set_mode(
        self,
        mode: str,
        reference_capital: Optional[float] = None,
        simulate_offline: Optional[bool] = None,
    ) -> None:
        normalized = mode.lower().strip()
        if normalized not in ("simulation", "paper", "real"):
            raise ValueError(f"Invalid broker mode: {mode}")
        self.mode = normalized
        if reference_capital is not None and reference_capital > 0:
            self.reference_capital = float(reference_capital)
        if simulate_offline is not None:
            self.simulate_offline = bool(simulate_offline)

    def _has_api_credentials(self) -> bool:
        api_key = os.getenv("BINANCE_API_KEY", "").strip()
        api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
        return bool(api_key and api_secret)

    def _fetch_testnet_usdt_balance(self) -> Dict[str, float]:
        """Read-only call to Binance Spot Testnet /api/v3/account."""
        api_key = os.getenv("BINANCE_API_KEY", "").strip()
        api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
        if not api_key or not api_secret:
            raise RuntimeError("Credenciales de Binance Testnet no configuradas en .env")

        timestamp = int(time.time() * 1000)
        query_string = urllib.parse.urlencode({"timestamp": timestamp, "recvWindow": 5000})
        signature = hmac.new(
            api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        url = f"{self.TESTNET_BASE_URL}/api/v3/account?{query_string}&signature={signature}"
        req = urllib.request.Request(
            url,
            headers={"X-MBX-APIKEY": api_key, "Accept": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        balances = payload.get("balances", [])
        usdt = next((b for b in balances if b.get("asset") == "USDT"), None)
        free_amt = float(usdt.get("free", 0.0)) if usdt else 0.0
        locked_amt = float(usdt.get("locked", 0.0)) if usdt else 0.0
        return {"free": free_amt, "locked": locked_amt}

    def get_balance(
        self,
        positions: List[Dict[str, Any]],
        realized_pnl: float = 0.0,
        config_reference_capital: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Compute or fetch current budget/balance according to SPEC-002."""
        now_iso = datetime.now(timezone.utc).isoformat()
        ref_cap = (
            float(config_reference_capital)
            if config_reference_capital is not None and config_reference_capital > 0
            else self.reference_capital
        )

        # Calculate position margin used and unrealized PnL from open positions
        used_capital = round(
            sum(
                abs(float(p.get("quantity", 0.0)) * float(p.get("entry_price", 0.0)))
                for p in positions
            ),
            2,
        )
        unrealized_pnl = round(
            sum(float(p.get("unrealized_pnl", 0.0)) for p in positions),
            2,
        )
        realized = round(float(realized_pnl), 2)

        # If simulated offline flag is enabled, return unreachable state for UI warning verification
        if self.simulate_offline:
            return {
                "broker": self.broker_name,
                "mode": self.mode,
                "testnet": self.testnet,
                "connected": False,
                "currency": "USDT",
                "reference_capital": ref_cap,
                "available_capital": None,
                "used_capital": None,
                "total_capital": None,
                "realized_pnl": realized,
                "unrealized_pnl": unrealized_pnl,
                "refresh_sec": self.refresh_sec,
                "warning": "Binance API no responde (timeout / desconexión detectada)",
                "updated_at": now_iso,
            }

        # Block real mode per SPEC-002
        if self.mode == "real":
            return {
                "broker": self.broker_name,
                "mode": "real",
                "testnet": False,
                "connected": False,
                "currency": "USDT",
                "reference_capital": ref_cap,
                "available_capital": None,
                "used_capital": None,
                "total_capital": None,
                "realized_pnl": realized,
                "unrealized_pnl": unrealized_pnl,
                "refresh_sec": self.refresh_sec,
                "warning": "Modo REAL bloqueado por política de seguridad (SPEC-002)",
                "updated_at": now_iso,
            }

        # Paper mode with Binance Testnet
        if self.mode == "paper":
            if not self._has_api_credentials():
                # Per SPEC-002 line 49: If no Binance credentials configured, fall back to synthetic reference capital
                # or if explicitly testing paper connection without keys, note fallback in source
                total_capital = round(ref_cap + realized + unrealized_pnl, 2)
                available_capital = round(max(0.0, total_capital - used_capital), 2)
                return {
                    "broker": self.broker_name,
                    "mode": "paper",
                    "source": "paper_synthetic_fallback",
                    "testnet": True,
                    "connected": True,
                    "currency": "USDT",
                    "reference_capital": ref_cap,
                    "available_capital": available_capital,
                    "used_capital": used_capital,
                    "total_capital": total_capital,
                    "realized_pnl": realized,
                    "unrealized_pnl": unrealized_pnl,
                    "refresh_sec": self.refresh_sec,
                    "warning": "Sin API key en .env — usando balance sintético de referencia",
                    "updated_at": now_iso,
                }
            try:
                testnet_bal = self._fetch_testnet_usdt_balance()
                available_capital = round(testnet_bal["free"], 2)
                used_capital_paper = round(max(testnet_bal["locked"], used_capital), 2)
                total_capital = round(available_capital + used_capital_paper + unrealized_pnl, 2)
                return {
                    "broker": self.broker_name,
                    "mode": "paper",
                    "source": "binance_testnet",
                    "testnet": True,
                    "connected": True,
                    "currency": "USDT",
                    "reference_capital": ref_cap,
                    "available_capital": available_capital,
                    "used_capital": used_capital_paper,
                    "total_capital": total_capital,
                    "realized_pnl": realized,
                    "unrealized_pnl": unrealized_pnl,
                    "refresh_sec": self.refresh_sec,
                    "warning": None,
                    "updated_at": now_iso,
                }
            except Exception as exc:
                return {
                    "broker": self.broker_name,
                    "mode": "paper",
                    "source": "binance_testnet",
                    "testnet": True,
                    "connected": False,
                    "currency": "USDT",
                    "reference_capital": ref_cap,
                    "available_capital": None,
                    "used_capital": None,
                    "total_capital": None,
                    "realized_pnl": realized,
                    "unrealized_pnl": unrealized_pnl,
                    "refresh_sec": self.refresh_sec,
                    "warning": f"Binance Testnet no responde: {exc}",
                    "updated_at": now_iso,
                }

        # Default: SIMULATION mode
        total_capital = round(ref_cap + realized + unrealized_pnl, 2)
        available_capital = round(max(0.0, total_capital - used_capital), 2)
        return {
            "broker": self.broker_name,
            "mode": "simulation",
            "source": "synthetic_config",
            "testnet": self.testnet,
            "connected": True,
            "currency": "USDT",
            "reference_capital": ref_cap,
            "available_capital": available_capital,
            "used_capital": used_capital,
            "total_capital": total_capital,
            "realized_pnl": realized,
            "unrealized_pnl": unrealized_pnl,
            "refresh_sec": self.refresh_sec,
            "warning": None,
            "updated_at": now_iso,
        }
