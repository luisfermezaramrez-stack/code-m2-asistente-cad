# SPEC-010 · HU-10 — Servicio desplegado en local con Docker Compose

- **ID**: SPEC-010
- **Historia**: #10 · 2 SP · Etiquetas: Backend · CPM: M (día 12) y N (día 13)
- **Responsable**: Juan Camilo Pérez (I2 · Servicio e interfaz)
- **Rama**: `feature/hu-10-despliegue-local`
- **Estado**: Especificada, pendiente de implementación
- **Plan**: [`plan.md`](./plan.md) · **Tareas**: [`tasks.md`](./tasks.md)

## Problema y contexto

El evaluador necesita levantar el servicio completo en su equipo y medir su latencia
sin depender de infraestructura remota. La versión original de la historia pedía HTTPS
sobre una GPU alquilada; desde HU-14 el modelo es DeepSeek por API y desde HU-15 la
interfaz es una SPA en Vue servida por FastAPI, así que el despliegue puede ser local,
sin GPU y con un solo origen.

> **Cambio de alcance (2026-11-13):** se reemplaza el despliegue HTTPS en la GPU
> alquilada por un despliegue local. Se eliminan el criterio de HTTPS y el registro de
> horas de GPU facturadas. Gemma con llama.cpp queda como opción en
> `docker-compose.gemma.yml`.
>
> **Ajuste por HU-15 (2026-11-13):** la interfaz Gradio en `:7860` ya no existe; la SPA
> en Vue se sirve desde el mismo origen que la API (`:8000`).

## Historia de usuario

Como evaluador, quiero levantar el servicio completo en mi equipo con Docker Compose y
usarlo desde `localhost`, para probarlo y medir su latencia sin depender de
infraestructura remota.

## Requisitos

### Funcionales

- **RF-1**: `make up` levanta API + SPA y el servidor MLflow con `docker compose up`.
- **RF-2**: la SPA y la API comparten el origen `http://localhost:8000`; MLflow queda en
  `http://127.0.0.1:5000`.
- **RF-3**: un script de humo envía solicitudes del banco a `POST /generar` del
  servicio desplegado y reporta éxito y latencia por solicitud.
- **RF-4**: `make down` detiene todos los contenedores del proyecto.

### No funcionales

- **RNF-1**: sin GPU; el único secreto es `DEEPSEEK_API_KEY` en `.env` (ignorado por git).
- **RNF-2**: latencia p90 ≤ 60 s sobre al menos 30 solicitudes del banco.
- **RNF-3**: los puertos solo escuchan en `127.0.0.1`/`localhost`; nada se expone a
  Internet.

## Criterios de aceptación

### AC1 — Arranque con un solo comando

- **Dado** una máquina limpia con Docker y un `.env` que solo define `DEEPSEEK_API_KEY`
- **Cuando** se ejecuta `make up`
- **Entonces** los contenedores de la API (con la SPA) y de MLflow quedan en estado
  saludable sin pasos manuales adicionales.

### AC2 — Acceso local

- **Dado** el servicio levantado
- **Cuando** se abre `http://localhost:8000` y se consulta `GET /health`
- **Entonces** la SPA carga, `/health` responde 200 y `/docs` muestra el contrato
  OpenAPI, tal como lo documenta el README.

### AC3 — Latencia

- **Dado** el servicio levantado con DeepSeek
- **Cuando** se envían al menos 30 solicitudes del banco HU-02 a `POST /generar`
- **Entonces** la latencia p90 medida es ≤ 60 s y queda registrada en el reporte.

### AC4 — Prueba de humo

- **Dado** el servicio recién desplegado
- **Cuando** se corre la prueba de humo con 5 solicitudes del banco (una por familia)
- **Entonces** 5 de 5 terminan con respuesta válida (pieza o declinación con motivo).

### AC5 — Apagado y documentación

- **Dado** el servicio levantado
- **Cuando** se ejecuta `make down`
- **Entonces** no queda ningún contenedor del proyecto en ejecución, y el README
  documenta requisitos (Docker, `DEEPSEEK_API_KEY`), arranque, URLs y apagado.

## Fuera de alcance

- Exposición pública, dominio o certificado HTTPS.
- GPU alquilada y registro de horas facturadas.
- Orquestación (Kubernetes) o despliegue en la nube; eso es del Módulo 4.

## Métricas de éxito

- Tiempo de arranque desde `make up` hasta `/health` = 200.
- Latencia p50/p90 sobre ≥ 30 solicitudes y 5/5 en la prueba de humo.
