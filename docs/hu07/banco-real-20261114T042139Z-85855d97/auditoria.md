# HU-07 · Auditoría de aceptación de la corrida real

Refs #7 · SPEC-016 · Fecha de la corrida: 2026-11-14 (UTC).

## Resultado y criterio aplicado

**Evidencia consistente:** 40 casos únicos, 30 positivos y 10 negativos; 40 registros
únicos y 40 corridas MLflow finalizadas con el mismo `solicitud_id`. Se descargaron
y reimportaron los 30 STEP, verificando SHA-256, volumen y ejes X/Y/Z dentro de ±2 %.
**30/30 conformes**, **10/10 declinaciones correctas**, sin errores técnicos,
geometrías no conformes ni errores silenciosos en ninguna familia.

[Reporte por caso y familia](20261114T042140Z-1303cab4/reporte.md).

La auditoría posterior solo leyó MLflow y archivos locales; no repitió inferencia.
El smoke anterior tiene otros IDs y directorio y está excluido de los denominadores.

## Contraste con issue #7

| Criterio | Evidencia y estado |
|---|---|
| AC1 · Un comando, 40 casos | Ejecutada una llamada a `evaluacion.ejecutar`, con 40 POST secuenciales y cero reintentos. `make bench-report` expone la CLI equivalente para futuras ejecuciones; no se volvió a ejecutar. |
| AC2 · Metas y familias | 30/30 ≥26; 10/10 ≥8; tabla por familia y categorías separadas en el reporte. |
| AC3 · Registro y STEP | 40 filas únicas, 30 STEP con hashes y 40 `run_id` verificados contra MLflow. En negativas el STEP es `no aplica`; no se inventan enlaces de piezas. Las referencias de servicio y disco son locales. |
| AC4 · Ajuste si falla una meta | Condición no activada: ambas metas se cumplieron. Sin ajustes ni segunda corrida. |
| AC5 · Reporte en docs y tarjeta | Markdown en `docs/hu07/`; su publicación se enlaza en #7 al abrir el PR. Pendientes aprobación humana y enlace desde el futuro informe HU-13. |

## Límite geométrico y revisión pendiente

**Volumen y caja conformes no descartan todas las diferencias de forma.** Piezas
con agujeros, posiciones, radios, acabados o topología distintos pueden conservar
esas magnitudes. La reimportación verifica el B-rep y estas medidas, no toda la
equivalencia entre el texto y la forma. Pendiente revisión humana de cada STEP
contra la solicitud/dibujo, además de revisión profesional estructural y normativa.
No se declara aptitud para fabricar ni aceptación/cierre de HU-07.

## Identidad auditada

- Modelo configurado: `deepseek-v4-pro`; versión configurada `deepseek-v4-pro`. No certifica una revisión inmutable de pesos del proveedor.
- Base Git evaluada: `4d64ee7f2e7b5ae045ea627d203b46018a6d961a`, más cambios sin commit archivados.
- Banco, bytes ejecutados: `2a23261f682a9bb93db9c77649b37f94a79d08f70a9340e21eda2709623f3939` (SHA-256).
- Banco normalizado a LF: `3abc990e3a447dcf2548924f72a4d3de1b92ed219a368be56dd534007214df0d` (SHA-256; comparación portable).
- Manifiesto de código: `a598899090a017bd0d62e30bdeef6f0c00e68c1f7603786ede0e3569ebd83e09` (SHA-256 de JSON ordenado ruta → hash).
- ZIP de código evaluado: `033cbe471a332cb6a5b938d3b1dd7c29afd89a500d410dac747e54d342e72744` (SHA-256).
- Prompt: `b64b187dd7b365c37ff7dad4150ecca69eccd3e4a12470c595f63d3b0a41b6d3` (SHA-256 UTF-8).
- Orquestación ejecutada: `35427ede89f9b4980e46e38973d3a05d2223a361c64f4daa8d43d9d9bb219b4f` (SHA-256).
- Imagen API: `sha256:219d90d7b9f1303e53942b9f222c3c93fff39ce01d466bedecc7aa77857285dc`.
- Inicio: `2026-11-14T04:21:39.637345+00:00`; fin: `2026-11-14T04:23:35.986756+00:00`.
- Se comprobaron invariantes de banco, código, contenedor y entorno antes/después de la corrida; ninguna credencial se publica.

Después de la corrida se incorporó develop actualizado por fast-forward. Cambiaron
documentación, dependencias frontend y la lista de hosts de MLflow, no el banco
ni el prompt ni la lógica numérica evaluada. Se añadió documentación del módulo y
el alias Make; el snapshot crudo sigue identificando exactamente lo ejecutado.

### Fuentes Python del backend evaluado (bytes crudos)

| Ruta | SHA-256 |
|---|---|
| `m2_cad/__init__.py` | `8a16b0ced11f9fc4ab942ed4afc730db2f8878fc9f4fa754e92ef023cb1f2db9` |
| `m2_cad/api.py` | `7b484634b660cd797885ab53139511bbd915232a4eecf8bdb9666aa20e862bcd` |
| `m2_cad/banco.py` | `926b59389d43528b3875292fe7c3d98916d145e73c0c5ee4e55715e008dd54b3` |
| `m2_cad/control.py` | `1bc361daf580222001d2cb40838129c5dcc0c539a52e305f6d5cdc8f47ee1d2d` |
| `m2_cad/dataset.py` | `ff88266b7f270b15452734cd5b0963249dbd00b8e175a274c2c070a07018c730` |
| `m2_cad/evaluacion.py` | `10d89a578cc2d0aba00cee644b2ead0d5c0c8c02b0c7b3e0da886447ba648ec2` |
| `m2_cad/pipeline.py` | `d7193f6c89fe89eb36906a7feab9976c014075535c127bf1c791331b948ad21f` |
| `m2_cad/registro.py` | `673ac8d24bc3a2a539fe24a54c33f69ed48d9009e821534a2e2b10afaf4f0b04` |
| `m2_cad/seguimiento.py` | `ae28cf4f366d625d8138255e1e1a4809d66d0ed891abc66aa736aecf08e07577` |
| `m2_cad/trabajos.py` | `ba9278c6d21ffa2171bce7a55613fe27dfbe69e23b16a5d51fc237b4ebd1622f` |
| `m2_cad/web.py` | `7064b8bf80286b54f3a83e8e06a81ffe2803cb41daf588bdf35f36110b88dd2b` |

## Conservación y publicación

SPEC-016 RNF-2 exige versionar solo el reporte Markdown. Los STEP, JSON, CSV, ZIP
y checkpoints están preservados localmente bajo esta misma carpeta, fuera de Git.
La clave real del contenedor se contrastó en memoria con las evidencias/source
previstas: no se encontró en ellas. No se publican `.env`, pesos, cachés, logs
de contenedor ni las copias redundantes por caso. El snapshot y sus hashes se
contrastan contra los bytes ejecutados; Git puede normalizar saltos de línea.
Las URLs `127.0.0.1` necesitan los servicios locales. Las rutas de archivos crudos
no son descargas públicas desde GitHub; su revisión requiere las evidencias locales.

## Índice de trazabilidad auditado

| Caso | Registro local preservado | STEP local preservado | MLflow auditado |
|---|---|---|---|
| HU02-P01 | `casos/HU02-P01/registro.json` · `717e9307f1154247920d7db5332e8292` | `casos/HU02-P01/pieza.step` | [bf9efa52e1ad4275992ba817f7bb8f01](http://127.0.0.1:5000/#/experiments/1/runs/bf9efa52e1ad4275992ba817f7bb8f01) |
| HU02-P02 | `casos/HU02-P02/registro.json` · `c0ecc57abe784bc1acddf1ec81d7627d` | `casos/HU02-P02/pieza.step` | [2f9824b147d4441db8b20107668feae4](http://127.0.0.1:5000/#/experiments/1/runs/2f9824b147d4441db8b20107668feae4) |
| HU02-P03 | `casos/HU02-P03/registro.json` · `580db7260dc848baaddb69a66edab9cb` | `casos/HU02-P03/pieza.step` | [03b3a2a1a60546c2a3f2c1cc1497f4d7](http://127.0.0.1:5000/#/experiments/1/runs/03b3a2a1a60546c2a3f2c1cc1497f4d7) |
| HU02-P04 | `casos/HU02-P04/registro.json` · `5a0790047cbb45e4b0bd23af627233dd` | `casos/HU02-P04/pieza.step` | [254f1d0b283d4b43951174a0a2aad31d](http://127.0.0.1:5000/#/experiments/1/runs/254f1d0b283d4b43951174a0a2aad31d) |
| HU02-P05 | `casos/HU02-P05/registro.json` · `b69058fbdfe5409099ab226bc33c9dfe` | `casos/HU02-P05/pieza.step` | [737eaec6f4234934a32c8ac6bceec662](http://127.0.0.1:5000/#/experiments/1/runs/737eaec6f4234934a32c8ac6bceec662) |
| HU02-P06 | `casos/HU02-P06/registro.json` · `70b50e1ee2104ebb964f1f931b7866eb` | `casos/HU02-P06/pieza.step` | [ee51a4511e90466a93acdbfb3b3e8c65](http://127.0.0.1:5000/#/experiments/1/runs/ee51a4511e90466a93acdbfb3b3e8c65) |
| HU02-P07 | `casos/HU02-P07/registro.json` · `92ec2e39ec3047498a70631b0228bb85` | `casos/HU02-P07/pieza.step` | [fba7f9a60b9649108dea5e1950fa858b](http://127.0.0.1:5000/#/experiments/1/runs/fba7f9a60b9649108dea5e1950fa858b) |
| HU02-P08 | `casos/HU02-P08/registro.json` · `4f5c307f67d74e388eeb449e934f8954` | `casos/HU02-P08/pieza.step` | [1ce2b1c9fd72481da1eafd9691ecb87a](http://127.0.0.1:5000/#/experiments/1/runs/1ce2b1c9fd72481da1eafd9691ecb87a) |
| HU02-P09 | `casos/HU02-P09/registro.json` · `2e59c9fee90e42669560324f4168a0fe` | `casos/HU02-P09/pieza.step` | [1d450cb6a636450b819ac0a631e1de87](http://127.0.0.1:5000/#/experiments/1/runs/1d450cb6a636450b819ac0a631e1de87) |
| HU02-P10 | `casos/HU02-P10/registro.json` · `daaa8ab70c664a21860b9805eb46e031` | `casos/HU02-P10/pieza.step` | [79426c00c3694e6d993fb51e9783a3be](http://127.0.0.1:5000/#/experiments/1/runs/79426c00c3694e6d993fb51e9783a3be) |
| HU02-P11 | `casos/HU02-P11/registro.json` · `d4466edecd1f462eb2f69481fbb17168` | `casos/HU02-P11/pieza.step` | [7772baf181b84456993128f90f5c2b65](http://127.0.0.1:5000/#/experiments/1/runs/7772baf181b84456993128f90f5c2b65) |
| HU02-P12 | `casos/HU02-P12/registro.json` · `b653b5d25bdc435aa6ce7f73d631c6ca` | `casos/HU02-P12/pieza.step` | [99a5a0098bef450ebaa0ee95cce38809](http://127.0.0.1:5000/#/experiments/1/runs/99a5a0098bef450ebaa0ee95cce38809) |
| HU02-P13 | `casos/HU02-P13/registro.json` · `76eb0bc374c7467596f0b9c44dcc7e20` | `casos/HU02-P13/pieza.step` | [e30219f5c2644416942d9df9ec59536d](http://127.0.0.1:5000/#/experiments/1/runs/e30219f5c2644416942d9df9ec59536d) |
| HU02-P14 | `casos/HU02-P14/registro.json` · `cec6c88a3efd40c2a62a39ab4bdb60bc` | `casos/HU02-P14/pieza.step` | [32de94124dc84a3fa65c098d1d2b6ffd](http://127.0.0.1:5000/#/experiments/1/runs/32de94124dc84a3fa65c098d1d2b6ffd) |
| HU02-P15 | `casos/HU02-P15/registro.json` · `71e5674ffd344c75b73528bdc4912664` | `casos/HU02-P15/pieza.step` | [b83cb81907df4ae383af9981dcea8d82](http://127.0.0.1:5000/#/experiments/1/runs/b83cb81907df4ae383af9981dcea8d82) |
| HU02-P16 | `casos/HU02-P16/registro.json` · `9a84cb9ef8c542cf9cb462e6b244e450` | `casos/HU02-P16/pieza.step` | [3494632a321a40e0beb0be684cb41b15](http://127.0.0.1:5000/#/experiments/1/runs/3494632a321a40e0beb0be684cb41b15) |
| HU02-P17 | `casos/HU02-P17/registro.json` · `9ddf59723b0a43e4af4a470019369db2` | `casos/HU02-P17/pieza.step` | [f3323a766f884c779aae5ab6d8f1271e](http://127.0.0.1:5000/#/experiments/1/runs/f3323a766f884c779aae5ab6d8f1271e) |
| HU02-P18 | `casos/HU02-P18/registro.json` · `b6019b7379184cf6b8892b0ed47c0901` | `casos/HU02-P18/pieza.step` | [64690d8322cd49298a9757d7d58b035e](http://127.0.0.1:5000/#/experiments/1/runs/64690d8322cd49298a9757d7d58b035e) |
| HU02-P19 | `casos/HU02-P19/registro.json` · `02ff97b6580847cd8807a64d567fff53` | `casos/HU02-P19/pieza.step` | [dd8f26d6afd64e488fd7e5d3b49d7fec](http://127.0.0.1:5000/#/experiments/1/runs/dd8f26d6afd64e488fd7e5d3b49d7fec) |
| HU02-P20 | `casos/HU02-P20/registro.json` · `657d50c5a31845a888e5189f1ebedc53` | `casos/HU02-P20/pieza.step` | [8e3dca82f3d649d2a388e973497f0efd](http://127.0.0.1:5000/#/experiments/1/runs/8e3dca82f3d649d2a388e973497f0efd) |
| HU02-P21 | `casos/HU02-P21/registro.json` · `b3263d31bc9347ecad8bf828ef8feb06` | `casos/HU02-P21/pieza.step` | [2d745c1a6b9c4a198d3817a3c76a37cc](http://127.0.0.1:5000/#/experiments/1/runs/2d745c1a6b9c4a198d3817a3c76a37cc) |
| HU02-P22 | `casos/HU02-P22/registro.json` · `63b74f8178c44e1198ce949e52060bc0` | `casos/HU02-P22/pieza.step` | [126b4e504c4c404a9711898a857609dd](http://127.0.0.1:5000/#/experiments/1/runs/126b4e504c4c404a9711898a857609dd) |
| HU02-P23 | `casos/HU02-P23/registro.json` · `3ab2a188022945f59aee9e1fd1148ca9` | `casos/HU02-P23/pieza.step` | [edc88592a4c944239d78a1a667de1686](http://127.0.0.1:5000/#/experiments/1/runs/edc88592a4c944239d78a1a667de1686) |
| HU02-P24 | `casos/HU02-P24/registro.json` · `a1867bc6994d45f88e7ace91ce4b4793` | `casos/HU02-P24/pieza.step` | [84cc22e5fcbf4893a01cf3dfad7be27f](http://127.0.0.1:5000/#/experiments/1/runs/84cc22e5fcbf4893a01cf3dfad7be27f) |
| HU02-P25 | `casos/HU02-P25/registro.json` · `999c1bbc73fb431aa76d4e9b261525e8` | `casos/HU02-P25/pieza.step` | [d6793c6391cc44dbb8d82b1b6881b9c8](http://127.0.0.1:5000/#/experiments/1/runs/d6793c6391cc44dbb8d82b1b6881b9c8) |
| HU02-P26 | `casos/HU02-P26/registro.json` · `4436022ffe4a468a99ca30acd9fb8e06` | `casos/HU02-P26/pieza.step` | [d1ffbd91f9714db8b893e8fa6c70daa0](http://127.0.0.1:5000/#/experiments/1/runs/d1ffbd91f9714db8b893e8fa6c70daa0) |
| HU02-P27 | `casos/HU02-P27/registro.json` · `e483283eb3b64c9caf4126a01b64a924` | `casos/HU02-P27/pieza.step` | [789ec4da0b2447ac8dff8510d82019e4](http://127.0.0.1:5000/#/experiments/1/runs/789ec4da0b2447ac8dff8510d82019e4) |
| HU02-P28 | `casos/HU02-P28/registro.json` · `028d67b3923e4c7caccf45f5aadc77d6` | `casos/HU02-P28/pieza.step` | [3405c4c6eb2246f38839b51fae8ba3b4](http://127.0.0.1:5000/#/experiments/1/runs/3405c4c6eb2246f38839b51fae8ba3b4) |
| HU02-P29 | `casos/HU02-P29/registro.json` · `a82482e92cb940cfbeaa093e03fd1a8a` | `casos/HU02-P29/pieza.step` | [c9576b85eacf405091237014df6561b5](http://127.0.0.1:5000/#/experiments/1/runs/c9576b85eacf405091237014df6561b5) |
| HU02-P30 | `casos/HU02-P30/registro.json` · `4312b4d742104013829a138c3915ab48` | `casos/HU02-P30/pieza.step` | [dbd5510606db4b3080b4f6fd3a5a3a2b](http://127.0.0.1:5000/#/experiments/1/runs/dbd5510606db4b3080b4f6fd3a5a3a2b) |
| HU02-N01 | `casos/HU02-N01/registro.json` · `45f62be6c38744d0aaa479826fbd91d3` | no aplica | [f55456eb1a9a4d7eb2b06fac22035fdc](http://127.0.0.1:5000/#/experiments/1/runs/f55456eb1a9a4d7eb2b06fac22035fdc) |
| HU02-N02 | `casos/HU02-N02/registro.json` · `3d0de8f993bf4645ace03b01fe902e77` | no aplica | [8f99e32d8dc842e495c1fdf7e3b0fbb8](http://127.0.0.1:5000/#/experiments/1/runs/8f99e32d8dc842e495c1fdf7e3b0fbb8) |
| HU02-N03 | `casos/HU02-N03/registro.json` · `dee900760e614e0a930e531c0b619756` | no aplica | [e1c9d7868f49494cb6ccc5ad4d7d10b9](http://127.0.0.1:5000/#/experiments/1/runs/e1c9d7868f49494cb6ccc5ad4d7d10b9) |
| HU02-N04 | `casos/HU02-N04/registro.json` · `7948660cb5cb45bdb47a600d5fb15620` | no aplica | [7ac3d278b40740e4b8358433ea413a89](http://127.0.0.1:5000/#/experiments/1/runs/7ac3d278b40740e4b8358433ea413a89) |
| HU02-N05 | `casos/HU02-N05/registro.json` · `de68ab8baf5d4c5ba7dd3d62b65779c0` | no aplica | [72c9e923de104d68b430366a634143ee](http://127.0.0.1:5000/#/experiments/1/runs/72c9e923de104d68b430366a634143ee) |
| HU02-N06 | `casos/HU02-N06/registro.json` · `9be97643315b4d4f932b5ba2da8009c4` | no aplica | [f7c33270b37e438a9984a81982aa0669](http://127.0.0.1:5000/#/experiments/1/runs/f7c33270b37e438a9984a81982aa0669) |
| HU02-N07 | `casos/HU02-N07/registro.json` · `489d971991d44a6ab93e80f2498219f0` | no aplica | [e70ee300c34c4595b28baf3551326497](http://127.0.0.1:5000/#/experiments/1/runs/e70ee300c34c4595b28baf3551326497) |
| HU02-N08 | `casos/HU02-N08/registro.json` · `427f45b4f20a454a828ecc159f7dca41` | no aplica | [6ab1dd21e330469c9fec99361e3bc2b3](http://127.0.0.1:5000/#/experiments/1/runs/6ab1dd21e330469c9fec99361e3bc2b3) |
| HU02-N09 | `casos/HU02-N09/registro.json` · `6cbdb822dfa44696bd6d1fc4c3a81978` | no aplica | [2739650f9c0b4294b80139750578d548](http://127.0.0.1:5000/#/experiments/1/runs/2739650f9c0b4294b80139750578d548) |
| HU02-N10 | `casos/HU02-N10/registro.json` · `501c9853c73e43bab0b607754edee812` | no aplica | [20c51b931c0f4cbfa784826ce8e814ea](http://127.0.0.1:5000/#/experiments/1/runs/20c51b931c0f4cbfa784826ce8e814ea) |

Los `run_id` y métricas se contrastaron con MLflow mediante consultas de lectura.
No se ejecutaron llamadas pagadas adicionales para esta auditoría.

## Checks previos al PR (sin inferencia)

- Ruff correcto en `src`, `tests`, verificación HTTP y script del smoke HU-07;
  `uv lock --check --offline` y `docker compose config --quiet` correctos.
- Vitest: **50 aprobadas**; TypeScript y build Vue correctos tras incorporar
  develop actualizado.
- Suite Python completa en Docker Linux sin red ni credenciales, con cobertura:
  **301 aprobadas, 1 fallida**, cobertura **96,52 %** (mínimo 70 % superado).
- El fallo es el gate HU-16 sin modificaciones
  `test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms`: p95 **56,5 ms** con
  cobertura frente a **50 ms**. No se omitió ni se relajó. Los ensayos aislados
  anteriores sin cobertura dieron 42,79 ms en HU-07 y 37,21 ms en develop; esto
  no demuestra una causa exclusiva de Windows ni permite declarar todos los
  checks locales en verde. El efecto exacto de instrumentación/carga no se aisló.
- Smoke de despliegue HTTP con **modelo simulado** y CAD/exportación reales:
  SSE incremental y cancelación local correctos, STEP/GLB/CSV descargables.
  No se ejecutó una segunda corrida del banco real.

Estos checks validan implementación y transporte; la revisión humana de forma y
de aceptación sigue pendiente. La CI remota del PR debe consultarse por separado.
