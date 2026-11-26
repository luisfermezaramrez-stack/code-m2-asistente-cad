# Sistema de diseño v2

Fuente única: [`frontend/src/design/tokens.css`](../frontend/src/design/tokens.css). Se importa una
sola vez desde `frontend/src/main.ts`. Los componentes y `frontend/src/style.css` solo consumen
`var(--...)`; cambiar un valor de token no exige tocar plantillas ni estilos.

El directorio `design/` conserva la maqueta histórica de HU-15 como referencia, pero ya no es la
fuente importada por la aplicación. La elección de tema vive en
[`frontend/src/design/theme.ts`](../frontend/src/design/theme.ts).

## Precedencia del tema

1. `localStorage['m2-cad-theme']` si contiene `light` u `dark`.
2. Si no hay preferencia guardada, `matchMedia('(prefers-color-scheme: dark)')`.
3. Si no hay API de preferencia, tema claro.

`initTheme()` aplica `data-theme` a `<html>`. El botón de la cabecera es la única preferencia
visible; `setTheme()` la persiste y `clearThemePreference()` devuelve el control al sistema.
Mientras no haya preferencia guardada, un cambio del sistema se refleja en caliente.
`GlbViewer.vue` relee `--color-viewer-background` al cambiar de tema.

En CSS, `:root` define el tema claro. El bloque `@media (prefers-color-scheme: dark)` aplica el
oscuro cuando no hay `data-theme`; `:root[data-theme='dark']` lo aplica de forma explícita. Como
la regla explícita usa el atributo, `data-theme='light'` gana aunque el sistema prefiera oscuro.

## Escala tipográfica

| Token | Valor | Proporción sobre `--text-body` | Uso |
| --- | --- | --- | --- |
| `--text-small` | `0.875rem` | 0.875 × | Marca, texto de ayuda y etiquetas secundarias del visor |
| `--text-body` | `1rem` | 1 × | Cuerpo, descripción, mensajes y encabezados `h3` |
| `--text-heading` | `1.25rem` | 1.25 × | Encabezados `h2` de paneles |
| `--text-title` | `1.75rem` | 1.75 × | Título `h1` de la página |

Las familias son `--font-body` (interfaz) y `--font-technical` (etiquetas de sistema). Los pesos
son `--weight-regular: 400` y `--weight-strong: 600`. Los interlineados son `--line-body: 1.6`
para texto continuo y `--line-heading: 1.25` para cabeceras. No se cargan fuentes remotas.

## Tokens de color

| Grupo | Tokens claros | Tokens oscuros |
| --- | --- | --- |
| Superficies | `--color-background: #eef2f6`, `--color-surface: #ffffff`, `--color-surface-subtle: #f5f7fa` | `#0e1726`, `#17263a`, `#203147` |
| Visor 3D | `--color-viewer-background: #2f3e4f` | `#2f3e4f` |
| Texto | `--color-text: #172b40`, `--color-muted: #465a70` | `#f2f6fb`, `#c3cede` |
| Bordes y foco | `--color-border: #748499`, `--color-focus: #7c3aed` | `#8fa1b8`, `#d6b4ff` |
| Acción | `--color-accent: #164e80`, `--color-on-accent: #ffffff` | `#8fc5ff`, `#0e1726` |
| Información | `--color-info: #164e80`, `--color-info-bg: #eaf2fa` | `#9ccdff`, `#17324c` |
| Éxito | `--color-success: #166344`, `--color-success-bg: #e9f5ee` | `#8be0ad`, `#14372b` |
| Advertencia | `--color-warning: #704800`, `--color-warning-bg: #fff4d6` | `#ffcf7a`, `#3b2c10` |
| Error | `--color-error: #a12232`, `--color-error-bg: #fff0f1` | `#ff9aa8`, `#3f1820` |
| Inactivo | `--color-idle: #465a70`, `--color-idle-bg: #f5f7fa` | `#c3cede`, `#203147` |

Los tokens derivados `--state-*-fg` / `--state-*-bg` apuntan siempre a los pares anteriores, así
que el estado no introduce paletas paralelas. El fondo del visor se mantiene oscuro en ambos temas
para conservar el contraste con la pieza metálica clara.

Espaciado (`--space-1` a `--space-7`), radios, grosores y medidas de control no cambian entre temas;
sus valores están en el archivo de tokens y los consume `style.css` por variable.

## Contraste verificado

Medido con luminancia relativa WCAG sobre los archivos de tokens; umbral AA: 4.5:1 para texto y
3:1 para foco, bordes y fondo del visor frente a `#d9d9d9`.

| Par | Claro | Oscuro |
| --- | --- | --- |
| texto / fondo | 12.82:1 | 16.55:1 |
| texto secundario / fondo | 6.31:1 | 11.29:1 |
| texto secundario / superficie | 7.10:1 | 9.60:1 |
| texto secundario / superficie suave | 6.62:1 | 8.30:1 |
| acento / fondo | 7.66:1 | 9.92:1 |
| acento / superficie | 8.62:1 | 8.44:1 |
| texto sobre acento | 8.62:1 | 9.92:1 |
| información | 7.63:1 | 7.88:1 |
| éxito | 6.46:1 | 8.29:1 |
| advertencia | 7.33:1 | 9.31:1 |
| error | 6.80:1 | 7.66:1 |
| inactivo | 6.62:1 | 8.30:1 |
| foco / fondo | 5.07:1 | 10.12:1 |
| foco / superficie | 5.70:1 | 8.61:1 |
| foco / superficie suave | 5.31:1 | 7.43:1 |
| borde / superficie | 3.82:1 | 5.79:1 |
| fondo del visor / pieza clara | 7.74:1 | 7.74:1 |

Las pruebas `frontend/tests/tokens.test.ts` recalculan estos pares desde el CSS; no son valores
copiados a mano. Fuera de alcance quedan las brechas WCAG no relacionadas con contraste
(SPEC-041).
