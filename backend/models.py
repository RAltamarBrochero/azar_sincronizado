"""
Modelo de datos para los sorteos de lotería.

Empezamos exclusivamente con la Lotería de Bogotá (campo `loteria`),
pero el modelo ya queda preparado para otras loterías colombianas.
"""
from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, UniqueConstraint, func

from .database import Base


class Sorteo(Base):
    __tablename__ = "sorteos"

    id = Column(Integer, primary_key=True, index=True)

    loteria = Column(String, nullable=False, index=True, default="Lotería de Bogotá")
    fecha = Column(Date, nullable=False, index=True)
    anio = Column(Integer, nullable=False, index=True)  # redundante pero acelera consultas por ciclos
    numero_sorteo = Column(Integer, nullable=True)  # número consecutivo del sorteo, si se conoce

    # Número del premio mayor. Se guarda como texto de 4 dígitos (ej: "0356")
    # para no perder ceros a la izquierda.
    numero = Column(String(4), nullable=False)
    serie = Column(String(10), nullable=True)
    ciudad = Column(String, nullable=True)  # ciudad donde se transmitió/realizó el sorteo, cuando se conoce

    fuente = Column(String, nullable=True)  # de dónde se obtuvo el dato (OCR, prensa, API oficial, manual...)
    verificado = Column(Boolean, default=False)  # True cuando el dato fue confirmado por al menos 2 fuentes

    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("loteria", "fecha", name="uq_loteria_fecha"),
    )
