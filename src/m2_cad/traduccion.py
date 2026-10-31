"""Traducción ES→EN de solicitudes de pieza, conservando números y unidades.

HU-03: el ingeniero describe la pieza en español y el sistema la traduce al
inglés antes de enviarla al modelo, sin alterar cifras ni unidades
(p. ej. "placa de 120 × 120 mm, 6 mm de espesor, 4 agujeros de 12 mm en un
círculo de 90 mm"). Cubre decimales con coma y debe responder en ≤ 5 s en el
percentil 90.
"""
