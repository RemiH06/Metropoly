"""
cardFactory.py
==============
Genera casillas (.html) y tarjetas (.html) para el tablero Metropoly.

Cambios respecto a la versión SVG:
  - Salida HTML en vez de SVG (fuente CSS, imagen real de fondo).
  - Scraper de imágenes integrado: si src/img/{nombre}/ ya existe con al menos
    una imagen, la usa directamente (caché). Si no, la scrapea.
  - Proporciones definidas en board_config.json (porcentajes, no px fijos).
  - Soporte completo de tipos de casilla (tipo 1-15).
  - Rotación la sigue manejando boardFactory vía CSS en el <td>.
  - force=False → salta archivos ya generados.
"""

import os
import re
import json
import math
import time
import random
import shutil
import base64
import io
import csv
import urllib.request
from urllib.parse import urlparse

import requests
from PIL import Image
from bs4 import BeautifulSoup

# ── Selenium (solo se importa si hay que scrapear) ──────────────────────────
try:
    from selenium import webdriver as _webdriver
    from selenium.webdriver.chrome.options import Options as _Options
    from selenium.webdriver.common.by import By as _By
    from selenium.webdriver.support.ui import WebDriverWait as _WebDriverWait
    from selenium.webdriver.support import expected_conditions as _EC
    from selenium.webdriver.common.keys import Keys as _Keys
    _SELENIUM_OK = True
except ImportError:
    _SELENIUM_OK = False


# =============================================================================
# PATHS Y CONFIG
# =============================================================================

_HERE          = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR       = os.path.join(_HERE, "src")
_IMG_DIR       = os.path.join(_SRC_DIR, "img")
_CASILLAS_DIR  = os.path.join(_HERE, "repo", "casillas")
_TARJETAS_DIR  = os.path.join(_HERE, "repo", "tarjetas")
_CONFIG_PATH   = os.path.join(_SRC_DIR, "board_config.json")
_PALETTE_PATH  = os.path.join(_SRC_DIR, "palette.html")
_FONT_PATH     = os.path.join(_SRC_DIR, "KabelHeavy.ttf")
_WEBDRIVER_DIR = os.path.join(_HERE, "webdriver")

os.makedirs(_IMG_DIR,      exist_ok=True)
os.makedirs(_CASILLAS_DIR, exist_ok=True)
os.makedirs(_TARJETAS_DIR, exist_ok=True)


# =============================================================================
# HELPERS — CONFIG / PALETTE / FONT
# =============================================================================

def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_colors() -> dict:
    with open(_PALETTE_PATH, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    style = soup.find("style").string
    keys = [
        "basicBG", "yellowBG", "redBG", "borderBlack",
        "red", "orange", "yellow", "green", "blue", "pink",
        "lightBlue", "brown", "purple", "teal", "lavender",
        "lightGreen", "deepBlue", "gold", "chineseRed", "white",
    ]
    return {k: style.split(f"--{k}:")[1].split(";")[0].strip() for k in keys}


def _font_b64() -> str:
    if not os.path.exists(_FONT_PATH):
        return ""
    with open(_FONT_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _safe_name(nombre: str) -> str:
    """Convierte el nombre a un string seguro para usar en nombres de archivo."""
    return re.sub(r'[^\w\-]', '_', nombre)


# =============================================================================
# SCRAPER DE IMÁGENES  (integrado desde GoogleImageScraper)
# =============================================================================

def _webdriver_exe() -> str:
    import sys
    return "chromedriver" if sys.platform != "win32" else "chromedriver.exe"


def _scrape_images(nombre: str, n: int = 1, headless: bool = True,
                   min_res=(80, 80), max_res=(3840, 2160), max_missed: int = 5) -> str | None:
    """
    Scrapea Google Imágenes buscando `nombre`, guarda la primera imagen válida
    en src/img/{safe_nombre}/ y devuelve la ruta absoluta.
    Devuelve None si falla o si Selenium no está disponible.
    """
    if not _SELENIUM_OK:
        print(f"[cardFactory] Selenium no disponible, sin imagen para '{nombre}'.")
        return None

    safe = _safe_name(nombre)
    save_dir = os.path.join(_IMG_DIR, safe)
    os.makedirs(save_dir, exist_ok=True)

    driver_path = os.path.join(_WEBDRIVER_DIR, _webdriver_exe())
    if not os.path.isfile(driver_path):
        # intenta patch automático igual que el repo original
        try:
            import patch as _patch
            _patch.download_lastest_chromedriver()
        except Exception:
            pass
    if not os.path.isfile(driver_path):
        print(f"[cardFactory] chromedriver no encontrado en {driver_path}.")
        return None

    url = f"https://www.google.com/search?q={urllib.parse.quote(nombre)}&source=lnms&tbm=isch"
    options = _Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = _webdriver.Chrome(
        service=_webdriver.chrome.service.Service(driver_path),
        options=options,
    )
    driver.set_window_size(1400, 1050)
    driver.get(url)

    image_urls = []
    count = 0
    missed = 0
    time.sleep(2)

    try:
        first = _WebDriverWait(driver, 10).until(
            _EC.element_to_be_clickable((_By.CSS_SELECTOR, 'div[jsname="dTDiAc"]'))
        )
        first.click()
    except Exception as e:
        print(f"[cardFactory] No se pudo hacer click en primera imagen: {e}")
        driver.quit()
        return None

    while count < n * 6 and missed < max_missed:
        try:
            time.sleep(1)
            class_names = ["n3VNCb", "iPVvYb", "r48jcc", "pT0Scc"]
            imgs = [driver.find_elements(_By.CLASS_NAME, c) for c in class_names
                    if driver.find_elements(_By.CLASS_NAME, c)]
            imgs = imgs[0] if imgs else []
            for img in imgs:
                src = img.get_attribute("src") or ""
                if "http" in src and "encrypted" not in src:
                    image_urls.append(src)
                    count += 1
                    break
            else:
                missed += 1
        except Exception:
            missed += 1
        try:
            if count % 3 == 0:
                driver.find_element(_By.TAG_NAME, "body").send_keys(_Keys.ARROW_RIGHT)
            driver.find_element(_By.CLASS_NAME, "mye4qd").click()
            time.sleep(1)
        except Exception:
            time.sleep(1)

    driver.quit()
    image_urls = list(set(image_urls))

    # Guardar la primera imagen válida
    for idx, img_url in enumerate(image_urls):
        try:
            resp = requests.get(img_url, timeout=5)
            if resp.status_code != 200:
                continue
            with Image.open(io.BytesIO(resp.content)) as pil:
                w, h = pil.size
                if w < min_res[0] or h < min_res[1] or w > max_res[0] or h > max_res[1]:
                    continue
                o = urlparse(img_url)
                stem = os.path.splitext(os.path.basename(o.path))[0] or f"img_{idx}"
                filename = f"{stem}.jpg"
                out_path = os.path.join(save_dir, filename)
                pil.convert("RGB").save(out_path, "JPEG")
                print(f"[cardFactory] Imagen guardada: {out_path}")
                return out_path
        except Exception as e:
            print(f"[cardFactory] Error descargando imagen: {e}")

    return None


def _get_image_path(nombre: str, cfg: dict) -> str | None:
    """
    Devuelve la ruta absoluta de una imagen para esta casilla.
    1. Si src/img/{safe_nombre}/ existe y tiene archivos → usa el primero.
    2. Si no → scrapea.
    3. Si scrapea y falla → None.
    """
    safe = _safe_name(nombre)
    folder = os.path.join(_IMG_DIR, safe)
    if os.path.isdir(folder):
        files = [f for f in os.listdir(folder)
                 if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        if files:
            return os.path.join(folder, files[0])

    sc = cfg.get("scraper", {})
    return _scrape_images(
        nombre,
        n=sc.get("images_per_tile", 1),
        headless=sc.get("headless", True),
        min_res=sc.get("min_resolution", [80, 80]),
        max_res=sc.get("max_resolution", [3840, 2160]),
        max_missed=sc.get("max_missed", 5),
    )


def _img_to_b64(path: str) -> str:
    """Convierte imagen a data URI base64 para incrustarla en el HTML."""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{data}"


# =============================================================================
# CARGA DE PROPIEDADES (compatible con JSON original)
# =============================================================================

class Propiedad:
    def __init__(self, nombre, color, carril, imagen, precio, renta_base, tipo, posicion):
        self.nombre     = nombre
        self.color      = color
        self.carril     = int(carril)
        self.imagen     = imagen
        self.precio     = precio
        self.renta_base = renta_base
        self.tipo       = int(tipo)
        self.posicion   = int(posicion)


def cargar_propiedades(path: str) -> list[Propiedad]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Propiedad(**p) for p in data]


# =============================================================================
# TIPO → ETIQUETA LEGIBLE
# =============================================================================

_TIPO_LABELS = {
    1:  ("PROPIEDAD",      "Renta base",  True),
    2:  ("EMPRESA",        "Efecto empresa", False),
    3:  ("TREN",           "Efecto tren", False),
    4:  ("AEROPUERTO",     "Efecto aeropuerto", False),
    5:  ("LOTERÍA",        "Premio acumulado", False),
    6:  ("MINA",           "Tira un dado al caer", False),
    7:  ("CASINO",         "Todos ponen 100K", False),
    8:  ("NEGOCIO",        "Negocio temporal", True),
    9:  ("TAXI",           "Uso único", True),
    10: ("FORTUNA",        "Efecto aleatorio", False),
    11: ("CÁRCEL",         "3 turnos · 200K/turno", False),
    12: ("HOSPITAL",       "3 turnos · 300K/turno", False),
    13: ("SALIDA",         "Cobras 5M al pasar", False),
    14: ("CASA DE CAMBIO", "Cambia dinero por oro", False),
    15: ("DÍA DE PAGA",    "50K por fortuna roja", False),
}


def _tipo_info(tipo: int):
    return _TIPO_LABELS.get(tipo, (f"TIPO {tipo}", "", False))


# =============================================================================
# SHARED CSS (fuente + reset base)
# =============================================================================

def _base_css(font_b64: str) -> str:
    font_face = ""
    if font_b64:
        font_face = f"""
        @font-face {{
            font-family: 'KabelHeavy';
            src: url('data:font/ttf;base64,{font_b64}') format('truetype');
        }}"""
    return f"""
        {font_face}
        *, *::before, *::after {{
            box-sizing: border-box;
            margin: 0; padding: 0;
            font-family: 'KabelHeavy', 'Impact', sans-serif;
        }}
    """


# =============================================================================
# GENERADOR DE CASILLA (tile)
# =============================================================================

def generar_casilla(propiedad, force: bool = False, cfg: dict = None, colors: dict = None):
    """
    Genera 4 archivos HTML (rotaciones 0/90/180/270) para una casilla.
    Si force=False y los 4 ya existen, los salta.
    """
    if cfg    is None: cfg    = _load_config()
    if colors is None: colors = _get_colors()

    tile_cfg = cfg["tile"]
    band_pct    = tile_cfg["color_band_pct"]       # % del alto que ocupa la franja
    name_pct    = tile_cfg["name_top_pct"]          # % desde arriba donde va el nombre
    price_pct   = 100 - tile_cfg["price_bottom_pct"]
    font_min    = tile_cfg["font_min"]
    font_pref   = tile_cfg["font_pref"]
    font_max    = tile_cfg["font_max"]

    # Colores
    lane_bg = {1: "basicBG", 2: "yellowBG", 3: "redBG"}
    bg_color     = colors[lane_bg.get(propiedad.carril, "basicBG")]
    border_color = colors["borderBlack"]
    band_color   = colors.get(propiedad.color, colors["blue"])

    # Imagen de fondo (base64 para portabilidad al imprimir)
    img_path = _get_image_path(propiedad.nombre, cfg)
    img_css  = ""
    if img_path:
        b64 = _img_to_b64(img_path)
        img_css = f"background-image: url('{b64}'); background-size: cover; background-position: center;"

    # Etiqueta de precio
    precio_str = ""
    if propiedad.precio and str(propiedad.precio) not in ("0", "0.0", "nan", ""):
        p = float(propiedad.precio)
        if p >= 1_000_000:
            precio_str = f"{p/1_000_000:g}M"
        elif p >= 1_000:
            precio_str = f"{p/1_000:g}K"
        else:
            precio_str = str(int(p))

    font_b64  = _font_b64()
    base_css  = _base_css(font_b64)

    # Nombre display: recortado si es muy largo
    nombre_display = propiedad.nombre
    if len(nombre_display) > 24:
        nombre_display = nombre_display[:22] + "…"

    for angle in [0, 90, 180, 270]:
        out_path = os.path.join(_CASILLAS_DIR, f"casilla_{_safe_name(propiedad.nombre)}_{angle}.html")
        if not force and os.path.exists(out_path):
            continue

        # La casilla siempre se dibuja "derecha" (0°); la rotación la aplica boardFactory
        # al momento de inlinear en el <td>. Guardamos los 4 para compatibilidad
        # con la estructura existente pero el contenido es idéntico.
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
    {base_css}

    html, body {{
        width: 100%; height: 100%;
        overflow: hidden;
        background: transparent;
    }}

    .tile {{
        position: relative;
        width: 100%; height: 100%;
        background-color: {bg_color};
        {img_css}
        border: 2px solid {border_color};
        overflow: hidden;
        display: flex;
        flex-direction: column;
    }}

    /* Franja de color superior */
    .tile__band {{
        position: absolute;
        top: 0; left: 0; right: 0;
        height: {band_pct}%;
        background-color: {band_color};
        border-bottom: 1.5px solid {border_color};
        z-index: 2;
    }}

    /* Overlay semitransparente para legibilidad sobre la foto */
    .tile__overlay {{
        position: absolute;
        top: {band_pct}%; left: 0; right: 0; bottom: 0;
        background: rgba(255,255,255,0.38);
        z-index: 1;
    }}

    /* Nombre de la casilla */
    .tile__name {{
        position: absolute;
        top: {name_pct}%;
        left: 4%; right: 4%;
        text-align: center;
        font-size: clamp({font_min}, {font_pref}, {font_max});
        font-weight: normal;
        color: {border_color};
        text-transform: uppercase;
        letter-spacing: 0.03em;
        line-height: 1.15;
        z-index: 3;
        text-shadow: 0 1px 3px rgba(255,255,255,0.8);
    }}

    /* Precio en la parte inferior */
    .tile__price {{
        position: absolute;
        top: {price_pct}%;
        left: 0; right: 0;
        text-align: center;
        font-size: clamp({font_min}, {font_pref}, {font_max});
        color: {border_color};
        z-index: 3;
        text-shadow: 0 1px 3px rgba(255,255,255,0.9);
    }}
</style>
</head>
<body>
<div class="tile">
    <div class="tile__band"></div>
    <div class="tile__overlay"></div>
    <div class="tile__name">{nombre_display}</div>
    {"" if not precio_str else f'<div class="tile__price">{precio_str}</div>'}
</div>
</body>
</html>"""

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

    print(f"[cardFactory] Casilla generada: {propiedad.nombre}")


# =============================================================================
# GENERADOR DE TARJETA (card)
# =============================================================================

_TIPO_DETALLE = {
    1:  lambda p: [
            ("Renta base",          f"${int(float(p.renta_base)):,}"),
            ("Con 1 casa",          f"${int(float(p.renta_base)*2):,}"),
            ("Con 2 casas",         f"${int(float(p.renta_base)*4):,}"),
            ("Con hotel",           f"${int(float(p.renta_base)*8):,}"),
            ("Precio hipoteca",     f"${int(float(p.precio)//2):,}"),
        ],
    2:  lambda p: [
            ("Fórmula de cobro",    "Dados × (10 × (2 + N empresas))"),
            ("Precio compra",       f"${int(float(p.precio)):,}"),
        ],
    3:  lambda p: [
            ("Cobro base",          f"${int(float(p.precio)):,}"),
            ("Cobro c/ 2 trenes",   f"${int(float(p.precio)*2):,}"),
            ("Cobro c/ 3 trenes",   f"${int(float(p.precio)*3):,}"),
            ("Cobro c/ 4 trenes",   f"${int(float(p.precio)*4):,}"),
            ("Mover al sig. tren",  "100K"),
        ],
    4:  lambda p: [
            ("Cobro base",          f"${int(float(p.precio)):,}"),
            ("Mover a cualquier aeropuerto", "200K"),
            ("Nota",                "Solo cobras 2M al pasar salida si usas aeropuerto"),
        ],
    5:  lambda p: [
            ("Efecto",              "Toma todo el dinero acumulado de impuestos"),
        ],
    6:  lambda p: [
            ("1",  "Hospital 3T · paga 300K · recibe 1 oro"),
            ("2",  "Hospital 3T · paga 300K · recibe 2 oro"),
            ("3",  "Hospital 3T · paga 300K · recibe 5 oro"),
            ("4",  "Hospital 3T · paga 300K · recibe 10 oro"),
            ("5",  "Paga 200K · recibe 10 oro"),
            ("6",  "Recibe 10 oro gratis"),
        ],
    7:  lambda p: [
            ("Efecto",              "Todos ponen 100K · se juega una mano de póker"),
            ("Premio",              "El ganador se lleva el bote"),
        ],
    8:  lambda p: [
            ("Precio base",         f"${int(float(p.precio)):,}"),
            ("Precio compra",       f"${int(float(p.precio)*3):,}"),
            ("Renta al caer",       f"${int(float(p.precio)*5):,}"),
            ("Duración",            f"{int(float(p.renta_base))} turnos"),
        ],
    9:  lambda p: [
            ("Precio base",         f"${int(float(p.precio)):,}"),
            ("Precio compra",       f"${int(float(p.precio)*3):,}"),
            ("Renta al caer",       f"${int(float(p.precio)*5):,}"),
            ("Movimiento extra",    "10K por casilla (máx. 200K)"),
        ],
    10: lambda p: [
            ("Efecto",              "Ver la carta al robarla"),
        ],
    11: lambda p: [
            ("Costo por turno",     "200K"),
            ("Costo salida rápida", "500K"),
            ("Duración",            "3 turnos"),
            ("Nota",                "Pierdes todos los efectos rojos positivos"),
        ],
    12: lambda p: [
            ("Costo por turno",     "300K"),
            ("Duración",            "3 turnos"),
        ],
    13: lambda p: [
            ("Premio al pasar",     "5,000,000"),
        ],
    14: lambda p: [
            ("Efecto",              "Cambia dinero por oro o viceversa"),
        ],
    15: lambda p: [
            ("Efecto",              "Recibes 50K por cada fortuna roja que tengas"),
        ],
}


def generar_tarjeta(propiedad, force: bool = False, cfg: dict = None, colors: dict = None):
    """
    Genera una tarjeta HTML para la propiedad.
    Si force=False y el archivo ya existe, lo salta.
    """
    if cfg    is None: cfg    = _load_config()
    if colors is None: colors = _get_colors()

    out_path = os.path.join(_TARJETAS_DIR, f"tarjeta_{_safe_name(propiedad.nombre)}.html")
    if not force and os.path.exists(out_path):
        return

    card_cfg  = cfg["card"]
    w         = card_cfg["width_px"]
    h         = card_cfg["height_px"]
    band_px   = card_cfg["color_band_px"]

    lane_bg = {1: "basicBG", 2: "yellowBG", 3: "redBG"}
    bg_color     = colors[lane_bg.get(propiedad.carril, "basicBG")]
    border_color = colors["borderBlack"]
    band_color   = colors.get(propiedad.color, colors["blue"])

    tipo_label, tipo_subtitle, _has_renta = _tipo_info(propiedad.tipo)
    detalles = _TIPO_DETALLE.get(propiedad.tipo, lambda p: [])(propiedad)

    # Imagen de fondo semitransparente en el área bajo la franja
    img_path = _get_image_path(propiedad.nombre, cfg)
    img_bg_css = ""
    if img_path:
        b64 = _img_to_b64(img_path)
        img_bg_css = f"""
        .card__body {{
            background-image: url('{b64}');
            background-size: cover;
            background-position: center;
        }}"""

    # Filas de detalle
    rows_html = ""
    for label, value in detalles:
        rows_html += f"""
            <tr>
                <td class="detail-label">{label}</td>
                <td class="detail-value">{value}</td>
            </tr>"""

    font_b64 = _font_b64()
    base_css = _base_css(font_b64)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
    {base_css}
    {img_bg_css}

    html, body {{
        width: {w}px; height: {h}px;
        overflow: hidden;
        background: transparent;
    }}

    .card {{
        width: {w}px; height: {h}px;
        border: 2.5px solid {border_color};
        display: flex;
        flex-direction: column;
        overflow: hidden;
        position: relative;
    }}

    /* ── Franja superior ───────────────────────────── */
    .card__band {{
        width: 100%;
        height: {band_px}px;
        background-color: {band_color};
        border-bottom: 1.5px solid {border_color};
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        padding: 0 6px;
    }}

    .card__type {{
        font-size: {card_cfg["font_title"]};
        color: rgba(255,255,255,0.85);
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }}

    .card__name {{
        font-size: {card_cfg["font_name"]};
        color: #fff;
        text-transform: uppercase;
        text-align: center;
        line-height: 1.1;
        letter-spacing: 0.04em;
        text-shadow: 0 1px 4px rgba(0,0,0,0.4);
    }}

    /* ── Cuerpo ────────────────────────────────────── */
    .card__body {{
        flex: 1;
        background-color: {bg_color};
        position: relative;
        display: flex;
        flex-direction: column;
    }}

    /* Overlay para que el texto sea legible sobre la foto */
    .card__body-overlay {{
        position: absolute;
        inset: 0;
        background: rgba(255,255,255,0.55);
        z-index: 0;
    }}

    .card__content {{
        position: relative;
        z-index: 1;
        padding: 10px 8px 8px;
        flex: 1;
        display: flex;
        flex-direction: column;
    }}

    /* ── Subtítulo de tipo ─────────────────────────── */
    .card__subtitle {{
        font-size: {card_cfg["font_body"]};
        text-align: center;
        color: {border_color};
        opacity: 0.65;
        margin-bottom: 8px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }}

    /* ── Tabla de detalles ─────────────────────────── */
    .detail-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: {card_cfg["font_body"]};
    }}

    .detail-table tr {{
        border-bottom: 1px solid rgba(0,0,0,0.10);
    }}

    .detail-label {{
        color: {border_color};
        padding: 3px 4px;
        width: 52%;
        opacity: 0.80;
    }}

    .detail-value {{
        color: {border_color};
        padding: 3px 4px;
        text-align: right;
        font-weight: 900;
    }}

    /* ── Pie: precio hipoteca / compra ─────────────── */
    .card__footer {{
        border-top: 1.5px solid {border_color};
        padding: 5px 8px;
        font-size: {card_cfg["font_body"]};
        color: {border_color};
        display: flex;
        justify-content: space-between;
        background: rgba(255,255,255,0.6);
    }}
</style>
</head>
<body>
<div class="card">

    <div class="card__band">
        <span class="card__type">{tipo_label}</span>
        <span class="card__name">{propiedad.nombre}</span>
    </div>

    <div class="card__body">
        <div class="card__body-overlay"></div>
        <div class="card__content">
            <div class="card__subtitle">{tipo_subtitle}</div>
            <table class="detail-table">
                {rows_html}
            </table>
        </div>
    </div>

    <div class="card__footer">
        <span>Carril {propiedad.carril}</span>
        <span>Pos. {propiedad.posicion}</span>
        {"<span>Hipoteca: $" + str(int(float(propiedad.precio)//2)) + "</span>" if propiedad.precio and str(propiedad.precio) not in ("0","0.0","nan","") else ""}
    </div>

</div>
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[cardFactory] Tarjeta generada: {propiedad.nombre}")