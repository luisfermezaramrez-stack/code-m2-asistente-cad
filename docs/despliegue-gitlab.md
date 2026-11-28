# Despliegue continuo desde GitLab

`.gitlab-ci.yml` valida cada rama que el espejo replica desde GitHub y, desde la rama
por defecto, publica la imagen y la despliega en un droplet por SSH. GitHub sigue
siendo la fuente de verdad: el código entra por PR a `main` en GitHub y el workflow
`espejo-gitlab.yml` lo replica en GitLab, donde el push dispara el pipeline.

## Etapas

| Etapa | Jobs | Cuándo corre |
| --- | --- | --- |
| `quality` | `lint`, `secretos`, `dependencias` | cada push |
| `test` | `run_test`, `e2e` | cada push |
| `build` | `build_image` | solo en la rama por defecto |
| `deploy` | `deploy` | rama por defecto y `DO_HOST` definido |

`build_image` construye la imagen, la levanta sin sesión y con una clave de descargas
efímera, espera a que el `HEALTHCHECK` de `/v1/health` quede `healthy` y pide la SPA
en `/`. Solo si eso pasa publica `luismeza2026/code:GDPIACD_2026_2S` y `:latest`.

`deploy` levanta dos contenedores de la misma imagen: la API (`m2-cad`, puerto 8000)
y, cuando la API está `healthy`, el worker de la cola (`m2-cad-worker`, HU-45). Los
volúmenes `m2-cad-data` y `m2-cad-outputs` conservan la cola, los artefactos y los
respaldos entre despliegues.

## Variables de GitLab

Se definen en *Settings → CI/CD → Variables*. Todas son **Protected** para que solo
lleguen a la rama por defecto; las de secretos, además, **Masked**.

| Variable | Tipo | Uso |
| --- | --- | --- |
| `REGISTRY_USER` | Variable | Usuario de Docker Hub para publicar la imagen |
| `REGISTRY_PASS` | Variable, masked | Token de acceso de Docker Hub |
| `DO_HOST` | Variable | IP o nombre del droplet; sin ella `deploy` no se agrega |
| `SSH_PRIVATE_KEY` | **File** | Clave privada con acceso `root` al droplet |
| `DEEPSEEK_API_KEY` | Variable, masked | Llamadas al modelo (HU-14) |
| `M2_DOWNLOAD_SECRET` | Variable, masked | Firma de descargas (HU-36), 32 bytes o más |
| `M2_AUTH_SECRET` | Variable, masked | Firma de la cookie de sesión (HU-53), 32 bytes o más |
| `M2_AUTH_USERS` | Variable | JSON de usuarios con hash PBKDF2 (`make hash-clave`) |
| `LLM_MODEL` | Variable, opcional | Por defecto `deepseek-v4-pro` |
| `M2_LOG_LEVEL` | Variable, opcional | Por defecto `INFO` |

Si falta un secreto obligatorio, `deploy` falla antes de conectarse y nombra la
variable. Los secretos viajan por stdin a `/opt/m2-cad/m2-cad.env` (permisos 600) y
los contenedores los leen con `--env-file`: no aparecen en la línea de comandos.

## Requisitos del droplet

- Docker instalado y `curl` disponible en el host.
- La clave pública de `SSH_PRIVATE_KEY` en `/root/.ssh/authorized_keys`.
- Puerto 8000 abierto en el firewall.
- La imagen es pública en Docker Hub: el droplet no hace `docker login`.

## Límites conocidos

- **HTTP sin TLS.** La API queda en `http://$DO_HOST:8000` y la cookie de sesión no
  puede marcarse `Secure`, porque el navegador no la devolvería. Las credenciales
  viajan sin cifrar. Para HTTPS con dominio propio está el compose cloud de HU-47
  ([runbook cloud](runbook-cloud.md)).
- **Topes de memoria.** `API_MEMORY` (1 GB) y `WORKER_MEMORY` (1,5 GB) son valores
  iniciales: ajustarlos al tamaño del droplet en las variables del job.
- **Validar no integra.** Que el pipeline pase en una rama de GitLab no la integra: la
  puerta sigue siendo el PR en GitHub.

## Rollback

Volver a desplegar una imagen anterior: re-ejecutar el job `deploy` de un pipeline
anterior de `main` en *Build → Pipelines*. Como la etiqueta `GDPIACD_2026_2S` es fija,
antes hay que re-ejecutar también su `build_image` para que la etiqueta apunte a esa
versión.
