"""HU-30: CSV transaccional y snapshots consistentes mediante bloqueo por ruta.

La ruta .lock NO se elimina tras cada uso: su identidad debe ser estable entre procesos
incluso cuando el CSV se reemplaza con os.replace().
"""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def _bloqueo(ruta: Path) -> Iterator[None]:
    """Bloqueo exclusivo por fichero independiente del CSV reemplazable."""
    candado = ruta.with_name(ruta.name + ".lock")
    candado.parent.mkdir(parents=True, exist_ok=True)
    with candado.open("a+b") as archivo:
        if os.name == "nt":
            import msvcrt

            archivo.seek(0, os.SEEK_END)
            if archivo.tell() == 0:
                archivo.write(b"0")
                archivo.flush()
            archivo.seek(0)
            msvcrt.locking(archivo.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                archivo.seek(0)
                msvcrt.locking(archivo.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(archivo.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(archivo.fileno(), fcntl.LOCK_UN)


def _publicar_bytes(destino: Path, contenido: bytes) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{destino.name}.",
            suffix=".tmp",
            dir=destino.parent,
            delete=False,
        ) as archivo:
            temporal = Path(archivo.name)
            archivo.write(contenido)
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(temporal, destino)
        if os.name != "nt":
            descriptor = os.open(destino.parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)


def _leer_filas(ruta: Path, campos: Sequence[str]) -> list[dict[str, str]]:
    if not ruta.exists():
        return []
    with ruta.open("r", newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        if lector.fieldnames != list(campos):
            raise ValueError("La cabecera del registro no coincide con CAMPOS.")
        filas = list(lector)
    if any(None in fila or None in fila.values() for fila in filas):
        raise ValueError("Registro CSV incompleto.")
    return filas


def anexar_sin_duplicar(
    ruta: Path, fila: Mapping[str, str], campos: Sequence[str]
) -> dict[str, str]:
    """Publica el registro íntegro o devuelve la primera fila de ese id."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with _bloqueo(ruta):
        filas = _leer_filas(ruta, campos)
        for existente in filas:
            if existente["id"] == fila["id"]:
                return existente
        filas.append(dict(fila))
        # Generar CSV con reglas de DictWriter, no concatenar líneas manualmente.
        import io

        salida = io.StringIO(newline="")
        escritor = csv.DictWriter(salida, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(filas)
        _publicar_bytes(ruta, salida.getvalue().encode("utf-8"))
    return dict(fila)


def backup(registro: Path, destino: Path) -> Path:
    """Crea snapshot exacto de CSV, serializado respecto de nuevas escrituras."""
    registro = Path(registro)
    destino = Path(destino)
    if registro.resolve() == destino.resolve():
        raise ValueError("El backup no puede ser el propio registro.")
    with _bloqueo(registro):
        if not registro.is_file():
            raise FileNotFoundError(registro)
        if destino.exists():
            raise FileExistsError(f"El backup ya existe: {destino}")
        _publicar_bytes(destino, registro.read_bytes())
    return destino


def _validar_snapshot(origen: Path) -> None:
    """Valida un snapshot con cualquiera de las cabeceras conocidas (HU-26).

    Un snapshot anterior a la última columna añadida se restaura byte a byte, como
    exige HU-30: la cabecera la migra la siguiente escritura del registro.
    """
    from m2_cad.registro import CAMPOS

    with origen.open("r", newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        cabecera = lector.fieldnames or []
        if not cabecera or cabecera != CAMPOS[: len(cabecera)]:
            raise ValueError("La cabecera del registro no coincide con CAMPOS.")
        if any(None in fila or None in fila.values() for fila in lector):
            raise ValueError("Registro CSV incompleto.")


def restore(registro: Path, origen: Path) -> Path:
    """Valida y restaura un snapshot byte a byte con reemplazo atómico."""
    registro = Path(registro)
    origen = Path(origen)
    if registro.resolve() == origen.resolve():
        raise ValueError("El origen no puede ser el propio registro.")
    # Importación local para mantener CAMPOS como fuente única de verdad.
    from m2_cad import registro as modulo_registro

    with _bloqueo(registro):
        if not origen.is_file():
            raise FileNotFoundError(origen)
        _validar_snapshot(origen)
        _publicar_bytes(registro, origen.read_bytes())
    # La cabecera restaurada puede ser anterior a CAMPOS: la próxima escritura la migra,
    # así que se olvida la comprobación ya hecha para esta ruta.
    modulo_registro._RUTAS_MIGRADAS.discard(registro.resolve())
    return registro


def main() -> int:
    parser = argparse.ArgumentParser(description="HU-30: backup/restore del registro CSV")
    sub = parser.add_subparsers(dest="accion", required=True)
    copia = sub.add_parser("backup")
    copia.add_argument("--registro", type=Path, default=Path("data/registro.csv"))
    copia.add_argument("--destino", required=True, type=Path)
    restaura = sub.add_parser("restore")
    restaura.add_argument("--registro", type=Path, default=Path("data/registro.csv"))
    restaura.add_argument("--origen", required=True, type=Path)
    args = parser.parse_args()
    try:
        ruta = (
            backup(args.registro, args.destino)
            if args.accion == "backup"
            else restore(args.registro, args.origen)
        )
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error de {args.accion}: {exc}\n")
    print(f"{args.accion}: {ruta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
