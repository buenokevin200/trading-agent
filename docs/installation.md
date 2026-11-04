# Trading System — Guía de instalación y operación

## Instalación

```bash
cd ~/trading-system
# No requiere dependencias externas — solo Python 3.12+ stdlib
python3 tests/test_all.py     # ejecutar pruebas (16/16 deben pasar)
python3 demo.py               # demostración sintética
```

## Arranque

```bash
# Modo simulación (único modo disponible)
python3 demo.py
```

El sistema arranca en modo `simulation`. No hay modo real activado ni conectable.

## Pausa / Reanudación / Parada

El orquestador expone:
- `orchestrator.pause()` — pausa el ciclo, mantiene vigilancia de posiciones
- `orchestrator.resume()` — reanuda el ciclo
- `Ctrl+C` — parada controlada, el estado persiste en `data/audit.jsonl`

## Recuperación tras reinicio

- El audit log es append-only y persistente (`data/audit.jsonl`)
- El lock de executor (`/tmp/trading-executor.lock`) detecta stale locks
- Las autorizaciones usadas se registran en el risk engine
- La idempotencia previene reenvíos duplicados

## Resolución de fallos

| Fallo | Síntoma | Solución |
|-------|---------|----------|
| Stale lock | "Another executor is active" | `rm /tmp/trading-executor.lock` |
| Audit corrupto | `verify_chain()` retorna False | Revisar `data/audit.jsonl` manualmente |
| Límites no configurados | R001 en auditoría | Editar `config/example_config.yaml` |

## Perfiles Hermes

Creados en `~/.hermes/profiles/`:
- `trading-orchestrator` (glm-5.2)
- `trading-researcher` (glm-5.2)
- `trading-strategist` (glm-5.2)
- `trading-risk` (glm-5.2)
- `trading-executor` (glm-5.2)

Verificar: `hermes profile list | grep trading`
