"""
Operaciones sobre la base de datos: crear, leer, listar y filtrar sorteos.
"""
from datetime import date
from typing import Optional

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from . import models, schemas


def crear_sorteo(db: Session, sorteo: schemas.SorteoCreate) -> models.Sorteo:
    db_sorteo = models.Sorteo(
        loteria=sorteo.loteria,
        fecha=sorteo.fecha,
        anio=sorteo.fecha.year,
        numero=sorteo.numero,
        serie=sorteo.serie,
        numero_sorteo=sorteo.numero_sorteo,
        fuente=sorteo.fuente,
        verificado=sorteo.verificado,
    )
    db.add(db_sorteo)
    db.commit()
    db.refresh(db_sorteo)
    return db_sorteo


def obtener_sorteo(db: Session, sorteo_id: int) -> Optional[models.Sorteo]:
    return db.query(models.Sorteo).filter(models.Sorteo.id == sorteo_id).first()


def listar_sorteos(
    db: Session,
    loteria: Optional[str] = None,
    anio: Optional[int] = None,
    anio_desde: Optional[int] = None,
    anio_hasta: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    orden: str = "asc",
) -> list[models.Sorteo]:
    query = db.query(models.Sorteo)

    if loteria:
        query = query.filter(models.Sorteo.loteria == loteria)
    if anio:
        query = query.filter(models.Sorteo.anio == anio)
    if anio_desde:
        query = query.filter(models.Sorteo.anio >= anio_desde)
    if anio_hasta:
        query = query.filter(models.Sorteo.anio <= anio_hasta)

    orden_campo = asc(models.Sorteo.fecha) if orden == "asc" else desc(models.Sorteo.fecha)
    query = query.order_by(orden_campo)

    return query.offset(skip).limit(limit).all()


def contar_sorteos(db: Session, loteria: Optional[str] = None) -> int:
    query = db.query(models.Sorteo)
    if loteria:
        query = query.filter(models.Sorteo.loteria == loteria)
    return query.count()


def eliminar_sorteo(db: Session, sorteo_id: int) -> bool:
    db_sorteo = obtener_sorteo(db, sorteo_id)
    if not db_sorteo:
        return False
    db.delete(db_sorteo)
    db.commit()
    return True


def obtener_todos_para_analisis(db: Session, loteria: Optional[str] = None) -> list[models.Sorteo]:
    """Trae todos los sorteos ordenados por fecha, usado por el módulo de estadísticas."""
    query = db.query(models.Sorteo)
    if loteria:
        query = query.filter(models.Sorteo.loteria == loteria)
    return query.order_by(asc(models.Sorteo.fecha)).all()
