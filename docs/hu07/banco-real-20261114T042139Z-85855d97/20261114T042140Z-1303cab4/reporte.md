# HU-07 · Corrida del banco

Modo: **HTTP**.

El modo HTTP no certifica por sí solo que el backend use un LLM real.
Las pruebas simuladas no son resultados de evaluación del LLM.

Construcciones conformes: **30/30** (meta ≥26).
Declinaciones correctas: **10/10** (meta ≥8).
Errores silenciosos: **0**.
Registros confirmados: **40/40**.

## Resumen por familia

| Familia | Pos. | Neg. | Conforme | Geom. no conforme | Decl. explícita | Decl. indebida | Fallo técnico | Silenciosos |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| adapter | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| flange | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| fuera_alcance | 0 | 10 | 0 | 0 | 10 | 0 | 0 | 0 |
| plate | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| sheet_bracket | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| spacer | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| tornillería | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |

## Resultados por caso

| Caso | Familia | Clasificación | Causa | Registro | STEP |
|---|---|---|---|---|---|
| HU02-P01 | plate | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/717e9307f1154247920d7db5332e8292) | [STEP](http://127.0.0.1:8000/registros/717e9307f1154247920d7db5332e8292/step) |
| HU02-P02 | plate | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/c0ecc57abe784bc1acddf1ec81d7627d) | [STEP](http://127.0.0.1:8000/registros/c0ecc57abe784bc1acddf1ec81d7627d/step) |
| HU02-P03 | plate | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/580db7260dc848baaddb69a66edab9cb) | [STEP](http://127.0.0.1:8000/registros/580db7260dc848baaddb69a66edab9cb/step) |
| HU02-P04 | plate | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/5a0790047cbb45e4b0bd23af627233dd) | [STEP](http://127.0.0.1:8000/registros/5a0790047cbb45e4b0bd23af627233dd/step) |
| HU02-P05 | plate | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/b69058fbdfe5409099ab226bc33c9dfe) | [STEP](http://127.0.0.1:8000/registros/b69058fbdfe5409099ab226bc33c9dfe/step) |
| HU02-P06 | sheet_bracket | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/70b50e1ee2104ebb964f1f931b7866eb) | [STEP](http://127.0.0.1:8000/registros/70b50e1ee2104ebb964f1f931b7866eb/step) |
| HU02-P07 | sheet_bracket | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/92ec2e39ec3047498a70631b0228bb85) | [STEP](http://127.0.0.1:8000/registros/92ec2e39ec3047498a70631b0228bb85/step) |
| HU02-P08 | sheet_bracket | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/4f5c307f67d74e388eeb449e934f8954) | [STEP](http://127.0.0.1:8000/registros/4f5c307f67d74e388eeb449e934f8954/step) |
| HU02-P09 | sheet_bracket | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/2e59c9fee90e42669560324f4168a0fe) | [STEP](http://127.0.0.1:8000/registros/2e59c9fee90e42669560324f4168a0fe/step) |
| HU02-P10 | sheet_bracket | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/daaa8ab70c664a21860b9805eb46e031) | [STEP](http://127.0.0.1:8000/registros/daaa8ab70c664a21860b9805eb46e031/step) |
| HU02-P11 | adapter | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/d4466edecd1f462eb2f69481fbb17168) | [STEP](http://127.0.0.1:8000/registros/d4466edecd1f462eb2f69481fbb17168/step) |
| HU02-P12 | adapter | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/b653b5d25bdc435aa6ce7f73d631c6ca) | [STEP](http://127.0.0.1:8000/registros/b653b5d25bdc435aa6ce7f73d631c6ca/step) |
| HU02-P13 | adapter | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/76eb0bc374c7467596f0b9c44dcc7e20) | [STEP](http://127.0.0.1:8000/registros/76eb0bc374c7467596f0b9c44dcc7e20/step) |
| HU02-P14 | adapter | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/cec6c88a3efd40c2a62a39ab4bdb60bc) | [STEP](http://127.0.0.1:8000/registros/cec6c88a3efd40c2a62a39ab4bdb60bc/step) |
| HU02-P15 | adapter | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/71e5674ffd344c75b73528bdc4912664) | [STEP](http://127.0.0.1:8000/registros/71e5674ffd344c75b73528bdc4912664/step) |
| HU02-P16 | flange | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/9a84cb9ef8c542cf9cb462e6b244e450) | [STEP](http://127.0.0.1:8000/registros/9a84cb9ef8c542cf9cb462e6b244e450/step) |
| HU02-P17 | flange | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/9ddf59723b0a43e4af4a470019369db2) | [STEP](http://127.0.0.1:8000/registros/9ddf59723b0a43e4af4a470019369db2/step) |
| HU02-P18 | flange | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/b6019b7379184cf6b8892b0ed47c0901) | [STEP](http://127.0.0.1:8000/registros/b6019b7379184cf6b8892b0ed47c0901/step) |
| HU02-P19 | flange | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/02ff97b6580847cd8807a64d567fff53) | [STEP](http://127.0.0.1:8000/registros/02ff97b6580847cd8807a64d567fff53/step) |
| HU02-P20 | flange | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/657d50c5a31845a888e5189f1ebedc53) | [STEP](http://127.0.0.1:8000/registros/657d50c5a31845a888e5189f1ebedc53/step) |
| HU02-P21 | spacer | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/b3263d31bc9347ecad8bf828ef8feb06) | [STEP](http://127.0.0.1:8000/registros/b3263d31bc9347ecad8bf828ef8feb06/step) |
| HU02-P22 | spacer | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/63b74f8178c44e1198ce949e52060bc0) | [STEP](http://127.0.0.1:8000/registros/63b74f8178c44e1198ce949e52060bc0/step) |
| HU02-P23 | spacer | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/3ab2a188022945f59aee9e1fd1148ca9) | [STEP](http://127.0.0.1:8000/registros/3ab2a188022945f59aee9e1fd1148ca9/step) |
| HU02-P24 | spacer | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/a1867bc6994d45f88e7ace91ce4b4793) | [STEP](http://127.0.0.1:8000/registros/a1867bc6994d45f88e7ace91ce4b4793/step) |
| HU02-P25 | spacer | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/999c1bbc73fb431aa76d4e9b261525e8) | [STEP](http://127.0.0.1:8000/registros/999c1bbc73fb431aa76d4e9b261525e8/step) |
| HU02-P26 | tornillería | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/4436022ffe4a468a99ca30acd9fb8e06) | [STEP](http://127.0.0.1:8000/registros/4436022ffe4a468a99ca30acd9fb8e06/step) |
| HU02-P27 | tornillería | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/e483283eb3b64c9caf4126a01b64a924) | [STEP](http://127.0.0.1:8000/registros/e483283eb3b64c9caf4126a01b64a924/step) |
| HU02-P28 | tornillería | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/028d67b3923e4c7caccf45f5aadc77d6) | [STEP](http://127.0.0.1:8000/registros/028d67b3923e4c7caccf45f5aadc77d6/step) |
| HU02-P29 | tornillería | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/a82482e92cb940cfbeaa093e03fd1a8a) | [STEP](http://127.0.0.1:8000/registros/a82482e92cb940cfbeaa093e03fd1a8a/step) |
| HU02-P30 | tornillería | conforme | Volumen y cada eje X/Y/Z dentro de ±2 % | [confirmado](http://127.0.0.1:8000/registros/4312b4d742104013829a138c3915ab48) | [STEP](http://127.0.0.1:8000/registros/4312b4d742104013829a138c3915ab48/step) |
| HU02-N01 | fuera_alcance | declinacion_explicita | Pieza declinada: El asistente no puede construir esta pieza: la solicitud está fuera del catálogo (el modelo indicó: «structural calculation/certification of a steel beam, not a CAD part»). Solo se generan piezas únicas del catálogo: placa, escuadra de chapa, adaptador, brida, espaciador, tornillo, perfil extruido, tubo. | [confirmado](http://127.0.0.1:8000/registros/45f62be6c38744d0aaa479826fbd91d3) | no aplica |
| HU02-N02 | fuera_alcance | declinacion_explicita | Pieza declinada: El asistente no puede construir esta pieza: la solicitud está fuera del catálogo (el modelo indicó: «Verificación y certificación de cumplimiento de la NSR-10 para una estructura metálica existente»). Solo se generan piezas únicas del catálogo: placa, escuadra de chapa, adaptador, brida, espaciador, tornillo, perfil extruido, tubo. | [confirmado](http://127.0.0.1:8000/registros/3d0de8f993bf4645ace03b01fe902e77) | no aplica |
| HU02-N03 | fuera_alcance | declinacion_explicita | Pieza declinada: El asistente no puede construir esta pieza: la solicitud está fuera del catálogo (el modelo indicó: «No puedo emitir certificados de cumplimiento RETIE; soy un planificador CAD para piezas mecánicas.»). Solo se generan piezas únicas del catálogo: placa, escuadra de chapa, adaptador, brida, espaciador, tornillo, perfil extruido, tubo. | [confirmado](http://127.0.0.1:8000/registros/dee900760e614e0a930e531c0b619756) | no aplica |
| HU02-N04 | fuera_alcance | declinacion_explicita | Pieza declinada: El asistente no puede construir esta pieza: la solicitud está fuera del catálogo (el modelo indicó: «BIM building model in native Revit format»). Solo se generan piezas únicas del catálogo: placa, escuadra de chapa, adaptador, brida, espaciador, tornillo, perfil extruido, tubo. | [confirmado](http://127.0.0.1:8000/registros/7948660cb5cb45bdb47a600d5fb15620) | no aplica |
| HU02-N05 | fuera_alcance | declinacion_explicita | Pieza declinada: El asistente no puede construir esta pieza: la solicitud está fuera del catálogo (el modelo indicó: «image-based reconstruction without textual geometry or dimensions»). Solo se generan piezas únicas del catálogo: placa, escuadra de chapa, adaptador, brida, espaciador, tornillo, perfil extruido, tubo. | [confirmado](http://127.0.0.1:8000/registros/de68ab8baf5d4c5ba7dd3d62b65779c0) | no aplica |
| HU02-N06 | fuera_alcance | declinacion_explicita | Pieza declinada: El asistente no puede construir esta pieza: la solicitud está fuera del catálogo (el modelo indicó: «assembly with multiple parts and articulated joints»). Solo se generan piezas únicas del catálogo: placa, escuadra de chapa, adaptador, brida, espaciador, tornillo, perfil extruido, tubo. | [confirmado](http://127.0.0.1:8000/registros/9be97643315b4d4f932b5ba2da8009c4) | no aplica |
| HU02-N07 | fuera_alcance | declinacion_explicita | Pieza declinada: El asistente no puede construir esta pieza: la solicitud está fuera del catálogo (el modelo indicó: «retraining a language model with custom examples and returning new weights»). Solo se generan piezas únicas del catálogo: placa, escuadra de chapa, adaptador, brida, espaciador, tornillo, perfil extruido, tubo. | [confirmado](http://127.0.0.1:8000/registros/489d971991d44a6ab93e80f2498219f0) | no aplica |
| HU02-N08 | fuera_alcance | declinacion_explicita | Pieza declinada: El asistente no puede construir esta pieza: la solicitud está fuera del catálogo (el modelo indicó: «user accounts, login and permissions are not expressible as a single mechanical part»). Solo se generan piezas únicas del catálogo: placa, escuadra de chapa, adaptador, brida, espaciador, tornillo, perfil extruido, tubo. | [confirmado](http://127.0.0.1:8000/registros/427f45b4f20a454a828ecc159f7dca41) | no aplica |
| HU02-N09 | fuera_alcance | declinacion_explicita | Pieza declinada: El asistente no puede construir esta pieza: la solicitud está fuera del catálogo (el modelo indicó: «concurrent multi-user CAD request management»). Solo se generan piezas únicas del catálogo: placa, escuadra de chapa, adaptador, brida, espaciador, tornillo, perfil extruido, tubo. | [confirmado](http://127.0.0.1:8000/registros/6cbdb822dfa44696bd6d1fc4c3a81978) | no aplica |
| HU02-N10 | fuera_alcance | declinacion_explicita | Pieza declinada: El asistente no puede construir esta pieza: la solicitud está fuera del catálogo (el modelo indicó: «FEA analysis and deformation certification are not supported by the constraint-kit DSL»). Solo se generan piezas únicas del catálogo: placa, escuadra de chapa, adaptador, brida, espaciador, tornillo, perfil extruido, tubo. | [confirmado](http://127.0.0.1:8000/registros/501c9853c73e43bab0b607754edee812) | no aplica |

Los valores medidos y las desviaciones por eje están en `resultados.json`,
conservado localmente fuera de Git (SPEC-016 RNF-2).

Una declinación correcta requiere negativo del banco, señal explícita del pipeline y motivo no vacío; no se exige coincidencia literal del motivo ni se certifica su equivalencia semántica automática.
Un error silencioso es una construcción aceptada por la API que incumple la referencia geométrica o construye un caso negativo.

## Seguimiento

HU-07 no se declara completada. Si falla una meta, revisar las causas por caso, documentar un ajuste y repetir una sola vez conservando ambas corridas. Esta herramienta no ajusta prompts ni reintenta automáticamente.

## Identidad y conservación de la corrida real

Commit base: `4d64ee7f2e7b5ae045ea627d203b46018a6d961a`; incluye cambios sin commit archivados.
Banco SHA-256: `2a23261f682a9bb93db9c77649b37f94a79d08f70a9340e21eda2709623f3939`.
Código SHA-256 (manifiesto): `a598899090a017bd0d62e30bdeef6f0c00e68c1f7603786ede0e3569ebd83e09`.
Prompt SHA-256: `b64b187dd7b365c37ff7dad4150ecca69eccd3e4a12470c595f63d3b0a41b6d3`.
Banco/código/configuración conservados durante la corrida: **True**.
El smoke previo queda excluido; 40 POST, 30 positivos y 10 negativos; sin reintentos.
Referencia del modelo configurado: DeepSeek por API; no certifica pesos inmutables del proveedor.
[Auditoría de aceptación y hashes](../auditoria.md).
Evidencias locales fuera de Git: `../identidad.json`, `../banco.csv`,
`../codigo-evaluado.zip`, `../registros.csv`, `../mlflow.json` y `../checkpoint.json`.

## Latencias, tokens y evidencia por caso

Latencia HTTP cliente media: **2.765 s**; p90: **2.956 s**.
p90 por rango más próximo (posición ceil(0,9 × 40)); no incluye descarga/consulta MLflow posterior.
Tokens disponibles en 40/40 casos: entrada **26280**, salida **2700**.
Copias STEP: **30**; corridas MLflow finalizadas: **40/40**.
El costo real no se estima con costo_usd=0 si los precios no están configurados; la corrida consume tokens de pago.
Conformidad basada en las medidas del pipeline contrastadas por el evaluador con cada eje del banco; no es certificación estructural.

| Caso | Categoría | HTTP | Cliente ms | Backend ms | Tokens entrada/salida | MLflow | STEP conservado |
|---|---|---:|---:|---:|---:|---|---|
| HU02-P01 | conforme | 200 | 2677.8 | 1771.319871000287 | 633.0/110.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/bf9efa52e1ad4275992ba817f7bb8f01) | [STEP](../casos/HU02-P01/pieza.step) |
| HU02-P02 | conforme | 200 | 2768.6 | 1964.761660000022 | 681.0/110.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/2f9824b147d4441db8b20107668feae4) | [STEP](../casos/HU02-P02/pieza.step) |
| HU02-P03 | conforme | 200 | 2804.4 | 1901.7281920000642 | 702.0/110.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/03b3a2a1a60546c2a3f2c1cc1497f4d7) | [STEP](../casos/HU02-P03/pieza.step) |
| HU02-P04 | conforme | 200 | 2878.4 | 2072.4661790000027 | 681.0/110.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/254f1d0b283d4b43951174a0a2aad31d) | [STEP](../casos/HU02-P04/pieza.step) |
| HU02-P05 | conforme | 200 | 2956.4 | 2118.4532760003094 | 702.0/110.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/737eaec6f4234934a32c8ac6bceec662) | [STEP](../casos/HU02-P05/pieza.step) |
| HU02-P06 | conforme | 200 | 2626.1 | 1786.7037249998248 | 690.0/91.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/ee51a4511e90466a93acdbfb3b3e8c65) | [STEP](../casos/HU02-P06/pieza.step) |
| HU02-P07 | conforme | 200 | 2238.9 | 1413.9028919998964 | 690.0/91.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/fba7f9a60b9649108dea5e1950fa858b) | [STEP](../casos/HU02-P07/pieza.step) |
| HU02-P08 | conforme | 200 | 2443.0 | 1605.555355999968 | 690.0/91.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/1ce2b1c9fd72481da1eafd9691ecb87a) | [STEP](../casos/HU02-P08/pieza.step) |
| HU02-P09 | conforme | 200 | 2649.0 | 1775.0987549998172 | 696.0/93.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/1d450cb6a636450b819ac0a631e1de87) | [STEP](../casos/HU02-P09/pieza.step) |
| HU02-P10 | conforme | 200 | 2615.8 | 1772.7974659997017 | 690.0/91.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/79426c00c3694e6d993fb51e9783a3be) | [STEP](../casos/HU02-P10/pieza.step) |
| HU02-P11 | conforme | 200 | 2710.4 | 1898.7596570000278 | 659.0/79.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/7772baf181b84456993128f90f5c2b65) | [STEP](../casos/HU02-P11/pieza.step) |
| HU02-P12 | conforme | 200 | 2665.5 | 1802.870772999995 | 659.0/79.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/99a5a0098bef450ebaa0ee95cce38809) | [STEP](../casos/HU02-P12/pieza.step) |
| HU02-P13 | conforme | 200 | 2498.1 | 1646.6226749998896 | 659.0/79.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/e30219f5c2644416942d9df9ec59536d) | [STEP](../casos/HU02-P13/pieza.step) |
| HU02-P14 | conforme | 200 | 2675.9 | 1874.4183859998884 | 659.0/79.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/32de94124dc84a3fa65c098d1d2b6ffd) | [STEP](../casos/HU02-P14/pieza.step) |
| HU02-P15 | conforme | 200 | 2329.5 | 1563.770088000183 | 659.0/79.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/b83cb81907df4ae383af9981dcea8d82) | [STEP](../casos/HU02-P15/pieza.step) |
| HU02-P16 | conforme | 200 | 7812.8 | 6990.1069739999 | 671.0/72.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/3494632a321a40e0beb0be684cb41b15) | [STEP](../casos/HU02-P16/pieza.step) |
| HU02-P17 | conforme | 200 | 2859.5 | 2042.695060999904 | 671.0/41.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/f3323a766f884c779aae5ab6d8f1271e) | [STEP](../casos/HU02-P17/pieza.step) |
| HU02-P18 | conforme | 200 | 3229.1 | 2379.9378859998797 | 676.0/74.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/64690d8322cd49298a9757d7d58b035e) | [STEP](../casos/HU02-P18/pieza.step) |
| HU02-P19 | conforme | 200 | 4007.0 | 3071.3129759997173 | 675.0/75.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/dd8f26d6afd64e488fd7e5d3b49d7fec) | [STEP](../casos/HU02-P19/pieza.step) |
| HU02-P20 | conforme | 200 | 2939.3 | 2094.4843699999183 | 671.0/72.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/8e3dca82f3d649d2a388e973497f0efd) | [STEP](../casos/HU02-P20/pieza.step) |
| HU02-P21 | conforme | 200 | 2421.2 | 1527.0260069996766 | 644.0/71.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/2d745c1a6b9c4a198d3817a3c76a37cc) | [STEP](../casos/HU02-P21/pieza.step) |
| HU02-P22 | conforme | 200 | 2514.7 | 1667.864093999924 | 644.0/71.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/126b4e504c4c404a9711898a857609dd) | [STEP](../casos/HU02-P22/pieza.step) |
| HU02-P23 | conforme | 200 | 2738.0 | 1923.699583999678 | 644.0/71.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/edc88592a4c944239d78a1a667de1686) | [STEP](../casos/HU02-P23/pieza.step) |
| HU02-P24 | conforme | 200 | 2380.5 | 1580.314301999806 | 644.0/71.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/84cc22e5fcbf4893a01cf3dfad7be27f) | [STEP](../casos/HU02-P24/pieza.step) |
| HU02-P25 | conforme | 200 | 2551.4 | 1667.7500759997201 | 644.0/71.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/d6793c6391cc44dbb8d82b1b6881b9c8) | [STEP](../casos/HU02-P25/pieza.step) |
| HU02-P26 | conforme | 200 | 2715.2 | 1831.7196610000792 | 693.0/84.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/d1ffbd91f9714db8b893e8fa6c70daa0) | [STEP](../casos/HU02-P26/pieza.step) |
| HU02-P27 | conforme | 200 | 2608.6 | 1677.0878710003672 | 693.0/84.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/789ec4da0b2447ac8dff8510d82019e4) | [STEP](../casos/HU02-P27/pieza.step) |
| HU02-P28 | conforme | 200 | 2819.8 | 1951.6532510001525 | 693.0/84.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/3405c4c6eb2246f38839b51fae8ba3b4) | [STEP](../casos/HU02-P28/pieza.step) |
| HU02-P29 | conforme | 200 | 2895.4 | 2044.1243450000002 | 691.0/82.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/c9576b85eacf405091237014df6561b5) | [STEP](../casos/HU02-P29/pieza.step) |
| HU02-P30 | conforme | 200 | 2993.0 | 2099.7342180003216 | 693.0/84.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/dbd5510606db4b3080b4f6fd3a5a3a2b) | [STEP](../casos/HU02-P30/pieza.step) |
| HU02-N01 | declinacion_explicita | 422 | 2301.4 | 1381.9355420000647 | 614.0/19.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/f55456eb1a9a4d7eb2b06fac22035fdc) | no aplica |
| HU02-N02 | declinacion_explicita | 422 | 2579.7 | 1621.1021100002654 | 606.0/27.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/8f99e32d8dc842e495c1fdf7e3b0fbb8) | no aplica |
| HU02-N03 | declinacion_explicita | 422 | 2197.3 | 1265.800302000116 | 600.0/33.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/e1c9d7868f49494cb6ccc5ad4d7d10b9) | no aplica |
| HU02-N04 | declinacion_explicita | 422 | 2220.7 | 1365.603695000118 | 605.0/14.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/7ac3d278b40740e4b8358433ea413a89) | no aplica |
| HU02-N05 | declinacion_explicita | 422 | 2276.7 | 1371.2746400001379 | 615.0/13.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/72c9e923de104d68b430366a634143ee) | no aplica |
| HU02-N06 | declinacion_explicita | 422 | 2281.7 | 1352.4401159997979 | 619.0/12.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/f7c33270b37e438a9984a81982aa0669) | no aplica |
| HU02-N07 | declinacion_explicita | 422 | 2583.5 | 1685.9682469998916 | 603.0/17.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/e70ee300c34c4595b28baf3551326497) | no aplica |
| HU02-N08 | declinacion_explicita | 422 | 2297.2 | 1439.1008890002013 | 604.0/20.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/6ab1dd21e330469c9fec99361e3bc2b3) | no aplica |
| HU02-N09 | declinacion_explicita | 422 | 2520.5 | 1670.4802719996223 | 604.0/12.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/2739650f9c0b4294b80139750578d548) | no aplica |
| HU02-N10 | declinacion_explicita | 422 | 2302.9 | 1385.356863999732 | 613.0/24.0 | [corrida](http://127.0.0.1:5000/#/experiments/1/runs/20c51b931c0f4cbfa784826ce8e814ea) | no aplica |

## Causas antes de ajustes

Sin casos fallidos en esta corrida; no se aplicaron ajustes ni se realizó una segunda corrida.

HU-07 no se declara cerrada automáticamente: esta evidencia requiere revisión humana.

## Verificación independiente de los STEP conservados

Sin nuevas llamadas al proveedor: se reimportaron los 30 STEP con CadQuery/OpenCascade
y se contrastaron volumen y cada eje X/Y/Z contra el banco archivado. **30/30**
quedan dentro de ±2 %. Se verificaron también los SHA-256 de los STEP y del
código archivado, y la correlación de las 40 filas con sus corridas MLflow.
Detalle local fuera de Git: `../verificacion-step.json`.
Los enlaces locales STEP se normalizaron a `/` después de generar el reporte;
no se modificaron resultados, banco, prompt, código evaluado ni configuración.

## Límite de forma y revisión humana

Volumen y caja conformes, aun al reimportar los STEP, no prueban equivalencia
completa de forma: cambios de agujeros, posición, radios, topología o acabados
pueden conservar esas magnitudes. Queda pendiente revisar humanamente cada STEP
contra la solicitud, además de la revisión profesional estructural/normativa.
No se declara aptitud de fabricación ni aprobación humana de esta evidencia.

Solo este Markdown y la auditoría se publican en Git. Los enlaces loopback de
API/MLflow requieren los servicios locales; las rutas STEP apuntan a la evidencia
cruda conservada en esta máquina y no se distribuyen por Git. No son URLs públicas.
