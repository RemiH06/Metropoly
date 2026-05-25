"""
generator.py
============
Punto de entrada principal. Lee el CSV / JSON / XLSX, genera casillas y
tarjetas (con caché), y construye el tablero HTML.

Uso básico:
    python generator.py                 # usa caché, no regenera lo que ya existe
    python generator.py --force         # regenera todo aunque exista
"""

import os
import sys
import argparse
from types import SimpleNamespace
import pandas as pd

from cardFactory  import generar_casilla, generar_tarjeta, cargar_propiedades, _load_config, _get_colors
from boardFactory import saveBoardHtml

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

INPUT_FILE  = os.path.join("props", "zmg.csv")
OUTPUT_FILE = os.path.join("repo", "tableros", "tablero_metropoly.html")


# ══════════════════════════════════════════════════════════════════════════════
# CARGA DE PROPIEDADES (CSV / JSON / XLSX)
# ══════════════════════════════════════════════════════════════════════════════

def cargar_propiedades_generico(path: str):
    """
    Carga propiedades desde JSON, CSV o Excel.
    Siempre devuelve una lista de objetos con atributos:
        .nombre  .color  .carril  .imagen  .precio  .renta_base  .tipo  .posicion
    """
    ext = os.path.splitext(path)[1].lower()

    if ext == ".json":
        return cargar_propiedades(path)

    if ext == ".csv":
        df = pd.read_csv(path)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Extensión no soportada: {ext}")

    columnas_esperadas = ["nombre", "color", "carril", "imagen",
                          "precio", "renta_base", "tipo", "posicion"]
    for col in columnas_esperadas:
        if col not in df.columns:
            raise ValueError(f"Falta la columna requerida: '{col}'")

    df["carril"]   = df["carril"].astype(int)
    df["tipo"]     = df["tipo"].astype(int)
    df["posicion"] = df["posicion"].astype(int)

    # Rellenar NaN en precio / renta_base con 0
    df["precio"]     = df["precio"].fillna(0)
    df["renta_base"] = df["renta_base"].fillna(0)

    return [SimpleNamespace(**row) for row in df.to_dict(orient="records")]


# ══════════════════════════════════════════════════════════════════════════════
# NOMBRES DE CARRILES Y ESQUINAS
# ══════════════════════════════════════════════════════════════════════════════

blueLane = [
    "Chapalita", "Providencia", "Americana", "Santa Tere", "Arcos Vallarta",
    "Country Club", "Jardines del Bosque", "Puerta de Hierro", "Andares",
    "Colonia Seattle", "Lomas de Atemajac", "Ciudad del Sol", "La Estancia",
    "Altamira", "Real Vallarta", "La Calma", "Monraz", "Ladrón de Guevara",
    "Colinas de San Javier", "Colonia Moderna",
]

yellowLane = [
    "Plaza del Sol", "Galerías Guadalajara", "Midtown Jalisco", "Mercado San Juan de Dios",
    "Plaza Patria", "Landmark", "Plaza Andares", "Templo Expiatorio", "Mercado de Atemajac",
    "Plaza Fórum Tlaquepaque", "Mercado de Abastos", "Plaza Bugambilias", "Plaza Ciudadela",
    "Tianguis Cultural", "Glorieta Chapalita", "Mercado Libertad", "El Salto", "Tonalá",
    "Tlaquepaque", "Tesistán", "Twin Lions", "Casino Majestic", "PlayCity", "Caliente",
    "Av. López Mateos", "Av. Vallarta", "Av. Patria", "Av. Hidalgo", "Av. Juárez",
    "Periférico Norte", "Lázaro Cárdenas", "Niños Héroes", "Aeropuerto GDL",
    "Andares", "San Juan de Dios", "Centro Histórico",
]

redLane = [
    "Fortuna del Colapso del Periférico", "Fortuna del Tráfico de López Mateos",
    "Fortuna de la Lluvia en la Glorieta", "Fortuna de la Marcha del Centro",
    "Fortuna del Desvío del Tren Ligero", "Fortuna del Parquímetro", "Fortuna del Multón",
    "Fortuna del Asalto", "Fortuna del Gasolinazo", "Fortuna de la Manifestación",
    "Fortuna de la Inspección Municipal", "Fortuna del Apagón",
]

blueCorners = [
    "Caseta de Zapotlanejo", "Hospital Civil de Guadalajara", "SIAPA", "Telcel Jalisco",
]

yellowCorners = [
    "Megacable Guadalajara", "UdeG", "Palacio Municipal de Guadalajara", "CFE Jalisco",
]

redCorners = [
    "Puente Grande", "Gas Natural del Occidente", "Caabsa Eagle", "Pemex López Mateos",
]


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Generador de tablero Metropoly")
    parser.add_argument(
        "--force", action="store_true",
        help="Regenera casillas/tarjetas aunque ya existan (ignora caché)"
    )
    parser.add_argument(
        "--input", default=INPUT_FILE,
        help=f"Ruta al archivo de propiedades (default: {INPUT_FILE})"
    )
    parser.add_argument(
        "--output", default=OUTPUT_FILE,
        help=f"Ruta de salida del tablero HTML (default: {OUTPUT_FILE})"
    )
    args = parser.parse_args()

    force = args.force
    if force:
        print("[generator] Modo FORCE: se regenerarán todas las casillas y tarjetas.")

    # Carga compartida (evita leer disco N veces)
    cfg    = _load_config()
    colors = _get_colors()

    propiedades = cargar_propiedades_generico(args.input)
    print(f"[generator] {len(propiedades)} propiedades cargadas desde '{args.input}'")

    for prop in propiedades:
        generar_casilla(prop, force=force, cfg=cfg, colors=colors)
        generar_tarjeta(prop, force=force, cfg=cfg, colors=colors)

    print("[generator] Generando tablero HTML...")
    saveBoardHtml(
        outputPath        = args.output,
        blueLaneNames     = blueLane,
        yellowLaneNames   = yellowLane,
        redLaneNames      = redLane,
        blueCornerNames   = blueCorners,
        yellowCornerNames = yellowCorners,
        redCornerNames    = redCorners,
        fit               = False,
    )
    print(f"[generator] Tablero guardado en '{args.output}'")


if __name__ == "__main__":
    main()
