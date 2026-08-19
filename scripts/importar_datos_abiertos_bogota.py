"""
Importa los resultados OFICIALES de la Lotería de Bogotá (2014 - hoy) desde
el portal de Datos Abiertos de Bogotá (datosabiertos.bogota.gov.co), gestionado
directamente por la Lotería de Bogotá vía CKAN.

Fuente: https://datosabiertos.bogota.gov.co/dataset/resultados-loteria-de-bogota
Licencia del dataset: "License Not Specified" en el portal — de uso público,
pero conviene mantener el enlace a la fuente original visible en la app
(ya lo hacemos guardándolo en el campo `fuente`).

Este script:
  1. Descarga el XLSX consolidado (2014 - fecha actual).
  2. Detecta automáticamente las columnas reales del archivo (los nombres
     exactos pueden variar entre actualizaciones del dataset).
  3. Normaliza y guarda cada sorteo en la base local, marcado como
     verificado=True porque proviene de una fuente oficial.

Uso:
    # Primero, modo de prueba: solo muestra qué columnas detectó, no guarda nada
    python -m scripts.importar_datos_abiertos_bogota --dry-run

    # Si el dry-run se ve bien, importar de verdad:
    python -m scripts.importar_datos_abiertos_bogota

No cubre 1970-2013: ese rango no tiene dataset oficial digitalizado y se
aborda en una fase posterior (hemeroteca / prensa histórica).
"""
import argparse
import re
import sys
from datetime import datetime

import pandas as pd
import requests

from backend.database import Base, SessionLocal, engine
from backend.models import Sorteo

URL_XLSX = (
    "https://datosabiertos.bogota.gov.co/dataset/bc8ad0d4-abff-43e2-9078-521271a784aa/"
    "resource/c49ba285-0e35-4fe4-ab0c-12d09fcd135b/download/"
    "resultados-loteria-de-bogota-a-junio-2026-sorteo-2851.xlsx"
)
# Si el nombre de archivo cambia (ej. "a-julio-2026-sorteo-2855"), consulta
# la página del dataset y actualiza esta URL:
#   https://datosabiertos.bogota.gov.co/dataset/resultados-loteria-de-bogota

ARCHIVO_LOCAL = "descargas_bogota.xlsx"

# Posibles nombres de columnas que puede traer el archivo real. El script
# busca la primera coincidencia (sin distinguir mayúsculas/tildes) para
# cada campo que necesitamos.
CANDIDATOS_COLUMNAS = {
    "fecha": ["fecha", "fecha sorteo", "fecha del sorteo"],
    "numero_sorteo": ["sorteo", "no sorteo", "numero sorteo", "número sorteo", "n sorteo"],
    "numero": ["numero", "número", "numero ganador", "número ganador", "premio mayor", "resultado"],
    "serie": ["serie", "serie ganadora"],
}


def _normalizar_texto(s: str) -> str:
    s = s.strip().lower()
    reemplazos = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    for a, b in reemplazos.items():
        s = s.replace(a, b)
    return s


def detectar_columnas(df: pd.DataFrame) -> dict:
    columnas_normalizadas = {_normalizar_texto(str(c)): c for c in df.columns}
    mapeo = {}
    for campo, candidatos in CANDIDATOS_COLUMNAS.items():
        for candidato in candidatos:
            if candidato in columnas_normalizadas:
                mapeo[campo] = columnas_normalizadas[candidato]
                break
    return mapeo


def descargar_xlsx(destino: str = ARCHIVO_LOCAL) -> str:
    print(f"Descargando {URL_XLSX} ...")
    headers = {"User-Agent": "Mozilla/5.0 (AzarSincronizado/1.0)"}
    resp = requests.get(URL_XLSX, headers=headers, timeout=60)
    resp.raise_for_status()
    with open(destino, "wb") as f:
        f.write(resp.content)
    print(f"Guardado como {destino} ({len(resp.content) / 1024:.0f} KB)")
    return destino


def limpiar_numero(valor) -> str | None:
    """Extrae solo dígitos y rellena a 4 posiciones. Devuelve None si no es válido."""
    if pd.isna(valor):
        return None
    digitos = re.sub(r"\D", "", str(valor))
    if not digitos:
        return None
    return digitos.zfill(4)[-4:]  # por si acaso viene con más de 4 dígitos


def parsear_fecha(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, (pd.Timestamp, datetime)):
        return valor.date()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(valor).strip(), fmt).date()
        except ValueError:
            continue
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra columnas detectadas, no guarda nada")
    parser.add_argument("--archivo", default=None, help="Usar un XLSX ya descargado en vez de bajarlo de nuevo")
    args = parser.parse_args()

    ruta = args.archivo or descargar_xlsx()

    try:
        df = pd.read_excel(ruta)
    except Exception as e:
        print(f"No se pudo leer el archivo como Excel: {e}")
        sys.exit(1)

    print(f"\nFilas leídas: {len(df)}")
    print(f"Columnas encontradas en el archivo: {list(df.columns)}\n")

    mapeo = detectar_columnas(df)
    print("Columnas que el script logró identificar automáticamente:")
    for campo, columna_real in mapeo.items():
        print(f"  {campo:15s} -> '{columna_real}'")

    faltantes = [c for c in ("fecha", "numero") if c not in mapeo]
    if faltantes:
        print(f"\n⚠️  No se pudieron identificar automáticamente: {faltantes}")
        print("Copia la lista de columnas de arriba y ajusta CANDIDATOS_COLUMNAS en este script.")
        sys.exit(1)

    if args.dry_run:
        print("\n--dry-run: no se guardó nada. Revisa el mapeo de arriba.")
        print("\nPrimeras 5 filas de muestra:")
        print(df.head())
        return

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    insertados, omitidos, invalidos = 0, 0, 0

    try:
        for _, fila in df.iterrows():
            fecha = parsear_fecha(fila[mapeo["fecha"]])
            numero = limpiar_numero(fila[mapeo["numero"]])
            if not fecha or not numero:
                invalidos += 1
                continue

            ya_existe = db.query(Sorteo).filter(
                Sorteo.loteria == "Lotería de Bogotá", Sorteo.fecha == fecha
            ).first()
            if ya_existe:
                omitidos += 1
                continue

            serie = None
            if "serie" in mapeo and not pd.isna(fila[mapeo["serie"]]):
                serie = re.sub(r"\D", "", str(fila[mapeo["serie"]])) or None

            numero_sorteo = None
            if "numero_sorteo" in mapeo and not pd.isna(fila[mapeo["numero_sorteo"]]):
                try:
                    numero_sorteo = int(fila[mapeo["numero_sorteo"]])
                except (ValueError, TypeError):
                    pass

            db.add(
                Sorteo(
                    loteria="Lotería de Bogotá",
                    fecha=fecha,
                    anio=fecha.year,
                    numero=numero,
                    serie=serie,
                    numero_sorteo=numero_sorteo,
                    fuente="Datos Abiertos Bogotá (oficial) — datosabiertos.bogota.gov.co",
                    verificado=True,
                )
            )
            insertados += 1

        db.commit()
    finally:
        db.close()

    print(f"\nListo. Insertados: {insertados} | Ya existían (omitidos): {omitidos} | Inválidos: {invalidos}")


if __name__ == "__main__":
    main()
