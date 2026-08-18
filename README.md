# Azar Sincronizado

Aplicación web + API para consultar el histórico de resultados de loterías
de Colombia. **Fase 1 (en la que estamos): Lotería de Bogotá, 1970–2026.**

## Qué cambió respecto a la versión anterior

El repositorio original no arrancaba porque `requirements.txt` estaba
guardado en codificación UTF-16 (se veía como `f a s t a p i = = 0 . 1 4 1 . 1`),
lo que hacía fallar `pip install -r requirements.txt`. Además:

- No había `.gitignore`, así que la carpeta `venv/` (200+ MB) quedó
  subida al repositorio.
- `main.py` no tenía ninguna ruta conectada a la base de datos: `data.py`
  creaba el engine de SQLAlchemy pero nunca se usaba.
- `sorteos.py` definía el modelo pero las tablas nunca se creaban
  (`Base.metadata.create_all` no se llamaba en ningún lado).
- No existía frontend (HTML/CSS/JS), a pesar de estar en la arquitectura.
- No existía la función de "ciclos del siete" pedida en la tercera fase.

Esta versión corrige todo lo anterior y deja el **módulo base funcionando
localmente de punta a punta**, tal como pedías: primero construir y probar
la app, y después atacar la obtención de datos históricos reales.

## Estructura del proyecto

```
azar_sincronizado/
├── backend/
│   ├── main.py        # FastAPI: rutas de la API + sirve el frontend
│   ├── database.py     # Conexión SQLite (SQLAlchemy)
│   ├── models.py        # Modelo Sorteo
│   ├── schemas.py        # Validación de entrada/salida (Pydantic)
│   ├── crud.py             # Consultas a la base de datos
│   └── stats.py             # Estadísticas + ciclos del siete
├── frontend/
│   ├── index.html      # Consulta histórica / Estadísticas / Ciclos / Hemeroteca
│   ├── style.css
│   └── app.js
├── scripts/
│   └── cargar_datos_demo.py   # Datos DE PRUEBA (ficticios) para validar la app
├── requirements.txt
└── .gitignore
```

## Cómo correrlo en local

```bash
python -m venv venv
source venv/bin/activate        # en Windows: venv\Scripts\activate
pip install -r requirements.txt

# Opcional: cargar datos ficticios para probar que todo funciona
python -m scripts.cargar_datos_demo

uvicorn backend.main:app --reload
```

Luego abre:
- **App web:** http://127.0.0.1:8000/app/
- **Documentación interactiva de la API:** http://127.0.0.1:8000/docs

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/estado` | Estado de la API y cantidad de sorteos cargados |
| GET | `/sorteos` | Lista sorteos (filtros: `loteria`, `anio`, `anio_desde`, `anio_hasta`) |
| POST | `/sorteos` | Registra un sorteo nuevo |
| GET | `/sorteos/{id}` | Consulta un sorteo puntual |
| DELETE | `/sorteos/{id}` | Elimina un sorteo |
| GET | `/estadisticas/resumen` | Total de sorteos, rango de años, números más frecuentes |
| GET | `/estadisticas/ciclos-siete` | Coincidencias cada 7/14/21/24/35/42/49/56 años |

### Sobre `/estadisticas/ciclos-siete`

Compara, entre todos los sorteos, si un mismo valor se repite exactamente
cada uno de esos ciclos de años, usando seis formas de comparación
(parámetro `tipo`, se puede repetir para pedir varias a la vez):

- `dos_primeros` — dos primeros dígitos del número
- `dos_ultimos` — dos últimos dígitos
- `tres_primeros` — tres primeros dígitos
- `tres_ultimos` — tres últimos dígitos
- `numero_completo` — los cuatro dígitos completos
- `combinado_serie` — número + serie combinados

> Nota: 24 no es múltiplo de 7 como el resto de ciclos (7, 14, 21, 28, 35…),
> pero se dejó tal como se pidió originalmente.

## ⚠️ Importante sobre los datos actuales

La base **no trae resultados históricos reales todavía**. El script
`scripts/cargar_datos_demo.py` genera datos **ficticios** únicamente para
comprobar que la API, la base de datos, el frontend y el análisis de
ciclos funcionan correctamente de punta a punta. Ningún número mostrado
con la fuente "dato de prueba (ficticio)" corresponde a un sorteo real.

## Próximos pasos (siguientes fases, según lo planeado)

1. **Fuente de datos histórica legítima:** definir de dónde vendrán los
   resultados reales 1970–2026 (API oficial si existe, prensa digitalizada,
   hemeroteca) antes de escribir cualquier scraper.
2. **OCR de periódicos:** extracción de resultados desde prensa histórica
   digitalizada, con doble verificación antes de marcar `verificado=true`.
3. **Hemeroteca y Google News:** búsqueda y contraste de fuentes.
4. **Agente IA:** asistente conversacional sobre el histórico ya cargado.
5. **Ampliar a las demás loterías de Colombia**, reutilizando el mismo
   modelo (`loteria` ya es un campo del modelo `Sorteo`).

La sección "Hemeroteca & noticias" del frontend ya está armada como
marcador de posición para cuando se conecte esta fase.
