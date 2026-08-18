"""
Módulo de estadísticas.

Incluye la función pedida en la tercera sección del proyecto: detectar
números del premio mayor que se repiten exactamente cada 7, 14, 21, 24,
35, 42, 49 o 56 años, comparando:

  - los dos primeros dígitos del número
  - los dos últimos dígitos del número
  - los tres primeros dígitos del número
  - los tres últimos dígitos del número
  - el número completo (4 dígitos)
  - el número combinado con la serie (número + serie)

Nota: 24 no es múltiplo de 7 como los demás ciclos (7,14,21,28,35,42,49,56),
pero se incluye tal como fue solicitado.
"""
from collections import defaultdict
from typing import Iterable

from . import models, schemas

CICLOS_ANIOS = [7, 14, 21, 24, 35, 42, 49, 56]

TIPOS_COMPARACION = {
    "dos_primeros": lambda numero, serie: numero[:2],
    "dos_ultimos": lambda numero, serie: numero[-2:],
    "tres_primeros": lambda numero, serie: numero[:3],
    "tres_ultimos": lambda numero, serie: numero[-3:],
    "numero_completo": lambda numero, serie: numero,
    "combinado_serie": lambda numero, serie: f"{numero}-{serie}" if serie else None,
}


def _agrupar_por_valor(sorteos: Iterable[models.Sorteo], tipo: str):
    """Agrupa los sorteos por el valor calculado (ej: dos primeros dígitos)."""
    extractor = TIPOS_COMPARACION[tipo]
    grupos: dict[str, list[models.Sorteo]] = defaultdict(list)
    for s in sorteos:
        valor = extractor(s.numero, s.serie)
        if valor is None:
            continue
        grupos[valor].append(s)
    return grupos


def encontrar_ciclos_de_siete(
    sorteos: list[models.Sorteo],
    tipos: list[str] | None = None,
    ciclos: list[int] | None = None,
) -> list[schemas.CicloCoincidencia]:
    """
    Recorre todos los sorteos y devuelve las coincidencias cuyo intervalo
    en años calza exactamente con alguno de los ciclos solicitados.
    """
    tipos = tipos or list(TIPOS_COMPARACION.keys())
    ciclos_validos = set(ciclos or CICLOS_ANIOS)

    resultados: list[schemas.CicloCoincidencia] = []

    for tipo in tipos:
        grupos = _agrupar_por_valor(sorteos, tipo)
        for valor, ocurrencias in grupos.items():
            if len(ocurrencias) < 2:
                continue
            ocurrencias_ordenadas = sorted(ocurrencias, key=lambda s: s.fecha)
            for i in range(len(ocurrencias_ordenadas)):
                for j in range(i + 1, len(ocurrencias_ordenadas)):
                    origen = ocurrencias_ordenadas[i]
                    repite = ocurrencias_ordenadas[j]
                    diff_anios = repite.anio - origen.anio
                    if diff_anios in ciclos_validos:
                        resultados.append(
                            schemas.CicloCoincidencia(
                                tipo=tipo,
                                ciclo_anios=diff_anios,
                                valor=valor,
                                anio_origen=origen.anio,
                                anio_repite=repite.anio,
                                fecha_origen=origen.fecha,
                                fecha_repite=repite.fecha,
                            )
                        )

    resultados.sort(key=lambda r: (r.tipo, r.ciclo_anios, r.anio_origen))
    return resultados


def resumen_estadistico(sorteos: list[models.Sorteo], top_n: int = 10) -> dict:
    """Resumen general: total de sorteos, rango de años y números más frecuentes."""
    if not sorteos:
        return {
            "total_sorteos": 0,
            "anio_min": None,
            "anio_max": None,
            "numeros_mas_frecuentes": [],
        }

    conteo: dict[str, int] = defaultdict(int)
    for s in sorteos:
        conteo[s.numero] += 1

    mas_frecuentes = sorted(conteo.items(), key=lambda kv: kv[1], reverse=True)[:top_n]

    return {
        "total_sorteos": len(sorteos),
        "anio_min": min(s.anio for s in sorteos),
        "anio_max": max(s.anio for s in sorteos),
        "numeros_mas_frecuentes": [
            {"numero": numero, "veces": veces} for numero, veces in mas_frecuentes
        ],
    }
