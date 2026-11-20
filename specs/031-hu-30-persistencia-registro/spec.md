# SPEC-031 · HU-30 — Persistencia transaccional, retención y backup del registro

- **ID**: SPEC-031
- **Historia**: issue por crear · Ola 1 · Tamaño M · Épica: Backend
- **Responsable**: Juan Camilo Pérez
- **Depende de**: —
- **Rama**: `feature/hu-30-persistencia-registro`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §4

## Problema y contexto

El registro de solicitudes (HU-06, [SPEC-004](../004-registro-solicitudes/spec.md)) es la
fuente de las métricas de los objetivos 1 y 2, pero su escritura no es segura bajo
concurrencia:

1. `data/registro.csv` se escribe en modo anexado con `open(ruta, "a", ...)`
   (`src/m2_cad/registro.py:89`), sin lock, sin escritura atómica (`os.replace`) y sin
   deduplicación por `id` (`src/m2_cad/registro.py:74-93`).
2. El gestor admite hasta 128 trabajos y cada uno corre en su propio hilo
   (`src/m2_cad/trabajos.py:144-170`), así que varias escrituras pueden coincidir.
3. Cada pieza crea un directorio nuevo en `outputs/` (`src/m2_cad/pipeline.py:434-435`)
   y nada lo depura: `outputs/` crece sin política de retención.
4. Solo existe `/health`, que responde `ok` sin consultar dependencias
   (`src/m2_cad/api.py:54-57`); no hay `/ready` ni comando de backup/restore.

## Historia de usuario

**Como** operador del servicio, **quiero** que el registro se escriba de forma
transaccional, se pueda respaldar y restaurar, y que `outputs/` tenga retención,
**para** no perder ni duplicar filas bajo carga y poder recuperar el estado tras un fallo.

## Requisitos

### Funcionales

- **RF-1**: la escritura del registro es atómica y serializada. La forma queda abierta
  como decisión de `plan.md`: escritura atómica sobre el CSV **o** migración a SQLite con
  esquema versionado.
- **RF-2**: el registro deduplica por `id`: reescribir una solicitud ya registrada no
  crea una segunda fila.
- **RF-3**: la retención de `outputs/` es configurable y se aplica sin intervención manual.
- **RF-4**: un comando de backup produce una copia del registro y un comando de restore
  la reinstala.
- **RF-5**: `/ready` comprueba las dependencias del servicio y falla si el modelo no está
  disponible; `/health` conserva su contrato actual.

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU: el modelo y la carga concurrente
  se simulan.
- **RNF-2**: se conservan las reglas de SPEC-004: ningún campo vacío (AC3) y exclusión de
  nombres y correos (AC4).
- **RNF-3**: los consumidores actuales del registro (`/registros/{id}`, el banco y el
  reporte de HU-07) siguen leyendo las mismas columnas.
- **Supuesto**: si se migra a SQLite, se ofrece una exportación al CSV actual para no
  romper a esos consumidores.

## Criterios de aceptación

### AC1 — Concurrencia sin pérdida ni duplicados

- **Dado** el servicio con el procesador simulado
- **Cuando** se lanzan N solicitudes concurrentes
- **Entonces** el registro contiene exactamente N filas, una por `id`, sin filas
  perdidas, truncadas ni duplicadas.

### AC2 — Restore exacto

- **Dado** un registro con filas y un backup tomado con el comando de backup
- **Cuando** se borra o altera el registro y se ejecuta el restore
- **Entonces** el registro restaurado es idéntico al respaldado.

### AC3 — `/ready` con el modelo caído

- **Dado** el servicio sin modelo disponible
- **Cuando** se consulta `/ready`
- **Entonces** responde con un código de error y nombra la dependencia que falla,
  mientras `/health` sigue respondiendo `ok`.

### AC4 — Retención de `outputs/`

- **Dado** una retención configurada y artefactos más antiguos que ella en `outputs/`
- **Cuando** se aplica la política
- **Entonces** se eliminan los artefactos vencidos y se conservan los vigentes.

## Fuera de alcance

- Base de datos externa o servicio gestionado (despliegue en nube,
  [SPEC-048](../048-hu-47-despliegue-nube/spec.md)).
- Cola persistente de trabajos ([SPEC-046](../046-hu-45-cola-persistente/spec.md)).
- Expiración y autorización de descargas
  ([SPEC-037](../037-hu-36-endurecimiento-descargas/spec.md)).

## Métricas de éxito

- 0 filas perdidas y 0 duplicadas en la prueba concurrente.
- Restore idéntico byte a byte (CSV) o fila a fila (SQLite).
- Tamaño de `outputs/` acotado por la retención configurada.
