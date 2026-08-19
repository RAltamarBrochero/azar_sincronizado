"""
Agente IA — sin llamadas a servicios externos, sin API key.

Responde preguntas en lenguaje natural sobre el histórico de sorteos
detectando la intención con expresiones regulares y consultando la base
de datos local (crud.py) y el módulo de estadísticas (stats.py).

No es un modelo de lenguaje: es un enrutador de intenciones. Cubre las
preguntas más comunes que alguien haría sobre este proyecto. Se puede
ampliar agregando más patrones en `INTENCIONES`.
"""
import re
from datetime import date

from sqlalchemy.orm import Session

from . import crud, stats

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def _normalizar(s: str) -> str:
    s = s.lower().strip()
    for a, b in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]:
        s = s.replace(a, b)
    return s


def _parsear_fecha(texto: str) -> date | None:
    m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", texto)
    if m:
        dia, mes_txt, anio = m.groups()
        mes = MESES.get(mes_txt)
        if mes:
            try:
                return date(int(anio), mes, int(dia))
            except ValueError:
                pass
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", texto)
    if m:
        anio, mes, dia = m.groups()
        try:
            return date(int(anio), int(mes), int(dia))
        except ValueError:
            pass
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", texto)
    if m:
        dia, mes, anio = m.groups()
        try:
            return date(int(anio), int(mes), int(dia))
        except ValueError:
            pass
    return None


def _respuesta_ayuda() -> str:
    return (
        "Puedo responder preguntas como:\n"
        "• «¿Qué número salió el 15 de junio de 1985?»\n"
        "• «¿Cuántas veces ha salido el 0356?»\n"
        "• «¿Cuál es el número más frecuente?»\n"
        "• «Resumen de 2020» o «¿Qué salió en 1990?»\n"
        "• «¿Hay ciclos del siete?» / «coincidencias cada 7 años»\n"
        "• «¿Cuántos sorteos hay cargados?»"
    )


def responder(db: Session, pregunta: str) -> str:
    texto = _normalizar(pregunta)

    # 1) Consulta por fecha exacta
    fecha = _parsear_fecha(texto)
    if fecha and ("que" in texto or "cual" in texto or "salio" in texto or "número" in pregunta.lower()):
        sorteos = crud.listar_sorteos(db, anio=fecha.year, limit=1000)
        encontrado = next((s for s in sorteos if s.fecha == fecha), None)
        if encontrado:
            return (
                f"El {fecha.strftime('%d/%m/%Y')} salió el número {encontrado.numero}"
                + (f", serie {encontrado.serie}" if encontrado.serie else "")
                + f" (fuente: {encontrado.fuente or 'sin especificar'}, "
                + f"{'verificado' if encontrado.verificado else 'sin verificar'})."
            )
        return f"No tengo ningún sorteo registrado para el {fecha.strftime('%d/%m/%Y')} todavía."

    # 2) Frecuencia de un número específico
    m = re.search(r"(?:cuantas veces|frecuencia).{0,20}?(\d{2,4})", texto)
    if m:
        numero_buscado = m.group(1).zfill(4)
        todos = crud.obtener_todos_para_analisis(db)
        coincidencias = [s for s in todos if s.numero == numero_buscado]
        if not coincidencias:
            return f"El número {numero_buscado} no ha salido en los datos cargados actualmente."
        anios = ", ".join(str(s.anio) for s in coincidencias)
        return f"El número {numero_buscado} ha salido {len(coincidencias)} vez/veces: años {anios}."

    # 3) Número más frecuente
    if "mas frecuente" in texto or "numero que mas sale" in texto or "numero que mas ha salido" in texto:
        todos = crud.obtener_todos_para_analisis(db)
        resumen = stats.resumen_estadistico(todos)
        if not resumen["numeros_mas_frecuentes"]:
            return "Todavía no hay suficientes datos cargados para calcular esto."
        top = resumen["numeros_mas_frecuentes"][0]
        return f"El número más frecuente hasta ahora es {top['numero']}, con {top['veces']} apariciones."

    # 4) Ciclos del siete
    if "ciclo" in texto or "cada 7" in texto or "cada siete" in texto:
        todos = crud.obtener_todos_para_analisis(db)
        coincidencias = stats.encontrar_ciclos_de_siete(todos)
        if not coincidencias:
            return "No encontré coincidencias de ciclos del siete con los datos cargados actualmente."
        c = coincidencias[0]
        extra = f" (y {len(coincidencias) - 1} coincidencias más)" if len(coincidencias) > 1 else ""
        return (
            f"Encontré {len(coincidencias)} coincidencia(s). Ejemplo: el valor {c.valor} "
            f"({c.tipo.replace('_', ' ')}) se repitió entre {c.anio_origen} y {c.anio_repite} "
            f"(ciclo de {c.ciclo_anios} años){extra}. Revisa la pestaña «Ciclos del siete» para el listado completo."
        )

    # 5) Resumen por año específico ("que salio en 1990", "resultados de 1990")
    m = re.search(r"\b(19|20)\d{2}\b", texto)
    if m and ("resumen" in texto or "que salio" in texto or "resultados de" in texto or "en el año" in texto):
        anio = int(m.group(0))
        sorteos = crud.listar_sorteos(db, anio=anio, limit=1000)
        if not sorteos:
            return f"No tengo sorteos cargados para el año {anio}."
        numeros = ", ".join(s.numero for s in sorteos)
        return f"En {anio} tengo {len(sorteos)} sorteo(s) registrado(s): {numeros}."

    # 6) Total de sorteos cargados
    if "cuantos sorteos" in texto or "cuantos hay" in texto or "total de sorteos" in texto:
        total = crud.contar_sorteos(db)
        return f"Actualmente hay {total} sorteos cargados en la base."

    # 7) Saludo
    if texto in ("hola", "buenas", "hey", "hi"):
        return "¡Hola! " + _respuesta_ayuda()

    # Fallback: no se reconoció la intención
    return "No estoy seguro de entender esa pregunta todavía. " + _respuesta_ayuda()
