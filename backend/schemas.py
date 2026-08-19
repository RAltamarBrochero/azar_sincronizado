"""
Esquemas Pydantic: validan lo que entra y define lo que sale de la API.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SorteoBase(BaseModel):
    loteria: str = Field(default="Lotería de Bogotá", max_length=100)
    fecha: date
    numero: str = Field(..., min_length=1, max_length=4)
    serie: Optional[str] = Field(default=None, max_length=10)
    ciudad: Optional[str] = Field(default=None, max_length=100)
    numero_sorteo: Optional[int] = None
    fuente: Optional[str] = None
    verificado: bool = False

    @field_validator("numero")
    @classmethod
    def normalizar_numero(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit():
            raise ValueError("El número del premio mayor debe contener solo dígitos")
        return v.zfill(4)  # completa con ceros a la izquierda, ej: "56" -> "0056"


class SorteoCreate(SorteoBase):
    pass


class SorteoOut(SorteoBase):
    id: int
    anio: int
    creado_en: Optional[datetime] = None

    class Config:
        from_attributes = True


class CicloCoincidencia(BaseModel):
    tipo: str  # ej: "dos_primeros", "dos_ultimos", "tres_primeros", "tres_ultimos", "numero_completo"
    ciclo_anios: int  # 7, 14, 21, 24, 35, 42, 49, 56
    valor: str
    anio_origen: int
    anio_repite: int
    fecha_origen: date
    fecha_repite: date


class EstadisticasResumen(BaseModel):
    total_sorteos: int
    anio_min: Optional[int] = None
    anio_max: Optional[int] = None
    numeros_mas_frecuentes: list[dict]


class PreguntaAgente(BaseModel):
    pregunta: str = Field(..., min_length=1, max_length=500)


class RespuestaAgente(BaseModel):
    respuesta: str
