"""
Carga un pequeño conjunto de datos DE PRUEBA (ficticios) en la base local,
únicamente para verificar que la aplicación funciona de punta a punta:
API, base de datos, frontend y el análisis de ciclos del siete.

IMPORTANTE: estos números NO son resultados reales de la Lotería de Bogotá.
Son datos inventados con fines de prueba técnica. Los resultados históricos
reales se incorporarán en la Fase 2 (OCR de prensa, hemeroteca, fuentes
oficiales verificadas), conforme a lo planeado en el proyecto.

Uso:
    python -m scripts.cargar_datos_demo
"""
import random
from datetime import date

from backend.database import Base, SessionLocal, engine
from backend.models import Sorteo

random.seed(7)  # reproducible


def generar_datos_prueba():
    """
    Genera sorteos ficticios repartidos entre 1970 y 2026, incluyendo
    a propósito algunas repeticiones exactas cada 7/14/21 años para que
    la función de ciclos del siete tenga algo que detectar durante la prueba.
    """
    registros = []

    # Semana "base": un sorteo ficticio por año, con número intencionalmente
    # repetido cada 7 años para poder probar /estadisticas/ciclos-siete.
    numero_base = "0356"
    for anio in range(1970, 2027, 7):
        registros.append(
            Sorteo(
                loteria="Lotería de Bogotá",
                fecha=date(anio, 6, 15),
                anio=anio,
                numero=numero_base,
                serie="012",
                fuente="dato de prueba (ficticio)",
                verificado=False,
            )
        )

    # Relleno aleatorio para tener más volumen de datos de prueba
    for anio in range(1970, 2027):
        if anio % 7 == 0:
            continue  # ya se agregó arriba
        numero = f"{random.randint(0, 9999):04d}"
        serie = f"{random.randint(0, 999):03d}"
        registros.append(
            Sorteo(
                loteria="Lotería de Bogotá",
                fecha=date(anio, 12, 20),
                anio=anio,
                numero=numero,
                serie=serie,
                fuente="dato de prueba (ficticio)",
                verificado=False,
            )
        )

    return registros


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existentes = db.query(Sorteo).count()
        if existentes > 0:
            print(f"La base ya tiene {existentes} sorteos. No se insertaron datos de prueba.")
            print("Si quieres reiniciar, borra el archivo azar.db y vuelve a ejecutar este script.")
            return

        registros = generar_datos_prueba()
        db.add_all(registros)
        db.commit()
        print(f"Se insertaron {len(registros)} sorteos DE PRUEBA (ficticios) para validar la app.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
