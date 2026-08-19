"""
Módulo de noticias: consulta el feed público RSS de Google News para
noticias recientes sobre la Lotería de Bogotá.

No requiere API key (Google News RSS es un endpoint público). Se consulta
en vivo en cada petición (no se guarda nada en la base) porque son
noticias transitorias, no resultados verificados.
"""
from urllib.parse import quote_plus

import feedparser

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=es-419&gl=CO&ceid=CO:es"

CONSULTA_POR_DEFECTO = '"Lotería de Bogotá" resultado sorteo'


def buscar_noticias(consulta: str = CONSULTA_POR_DEFECTO, limite: int = 15) -> list[dict]:
    url = GOOGLE_NEWS_RSS.format(query=quote_plus(consulta))
    feed = feedparser.parse(url)

    noticias = []
    for entrada in feed.entries[:limite]:
        noticias.append(
            {
                "titulo": entrada.get("title"),
                "enlace": entrada.get("link"),
                "fuente": entrada.get("source", {}).get("title") if entrada.get("source") else None,
                "publicado": entrada.get("published"),
                "resumen": entrada.get("summary"),
            }
        )
    return noticias
