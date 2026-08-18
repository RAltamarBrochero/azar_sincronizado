"""
Azar Sincronizado — API
Fase 1: Lotería de Bogotá, resultados históricos 1970–2026.

Ejecutar localmente:
    uvicorn backend.main:app --reload
"""
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import crud, models, schemas, stats
from .database import Base, SessionLocal, engine, get_db

# Crea las tablas si no existen todavía
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Azar Sincronizado",
    description="Sistema histórico de resultados de loterías de Colombia — Módulo Lotería de Bogotá",
    version="2.0.0",
)

# Permite que el frontend (HTML/JS) sirva las peticiones sin problemas de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------

@app.get("/", tags=["General"])
def inicio():
    return {
        "proyecto": "Azar Sincronizado",
        "estado": "activo",
        "modulo_actual": "Lotería de Bogotá (1970-2026)",
        "documentacion": "/docs",
    }


@app.get("/estado", tags=["General"])
def estado(db: Session = Depends(get_db)):
    total = crud.contar_sorteos(db)
    return {
        "api": "funcionando",
        "version": app.version,
        "sorteos_registrados": total,
    }


# ---------------------------------------------------------------------------
# Sorteos (CRUD)
# ---------------------------------------------------------------------------

@app.post("/sorteos", response_model=schemas.SorteoOut, tags=["Sorteos"])
def crear_sorteo(sorteo: schemas.SorteoCreate, db: Session = Depends(get_db)):
    existentes = crud.listar_sorteos(db, loteria=sorteo.loteria, limit=100000)
    if any(s.fecha == sorteo.fecha for s in existentes):
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe un sorteo registrado para {sorteo.loteria} en la fecha {sorteo.fecha}.",
        )
    return crud.crear_sorteo(db, sorteo)


@app.get("/sorteos", response_model=list[schemas.SorteoOut], tags=["Sorteos"])
def listar_sorteos(
    loteria: str | None = Query(default=None, description="Ej: 'Lotería de Bogotá'"),
    anio: int | None = Query(default=None, description="Filtra por un año exacto"),
    anio_desde: int | None = Query(default=None, ge=1970),
    anio_hasta: int | None = Query(default=None, le=2026),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return crud.listar_sorteos(
        db,
        loteria=loteria,
        anio=anio,
        anio_desde=anio_desde,
        anio_hasta=anio_hasta,
        skip=skip,
        limit=limit,
    )


@app.get("/sorteos/{sorteo_id}", response_model=schemas.SorteoOut, tags=["Sorteos"])
def obtener_sorteo(sorteo_id: int, db: Session = Depends(get_db)):
    sorteo = crud.obtener_sorteo(db, sorteo_id)
    if not sorteo:
        raise HTTPException(status_code=404, detail="Sorteo no encontrado")
    return sorteo


@app.delete("/sorteos/{sorteo_id}", tags=["Sorteos"])
def eliminar_sorteo(sorteo_id: int, db: Session = Depends(get_db)):
    ok = crud.eliminar_sorteo(db, sorteo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Sorteo no encontrado")
    return {"mensaje": "Sorteo eliminado"}


# ---------------------------------------------------------------------------
# Estadísticas
# ---------------------------------------------------------------------------

@app.get("/estadisticas/resumen", tags=["Estadísticas"])
def estadisticas_resumen(
    loteria: str | None = Query(default="Lotería de Bogotá"),
    db: Session = Depends(get_db),
):
    sorteos = crud.obtener_todos_para_analisis(db, loteria=loteria)
    return stats.resumen_estadistico(sorteos)


@app.get("/estadisticas/ciclos-siete", response_model=list[schemas.CicloCoincidencia], tags=["Estadísticas"])
def ciclos_de_siete(
    loteria: str | None = Query(default="Lotería de Bogotá"),
    tipo: list[str] | None = Query(
        default=None,
        description="dos_primeros, dos_ultimos, tres_primeros, tres_ultimos, numero_completo, combinado_serie",
    ),
    db: Session = Depends(get_db),
):
    """
    Detecta números del premio mayor que se repiten exactamente cada
    7, 14, 21, 24, 35, 42, 49 o 56 años.
    """
    sorteos = crud.obtener_todos_para_analisis(db, loteria=loteria)
    if len(sorteos) < 2:
        return []
    return stats.encontrar_ciclos_de_siete(sorteos, tipos=tipo)


# ---------------------------------------------------------------------------
# Frontend estático (HTML/CSS/JS)
# ---------------------------------------------------------------------------
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")
