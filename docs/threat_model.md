# Modelo de amenazas y límites conocidos

## Activos

1. **Datos sintéticos** — generados localmente, no requieren protección
2. **Audit log** — append-only con hash chain, tamper detection
3. **Autorizaciones** — single-use, parameter-bound, expiring
4. **Risk engine** — determinista, independiente del modelo
5. **Perfiles Hermes** — aislados, sin credenciales de trading

## Amenazas identificadas

| ID | Amenaza | Vector | Mitigación | Residual |
|----|---------|--------|------------|----------|
| T1 | Prompt injection desde datos | Metadata en observaciones | Risk engine ignora metadata; evalúa solo config | Bajo |
| T2 | Reuso de autorización | Intento de reusar auth usada | Single-use + tracking en risk engine | Bajo |
| T3 | Parámetros alterados | Modificar intent vs auth | Validación exacta de parámetros | Bajo |
| T4 | Doble executor | Dos procesos ejecutores | File-based lock con PID check | Medio (lock no distribuido) |
| T5 | Fallo del modelo | Provider cae o presupuesto agotado | Motores deterministas siguen funcionando | Bajo |
| T6 | Tamper audit | Modificar audit.jsonl | Hash chain verification | Medio (no immutabilidad absoluta) |
| T7 | Datos vencidos | Observaciones stale | max_data_age_sec + quality check | Bajo |
| T8 | Emergency stop bypass | Intentar operar con stop activo | Check en risk engine antes de cualquier exposición | Bajo |
| T9 | Modo real activado sin autorización | Cambiar mode a "real" | No hay código de modo real; solo simulación | Bajo |
| T10 | Secretos en contexto del modelo | API keys en SOUL/memory | Secretos solo en servicio aislado; SOUL no los contiene | Bajo |

## Límites conocidos

1. **No immutabilidad absoluta del audit** — es append-only a nivel aplicación, no a nivel OS. Un atacante con acceso al filesystem puede modificar el archivo. La detección de tamper funciona pero no previene la modificación.

2. **Lock de executor no distribuido** — el file-based lock funciona en un solo host. Para multi-host se necesitaría un lock distribuido (Redis, etcd).

3. **Simulador no modela liquidez real** — el simulador asume liquidez infinita. Un broker real puede rechazar órdenes por falta de liquidez.

4. **No hay separación temporal de datos** — la demo usa datos sintéticos sin separación train/validation/test. Una estrategia real requeriría esto antes de cualquier evaluación.

5. **Stop-loss no garantiza pérdida máxima** — gaps, deslizamiento y rechazos del broker pueden hacer que el fill ocurra peor que el stop. El sistema detecta el hit del stop pero no garantiza el precio de ejecución.

6. **No hay broker real conectado** — el contrato `BrokerAdapter` está definido pero sin implementación verificada. Cualquier integración futura requiere verificación.

7. **Modelo único (glm-5.2)** — todos los perfiles usan el mismo modelo. La diversidad de modelos (sugerida en la spec) no está implementada porque solo glm-5.2 está disponible.

## No soportado

- Modo real / paper trading con broker verificado
- Withdrawals / transfers
- Apalancamiento / posiciones cortas
- Multi-host deployment
- Estrategias complejas (solo SMA cross de prueba)
- Datos de mercado reales
- Presupuesto de modelos medido
- Canal de alertas (Telegram/email)
