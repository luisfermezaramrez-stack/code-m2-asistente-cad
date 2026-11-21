# Constitución del proyecto — remisión

La constitución de este proyecto es **[`CONSTITUTION.md`](../../CONSTITUTION.md)**, en la raíz
del repositorio. Es la fuente única de verdad sobre propósito, alcance, stack, estructura,
convenciones, calidad, flujo de trabajo y decisiones técnicas.

## Instrucciones para los comandos de Spec Kit

- Toda validación constitucional (el "Constitution Check" de `/speckit.plan`, la alineación
  constitucional de `/speckit.analyze` y cualquier otra) debe **leer y aplicar
  `CONSTITUTION.md` completo**, desde la raíz del repositorio.
- Las reglas normativas son las que `CONSTITUTION.md` declara como obligatorias (por ejemplo,
  `uv` como único gestor de dependencias, cobertura ≥ 70 % y Conventional Commits). Un
  conflicto con ellas es un hallazgo crítico.
- Este archivo no copia reglas: sólo remite a `CONSTITUTION.md`, para que no existan dos
  versiones que puedan divergir.

## Mantenimiento

- **No ejecutes `/speckit.constitution`** para regenerar este archivo: reemplazaría la remisión
  por una constitución paralela.
- Los cambios de gobernanza se hacen en `CONSTITUTION.md`, en el mismo commit del cambio que
  los motiva.

Decisión registrada en `CONSTITUTION.md` §9 (HU-56, SPEC-057).
