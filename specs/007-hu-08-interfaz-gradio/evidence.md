# HU-08 — Evidencias de implementación y validación

**Proyecto:** Asistente CAD — Diseño preliminar de componentes metálicos auxiliares  
**Historia:** HU-08 — Interfaz web con Gradio  
**Rama:** `feature/hu-08-gradio`  
**Fecha de registro:** 11 de noviembre de 2026  
**Estado:** Validación parcial; pendiente cierre de criterios de aceptación

## 1. Entorno de desarrollo

| Elemento | Configuración |
|---|---|
| Sistema operativo | macOS, MacBook Pro Intel |
| Python utilizado en las pruebas | 3.12.13 |
| Interfaz | Gradio Blocks |
| API | FastAPI |
| Contenedores | Docker con Colima |
| Gestión de dependencias | uv |
| Navegadores | Chrome y Firefox, pendientes de prueba completa |
| Versión exacta de Gradio | Pendiente de registrar |

## 2. Pruebas automatizadas

### Comando ejecutado

```bash
PYTHONPATH=src uv run --no-project --with pytest --with pytest-cov --with gradio python -m pytest tests/test_interfaz.py --cov=m2_cad.interfaz --cov-report=term-missing -v
```

### Resultados verificados

En una ejecución registrada:

- 20 pruebas aprobadas.
- 0 pruebas fallidas.
- Cobertura de `interfaz.py`: **92,68 %**.
- Cobertura mínima exigida: 70 %.

Posteriormente se incorporaron dos pruebas adicionales para verificar la compatibilidad con las respuestas del pipeline CAD y las declinaciones HTTP 422. Su ejecución fue reportada como satisfactoria; queda pendiente registrar la salida final completa con cobertura actualizada.

### Funcionalidades comprobadas

- Validación de entradas vacías y superiores a 1000 caracteres.
- Comunicación HTTP con FastAPI mediante simulaciones.
- Presentación de mensajes de declinación.
- Manejo de errores de conexión.
- Protección frente al acceso a archivos externos.
- Disponibilidad independiente de archivos STEP y GLB.
- Creación automática de `outputs/`.
- Manejo de respuestas con `bom_csv`.
- Interpretación de declinaciones HTTP 422.

Estas pruebas utilizan simulaciones y no demuestran por sí solas una generación CAD real.

## 3. Verificación de Docker

### Validación de configuración

Comando ejecutado:

```bash
docker compose config --quiet
```

**Resultado:** finalizó sin errores.

### Arranque de Gradio

Comando ejecutado:

```bash
docker compose up --build --no-deps -d m2-cad-ui
```

Se verificó posteriormente el estado mediante:

```bash
docker compose ps m2-cad-ui
```

**Resultado:** servicio `m2-cad-ui` en estado `Up`, con el puerto 7860 publicado.

### Accesibilidad HTTP

Comando ejecutado:

```bash
curl -I http://localhost:7860
```

Salida registrada:

```text
HTTP/1.1 200 OK
date: Wed, 11 Nov 2026 08:04:38 GMT
server: uvicorn
content-length: 30861
content-type: text/html; charset=utf-8
```

**Conclusión:** Gradio responde correctamente desde un contenedor Docker mediante el puerto 7860.

Esta prueba se ejecutó con `--no-deps`, por lo que no acredita el funcionamiento de FastAPI ni del pipeline completo.

## 4. Verificación de directorios compartidos

Se creó un archivo temporal dentro del contenedor:

```bash
docker compose exec -T m2-cad-ui touch /app/outputs/.hu08_test
```

Se comprobó su existencia en el equipo anfitrión:

```bash
ls -la outputs/.hu08_test
```

Resultado registrado:

```text
-rw-r--r--  1 jkammusic  staff  0 Nov 11 03:05 outputs/.hu08_test
```

También se verificó mediante `docker compose config` que ambos servicios utilizan:

```text
Host:       ./outputs
Contenedor: /app/outputs
```

**Conclusión:** el volumen funciona desde Gradio y la configuración de Docker Compose contempla el mismo directorio para FastAPI.

Pendiente: comprobar el acceso desde FastAPI en ejecución.

## 5. Correcciones solicitadas por el revisor

| Hallazgo | Corrección | Evidencia |
|---|---|---|
| B1 | Servicio independiente `m2-cad-ui` | Contenedor `Up` y HTTP 200 |
| B2 | Host y puerto configurables | Acceso HTTP desde el anfitrión |
| B3 | Creación y volumen compartido de `outputs/` | Prueba de archivo y configuración Compose |
| B4 | URL real en errores de conexión | Prueba automatizada |
| N1 | Restricción de versión de Gradio | Declaración en `pyproject.toml`; verificar lockfile final |
| N2 | Especificación, plan, tareas y evidencias | Documentación en `specs/007-hu-08-interfaz-gradio/` |
| N3 | Ampliación de cobertura de errores | Pruebas automatizadas |
| N4 | Timeout configurable | Pendiente |

## 6. Evidencia de los criterios de aceptación

| Criterio | Evidencia disponible | Estado |
|---|---|---|
| AC1 — Descarga en máximo 3 clics | Flujo y componentes implementados; pruebas con simulaciones | Pendiente validación real |
| AC2 — Declinación con motivo y sin descargas | Pruebas automatizadas, incluidas respuestas HTTP 422 simuladas | Validado con simulaciones |
| AC3 — Advertencia de diseño preliminar | Texto visible en la interfaz; revisión previa del PR | Validado |
| AC4 — Cinco solicitudes en Chrome y Firefox | Sin evidencias de ejecución completa | Pendiente |
| AC5 — STEP disponible aunque falte GLB | Prueba automatizada con archivos simulados | Validado con simulaciones; pendiente prueba real |

## 7. Pruebas de humo en navegadores

**Pendientes de ejecutar y documentar con el pipeline real.**

| Caso | Solicitud | Chrome | Firefox | Evidencia |
|---|---|---|---|---|
| 1 | Solicitud CAD válida 1 | Pendiente | Pendiente | Capturas pendientes |
| 2 | Solicitud CAD válida 2 | Pendiente | Pendiente | Capturas pendientes |
| 3 | Solicitud CAD válida 3 | Pendiente | Pendiente | Capturas pendientes |
| 4 | Solicitud fuera del catálogo | Pendiente | Pendiente | Capturas pendientes |
| 5 | Solicitud para comprobar descargas y visor | Pendiente | Pendiente | Capturas pendientes |

Para cada navegador se registrarán el resultado esperado, el resultado obtenido, las descargas, el número de clics, los mensajes y una captura de pantalla.

## 8. Validaciones pendientes para el nuevo PR

- [ ] Registrar la versión exacta de Gradio.
- [ ] Incorporar y probar el timeout configurable.
- [ ] Registrar la salida final de Pytest con las pruebas adicionales.
- [ ] Ejecutar Ruff y la batería completa del repositorio.
- [ ] Verificar el acceso al volumen desde FastAPI.
- [ ] Ejecutar el despliegue completo con el pipeline CAD.
- [ ] Validar STEP, GLB y CSV reales.
- [ ] Ejecutar cinco solicitudes en Chrome y Firefox.
- [ ] Adjuntar capturas de pantalla de los criterios AC1–AC5.
- [ ] Crear un nuevo Pull Request hacia `develop`.

## 9. Conclusión

La interfaz Gradio cuenta con pruebas automatizadas satisfactorias y un despliegue Docker independiente verificado mediante HTTP 200.

Se incorporaron correcciones para configurar el servidor, compartir los archivos de salida y adaptar la interfaz a las respuestas del pipeline CAD.

**La HU-08 todavía no se considera completamente aceptada**, debido a las pruebas funcionales de extremo a extremo y las evidencias pendientes de Chrome y Firefox.

El nuevo PR se presentará para revisión definitiva una vez completados los criterios exigidos.


## 10. Validación de N4 — Timeout configurable

### Objetivo
Verificar que la conexión HTTP de Gradio utiliza correctamente el valor configurado mediante `M2_API_TIMEOUT`.

### Implementación
- Variable: `M2_API_TIMEOUT`.
- Valor predeterminado: 70 segundos.
- Archivo: `src/m2_cad/interfaz.py`.
- Entorno: Python 3.12.13, macOS.

### Comando ejecutado

```bash
PYTHONPATH=src uv run --no-project --with pytest --with pytest-cov --with gradio python -m pytest tests/test_interfaz.py --cov=m2_cad.interfaz --cov-report=term-missing -v
```

### Resultados

- **Pruebas aprobadas:** 23/23 (100 %).
- **Pruebas fallidas:** 0.
- **Cobertura obtenida:** 93,10 %.
- **Cobertura mínima requerida:** 70 %.
- **Tiempo de ejecución:** 9,81 segundos.
- **Prueba de timeout:** `test_consultar_api_timeout_configurable` — PASSED.
- **Estado:** APROBADO.

### Conclusión
Se confirmó que Gradio utiliza correctamente el timeout configurable. Las 23 pruebas automatizadas finalizaron satisfactoriamente, alcanzando una cobertura del 93,10 %, superior al mínimo exigido.

**N4 queda validado.** La integración de extremo a extremo con el pipeline CAD y las pruebas en Chrome y Firefox siguen pendientes.

## 11. Validación conjunta de componentes

**Objetivo:** comprobar que las modificaciones de HU-08 no afectan las pruebas de FastAPI y traducción.

**Entorno:** macOS Intel, Python 3.12.13.

**Resultados:**
- Pruebas recopiladas: 55.
- Pruebas aprobadas: **51**.
- Pruebas omitidas: **4** (dependencia `cadquery` no disponible).
- Pruebas fallidas: **0**.
- Tiempo de ejecución: **6,56 segundos**.

**Conclusión:** las pruebas ejecutables de FastAPI, traducción y Gradio finalizaron satisfactoriamente. Queda pendiente ejecutar las cuatro pruebas relacionadas con el pipeline CAD en un entorno con sus dependencias instaladas.

## 12. Validación de comunicación Gradio–FastAPI

### Objetivo
Comprobar la comunicación HTTP entre Gradio y FastAPI mediante contenedores Docker independientes, sin ejecutar el modelo de IA.

### Configuración
- Gradio: `http://localhost:7860`
- FastAPI: `http://localhost:8000`
- Comunicación interna: `http://m2-cad:8000`
- Entorno: Docker con Colima, macOS Intel.

### Prueba realizada
Se ingresó una descripción técnica de una placa metálica desde Gradio y se ejecutó la solicitud de generación.

### Resultado
- La interfaz envió la solicitud a FastAPI.
- El servicio respondió indicando que el pipeline CAD no estaba disponible.
- Gradio mostró el mensaje sin detener la aplicación.
- No se presentaron archivos de descarga.

**Estado: APROBADO para comunicación y manejo de indisponibilidad.**

### Limitación
La generación CAD real no fue evaluada porque el servidor del modelo requiere un entorno compatible con GPU. Esta verificación deberá coordinarse con el responsable del pipeline y no sustituye la validación funcional completa de AC4.