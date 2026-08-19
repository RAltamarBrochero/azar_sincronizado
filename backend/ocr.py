"""
Módulo OCR: lee una imagen (foto o escaneo de una página de periódico) y
propone un resultado de sorteo, para que un humano lo revise y confirme
antes de guardarlo.

Este módulo NO descarga ni scrapea ninguna hemeroteca por su cuenta.
La imagen debe subirla la persona, desde una fuente a la que tenga acceso
legítimo (foto propia en la biblioteca, PDF de un archivo con suscripción,
recorte propio, etc.). Aquí solo se automatiza la lectura del texto y la
extracción de candidatos a número/fecha — la confirmación siempre la hace
un humano vía el endpoint POST /sorteos existente.
"""
import re
from datetime import date
from io import BytesIO

import pytesseract
from PIL import Image, ImageOps

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# Palabras clave que suelen aparecer INMEDIATAMENTE antes del número en avisos de prensa
PALABRAS_CLAVE_NUMERO = ["premio mayor", "numero ganador", "número ganador"]


def _preprocesar(imagen: Image.Image) -> Image.Image:
    """Escala de grises + contraste, mejora bastante la lectura de OCR en recortes de prensa."""
    img = ImageOps.grayscale(imagen)
    img = ImageOps.autocontrast(img)
    return img


def extraer_texto(bytes_imagen: bytes, idioma: str = "spa") -> str:
    imagen = Image.open(BytesIO(bytes_imagen))
    imagen = _preprocesar(imagen)
    try:
        return pytesseract.image_to_string(imagen, lang=idioma)
    except pytesseract.TesseractError:
        # El paquete de idioma español (tesseract-ocr-spa) puede no estar instalado.
        # Reintenta con el idioma por defecto en vez de fallar por completo.
        return pytesseract.image_to_string(imagen)


def _normalizar(s: str) -> str:
    s = s.lower()
    for a, b in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]:
        s = s.replace(a, b)
    return s


def buscar_fecha_candidata(texto: str) -> date | None:
    texto_norm = _normalizar(texto)

    # Formato "15 de junio de 1985"
    m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", texto_norm)
    if m:
        dia, mes_txt, anio = m.groups()
        mes = MESES.get(mes_txt)
        if mes:
            try:
                return date(int(anio), mes, int(dia))
            except ValueError:
                pass

    # Formato "15/06/1985" o "15-06-1985"
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", texto)
    if m:
        dia, mes, anio = m.groups()
        try:
            return date(int(anio), int(mes), int(dia))
        except ValueError:
            pass

    return None


def buscar_numeros_candidatos(texto: str, fecha_detectada: date | None = None) -> list[str]:
    """
    Devuelve números de 4 dígitos encontrados en el texto, priorizando los
    que aparecen justo después de palabras clave como 'premio mayor', y
    descartando el año de la fecha detectada (falso positivo frecuente).
    """
    texto_norm = _normalizar(texto)
    candidatos_prioritarios = []
    candidatos_generales = re.findall(r"\b\d{4}\b", texto)

    for palabra in PALABRAS_CLAVE_NUMERO:
        idx = texto_norm.find(palabra)
        if idx == -1:
            continue
        # Ventana angosta y solo hacia adelante: el número casi siempre va después de la palabra clave
        ventana = texto[idx: idx + len(palabra) + 40]
        candidatos_prioritarios += re.findall(r"\b\d{4}\b", ventana)

    anio_str = str(fecha_detectada.year) if fecha_detectada else None

    vistos = []
    for n in candidatos_prioritarios + candidatos_generales:
        if n == anio_str:
            continue  # descarta el año de la fecha como candidato a número de sorteo
        if n not in vistos:
            vistos.append(n)
    return vistos[:10]


def buscar_serie_candidata(texto: str) -> str | None:
    m = re.search(r"serie\s*(?:no|n[°º.]?)?\s*[:.]?\s*(\d{1,3})", texto, flags=re.IGNORECASE)
    if m:
        return m.group(1).zfill(3)
    return None


def procesar_imagen(bytes_imagen: bytes) -> dict:
    """
    Punto de entrada del módulo: procesa una imagen y devuelve candidatos.
    NO guarda nada en la base — eso lo hace el humano vía POST /sorteos
    después de revisar y corregir lo que haga falta.
    """
    texto = extraer_texto(bytes_imagen)
    fecha = buscar_fecha_candidata(texto)
    return {
        "texto_detectado": texto.strip(),
        "fecha_candidata": fecha,
        "numeros_candidatos": buscar_numeros_candidatos(texto, fecha_detectada=fecha),
        "serie_candidata": buscar_serie_candidata(texto),
    }
