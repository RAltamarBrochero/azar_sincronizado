"""
Importa dos fuentes históricas distintas que NO son la misma lotería:

    - historicoloteria-bta.xls   -> LOTERÍA DE LA CRUZ ROJA COLOMBIANA (1965-2007)
      Confirmado contra la fuente oficial: lotecruz.org.co/resultados/
      (el nombre "-bta" del archivo era engañoso; a pesar del nombre, NO es
      Lotería de Bogotá — el sorteo se transmitía de forma itinerante entre
      ciudades, columna 'Ciudad' variable, propio de la Cruz Roja).

    - resultados-loteria-de-bogota*.csv -> LOTERÍA DE BOGOTÁ (2014-2023)
      Oficial, de datosabiertos.bogota.gov.co, ya confirmado antes.

A diferencia del importador que descarga en vivo de Datos Abiertos Bogotá,
este script trabaja con archivos que YA TIENES en tu máquina. No descarga
nada de internet.

No cubre 2008-2013 de ninguna de las dos loterías (hueco real, pendiente).

VALIDACIÓN DE FECHAS: el archivo .xls mezcla 3 formatos de fecha distintos
en la misma columna. En vez de adivinar, este script ordena por número de
sorteo (que es secuencial, ~1 por semana) y compara cada fecha contra su
vecino más cercano hacia atrás Y hacia adelante. Cualquier fila cuya fecha
no encaje con ninguno de los dos se guarda en un CSV de revisión aparte en
vez de importarse a ciegas.

Uso:
    python -m scripts.importar_historico_local --xls ruta/historicoloteria-bta.xls \\
        --csv ruta/resultados-loteria-de-bogota.csv ruta/resultados-loteria-de-bogota-2022.csv

    # Modo de prueba: no guarda nada, solo genera el reporte
    python -m scripts.importar_historico_local --xls ... --csv ... --dry-run
"""
import argparse
import re
import sys
from datetime import date, datetime, timedelta

import pandas as pd

from backend.database import Base, SessionLocal, engine
from backend.models import Sorteo

TOLERANCIA_DIAS = 3  # cuánto puede desviarse una fecha del patrón semanal antes de marcarse dudosa
MAX_SALTO_SEMANAS = 6  # a veces hay sorteos saltados (vacaciones, etc.), toleramos hasta 6 semanas de hueco

# El archivo historicoloteria-bta.xls, confirmado con la fuente oficial
# (lotecruz.org.co/resultados/, que ofrece un histórico .xls casi idéntico
# hasta mediados de 2007), es en realidad de la LOTERÍA DE LA CRUZ ROJA
# COLOMBIANA, no de la Lotería de Bogotá. El nombre del archivo ("-bta")
# resultó ser engañoso. Esto también explica por qué la columna Ciudad
# variaba tanto entre sorteos (Bogotá, Medellín, Cali...): la Cruz Roja
# transmitía su sorteo de forma itinerante entre ciudades.
NOMBRE_LOTERIA_XLS = "Lotería de la Cruz Roja Colombiana"


def limpiar_numero_serie(valor: str) -> tuple[str | None, str | None]:
    """'4930-09' -> ('4930','09') | '3915' -> ('3915', None) | '*' -> (None, None)"""
    if valor is None:
        return None, None
    texto = str(valor).strip()
    if not texto or texto == "*":
        return None, None
    if "-" in texto:
        numero, serie = texto.split("-", 1)
    else:
        numero, serie = texto, None
    numero = re.sub(r"\D", "", numero)
    if not numero:
        return None, None
    numero = numero.zfill(4)[-4:]
    if serie:
        serie = re.sub(r"\D", "", serie) or None
    return numero, serie


def parsear_fecha_flexible(valor) -> date | None:
    """Intenta varios formatos conocidos del archivo .xls. Devuelve None si ninguno calza."""
    if pd.isna(valor):
        return None
    texto = str(valor).strip()

    formatos = [
        "%m/%d/%Y",   # 02/22/2000
        "%Y-%m-%d",   # 2007-05-15
        "%d-%m-%Y",   # 17-04-2007
        "%d-%m-%y",   # 11-09-01
        "%m-%d-%y",
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def _consistente(fecha_a: date, sorteo_a: int, fecha_b: date, sorteo_b: int) -> bool:
    """¿La fecha_b encaja razonablemente con fecha_a dado el número de semanas entre sorteos?"""
    semanas = abs(sorteo_b - sorteo_a)
    if semanas == 0 or semanas > MAX_SALTO_SEMANAS:
        return False
    esperado_dias = semanas * 7
    delta_dias = abs((fecha_b - fecha_a).days)
    return abs(delta_dias - esperado_dias) <= TOLERANCIA_DIAS


def procesar_xls(ruta: str) -> tuple[list[dict], list[dict]]:
    """
    Devuelve (filas_buenas, filas_para_revisar).

    La fecha de cada fila se valida contra su vecino más cercano hacia atrás
    Y hacia adelante (no solo hacia atrás): así, si una sola fila tiene la
    fecha mal, se marca solo ESA fila en vez de contaminar en cascada a
    todas las filas correctas que vienen después de ella.
    """
    df = pd.read_excel(ruta)
    df = df.sort_values("Sorteo").reset_index(drop=True)

    # Primera pasada: parsear todo lo que se pueda, sin decidir todavía qué es "bueno"
    crudos = []
    for _, fila in df.iterrows():
        numero, serie = limpiar_numero_serie(fila["Premio1"])
        ciudad = str(fila["Ciudad"]).strip() if pd.notna(fila["Ciudad"]) else None
        fecha = parsear_fecha_flexible(fila["Fecha"])
        crudos.append({
            "sorteo": int(fila["Sorteo"]),
            "fecha": fecha,
            "numero": numero,
            "serie": serie,
            "ciudad": ciudad,
        })

    buenas, revisar = [], []

    for i, actual in enumerate(crudos):
        motivo = None

        if actual["numero"] is None:
            motivo = "número de premio mayor no interpretable"
        elif actual["fecha"] is None:
            motivo = "fecha no interpretable con los formatos conocidos"
        else:
            # Busca el vecino parseable más cercano hacia atrás y hacia adelante
            anterior = next((c for c in reversed(crudos[:i]) if c["fecha"] is not None), None)
            siguiente = next((c for c in crudos[i + 1:] if c["fecha"] is not None), None)

            ok_atras = anterior is not None and _consistente(
                anterior["fecha"], anterior["sorteo"], actual["fecha"], actual["sorteo"]
            )
            ok_adelante = siguiente is not None and _consistente(
                actual["fecha"], actual["sorteo"], siguiente["fecha"], siguiente["sorteo"]
            )

            # Si no hay ningún vecino para comparar (extremos del archivo), se acepta.
            sin_vecinos = anterior is None and siguiente is None

            if not (ok_atras or ok_adelante or sin_vecinos):
                motivo = (
                    f"la fecha no encaja ni con el sorteo anterior "
                    f"({anterior['sorteo'] if anterior else '?'}: {anterior['fecha'] if anterior else '?'}) "
                    f"ni con el siguiente "
                    f"({siguiente['sorteo'] if siguiente else '?'}: {siguiente['fecha'] if siguiente else '?'})"
                )

        registro = {
            "loteria": NOMBRE_LOTERIA_XLS,
            "fecha": actual["fecha"],
            "numero": actual["numero"],
            "serie": actual["serie"],
            "ciudad": actual["ciudad"],
            "numero_sorteo": actual["sorteo"],
            "fuente": "Archivo histórico personal (historicoloteria-bta.xls)",
            "verificado": False,
        }

        if motivo:
            registro["motivo_revision"] = motivo
            revisar.append(registro)
        else:
            buenas.append(registro)

    return buenas, revisar


def procesar_csv_oficial(ruta: str) -> list[dict]:
    """Lee un CSV de Datos Abiertos y se queda solo con la fila de PREMIO MAYOR de cada sorteo."""
    df = None
    for codificacion in ("utf-8", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(ruta, sep=";", encoding=codificacion, dtype=str)
            break
        except UnicodeDecodeError:
            continue
    if df is None:
        raise ValueError(f"No se pudo leer {ruta} con ninguna codificación conocida (utf-8/latin-1/cp1252)")

    df.columns = [c.strip().upper() for c in df.columns]

    mask_mayor = df["NOMBRE_PREMIO"].str.upper().str.contains("PREMIO MAYOR", na=False)
    df_mayor = df[mask_mayor]

    filas = []
    for _, fila in df_mayor.iterrows():
        numero, serie_extra = limpiar_numero_serie(fila["NUMERO"])
        serie = str(fila["SERIE"]).strip() if pd.notna(fila.get("SERIE")) else serie_extra

        try:
            fecha = datetime.strptime(str(fila["FECHA"]).strip(), "%d/%m/%Y").date()
        except ValueError:
            fecha = None

        if not numero or not fecha:
            continue

        filas.append({
            "loteria": "Lotería de Bogotá",
            "fecha": fecha,
            "numero": numero,
            "serie": serie,
            "ciudad": None,
            "numero_sorteo": int(fila["SORTEO"]) if pd.notna(fila.get("SORTEO")) else None,
            "fuente": "Datos Abiertos Bogotá (oficial, archivo local)",
            "verificado": True,
        })
    return filas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--xls", help="Ruta al historicoloteria-bta.xls")
    parser.add_argument("--csv", nargs="*", default=[], help="Rutas a uno o más CSV oficiales")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.xls and not args.csv:
        print("Debes indicar al menos --xls o --csv")
        sys.exit(1)

    todas_buenas: list[dict] = []
    todas_revisar: list[dict] = []

    if args.xls:
        print(f"Procesando {args.xls} ...")
        buenas, revisar = procesar_xls(args.xls)
        print(f"  {len(buenas)} filas listas para importar, {len(revisar)} requieren revisión manual")
        todas_buenas += buenas
        todas_revisar += revisar

    for ruta_csv in args.csv:
        print(f"Procesando {ruta_csv} ...")
        filas = procesar_csv_oficial(ruta_csv)
        print(f"  {len(filas)} filas de PREMIO MAYOR encontradas")
        todas_buenas += filas

    if todas_revisar:
        df_revisar = pd.DataFrame(todas_revisar)
        df_revisar.to_csv("revisar_manual.csv", index=False, encoding="utf-8")
        print(f"\n⚠️  {len(todas_revisar)} filas necesitan revisión manual -> revisar_manual.csv")

    if args.dry_run:
        print(f"\n--dry-run: no se guardó nada. {len(todas_buenas)} filas listas para importar en un run real.")
        return

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    insertados, omitidos, duplicados_en_lote = 0, 0, 0
    fechas_vistas_en_lote = set()

    try:
        for reg in todas_buenas:
            clave = (reg["loteria"], reg["fecha"])
            if clave in fechas_vistas_en_lote:
                duplicados_en_lote += 1
                continue
            fechas_vistas_en_lote.add(clave)

            ya_existe = db.query(Sorteo).filter(
                Sorteo.loteria == reg["loteria"], Sorteo.fecha == reg["fecha"]
            ).first()
            if ya_existe:
                omitidos += 1
                continue

            db.add(Sorteo(
                loteria=reg["loteria"],
                fecha=reg["fecha"],
                anio=reg["fecha"].year,
                numero=reg["numero"],
                serie=reg["serie"],
                ciudad=reg["ciudad"],
                numero_sorteo=reg["numero_sorteo"],
                fuente=reg["fuente"],
                verificado=reg["verificado"],
            ))
            insertados += 1

        db.commit()
    finally:
        db.close()

    print(f"\nListo. Insertados: {insertados} | Ya existían: {omitidos} | Duplicados dentro del mismo lote: {duplicados_en_lote}")


if __name__ == "__main__":
    main()
