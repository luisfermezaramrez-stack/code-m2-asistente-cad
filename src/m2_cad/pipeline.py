"""Pipeline de generación y verificación geométrica (HU-04, HU-05).

Convierte la solicitud traducida en un programa CAD, lo valida contra el
verificador de constraint-kit, construye la pieza B-rep y entrega STEP, GLB y
lista de materiales; o declina con motivo en español cuando no puede
construirla. Toda salida lleva la marca "diseño preliminar".
"""
