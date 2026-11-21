# SPEC-031 — HU-30: Plan técnico

## Objetivo
Garantizar registro sin pérdida ni duplicados bajo concurrencia, backup/restore, retención
configurable de `outputs/` y `/ready` con fallos identificables, manteniendo el contrato
CSV de HU-06 y los consumidores actuales.

## Decisión de persistencia
Mantener `data/registro.csv` y las columnas de `registro.CAMPOS`. Escribir cada operación
como transacción: adquirir bloqueo estable por ruta (`.lock`), leer/deduplicar por `id`,
escribir el CSV completo a un temporal en el mismo directorio, `flush` + `fsync` y
`os.replace`. El bloqueo es entre hilos y procesos (fcntl en POSIX y msvcrt en Windows).
El bloqueo permanece en un archivo separado para que el reemplazo del CSV no invalide
los bloqueos de otras solicitudes. Ante `id` repetido, conservar y devolver la fila
registrada primero (idempotencia); no se modifica su contenido.

Costos: la estrategia reescribe el CSV completo (O(N) por inserción). Es apropiada para
el tamaño del prototipo; si escala, evaluar SQLite con exportación compatible.

## AC1: concurrencia
Pruebas con ThreadPoolExecutor: filas exactas e IDs únicos; duplicados conservan
la primera fila, columnas inalteradas y sanitización HU-06.

## AC2: backup/restore
CLI `python -m m2_cad.persistencia_registro backup --registro ... --destino ...`
y `restore --registro ... --origen ...`. Backup obtiene instantánea con el mismo lock,
escribe a temporal y reemplaza en destino. Restore valida la cabecera antes de reemplazar
de forma atómica, bajo lock; compara bytes antes/después en pruebas.
No sobrescribir backups preexistentes. Mantener backups fuera del repositorio.

## AC3: disponibilidad (etapa posterior)
Agregar `GET /ready` con HTTP 503 y dependencia explícita cuando falta la configuración
del modelo; verificar también accesibilidad del registro. Conservar `GET /health`.
La comprobación del modelo será local (configuración), sin consumir API externa.

## AC4: retención (etapa posterior)
Política de retención configurable para subcarpetas de `outputs/`, con activación
automática en el ciclo de vida; no borrar directorios activos ni seguir symlinks.
Probar vencidos/vigentes con directorio temporal y reloj controlado. No confundir
retención física con la expiración de credenciales de HU-36.

## Compatibilidad y seguridad
- Mantener nombre, firma y retorno de `registrar()`.
- Mantener 8 columnas, marcadores no vacíos y sanitización de nombres/correos.
- No modificar el motor CAD ni los endpoints de descarga de HU-36.
- No incluir datos de producción, backups ni secretos en Git.
- Sin DeepSeek, red externa, GPU ni CadQuery en pruebas unitarias de HU-30.

## Validación y entrega
Pytest focalizado, regresión de `test_registro.py`/API, Ruff, cobertura, CI y PR hacia
`main`. Documentar restricciones y evidencia real en `evidence.md`.

## AC4 — Retención automática (implementada)

La retención se activa al iniciar FastAPI **solo cuando** está definida la variable
`M2_OUTPUT_RETENTION_DAYS` (ejemplo: `7`). `M2_OUTPUT_SWEEP_SECONDS` determina
el intervalo de comprobación (por defecto, 3600 segundos). Sin la primera
variable, la limpieza queda desactivada para no borrar artefactos de instalaciones
existentes sin una decisión explícita del operador.

La limpieza se ejecuta al inicio y luego periódicamente en segundo plano, solo
si el gestor no tiene generaciones activas. Elimina subcarpetas con nombres UUID
hexadecimales cuando su última modificación (incluidos archivos contenidos) es
más antigua que la política. Ignora symlinks y otras carpetas. No borra el CSV.

**Limitación:** la política usa antigüedad de archivos, no vencimiento de tokens.
En despliegues con múltiples réplicas es necesario coordinar su actividad sobre
el almacenamiento compartido antes de permitir limpiezas concurrentes.
