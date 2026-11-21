# HU-30 — Seguimiento de tareas

## 1. Spec-first
- [x] Revisar SPEC-031 y flujos actuales de CSV, `outputs/` y `/health`.
- [x] Elegir CSV transaccional y documentar trade-offs en `plan.md`.
- [x] Crear `tasks.md`.

## 2. AC1 — Registro concurrente
- [ ] Implementar lock entre procesos y threads para cada registro CSV.
- [ ] Deduplicar por ID y publicar con reemplazo atómico.
- [ ] Preservar contrato y sanitización HU-06.
- [ ] Probar concurrencia y duplicados.

## 3. AC2 — Backup y restore
- [ ] Crear comandos de backup y restore.
- [ ] Verificar restauración byte a byte, escritura atómica y ruta inexistente.

## 4. AC3 — Readiness
- [ ] Implementar `/ready` con detalle de dependencia y HTTP 503.
- [ ] Comprobar `/health` inalterado y simular modelo sin configurar.

## 5. AC4 — Retención
- [ ] Implementar política configurable de `outputs/`.
- [ ] Ejecutar retención automáticamente sin tocar trabajos activos.
- [ ] Probar artefactos vencidos, vigentes y rutas seguras.

## 6. Calidad y entrega
- [ ] Ejecutar Pytest de HU-30 y regresión de registro/API.
- [ ] Ejecutar Ruff, medir cobertura y revisar el diff.
- [ ] Crear `evidence.md` con resultados reales.
- [ ] Publicar commit y PR hacia `main`, para revisión de Luis.
- [ ] Verificar GitHub Actions antes del merge.
