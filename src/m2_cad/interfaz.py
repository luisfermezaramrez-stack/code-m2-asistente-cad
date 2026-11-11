"""Interfaz Gradio para solicitudes preliminares CAD (HU-08)."""

import json
import os
from html import escape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import gradio as gr

RAIZ = Path(__file__).resolve().parents[2]
SALIDAS = RAIZ / "outputs"
API_URL = os.getenv("M2_API_URL", "http://127.0.0.1:8000").rstrip("/")
HOST = os.getenv("M2_UI_HOST", "127.0.0.1")
PUERTO_UI = int(os.getenv("M2_UI_PORT", "7860"))
API_TIMEOUT = int(os.getenv("M2_API_TIMEOUT", "70"))


def consultar_api(texto: str) -> dict:
    """Envía la solicitud a FastAPI, sin depender del pipeline local."""
    solicitud = Request(
        f"{API_URL}/generar",
        data=json.dumps({"texto": texto}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(solicitud, timeout=API_TIMEOUT) as respuesta:
            return json.load(respuesta)
    except HTTPError as exc:
        try:
            detalle = json.loads(exc.read().decode("utf-8")).get("detail", f"HTTP {exc.code}")
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            detalle = f"HTTP {exc.code}"
        if not isinstance(detalle, str):
            detalle = "Solicitud inválida. Revisa la descripción."
        raise RuntimeError(detalle) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"No hay conexión con el servicio CAD en {API_URL}.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("FastAPI devolvió una respuesta inválida.") from exc


def archivo_seguro(nombre: str | None, extension: str) -> str | None:
    """Solo permite archivos existentes dentro del directorio outputs/."""
    if not isinstance(nombre, str) or not nombre:
        return None
    ruta = Path(nombre)
    if not ruta.is_absolute():
        ruta = RAIZ / ruta if ruta.parts[0] == "outputs" else SALIDAS / ruta
    ruta = ruta.resolve()
    if (
        ruta.is_relative_to(SALIDAS.resolve())
        and ruta.is_file()
        and ruta.suffix.lower() == extension
    ):
        return str(ruta)
    return None


def procesar_solicitud(texto: str):
    """Adapta la respuesta de FastAPI a los componentes de Gradio."""
    oculto = gr.update(value=None, visible=False)
    texto = texto.strip()
    if not texto or len(texto) > 1000:
        return "⚠️ Escribe una descripción de entre 1 y 1000 caracteres.", oculto, oculto, oculto

    try:
        respuesta = consultar_api(texto)
    except RuntimeError as exc:
        detalle = str(exc)

        if detalle.startswith("Pieza declinada:"):
            motivo = escape(detalle.removeprefix("Pieza declinada:").strip())
            return f"**Solicitud declinada:** {motivo}", oculto, oculto, oculto

        return f"⚠️ {escape(detalle)}", oculto, oculto, oculto

    estado = respuesta.get("resultado")
    if estado in {"declinacion", "declinada"}:
        motivo = escape(str(respuesta.get("motivo", "Solicitud fuera del alcance del catálogo.")))
        return f"**Solicitud declinada:** {motivo}", oculto, oculto, oculto
    if estado != "generada" and not respuesta.get("step"):
        return "⚠️ Respuesta del servicio no reconocida.", oculto, oculto, oculto

    glb = archivo_seguro(respuesta.get("glb"), ".glb")
    step = archivo_seguro(respuesta.get("step"), ".step")
    csv = archivo_seguro(
        respuesta.get("bom_csv") or respuesta.get("csv"),
        ".csv",
    )
    aviso = "✅ Diseño preliminar generado. Descarga los archivos disponibles."
    if not step:
        aviso += " **Aviso:** no hay archivo STEP disponible todavía."
    if not glb:
        aviso += " La vista 3D no está disponible; el STEP puede descargarse si existe."
    return (
        aviso,
        gr.update(value=glb, visible=bool(glb)),
        gr.update(value=step, visible=bool(step)),
        gr.update(value=csv, visible=bool(csv)),
    )


def crear_interfaz() -> gr.Blocks:
    """Construye la interfaz de HU-08 sin iniciar servicios al importarla."""
    SALIDAS.mkdir(parents=True, exist_ok=True)
    with gr.Blocks(title="Asistente CAD — Diseño preliminar") as demo:
        gr.Markdown("# Asistente CAD — Diseño preliminar")
        gr.Markdown(
            "Describe una pieza metálica auxiliar en español. "
            "**Los resultados son preliminares:** no sustituyen la revisión "
            "estructural ni normativa por un profesional responsable."
        )
        with gr.Row():
            with gr.Column():
                entrada = gr.Textbox(
                    label="Descripción técnica",
                    lines=5,
                    max_lines=8,
                    placeholder="Ej.: Placa de 120 × 120 mm, espesor 6 mm y 4 agujeros de 12 mm",
                )
                boton = gr.Button("Generar diseño preliminar", variant="primary")
                estado = gr.Markdown("Ingresa una descripción para comenzar.")
            with gr.Column():
                modelo = gr.Model3D(label="Vista 3D (GLB)", visible=False, interactive=False)
                step = gr.File(label="Descargar STEP", visible=False, interactive=False)
                csv = gr.File(
                    label="Descargar lista de materiales (CSV)",
                    visible=False,
                    interactive=False,
                )
        boton.click(
            fn=procesar_solicitud,
            inputs=[entrada],
            outputs=[estado, modelo, step, csv],
        )
    return demo


if __name__ == "__main__":
    SALIDAS.mkdir(exist_ok=True)
    crear_interfaz().launch(
        server_name=HOST,
        server_port=PUERTO_UI,
        allowed_paths=[str(SALIDAS.resolve())],
    )
