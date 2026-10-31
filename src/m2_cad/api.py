"""API FastAPI: POST /generar y GET /health (HU-06).

Responde 200 con STEP o declinación y 422 ante texto vacío o de más de
1000 caracteres. Registra texto, traducción, resultado, latencia, error y
versión del modelo por solicitud, sin nombres ni correos.
"""
