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
        .nombre  .color  .carril  .imagen  .precio  .renta_base  .tipo
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
                          "precio", "renta_base", "tipo"]
    for col in columnas_esperadas:
        if col not in df.columns:
            raise ValueError(f"Falta la columna requerida: '{col}'")

    df["carril"]   = df["carril"].astype(int)
    df["tipo"]     = df["tipo"].astype(int)

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
    "Estación Centro (Línea 1)", "Estación Zapopan Centro",
    "Estación Tetlán", "Estación Tlaquepaque",
    "Aeropuerto Internacional de Guadalajara (GDL)", "Aeropuerto de Zapopan",
    "Aeropuerto de Toluquilla", "Helipuerto Puerta de Hierro",
    "Fortuna de Chapultepec", "Fortuna de Andares",
    "Fortuna del Centro Histórico", "El Colli",
]

yellowLane = [
    "Plaza del Sol", "Galerías Guadalajara", "Midtown Jalisco",
    "Mercado San Juan de Dios", "Plaza Patria", "Landmark", "Plaza Andares",
    "Templo Expiatorio", "Mercado de Atemajac", "Plaza Fórum Tlaquepaque",
    "Mercado de Abastos", "Plaza Bugambilias", "Plaza Ciudadela",
    "Mercado Libertad", "Tonalá", "Tlaquepaque",
    "Twin Lions", "Casino Majestic", "PlayCity", "Caliente",
    "Av. López Mateos", "Av. Vallarta", "Av. Patria", "Av. Hidalgo",
    "Av. Juárez", "Periférico Norte", "Lázaro Cárdenas", "Niños Héroes",
]

redLane = [
    "Colapso del Periférico", "Tráfico de López Mateos",
    "Lluvia en la Glorieta", "Marcha del Centro",
    "Desvío del Tren Ligero", "El Parquímetro", "El Multón",
    "Asalto", "El Gasolinazo", "Manifestación",
    "Inspección Municipal", "Apagón",
    "Casa de Cambio Chapultepec", "Casa de Cambio Providencia",
    "Casa de Cambio Tlaquepaque", "Casa de Cambio Centro",
    "Día de Paga Norte", "Día de Paga Sur",
    "Día de Paga Oriente", "Día de Paga Poniente",
    "La Seca", "El Temblor", "El Bache", "La Lluvia Ácida",
]

blueCorners = [
    "Caseta de Zapotlanejo", "IMSS Jalisco", "SIAPA", "Telcel Jalisco",
]

yellowCorners = [
    "Megacable Guadalajara", "UdeG",
    "Palacio Municipal de Guadalajara", "CFE Jalisco",
]

redCorners = [
    "Puente Grande", "Gas Natural del Occidente",
    "Caabsa Eagle", "Pemex López Mateos",
]


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def _check_fonts():
    """Verifica que los recursos de fuente existen y advierte si faltan."""
    from cardFactory import _FONT_PATH, _font_b64
    import os

    if not os.path.exists(_FONT_PATH):
        print(
            f"\n⚠️  ADVERTENCIA: No se encontró la fuente en '{_FONT_PATH}'\n"
            f"   Las casillas y tarjetas usarán Impact como fallback.\n"
            f"   Coloca KabelHeavy.ttf en src/ para usar la fuente correcta.\n"
        )
        return False

    b64 = _font_b64()
    if not b64:
        print(
            f"\n⚠️  ADVERTENCIA: El archivo '{_FONT_PATH}' existe pero no se pudo leer.\n"
            f"   Verifica que el archivo no esté corrupto o vacío.\n"
        )
        return False

    size_kb = os.path.getsize(_FONT_PATH) // 1024
    if size_kb < 100:
        print(
            f"\n⚠️  ADVERTENCIA: '{_FONT_PATH}' es sospechosamente pequeño ({size_kb} KB).\n"
            f"   Un TTF válido de KabelHeavy debería pesar ~150 KB.\n"
            f"   El archivo podría estar incompleto — la fuente puede no renderizar correctamente.\n"
        )
        return False

    print(f"[generator] Fuente KabelHeavy OK ({size_kb} KB)")
    return True


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
    parser.add_argument(
        "--workers", type=int, default=1,
        help="Número de workers paralelos para scraping (default: 1, recomendado: 2-3)"
    )
    args = parser.parse_args()

    force = args.force
    if force:
        print("[generator] Modo FORCE: se regenerarán todas las casillas y tarjetas.")

    _check_fonts()

    cfg    = _load_config()
    colors = _get_colors()

    # ── Cargar CSV ───────────────────────────────────────────────────────────
    import pandas as pd

    raw_df = pd.read_csv(args.input)
    raw_df['precio']     = pd.to_numeric(raw_df['precio'],     errors='coerce').fillna(0)
    raw_df['renta_base'] = pd.to_numeric(raw_df['renta_base'], errors='coerce').fillna(0)

    # ── Construir listas de carriles ordenadas por precio ────────────────────
    def build_sorted_lane(df, carril, slots):
        sub       = df[df['carril'] == carril]
        props     = sub[sub['tipo'] == 1].sort_values('precio').reset_index(drop=True)
        non_props = sub[(sub['tipo'] != 1) & (sub['tipo'] != 2) & (sub['tipo'] != 16)].reset_index(drop=True)
        return pd.concat([props, non_props], ignore_index=True)['nombre'].tolist()[:slots]

    from boardFactory import sideLengthFromPerimeter, BLUE_CANONICAL
    boardSize    = sideLengthFromPerimeter(BLUE_CANONICAL)
    blue_slots   = (boardSize - 1 - 1) * 4
    yellow_slots = (boardSize - 2 - 1 - 1) * 4
    red_slots    = (boardSize - 4 - 1 - 1) * 4

    sorted_blue   = build_sorted_lane(raw_df, 1, blue_slots)
    sorted_yellow = build_sorted_lane(raw_df, 2, yellow_slots)
    sorted_red    = build_sorted_lane(raw_df, 3, red_slots)

    print(f"[generator] Lanes: azul={len(sorted_blue)}, amarillo={len(sorted_yellow)}, rojo={len(sorted_red)}")

    # Cargar propiedades — colores ya están explícitos en el CSV
    propiedades = cargar_propiedades_generico(args.input)
    total = len(propiedades)

    # ── Contadores de progreso thread-safe ───────────────────────────────────
    import threading
    lock      = threading.Lock()
    completed = [0]   # lista mutable para poder modificar desde dentro del closure

    def procesar(prop):
        generar_casilla(prop, force=force, cfg=cfg, colors=colors)
        generar_tarjeta(prop, force=force, cfg=cfg, colors=colors)
        with lock:
            completed[0] += 1
            remaining = total - completed[0]
            print(f"[generator] [{completed[0]}/{total}] {prop.nombre} — {remaining} restantes")

    # ── Ejecución ─────────────────────────────────────────────────────────────
    workers = max(1, args.workers)
    if workers == 1:
        for prop in propiedades:
            procesar(prop)
    else:
        print(f"[generator] Usando {workers} workers paralelos")
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(procesar, prop): prop for prop in propiedades}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    prop = futures[future]
                    print(f"[generator] Error en '{prop.nombre}': {e}")

    print("[generator] Generando tablero HTML...")
    saveBoardHtml(
        outputPath        = args.output,
        blueLaneNames     = sorted_blue,
        yellowLaneNames   = sorted_yellow,
        redLaneNames      = sorted_red,
        blueCornerNames   = blueCorners,
        yellowCornerNames = yellowCorners,
        redCornerNames    = redCorners,
        fit               = False,
    )
    print(f"[generator] Tablero guardado en '{args.output}'")


if __name__ == "__main__":
    main()