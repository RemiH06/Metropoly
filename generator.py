import os
from types import SimpleNamespace  # 👈 Para convertir dict -> objeto con atributos
import pandas as pd

from cardFactory import generar_casilla, generar_tarjeta, cargar_propiedades
from boardFactory import saveBoardHtml

# ================== CONFIGURACIÓN DE ENTRADA ==================

# Cambia esto a .json / .csv / .xlsx según necesites
INPUT_FILE = 'props/zmg.csv'


def cargar_propiedades_generico(path: str):
    """
    Carga propiedades desde:
    - JSON (usa la función original cargar_propiedades)
    - CSV
    - Excel (.xlsx, .xls)

    Siempre regresa una lista de objetos con atributos:
        propiedad.nombre, propiedad.color, propiedad.carril, etc.
    """
    ext = os.path.splitext(path)[1].lower()

    # Caso original: JSON -> usamos tu función ya existente
    if ext == ".json":
        return cargar_propiedades(path)

    # CSV / Excel -> usamos pandas
    if ext == ".csv":
        df = pd.read_csv(path)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Extensión de archivo no soportada: {ext}")

    # Columnas que deben existir en el archivo
    columnas_esperadas = [
        "nombre",
        "color",
        "carril",
        "imagen",
        "precio",
        "renta_base",
        "tipo",
        "posicion",
    ]
    for col in columnas_esperadas:
        if col not in df.columns:
            raise ValueError(f"Falta la columna requerida en el archivo: '{col}'")

    # Tipos básicos
    df["carril"] = df["carril"].astype(int)
    df["tipo"] = df["tipo"].astype(int)
    df["posicion"] = df["posicion"].astype(int)

    # Convertimos a lista de dicts...
    records = df.to_dict(orient="records")
    # ...y luego a objetos con atributos (propiedad.carril, propiedad.nombre, etc.)
    propiedades = [SimpleNamespace(**row) for row in records]
    return propiedades


# ================== CARGA Y GENERACIÓN DE CASILLAS ==================

propiedades = cargar_propiedades_generico(INPUT_FILE)

for propiedad in propiedades:
    generar_casilla(propiedad)
    generar_tarjeta(propiedad)


# ================== DEFINICIÓN DE CARRILES Y ESQUINAS ==================

blueLane = [
    "Chapalita", "Providencia", "Americana", "Santa Tere", "Arcos Vallarta",
    "Country Club", "Jardines del Bosque", "Puerta de Hierro", "Andares",
    "Colonia Seattle", "Lomas de Atemajac", "Ciudad del Sol", "La Estancia",
    "Altamira", "Real Vallarta", "La Calma", "Monraz", "Ladrón de Guevara",
    "Colinas de San Javier", "Colonia Moderna"
]

yellowLane = [
    "Plaza del Sol", "Galerías Guadalajara", "Midtown Jalisco", "Mercado San Juan de Dios",
    "Plaza Patria", "Landmark", "Plaza Andares", "Templo Expiatorio", "Mercado de Atemajac",
    "Plaza Fórum Tlaquepaque", "Mercado de Abastos", "Plaza Bugambilias", "Plaza Ciudadela",
    "Tianguis Cultural", "Glorieta Chapalita", "Mercado Libertad", "El Salto", "Tonalá",
    "Tlaquepaque", "Tesistán", "Twin Lions", "Casino Majestic", "PlayCity", "Caliente",
    "Av. López Mateos", "Av. Vallarta", "Av. Patria", "Av. Hidalgo", "Av. Juárez",
    "Periférico Norte", "Lázaro Cárdenas", "Niños Héroes", "Aeropuerto GDL",
    "Andares", "San Juan de Dios", "Centro Histórico"
]

redLane = [
    "Fortuna del Colapso del Periférico", "Fortuna del Tráfico de López Mateos",
    "Fortuna de la Lluvia en la Glorieta", "Fortuna de la Marcha del Centro",
    "Fortuna del Desvío del Tren Ligero", "Fortuna del Parquímetro", "Fortuna del Multón",
    "Fortuna del Asalto", "Fortuna del Gasolinazo", "Fortuna de la Manifestación",
    "Fortuna de la Inspección Municipal", "Fortuna del Apagón"
]

blueCorners = [
    "Caseta de Zapotlanejo", "Hospital Civil de Guadalajara", "SIAPA", "Telcel Jalisco"
]

yellowCorners = [
    "Megacable Guadalajara", "UdeG", "Palacio Municipal de Guadalajara", "CFE Jalisco"
]

redCorners = [
    "Puente Grande", "Gas Natural del Occidente", "Caabsa Eagle", "Pemex López Mateos"
]

outputPath = "repo/tableros/tablero_metropoly.html"

saveBoardHtml(
    outputPath=outputPath,
    blueLaneNames=blueLane,
    yellowLaneNames=yellowLane,
    redLaneNames=redLane,
    blueCornerNames=blueCorners,
    yellowCornerNames=yellowCorners,
    redCornerNames=redCorners,
    fit=False,
)
