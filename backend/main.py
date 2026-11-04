"""FastAPI + WebSocket backend for the Multi-Agent Synthetic Trading Dashboard.

SIMULATION ONLY — NO REAL BROKER — NO CREDENTIALS.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cycle_runner import CycleRunner
from ws_manager import WebSocketManager

load_dotenv()

CYCLE_FREQUENCY_SEC = float(os.getenv("CYCLE_FREQUENCY_SEC", "5"))

ws_manager = WebSocketManager()
runner = CycleRunner(ws_manager=ws_manager, frequency_sec=CYCLE_FREQUENCY_SEC)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await runner.start()
    yield
    await runner.stop()


app = FastAPI(
    title="Multi-Agent Trading System Dashboard API (SIMULATION)",
    description="Synthetic simulation dashboard API — NO REAL BROKER, NO CREDENTIALS.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CycleRequest(BaseModel):
    instrument: Optional[str] = None


class ConfigRequest(BaseModel):
    instrument: Optional[str] = None
    frequency_sec: Optional[float] = None


class EmergencyStopRequest(BaseModel):
    reason: Optional[str] = "Manual operator activation from dashboard"
    reset: Optional[bool] = False


@app.get("/api/status")
async def get_status() -> Dict[str, Any]:
    return runner.get_status()


@app.get("/api/positions")
async def get_positions() -> Dict[str, Any]:
    status = runner.get_status()
    return {
        "mode": "SIMULATION",
        "positions": runner.get_positions(),
        "realized_pnl": status["realized_pnl"],
        "unrealized_pnl": status["unrealized_pnl"],
        "total_pnl": status["total_pnl"],
    }


@app.get("/api/orders")
async def get_orders(status: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    orders = runner.get_orders()
    if status and status != "all":
        orders = [o for o in orders if str(o.get("status", "")).lower() == status.lower()]
    return {
        "mode": "SIMULATION",
        "orders": orders,
    }


@app.get("/api/signals")
async def get_signals(limit: int = Query(default=50, ge=1, le=200)) -> Dict[str, Any]:
    return {
        "mode": "SIMULATION",
        "signals": runner.get_signals(limit=limit),
    }


@app.get("/api/audit")
async def get_audit(limit: int = Query(default=20, ge=1, le=200)) -> Dict[str, Any]:
    return {
        "mode": "SIMULATION",
        "events": runner.get_audit(limit=limit),
    }


@app.get("/api/candles")
async def get_candles(
    instrument: str = Query(default="SYNTH/BTC"),
    limit: int = Query(default=120, ge=10, le=300),
) -> Dict[str, Any]:
    return {
        "mode": "SIMULATION",
        "instrument": instrument,
        "candles": runner.get_candles(instrument=instrument, limit=limit),
    }


@app.post("/api/cycle")
async def run_manual_cycle(req: Optional[CycleRequest] = None) -> Dict[str, Any]:
    inst = req.instrument if req and req.instrument else runner.active_instrument
    result = await runner.execute_and_broadcast_cycle(instrument=inst)
    return {
        "mode": "SIMULATION",
        "result": result,
        "status": runner.get_status(),
    }


@app.post("/api/pause")
async def pause_system() -> Dict[str, Any]:
    runner.orch.pause()
    status = runner.get_status()
    await ws_manager.broadcast(
        "cycle_complete",
        {
            "cycle_count": status["cycle_count"],
            "instrument": runner.active_instrument,
            "status": status,
            "audit": runner.get_audit(limit=20),
        },
    )
    return status


@app.post("/api/resume")
async def resume_system() -> Dict[str, Any]:
    runner.orch.resume()
    status = runner.get_status()
    await ws_manager.broadcast(
        "cycle_complete",
        {
            "cycle_count": status["cycle_count"],
            "instrument": runner.active_instrument,
            "status": status,
            "audit": runner.get_audit(limit=20),
        },
    )
    return status


@app.post("/api/emergency-stop")
async def emergency_stop(req: Optional[EmergencyStopRequest] = None) -> Dict[str, Any]:
    if req and req.reset:
        if hasattr(runner.orch, "reset_emergency_stop"):
            runner.orch.reset_emergency_stop()
        else:
            runner.orch.emergency_stop = False
    else:
        reason = req.reason if req and req.reason else "Manual operator activation"
        if hasattr(runner.orch, "activate_emergency_stop"):
            runner.orch.activate_emergency_stop(reason=reason)
        else:
            runner.orch.emergency_stop = True
            runner.orch.pause()

    status = runner.get_status()
    await ws_manager.broadcast(
        "cycle_complete",
        {
            "cycle_count": status["cycle_count"],
            "instrument": runner.active_instrument,
            "status": status,
            "audit": runner.get_audit(limit=20),
        },
    )
    return status


@app.post("/api/config")
async def update_config(req: ConfigRequest) -> Dict[str, Any]:
    if req.instrument in ("SYNTH/BTC", "SYNTH/ETH"):
        runner.active_instrument = req.instrument
    if req.frequency_sec is not None:
        runner.frequency_sec = max(1.0, min(60.0, float(req.frequency_sec)))
    status = runner.get_status()
    await ws_manager.broadcast(
        "cycle_complete",
        {
            "cycle_count": status["cycle_count"],
            "instrument": runner.active_instrument,
            "status": status,
            "audit": runner.get_audit(limit=20),
        },
    )
    return status


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        # Send initial state snapshot immediately on connect
        await websocket.send_json(
            {
                "type": "initial_state",
                "data": {
                    "status": runner.get_status(),
                    "positions": runner.get_positions(),
                    "orders": runner.get_orders(),
                    "signals": runner.get_signals(limit=50),
                    "audit": runner.get_audit(limit=20),
                    "candles": {
                        "SYNTH/BTC": runner.get_candles("SYNTH/BTC", limit=120),
                        "SYNTH/ETH": runner.get_candles("SYNTH/ETH", limit=120),
                    },
                },
            }
        )
        while True:
            # Keep connection alive and handle optional client pings/commands
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_json({"type": "pong", "data": {}})
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)
