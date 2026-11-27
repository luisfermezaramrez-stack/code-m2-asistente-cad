# Política de excepciones de seguridad — SPEC-029 (HU-28)

> Fuente de requisitos: `specs/029-hu-28-escaneo-seguridad/spec.md` (RF-4) y
> `CONSTITUTION.md` §6. Esta política explica **dónde** se declara una excepción,
> **quién** la aprueba y **cuándo** deja de valer. El escaneo la hace cumplir en
> cada corrida: `make security-secretos` y `make security-dependencias` dependen de
> `make security-excepciones-validar`, así que una excepción incompleta, vencida o
> con revisión a más de 180 días hace fallar el job antes de escanear.

El escaneo de seguridad corre en dos jobs independientes sobre cada PR a `main`:

| Job | Herramienta | Qué bloquea |
|---|---|---|
| `secretos` | `gitleaks 8.30.1` sobre el historial | cualquier secreto detectado |
| `dependencias` | `pip-audit 2.10.1` sobre el export de `uv.lock` | un advisory con corrección publicada, de severidad alta o crítica, o de severidad no clasificable |

Una excepción es un acuerdo explícito, escrito y con fecha, para no corregir un
hallazgo concreto. **No es una forma de silenciar el escaneo**: el hallazgo sigue
apareciendo en el log de cada corrida y la entrada sigue versionada en el
repositorio.

## 1. Dónde se declaran

Solo hay dos archivos, uno por herramienta, y son la única vía de aceptación:

- `security/excepciones-secretos.toml` — excepciones de `gitleaks`.
- `security/excepciones-dependencias.toml` — excepciones de `pip-audit`.

No se admiten claves desconocidas, entradas que no sean tablas ni listas dentro de
las entradas. Los dos archivos llevan el esquema documentado en comentarios.
`excepciones-secretos.toml` no tiene excepciones aprobadas;
`excepciones-dependencias.toml` tiene las de `vtk` 9.3.1 (fijado por el kernel CAD)
y `diskcache` 5.6.3 (sin corrección publicada), con revisión el 2027-05-25.

### Esquema de `excepciones-secretos.toml`

```toml
[[excepciones]]
archivo = "ruta/relativa/al/archivo"   # tal como lo reporta gitleaks (File)
linea = 12                             # línea del hallazgo (StartLine)
regla = "generic-api-key"              # id de la regla (RuleID)
justificacion = "Por qué no se puede rotar ni retirar del historial."
aprobado_por = "Nombre Apellido"
revision = "2026-12-31"                # fecha ISO, máxima 180 días vista
```

### Esquema de `excepciones-dependencias.toml`

```toml
[[excepciones]]
advisory = "PYSEC-2026-1475"           # id del advisory o su CVE (CVE-2024-56326)
paquete = "jinja2"                     # paquete instalado que arrastra el advisory
justificacion = "Por qué no se puede actualizar el paquete ahora."
aprobado_por = "Nombre Apellido"
revision = "2026-12-31"                # fecha ISO, máxima 180 días vista
```

La coincidencia es exacta: el secreto se identifica por archivo, línea y regla; el
advisory, por paquete más advisory **o** CVE. Una excepción de un advisory no
cubre otro, aunque compartan paquete.

## 2. Quién aprueba

Basta **una firma**, y puede darla **cualquier integrante del equipo**: quien
aprueba el PR que introduce la excepción es quien la firma. **Nadie aprueba su
propia excepción**: quien abre el PR no puede ser quien lo aprueba, así que la
firma siempre es de otra persona.

La aprobación se hace por PR: la excepción entra versionada con su justificación
y su fecha, y la aprobación del PR es la firma. Por eso `aprobado_por` remite a
esa aprobación (por ejemplo, «Aprobador del PR de HU-28») en lugar de anticipar
un nombre que todavía no existe cuando se escribe la entrada.

## 3. Justificación obligatoria

`justificacion` es obligatoria, en español, con **20 caracteres como mínimo**, y
debe explicar **por qué el hallazgo no se puede corregir** — no basta con
describirlo ni con decir que «es de bajo riesgo». Sirve una razón verificable:

- el paquete está atado al kernel CAD vendoreado y su actualización es coordinada;
- la cadena detectada es una credencial falsa de una fixture de pruebas;
- el proveedor retiró el servicio y la clave ya no tiene efecto;
- la corrección publicada rompe una integración que todavía no se puede migrar.

No sirven «falso positivo» sin evidencia, «pendiente» sin fecha ni la copia del
mensaje de la herramienta.

## 4. Fecha de revisión obligatoria

`revision` es obligatoria, en formato ISO (`AAAA-MM-DD`), **hoy o posterior** y
**como máximo 180 días vista**. Es una fecha de revisión, no una fecha de
caducidad arbitraria: al llegar, alguien decide si el hallazgo se corrige o si la
excepción se renueva con una razón nueva.

## 5. Qué pasa cuando vence

Una excepción vencida **hace fallar el job**: deja de desbloquear el hallazgo y el
log lo dice explícitamente («excepción vencida»). El validador
(`make security-excepciones-validar`) falla antes de escanear si algún archivo
tiene una fecha pasada, sin justificación, sin aprobador o con claves fuera del
esquema.

## 6. Visibilidad

Toda excepción **permanece visible**: vive en el repositorio (versionada, sujeta a
revisión de PR) y aparece en el log de CI con su justificación, su aprobador y su
fecha de revisión. Nunca se excluye un hallazgo con un `allowlist` en
`.gitleaks.toml` ni con una bandera del pipeline: la única exclusión de código del
escaneo es `tests/fixtures/seguridad/`, donde viven credenciales **falsas** de la
suite de pruebas, y está declarada y comentada en la configuración del escáner.

## 7. Cómo retirar una excepción

Una excepción se retira cuando el hallazgo se corrige, cuando el paquete deja de
usarse o cuando vence. Retirarla es borrar su bloque `[[excepciones]]` del archivo
correspondiente:

1. Corrige el hallazgo en el mismo PR: rota y retira la clave, o actualiza el
   paquete con `uv lock --upgrade-package <paquete>` (y `uv add "<paquete>>=<versión>"`).
2. Borra el bloque `[[excepciones]]` completo de
   `security/excepciones-secretos.toml` o de `security/excepciones-dependencias.toml`.
3. Corre `make security-excepciones-validar` y el job del escáner que corresponda:
   el hallazgo ya no debe aparecer.
4. Si la excepción se renueva en lugar de retirarse, actualiza `revision`,
   `justificacion` y `aprobado_por` en una entrada nueva revisada por PR — no
   cambies la fecha sin una razón escrita.

El historial de Git conserva la excepción retirada: nunca hace falta reescribirlo
para dejar constancia de que existió.
