"""
fortunaFactory.py
=================
Genera tarjetas de fortuna (.html) para los tres carriles de Metropoly.

Formato: horizontal (350×200px), estilo Monopoly Suerte/Caja Comunidad.
Estructura:
  ┌────────────────────────────────────────┐
  │  [franja de color]  FORTUNA AZUL/...  │
  ├───────────┬────────────────────────────┤
  │           │  Nombre de la carta        │
  │  [sprite] │                            │
  │  gw_XY    │  Descripción del efecto    │
  │           │                            │
  │           │  ★★★☆☆  nivel              │
  └───────────┴────────────────────────────┘

Sprites: src/gw/gw_{carril}{nivel}.svg
  - carril 1=azul, 2=amarillo, 3=rojo
  - nivel 1-5

CSV: props/fortunas.csv
  columnas: nombre, carril, nivel, efecto, tipo, cantidad
"""

import os
import re
import json
import pandas as pd
from bs4 import BeautifulSoup

# =============================================================================
# PATHS
# =============================================================================

_HERE        = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR     = os.path.join(_HERE, "src")
_GW_DIR      = os.path.join(_SRC_DIR, "gw")
_FONT_PATH   = os.path.join(_SRC_DIR, "KabelHeavy.ttf")
_PALETTE_PATH= os.path.join(_SRC_DIR, "palette.html")
_OUT_DIR     = os.path.join(_HERE, "repo", "fortunas")

os.makedirs(_OUT_DIR, exist_ok=True)
os.makedirs(_GW_DIR,  exist_ok=True)


# =============================================================================
# HELPERS
# =============================================================================

def _safe_name(s: str) -> str:
    return re.sub(r'[^\w\-]', '_', s)


def _get_colors() -> dict:
    with open(_PALETTE_PATH, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    style = soup.find("style").string
    keys = [
        "basicBG", "yellowBG", "redBG", "borderBlack",
        "blue", "yellow", "red", "white",
    ]
    return {k: style.split(f"--{k}:")[1].split(";")[0].strip() for k in keys}


def _font_face_css() -> str:
    if not os.path.exists(_FONT_PATH):
        return ""
    return """@font-face {
    font-family: 'KabelHeavy';
    src: url('../../../src/KabelHeavy.ttf') format('truetype');
}"""


def _stars(nivel: int) -> str:
    """Genera indicador visual de nivel con estrellas."""
    filled = "★" * nivel
    empty  = "☆" * (5 - nivel)
    return filled + empty


def _sprite_path(carril: int, nivel: int) -> str:
    """Ruta relativa al sprite desde repo/fortunas/"""
    # Soporta .svg y .png — prioriza .svg si existe
    for ext in ("svg", "png"):
        if os.path.exists(os.path.join(_GW_DIR, f"gw_{carril}{nivel}.{ext}")):
            return f"../../src/gw/gw_{carril}{nivel}.{ext}"
    return f"../../src/gw/gw_{carril}{nivel}.png"  # fallback


def _sprite_exists(carril: int, nivel: int) -> bool:
    for ext in ("svg", "png"):
        if os.path.exists(os.path.join(_GW_DIR, f"gw_{carril}{nivel}.{ext}")):
            return True
    return False


def _lane_info(carril: int, colors: dict) -> tuple[str, str, str]:
    """Devuelve (nombre_carril, color_franja, color_fondo)"""
    if carril == 1:
        return "Fortuna Azul",   colors["blue"],   colors["basicBG"]
    elif carril == 2:
        return "Fortuna Amarilla", colors["yellow"], colors["yellowBG"]
    else:
        return "Fortuna Roja",   colors["red"],    colors["redBG"]


def _nivel_color(nivel: int) -> str:
    """Color de las estrellas según nivel."""
    palette = {1: "#9B111E", 2: "#F7941D", 3: "#FEF200",
               4: "#1FB25A", 5: "#0072BB"}
    return palette.get(nivel, "#888")


# =============================================================================
# GENERADOR DE TARJETA
# =============================================================================

def generar_fortuna(row, force: bool = False, colors: dict = None):
    """
    Genera una tarjeta HTML para una carta de fortuna.
    El nombre de archivo incluye carril y nivel: fortuna_{carril}_{safe_nombre}.html
    """
    if colors is None:
        colors = _get_colors()

    carril  = int(row["carril"])
    nivel   = int(row["nivel"])
    nombre  = str(row["nombre"])
    efecto  = str(row["efecto"])

    safe    = _safe_name(nombre)
    out_path = os.path.join(_OUT_DIR, f"fortuna_{carril}_{safe}.html")

    if not force and os.path.exists(out_path):
        return

    lane_name, band_color, bg_color = _lane_info(carril, colors)
    border_color = colors["borderBlack"]
    stars        = _stars(nivel)
    star_color   = _nivel_color(nivel)
    font_face    = _font_face_css()
    sprite_path  = _sprite_path(carril, nivel)
    has_sprite   = _sprite_exists(carril, nivel)

    # Sprite: imagen si existe, placeholder de color si no
    if has_sprite:
        sprite_html = f'<img src="{sprite_path}" alt="nivel {nivel}" style="width:80px;height:80px;object-fit:contain;">'
    else:
        # Placeholder con número de nivel mientras no estén los sprites
        sprite_html = f'''<div style="
            width:80px;height:80px;
            background:{band_color};
            border-radius:50%;
            display:flex;align-items:center;justify-content:center;
            font-size:32px;font-weight:900;color:white;
            opacity:0.7;
        ">{nivel}</div>'''

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
{f'<style>{font_face}</style>' if font_face else ''}
<style>
    *, *::before, *::after {{
        box-sizing: border-box; margin: 0; padding: 0;
        font-family: 'KabelHeavy', 'Century Gothic', 'Futura', sans-serif;
    }}
    html, body {{
        width: 350px; height: 200px;
        overflow: hidden; background: transparent;
    }}
    .card {{
        width: 350px; height: 200px;
        border: 2.5px solid {border_color};
        display: flex; flex-direction: column;
        overflow: hidden; background: {bg_color};
    }}
    .card__header {{
        width: 100%; height: 32px;
        background: {band_color};
        border-bottom: 1.5px solid {border_color};
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
    }}
    .card__header span {{
        font-size: 11px; letter-spacing: 0.12em;
        text-transform: uppercase; color: white;
        text-shadow: 0 1px 2px rgba(0,0,0,0.4);
    }}
    .card__body {{
        flex: 1; display: flex; flex-direction: row;
        overflow: hidden;
    }}
    .card__sprite {{
        width: 110px; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center;
        border-right: 1px solid {border_color}22;
        padding: 8px;
    }}
    .card__content {{
        flex: 1; padding: 10px 12px 8px;
        display: flex; flex-direction: column; justify-content: space-between;
    }}
    .card__nombre {{
        font-size: 13px; font-weight: 900;
        text-transform: uppercase;
        color: {border_color};
        letter-spacing: 0.04em;
        line-height: 1.1;
        margin-bottom: 6px;
    }}
    .card__efecto {{
        font-size: 10.5px; color: {border_color};
        line-height: 1.4; flex: 1;
        opacity: 0.85;
    }}
    .card__nivel {{
        margin-top: 6px;
        display: flex; align-items: center; gap: 6px;
    }}
    .card__stars {{
        font-size: 13px; color: {star_color};
        letter-spacing: 1px;
    }}
    .card__nivel-label {{
        font-size: 9px; opacity: 0.5;
        text-transform: uppercase; letter-spacing: 0.08em;
        color: {border_color};
    }}
</style>
</head>
<body>
<div class="card">
    <div class="card__header">
        <span>{lane_name}</span>
    </div>
    <div class="card__body">
        <div class="card__sprite">
            {sprite_html}
        </div>
        <div class="card__content">
            <div class="card__nombre">{nombre}</div>
            <div class="card__efecto">{efecto}</div>
            <div class="card__nivel">
                <span class="card__stars">{stars}</span>
                <span class="card__nivel-label">Nivel {nivel}</span>
            </div>
        </div>
    </div>
</div>
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


# =============================================================================
# CARGA Y GENERACIÓN MASIVA
# =============================================================================

def cargar_fortunas(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = ["nombre", "carril", "nivel", "efecto", "tipo", "cantidad"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Falta columna requerida en fortunas CSV: '{col}'")
    df["carril"]   = df["carril"].astype(int)
    df["nivel"]    = df["nivel"].astype(int)
    df["cantidad"] = df["cantidad"].astype(int)
    return df


def generar_todas(csv_path: str, force: bool = False):
    """Genera todas las tarjetas de fortuna desde el CSV."""
    df     = cargar_fortunas(csv_path)
    colors = _get_colors()
    total  = len(df)

    # Resumen de sprites faltantes
    faltantes = []
    for carril in [1, 2, 3]:
        for nivel in [1, 2, 3, 4, 5]:
            if not _sprite_exists(carril, nivel):
                faltantes.append(f"gw_{carril}{nivel}.svg")
    if faltantes:
        print(f"[fortunaFactory] ⚠️  Sprites faltantes en src/gw/ (se usará placeholder):")
        for f in faltantes:
            print(f"   {f}")

    for i, (_, row) in enumerate(df.iterrows(), 1):
        generar_fortuna(row, force=force, colors=colors)

    print(f"[fortunaFactory] {total} tarjetas de fortuna generadas en repo/fortunas/")
    print(f"[fortunaFactory] Distribución:")
    for carril, nombre in [(1, "Azul"), (2, "Amarillo"), (3, "Rojo")]:
        sub = df[df["carril"] == carril]
        copias = sub["cantidad"].sum()
        print(f"   Carril {carril} ({nombre}): {len(sub)} tipos · {copias} copias")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generador de tarjetas de fortuna")
    parser.add_argument("--input",  default=os.path.join("props", "fortunas.csv"))
    parser.add_argument("--force",  action="store_true")
    args = parser.parse_args()
    generar_todas(args.input, force=args.force)