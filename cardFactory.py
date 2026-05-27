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

# ── Selenium (se importa en tiempo de ejecución dentro de _scrape_images) ───
_SELENIUM_OK = None   # None = no verificado aún


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
    Devuelve None si falla o si Selenium no está instalado.
    """
    # Import en tiempo de ejecución para detectar instalaciones posteriores
    try:
        from selenium import webdriver as _webdriver
        from selenium.webdriver.chrome.options import Options as _Options
        from selenium.webdriver.common.by import By as _By
        from selenium.webdriver.support.ui import WebDriverWait as _WebDriverWait
        from selenium.webdriver.support import expected_conditions as _EC
        from selenium.webdriver.common.keys import Keys as _Keys
    except ImportError:
        print(
            "[cardFactory] Selenium no instalado. Ejecuta:\n"
            "    pip install selenium\n"
            "y asegúrate de tener chromedriver en la carpeta webdriver/"
        )
        return None

    safe = _safe_name(nombre)
    save_dir = os.path.join(_IMG_DIR, safe)
    os.makedirs(save_dir, exist_ok=True)

    url = f"https://www.google.com/search?q={urllib.parse.quote(nombre)}&tbm=isch&hl=es"
    options = _Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1400,1050")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver_path = os.path.join(_WEBDRIVER_DIR, _webdriver_exe())

    # Intentar usar webdriver-manager para obtener el driver correcto
    # automáticamente según la versión de Chrome instalada
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service as ChromeService
        service = ChromeService(ChromeDriverManager().install())
    except ImportError:
        # webdriver-manager no instalado, usar driver manual
        if not os.path.isfile(driver_path):
            print(
                "[cardFactory] chromedriver no encontrado. Instala webdriver-manager:\n"
                "    pip install webdriver-manager\n"
                "o coloca chromedriver.exe manualmente en la carpeta webdriver/"
            )
            return None
        service = _webdriver.chrome.service.Service(driver_path)
    except Exception as e:
        print(f"[cardFactory] Error configurando chromedriver: {e}")
        return None

    try:
        driver = _webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"[cardFactory] No se pudo iniciar Chrome: {e}")
        return None
    driver.set_window_size(1400, 1050)
    driver.get(url)
    time.sleep(3)

    # Intentar aceptar cookies si aparece el diálogo
    try:
        for btn_text in ["Aceptar todo", "Accept all", "Aceptar"]:
            btns = driver.find_elements(_By.XPATH, f"//button[contains(., '{btn_text}')]")
            if btns:
                btns[0].click()
                time.sleep(1)
                break
    except Exception:
        pass

    image_urls = []

    # Estrategia 1: extraer URLs de imágenes directamente del HTML/JS de la página
    # Google incrusta las URLs en atributos data-src y src de las miniaturas
    def extract_urls_from_page() -> list:
        found = []
        # Buscar imágenes con src de http (no data:image)
        imgs = driver.find_elements(_By.CSS_SELECTOR, "img[src^='http']")
        for img in imgs:
            src = img.get_attribute("src") or ""
            if src.startswith("http") and "encrypted" not in src and "gstatic" not in src:
                found.append(src)
        # También buscar en data-src
        imgs2 = driver.find_elements(_By.CSS_SELECTOR, "img[data-src^='http']")
        for img in imgs2:
            src = img.get_attribute("data-src") or ""
            if src.startswith("http") and "encrypted" not in src:
                found.append(src)
        return list(set(found))

    # Estrategia 2: click en miniaturas y extraer imagen de alta resolución
    def try_click_thumbnails() -> list:
        found = []
        # Selectores conocidos de miniaturas en Google Images (varios por compatibilidad)
        thumb_selectors = [
            'div[jsname="dTDiAc"]',
            'div[data-id]',
            'g-img > img',
            '.rg_i',
            'img.YQ4gaf',
            'img.t0fcAb',
        ]
        thumbs = []
        for sel in thumb_selectors:
            thumbs = driver.find_elements(_By.CSS_SELECTOR, sel)
            if thumbs:
                break

        for thumb in thumbs[:5]:
            try:
                driver.execute_script("arguments[0].click();", thumb)
                time.sleep(1.5)
                # Buscar imagen de alta res en el panel lateral
                for hi_sel in ['img.sFlh5c', 'img.r48jcc', 'img.iPVvYb', 'img.n3VNCb']:
                    hi_imgs = driver.find_elements(_By.CSS_SELECTOR, hi_sel)
                    for hi in hi_imgs:
                        src = hi.get_attribute("src") or ""
                        if src.startswith("http") and "encrypted" not in src and len(src) > 50:
                            found.append(src)
                            break
                if found:
                    break
            except Exception:
                continue
        return found

    # Estrategia 3: extraer URLs del page source (Google embebe JSON con URLs)
    def extract_from_source() -> list:
        found = []
        try:
            src = driver.page_source
            # Google embebe URLs de imagen en formato ["https://...","width","height"]
            matches = re.findall(r'"(https://[^"]+\.(?:jpg|jpeg|png|webp))"', src)
            for m in matches:
                if "encrypted" not in m and "gstatic" not in m:
                    found.append(m)
        except Exception:
            pass
        return list(set(found))

    # Primero intentar clicks para imagen de mayor calidad
    image_urls = try_click_thumbnails()

    # Si no funcionó, extracción directa de miniaturas
    if not image_urls:
        image_urls = extract_urls_from_page()

    # Último recurso: parsear el page source
    if not image_urls:
        image_urls = extract_from_source()
        print(f"[cardFactory] Estrategia page source: {len(image_urls)} URLs")

    driver.quit()
    image_urls = list(set(image_urls))
    print(f"[cardFactory] '{nombre}': {len(image_urls)} URLs encontradas")
    for i, u in enumerate(image_urls[:3]):
        print(f"[cardFactory]   [{i}] {u[:80]}")

    # Guardar la primera imagen válida
    for idx, img_url in enumerate(image_urls):
        try:
            resp = requests.get(img_url, timeout=5)
            if resp.status_code != 200:
                print(f"[cardFactory]   URL {idx}: HTTP {resp.status_code}")
                continue
            with Image.open(io.BytesIO(resp.content)) as pil:
                w, h = pil.size
                if w < min_res[0] or h < min_res[1] or w > max_res[0] or h > max_res[1]:
                    print(f"[cardFactory]   URL {idx}: resolución {w}x{h} fuera de rango")
                    continue
                o = urlparse(img_url)
                stem = os.path.splitext(os.path.basename(o.path))[0] or f"img_{idx}"
                filename = f"{stem}.jpg"
                out_path = os.path.join(save_dir, filename)
                pil.convert("RGB").save(out_path, "JPEG")
                print(f"[cardFactory] Imagen guardada: {out_path}")
                return out_path
        except Exception as e:
            print(f"[cardFactory]   URL {idx}: error — {e}")

    print(f"[cardFactory] '{nombre}': sin imagen válida")
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
    def __init__(self, nombre, color, carril, imagen, precio, renta_base, tipo):
        self.nombre     = nombre
        self.color      = color
        self.carril     = int(carril)
        self.imagen     = imagen
        self.precio     = precio
        self.renta_base = renta_base
        self.tipo       = int(tipo)


def cargar_propiedades(path: str) -> list[Propiedad]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Propiedad(**p) for p in data]


# =============================================================================
# TIPO → ETIQUETA LEGIBLE
# =============================================================================

_TIPO_LABELS = {
    1:  ("PROPIEDAD",      "Renta",              True),
    2:  ("EMPRESA",        "Empresa de servicio", False),
    3:  ("TREN",           "Transporte",          False),
    4:  ("AEROPUERTO",     "Transporte aéreo",    False),
    5:  ("LOTERÍA",        "Premio acumulado",    False),
    6:  ("MINA",           "Tira un dado",        False),
    7:  ("CASINO",         "¡Todos al póker!",    False),
    8:  ("NEGOCIO",        "Negocio temporal",    True),
    9:  ("TAXI",           "Uso único",           True),
    10: ("FORTUNA",        "Roba una carta",      False),
    11: ("CÁRCEL",         "No pases, no cobres", False),
    12: ("HOSPITAL",       "Reposo obligatorio",  False),
    13: ("SALIDA",         "¡Cobra al pasar!",    False),
    14: ("CASA DE CAMBIO", "Dinero ↔ Oro",        False),
    15: ("DÍA DE PAGA",    "Cobra tus fortunas",  False),
}


def _tipo_info(tipo: int):
    return _TIPO_LABELS.get(tipo, (f"TIPO {tipo}", "", False))


# =============================================================================
# EMPRESA → EFECTO ESPECÍFICO
# (mapa por nombre para tipo=2, ya que cada empresa tiene reglas distintas)
# =============================================================================

_EMPRESA_EFECTOS = {
    # ── Carril azul ──────────────────────────────────────────────────────────
    "Caseta de Zapotlanejo": [
        ("Efecto",       "Recibes 1M extra cada vez que alguien pase por la Salida"),
        ("Al caer",      "Fórmula: Dados × (10 × (2 + N empresas))"),
    ],
    "IMSS Jalisco": [
        ("Efecto dueño",  "Recibes todos los gastos médicos ajenos · nunca pagas los tuyos"),
        ("Al caer",       "300K fijo (tarifa IMSS)"),
        ("Nota",          "No se puede sacar a alguien del hospital, solo mitigar con efectos rojos"),
    ],
    "SIAPA": [
        ("Efecto",        "Transfiere fortunas entre jugadores cada 5 turnos"),
        ("Al caer",       "Fórmula: Dados × (10 × (2 + N empresas))"),
    ],
    "Telcel Jalisco": [
        ("Efecto",        "El dueño puede ver la carta de hasta arriba de cualquier mazo"),
        ("Al caer",       "Fórmula: Dados × (10 × (2 + N empresas))"),
    ],
    # ── Carril amarillo ──────────────────────────────────────────────────────
    "Megacable Guadalajara": [
        ("Efecto",        "El dueño puede revolver cualquier mazo de fortunas una vez por turno"),
        ("Al caer",       "Fórmula: Dados × (10 × (2 + N empresas))"),
    ],
    "UdeG": [
        ("Efecto",        "Tirada extra cuando al menos 2 dados caen igual"),
        ("Costo",         "Sacrifica un turno y paga el precio de la tarjeta"),
        ("Al caer",       "Fórmula: Dados × (10 × (2 + N empresas))"),
    ],
    "Palacio Municipal de Guadalajara": [
        ("Efecto",        "Retiene el 10% de todas las transacciones del juego"),
        ("Al caer",       "Sin costo al caer · solo cobra por transacciones"),
    ],
    "CFE Jalisco": [
        ("Efecto",        "Recupera del banco el 20% del total apostado por mano en el Casino"),
        ("Al caer",       "Fórmula: Dados × (10 × (2 + N empresas))"),
    ],
    # ── Carril rojo ──────────────────────────────────────────────────────────
    "Puente Grande": [
        ("Efecto dueño",  "Recibes todos los gastos de cárcel de los demás jugadores"),
        ("Si el dueño va a la cárcel", "Pierde la empresa · regresa al gobierno"),
        ("Al caer",       "200K fijo (tarifa penal)"),
    ],
    "Gas Natural del Occidente": [
        ("Efecto",        "Puedes destruir e inhabilitar 2 casillas convirtiéndolas en lotes vacíos"),
        ("Nota",          "Las casillas de otros carriles en esa posición siguen activas"),
        ("Al caer",       "Fórmula: Dados × (10 × (2 + N empresas))"),
    ],
    "Caabsa Eagle": [
        ("Efecto",        "Coloca un obstáculo en cualquier casilla obligando a cambiar de carril"),
        ("Nota",          "Los efectos negativos en esa casilla siguen aplicando"),
        ("Al caer",       "Fórmula: Dados × (10 × (2 + N empresas))"),
    ],
    "Pemex López Mateos": [
        ("Efecto",        "Recibes la mitad de todo el dinero que muevan los taxis"),
        ("Al caer",       "Fórmula: Dados × (10 × (2 + N empresas))"),
    ],
}

def _empresa_detalle(nombre: str) -> list:
    """Devuelve los detalles de una empresa por nombre. Fallback genérico si no está mapeada."""
    return _EMPRESA_EFECTOS.get(nombre, [
        ("Efecto",      "Ver reglas del juego"),
        ("Al caer",     "Fórmula: Dados × (10 × (2 + N empresas))"),
    ])


# =============================================================================
# SHARED CSS (fuente + reset base)
# =============================================================================

def _font_exists() -> bool:
    return os.path.exists(_FONT_PATH)


def _font_face_css(rel_path: str) -> str:
    """
    Devuelve el bloque @font-face usando una ruta relativa al TTF.
    Si la fuente no existe, devuelve string vacío (fallback a Impact).
    """
    if not _font_exists():
        return ""
    return f"""@font-face {{
            font-family: 'KabelHeavy';
            src: url('{rel_path}') format('truetype');
        }}"""


def _base_css() -> str:
    """CSS base — referencia KabelHeavy por nombre, con Century Gothic como fallback."""
    return """
        *, *::before, *::after {
            box-sizing: border-box;
            margin: 0; padding: 0;
            font-family: 'KabelHeavy', 'Century Gothic', 'URW Gothic', 'Futura', sans-serif;
        }
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

    # Las empresas (tipo 2) van en esquinas — sin franja de color de grupo
    # Las demás casillas muestran franja con el color de su grupo
    is_corner_type = propiedad.tipo == 2
    if is_corner_type:
        band_color = bg_color   # franja del mismo color que el fondo = invisible
        effective_band_pct = 0
    else:
        band_color = colors.get(propiedad.color, colors["blue"])
        effective_band_pct = band_pct

    # Imagen de fondo (base64 para portabilidad al imprimir)
    img_path = _get_image_path(propiedad.nombre, cfg)
    img_css  = ""
    if img_path:
        b64 = _img_to_b64(img_path)
        img_css = f"background-image: url('{b64}'); background-size: cover; background-position: center;"

    # Etiqueta de precio
    # Tipos que no se pueden comprar — no muestran precio ni hipoteca
    NO_COMPRABLE = {10, 14, 15}
    is_comprable = propiedad.tipo not in NO_COMPRABLE

    precio_str = ""
    if is_comprable and propiedad.precio and str(propiedad.precio) not in ("0", "0.0", "nan", ""):
        p = float(propiedad.precio)
        if p >= 1_000_000:
            precio_str = f"{p/1_000_000:g}M"
        elif p >= 1_000:
            precio_str = f"{p/1_000:g}K"
        else:
            precio_str = str(int(p))

    # Ruta relativa al TTF desde repo/casillas/
    font_face = _font_face_css("../../src/KabelHeavy.ttf")
    base_css  = _base_css()

    # Nombre display: recortado si es muy largo
    nombre_display = propiedad.nombre
    if len(nombre_display) > 24:
        nombre_display = nombre_display[:22] + "…"

    has_font = _font_exists()   # True si KabelHeavy.ttf existe

    for angle in [0, 90, 180, 270]:
        out_path = os.path.join(_CASILLAS_DIR, f"casilla_{_safe_name(propiedad.nombre)}_{angle}.html")
        if not force and os.path.exists(out_path):
            with open(out_path, "r", encoding="utf-8") as f:
                existing = f.read()
            needs_image = img_path and "background-image" not in existing
            needs_font  = has_font and "@font-face" not in existing
            # Invalidar si el color de franja cambió — busca el background-color de .tile__band
            resolved_color = colors.get(propiedad.color, "")
            needs_color = resolved_color and f"background-color: {resolved_color}" not in existing
            if not needs_image and not needs_font and not needs_color:
                continue

        # La casilla siempre se dibuja "derecha" (0°); la rotación la aplica boardFactory
        # al momento de inlinear en el <td>. Guardamos los 4 para compatibilidad
        # con la estructura existente pero el contenido es idéntico.
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
{f'<style>{font_face}</style>' if font_face else ''}
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
        height: {effective_band_pct}%;
        background-color: {band_color};
        {f'border-bottom: 1.5px solid {border_color};' if not is_corner_type else ''}
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
        top: {5 if is_corner_type else name_pct}%;
        left: 4%; right: 4%;
        text-align: center;
        font-size: 11px;
        font-weight: normal;
        color: {border_color};
        text-transform: uppercase;
        letter-spacing: 0.06em;
        line-height: 1.2;
        z-index: 3;
        text-shadow: 0 1px 2px rgba(255,255,255,0.9);
        word-break: break-word;
    }}

    /* Precio en la parte inferior */
    .tile__price {{
        position: absolute;
        top: {price_pct}%;
        left: 0; right: 0;
        text-align: center;
        font-size: 10px;
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
    # ── 1: PROPIEDAD ─────────────────────────────────────────────────────────
    1: lambda p: [
        ("Renta base",       f"${int(float(p.renta_base)):,}"),
        ("Con 1 casa",       f"${int(float(p.renta_base) * 2):,}"),
        ("Con 2 casas",      f"${int(float(p.renta_base) * 4):,}"),
        ("Con 3 casas",      f"${int(float(p.renta_base) * 8):,}"),
        ("Con 4 casas",      f"${int(float(p.renta_base) * 16):,}"),
        ("Con hotel",        f"${int(float(p.renta_base) * 32):,}"),
        ("Costo casa",       f"${int(float(p.precio)):,}"),
        ("Costo hotel",      f"${int(float(p.precio) * 4):,}  (4 casas)"),
        ("Precio hipoteca",  f"${int(float(p.precio) // 2):,}"),
    ],

    # ── 2: EMPRESA ───────────────────────────────────────────────────────────
    # Delegado a _empresa_detalle() por nombre; ver sección _EMPRESA_EFECTOS
    2: lambda p: _empresa_detalle(p.nombre),

    # ── 3: TREN ──────────────────────────────────────────────────────────────
    3: lambda p: [
        ("Cobro c/ 1 tren",  f"${int(float(p.precio)):,}"),
        ("Cobro c/ 2 trenes", f"${int(float(p.precio) * 2):,}"),
        ("Cobro c/ 3 trenes", f"${int(float(p.precio) * 3):,}"),
        ("Cobro c/ 4 trenes", f"${int(float(p.precio) * 4):,}"),
        ("Mover al sig. tren", "100K"),
        ("Nota",              "Si usas el tren, solo cobras 2M al pasar la Salida"),
    ],

    # ── 4: AEROPUERTO ────────────────────────────────────────────────────────
    4: lambda p: [
        ("Cobro c/ 1 aeropuerto", f"${int(float(p.precio)):,}"),
        ("Cobro c/ 2",        f"${int(float(p.precio) // 2):,}"),
        ("Cobro c/ 3",        f"${int(float(p.precio) // 3):,}"),
        ("Cobro c/ 4",        f"${int(float(p.precio) // 4):,}"),
        ("Volar a cualquier aeropuerto", "200K"),
        ("Nota",              "Si usas el aeropuerto, solo cobras 2M al pasar la Salida"),
    ],

    # ── 5: LOTERÍA ───────────────────────────────────────────────────────────
    5: lambda p: [
        ("Efecto",            "Toma todo el dinero acumulado de impuestos del centro"),
        ("Nota",              "Si el bote está vacío, no cobras nada"),
    ],

    # ── 6: MINA ──────────────────────────────────────────────────────────────
    6: lambda p: [
        ("🎲 1",  "Hospital 3 turnos · paga 300K · recibe 1 oro"),
        ("🎲 2",  "Hospital 3 turnos · paga 300K · recibe 2 oro"),
        ("🎲 3",  "Hospital 3 turnos · paga 300K · recibe 5 oro"),
        ("🎲 4",  "Hospital 3 turnos · paga 300K · recibe 10 oro"),
        ("🎲 5",  "Paga 200K · recibe 10 oro"),
        ("🎲 6",  "Recibe 10 oro gratis"),
    ],

    # ── 7: CASINO ────────────────────────────────────────────────────────────
    7: lambda p: [
        ("Al caer",           "Todos los jugadores ponen 100K en el bote"),
        ("Mecánica",          "Se juega una mano de póker"),
        ("Retiro",            "Cualquier jugador puede retirarse en cualquier momento"),
        ("Premio",            "El ganador se lleva todo el bote"),
        ("Bonus dueño CFE",   "CFE recupera 20% del total apostado de la banca"),
    ],

    # ── 8: NEGOCIO ───────────────────────────────────────────────────────────
    8: lambda p: [
        ("Al caer (sin dueño)", f"${int(float(p.precio)):,}"),
        ("Precio de compra",  f"${int(float(p.precio) * 3):,}"),
        ("Renta al caer",     f"${int(float(p.precio) * 5):,}"),
        ("Duración",          f"{int(float(p.renta_base))} turnos"),
        ("Vencimiento",       "Regresa al gobierno al expirar"),
    ],

    # ── 9: TAXI ──────────────────────────────────────────────────────────────
    9: lambda p: [
        ("Al caer (sin dueño)", f"${int(float(p.precio)):,}"),
        ("Precio de compra",  f"${int(float(p.precio) * 3):,}"),
        ("Renta al caer",     f"${int(float(p.precio) * 5):,}"),
        ("Uso único",         "Expira tras la primera renta cobrada"),
        ("Si caes en el tuyo","Compra movimientos: 10K por casilla (máx. 200K)"),
        ("Bonus Pemex",       "Pemex recibe la mitad de todo lo que muevas"),
    ],

    # ── 10: FORTUNA ──────────────────────────────────────────────────────────
    # El efecto específico está en la carta física; la tarjeta solo indica el carril
    10: lambda p: _fortuna_detalle(p.carril),

    # ── 11: CÁRCEL ───────────────────────────────────────────────────────────
    11: lambda p: [
        ("Condición de entrada", "3 fortunas iguales · condición de juego · casilla policía"),
        ("Costo por turno",   "200K"),
        ("Salida rápida",     "500K"),
        ("Duración",          "3 turnos"),
        ("Pierdes",           "Todos los efectos rojos positivos acumulados"),
        ("Si el dueño cae",   "Pierde la empresa · regresa al gobierno"),
    ],

    # ── 12: HOSPITAL ─────────────────────────────────────────────────────────
    12: lambda p: [
        ("Condición de entrada", "Mina · Carta de pistola · otros efectos"),
        ("Costo por turno",   "300K"),
        ("Duración",          "3 turnos"),
        ("Dueño del IMSS",    "Recibe todos los gastos médicos ajenos · nunca paga los suyos"),
        ("Nota",              "No se puede sacar a alguien sin efectos rojos"),
    ],

    # ── 13: SALIDA ───────────────────────────────────────────────────────────
    13: lambda p: [
        ("Premio al pasar",   "5,000,000"),
        ("Si usas tren",      "Solo cobras 2,000,000"),
        ("Si usas aeropuerto","Solo cobras 2,000,000"),
    ],

    # ── 14: CASA DE CAMBIO ───────────────────────────────────────────────────
    14: lambda p: [
        ("Efecto",            "Cambia dinero por oro o viceversa"),
        ("Ubicación",         "Esquinas del carril amarillo"),
        ("Nota",              "La tasa de cambio la decide el banco"),
    ],

    # ── 15: DÍA DE PAGA ──────────────────────────────────────────────────────
    15: lambda p: [
        ("Efecto",            "Recibes 200K por cada propiedad que tengas"),
        ("No comprable",      "Esta casilla no se puede adquirir"),
        ("Nota",              "Solo cuentan propiedades tipo 1 en tu poder"),
    ],

    # ── 16: EMPRESA + SALIDA (Caseta de Zapotlanejo) ─────────────────────────
    16: lambda p: [
        ("Tipo",              "Empresa especial · también es la casilla de Salida"),
        ("Al pasar",          "Recibes el 20% del salario base acordado"),
        ("Si tiene dueño",    "El salario al pasar va al dueño · lo cobra cuando pase él mismo"),
        ("Precio de compra",  f"${int(float(p.precio)):,}"),
        ("Cobro al caer",     f"Dados × (10 × (2 + N° de empresas que posees))"),
        ("Oficinas",          f"Hasta 4 · duplican el cobro por dados"),
        ("Torres",            f"Hasta 2 · el cobro se duplica dos veces adicionales"),
    ],
}


def _fortuna_detalle(carril: int) -> list:
    """Devuelve la descripción de cartas disponibles según el carril."""
    if carril == 1:  # azul
        return [
            ("Carta de pistola ×4", "Asalta a un jugador en la misma casilla: envíalo al hospital, roba dinero o una propiedad"),
            ("Accidente ×1",        "Pierdes automáticamente todo tu dinero"),
            ("Carta de hijo ×2",    "Pagas el doble 3 turnos · luego tienes un 4° dado permanente"),
        ]
    elif carril == 2:  # amarillo
        return [
            ("Suerte alterada ×4",  "Comodín para cualquier mano de póker"),
            ("Patrón de oro ×2",    "Cambia todo tu dinero por oro de inmediato"),
            ("Dados cargados ×6",   "Tira los dados una vez más este turno"),
        ]
    else:  # rojo
        return [
            ("Banca popular ×1",       "Administras el banco · todo su dinero pasa a tus manos"),
            ("Seguro social ×8",       "Ve al hospital una vez sin pagar"),
            ("Prestaciones sup. ×4",   "Por cada negocio que tengas, paga 100K"),
            ("Manifestación ×2",       "Los demás juegan con 1 solo dado hasta tu próximo turno"),
            ("Turnocturno ×6",         "Tira los dados una vez más este turno"),
            ("Revolución ×1",          "Efecto inmediato: todas las casas y hoteles regresan al gobierno (requiere mayoría)"),
        ]


def generar_tarjeta(propiedad, force: bool = False, cfg: dict = None, colors: dict = None):
    """
    Genera una tarjeta HTML para la propiedad.
    Si force=False y el archivo ya existe, lo salta.
    """
    if cfg    is None: cfg    = _load_config()
    if colors is None: colors = _get_colors()

    out_path = os.path.join(_TARJETAS_DIR, f"tarjeta_{_safe_name(propiedad.nombre)}.html")

    # Verificar caché: obtener img_path primero para saber si debemos regenerar
    img_path = _get_image_path(propiedad.nombre, cfg)

    if not force and os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            existing = f.read()
        needs_image = img_path and "background-image" not in existing
        needs_font  = _font_exists() and "@font-face" not in existing
        resolved_color = colors.get(propiedad.color, "")
        needs_color = resolved_color and f"background-color: {resolved_color}" not in existing
        if not needs_image and not needs_font and not needs_color:
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

    # Ruta relativa al TTF desde repo/tarjetas/
    font_face = _font_face_css("../../src/KabelHeavy.ttf")
    base_css  = _base_css()

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
{f'<style>{font_face}</style>' if font_face else ''}
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
        {"<span>Hipoteca: $" + str(int(float(propiedad.precio)//2)) + "</span>" if is_comprable and propiedad.precio and str(propiedad.precio) not in ("0","0.0","nan","") else ""}
    </div>

</div>
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[cardFactory] Tarjeta generada: {propiedad.nombre}")