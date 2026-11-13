# HU-16 — Seguimiento de tareas: MLflow

- **Responsable**: Luis Meza
- **Rama**: `feature/hu-16-mlflow`
- **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

## 1. Módulo de seguimiento

- [ ] `uv add mlflow-skinny` y verificar que `uv.lock` queda actualizado.
- [ ] Crear `src/m2_cad/seguimiento.py` con `iniciar_corrida`, `registrar_params`,
      `registrar_metricas`, `registrar_tags`, `registrar_artefactos` y `finalizar`.
- [ ] Implementar el modo no-op para `MLFLOW_TRACKING_ENABLED=0` y para URI inválida.
- [ ] Reutilizar `_sanitizar` de `registro.py` en todo texto registrado (AC5).
- [ ] Escribir pruebas del módulo contra `tmp_path/mlruns` (sin red).

## 2. Instrumentación del pipeline y la API (AC2, AC3)

- [ ] Añadir contexto de seguimiento opcional a `pipeline.generar_pieza` sin cambiar su
      firma pública usada por las pruebas existentes.
- [ ] Medir latencia extremo a extremo en `api.procesar_con_pipeline`.
- [ ] Registrar `programa.json`, `step`, `glb` y `bom_csv` desde `outputs/<uuid>/`.
- [ ] Cerrar con `estado=entregada` en éxito, `declinada` con `motivo_declinacion`, y
      `error` con la clase de la excepción.
- [ ] Garantizar que ninguna corrida queda en `RUNNING` (prueba explícita).

## 3. Banco comparativo (AC4, AC7)

- [ ] Registrar la versión de modelo servida (`deepseek-v4-pro`, GGUF heredado) como
      parámetro y versión de modelo.
- [ ] Abrir corrida padre por modelo en `m2-cad-banco` con los precios de entrada/salida.
- [ ] Registrar una corrida hija por caso con `acierto`, `dsl_check_ok` y
      `error_relativo_pct`.
- [ ] Volcar el resumen de `resumir` como métricas de la corrida padre.
- [ ] Eliminar el marcador `version="desconocida"` del registro (AC7).

## 4. Degradación segura (AC6)

- [ ] Capturar excepciones del cliente MLflow y emitir advertencia, nunca propagar.
- [ ] Prueba con URI inalcanzable: la generación concluye igual.
- [ ] Medir sobrecarga con backend local y documentar el valor obtenido (≤ 50 ms p95).

## 5. Despliegue (AC1)

- [ ] Añadir servicio `mlflow` a `docker-compose.yml` con imagen fija y volumen `/mlflow`.
- [ ] Conectar `m2-cad` con `MLFLOW_TRACKING_URI=http://mlflow:5000`.
- [ ] Añadir objetivo `make mlflow` al Makefile.
- [ ] Publicar el puerto solo en `127.0.0.1:5000`.
- [ ] Ignorar `mlruns/`, `mlflow.db` y los artefactos volcados en `.gitignore`.
- [ ] Verificar `docker compose config --quiet` y `curl -I http://127.0.0.1:5000`.

## 6. Documentación

- [ ] Documentar las variables nuevas en el README y en `.env.example`.
- [ ] Actualizar `CONSTITUTION.md` en el mismo commit: §0 estado, §3 stack, §4 estructura
      (módulo `seguimiento.py`), §9 historial de decisiones.
- [ ] Crear `evidence.md` con las capturas de las dos corridas comparadas.

## 7. Validación final

- [ ] `make check` (Ruff + pytest) sin errores.
- [ ] `make cov` ≥ 70 %.
- [ ] `make bench` con dos modelos registrando corridas comparables.
- [ ] Verificar AC5 con el corpus de HU-06 (0 correos, 0 nombres).
- [ ] Abrir el PR hacia `develop` y solicitar revisión.

## 8. Estado general

**HU-16 no iniciada.** Planificada en `specs/009-hu-16-mlflow/`; sin código ni
dependencia instalada todavía. No se marca ninguna tarea como hecha hasta observar su
resultado (prueba, comando o captura).
