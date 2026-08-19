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

## OCR de periódicos (1970 — 2013)

No existe un dataset digital oficial para este rango, así que el flujo es
**semi-automático y siempre con revisión humana**: nadie sube resultados
sin confirmarlos.

1. Consigue la foto/escaneo de la página del periódico con el resultado,
   desde una fuente a la que tengas acceso legítimo:
   - Consulta presencial en la **Hemeroteca digital de la Biblioteca
     Nacional de Colombia** (catalogoenlinea.bibliotecanacional.gov.co).
   - Archivo digital con suscripción de El Tiempo / El Espectador.
   - Recortes propios, microfilm fotografiado, etc.
2. En la pestaña **"Cargar recorte (OCR)"** de la app, sube la imagen.
3. El sistema (Tesseract OCR) propone fecha, número y serie detectados.
4. **Revisas y corriges** lo que haga falta antes de guardar. El sorteo
   queda guardado con `verificado=false` y `fuente="OCR de periódico"`.
5. Cuando encuentres una segunda fuente independiente que confirme el
   mismo resultado, actualiza el registro a `verificado=true` (vía
   `PATCH`/`PUT` — pendiente de agregar ese endpoint, o directo en la
   base por ahora).

Este módulo **no scrapea ninguna hemeroteca automáticamente** — sería
tanto técnicamente frágil como probablemente contrario a los términos de
esas plataformas. La automatización real está en la lectura OCR de una
imagen que tú ya obtuviste legítimamente, no en conseguir la imagen.

Requiere tener instalado Tesseract OCR en el sistema (no solo la librería
Python):

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-spa

# macOS
brew install tesseract tesseract-lang
```

## Agente IA (sin API externa, sin costo)

Pestaña **"Agente IA"**: responde preguntas en lenguaje natural sobre el
histórico cargado, buscando directamente en la base local. No usa ningún
modelo de lenguaje ni API paga — es un enrutador de intenciones por
expresiones regulares (`backend/agente.py`) sobre las mismas funciones de
`crud.py` y `stats.py` que ya usa el resto de la app.

Preguntas que entiende ahora mismo:
- "¿Qué número salió el 15 de junio de 1985?"
- "¿Cuántas veces ha salido el 0356?"
- "¿Cuál es el número más frecuente?"
- "¿Qué salió en 1990?" / "Resumen de 2020"
- "¿Hay ciclos del siete?"
- "¿Cuántos sorteos hay cargados?"

Para agregar más preguntas que entienda, se agregan patrones nuevos en
`INTENCIONES`/las funciones de `backend/agente.py` — no requiere tocar el
resto de la app. Si en el futuro quieres respuestas más naturales (no solo
patrones fijos), se puede conectar a la API de Claude u otro modelo, pero
eso ya implica una API key y costo por uso.

## Importar resultados OFICIALES reales (2014 — hoy)

Fuente: [Datos Abiertos Bogotá](https://datosabiertos.bogota.gov.co/dataset/resultados-loteria-de-bogota),
publicado directamente por la Lotería de Bogotá, actualizado mensualmente.
No cubre 1970–2013 (ver sección de próximos pasos).

```bash
# 1. Primero en modo de prueba: muestra qué columnas detectó, no guarda nada
python -m scripts.importar_datos_abiertos_bogota --dry-run

# 2. Si el mapeo de columnas se ve correcto, importar de verdad
python -m scripts.importar_datos_abiertos_bogota
```

El script detecta automáticamente los nombres reales de las columnas del
archivo (pueden variar levemente entre actualizaciones del dataset), y si
no logra identificar `fecha` o `numero` se detiene y te dice qué agregar
en `CANDIDATOS_COLUMNAS` dentro del script, en vez de importar datos mal
interpretados.

Cada sorteo importado por esta vía queda guardado con `verificado=true`
y `fuente="Datos Abiertos Bogotá (oficial)"`, para distinguirlo claramente
de los datos de prueba ficticios.

> Si el nombre del archivo XLSX cambia (la URL incluye el mes y el número
> de sorteo, ej. `...-a-julio-2026-sorteo-2855.xlsx`), actualiza la
> constante `URL_XLSX` en `scripts/importar_datos_abiertos_bogota.py`
> con el enlace vigente desde la página del dataset.

## ⚠️ Importante sobre los datos actuales

La base **no trae resultados históricos reales todavía**. El script
`scripts/cargar_datos_demo.py` genera datos **ficticios** únicamente para
comprobar que la API, la base de datos, el frontend y el análisis de
ciclos funcionan correctamente de punta a punta. Ningún número mostrado
con la fuente "dato de prueba (ficticio)" corresponde a un sorteo real.

## Próximos pasos (siguientes fases, según lo planeado)

1. ~~Fuente de datos histórica legítima~~ ✅ resuelto para 2014-hoy con
   Datos Abiertos Bogotá. **Pendiente: 1970-2013**, que no tiene dataset
   oficial digitalizado y requiere ir a prensa/hemeroteca.
2. ~~OCR de periódicos (1970-2013)~~ ✅ implementado: módulo de carga de
   recortes con revisión humana obligatoria antes de guardar. Falta
   conseguir las imágenes reales de hemeroteca/prensa (paso manual, ver
   sección de arriba) y cargarlas una por una.
3. ~~Google News~~ ✅ implementado: pestaña "Hemeroteca & noticias" consulta
   en vivo el RSS público de Google News (sin API key), con buscador
   personalizable.
4. ~~Agente IA~~ ✅ implementado: pestaña "Agente IA" basada en reglas
   (sin API externa, sin costo). Pendiente si se quiere: conectarlo a un
   modelo de lenguaje real para respuestas más flexibles.
5. **Ampliar a las demás loterías de Colombia**, reutilizando el mismo
   modelo (`loteria` ya es un campo del modelo `Sorteo`).

La sección "Hemeroteca & noticias" del frontend ya está armada como
marcador de posición para cuando se conecte esta fase.
