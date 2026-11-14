"""Build Vue y CORS explícito, sin fallback HTML para rutas desconocidas."""

import os
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse


def origenes_frontend() -> list[str]:
    """Solo orígenes HTTP(S) completos: nada de comodines, rutas o credenciales."""
    valor = os.getenv("M2_CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
    origenes = []
    for valor_origen in valor.split(","):
        origen = valor_origen.strip().rstrip("/")
        if not origen:
            continue
        url = urlsplit(origen)
        if (
            "*" in origen
            or url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username
            or url.password
            or url.path
            or url.query
            or url.fragment
        ):
            raise ValueError("M2_CORS_ORIGINS requiere orígenes HTTP(S) exactos, sin comodines.")
        origenes.append(origen)
    return origenes


def configurar_web(
    app: FastAPI,
    *,
    directorio: Path | None = None,
    origenes: list[str] | None = None,
) -> None:
    """Añade solo / y /assets: la SPA actual no tiene rutas de navegación propias."""
    dist = directorio or Path(
        os.getenv(
            "M2_FRONTEND_DIST", str(Path(__file__).resolve().parents[2] / "frontend" / "dist")
        )
    )
    dist = dist.resolve()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origenes if origenes is not None else origenes_frontend(),
        allow_credentials=False,
        allow_methods=["GET", "HEAD", "POST", "DELETE"],
        allow_headers=["Accept", "Content-Type"],
        expose_headers=["X-Solicitud-ID", "Content-Disposition"],
    )

    @app.get("/", include_in_schema=False)
    @app.head("/", include_in_schema=False)
    def inicio() -> FileResponse:
        indice = dist / "index.html"
        if not indice.is_file():
            raise HTTPException(503, "El build de la interfaz todavía no está disponible.")
        return FileResponse(indice, media_type="text/html", headers={"Cache-Control": "no-cache"})

    @app.get("/assets/{nombre:path}", include_in_schema=False)
    @app.head("/assets/{nombre:path}", include_in_schema=False)
    def recurso(nombre: str) -> FileResponse:
        assets = (dist / "assets").resolve()
        ruta = (assets / nombre).resolve()
        if not ruta.is_relative_to(assets) or not ruta.is_file():
            raise HTTPException(404, "Recurso no encontrado.")
        return FileResponse(ruta, headers={"Cache-Control": "public, max-age=31536000, immutable"})
