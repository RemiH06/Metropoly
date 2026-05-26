"""
boardFactory.py
===============
Genera el tablero HTML de Metropoly con 3 anillos concéntricos.

Cambio respecto a la versión anterior:
  - renderTileCell lee el archivo casilla_{nombre}_{angle}.html y lo inlinea
    directamente en el <td>, en vez de usar un <img src=...>.
  - El <div class="tile"> dentro del HTML inlineado ya tiene width/height 100%,
    así que hereda las dimensiones del <td> sin necesidad de transform.
"""

import os
import json
import math
from dataclasses import dataclass
from typing import Dict, Tuple, List, Optional


# =========================
# CONSTANTS
# =========================

TILE_WIDTH   = 50
TILE_HEIGHT  = TILE_WIDTH * 1.5
CORNER_SIZE  = TILE_HEIGHT

BLUE_CANONICAL   = 40
YELLOW_CANONICAL = BLUE_CANONICAL - 4
RED_CANONICAL    = YELLOW_CANONICAL - 4

NULL_TILE_FILE = "casilla_NULL"

DEFAULT_TILES_DIR  = os.path.join("repo", "casillas")
DEFAULT_PROPS_PATH = os.path.join("props", "zmg.csv")


# =========================
# MODEL
# =========================

@dataclass
class TileCell:
    htmlPath:  str           # ruta al .html de la casilla
    rotation:  int           # grados de rotación
    name:      Optional[str]
    lane:      str
    isCorner:  bool


# =========================
# PROPERTIES HELPERS
# =========================

def loadProperties(propsPath: str = DEFAULT_PROPS_PATH) -> Dict[str, dict]:
    """
    Carga propiedades desde JSON, CSV o Excel.
    Devuelve un dict indexado por nombre de casilla.
    Si el archivo no existe, devuelve {} silenciosamente.
    """
    if not os.path.exists(propsPath):
        return {}

    ext = os.path.splitext(propsPath)[1].lower()

    if ext == ".json":
        with open(propsPath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "properties" in data:
            propList = data["properties"]
        elif isinstance(data, list):
            propList = data
        else:
            propList = []
        propByName: Dict[str, dict] = {}
        for prop in propList:
            name = prop.get("name") or prop.get("nombre") or prop.get("Nombre")
            if name:
                propByName[name] = prop
        return propByName

    # CSV / Excel — usa pandas si está disponible
    try:
        import pandas as pd
        if ext == ".csv":
            df = pd.read_csv(propsPath)
        else:
            df = pd.read_excel(propsPath)
        return {row["nombre"]: row.to_dict() for _, row in df.iterrows() if "nombre" in df.columns}
    except ImportError:
        return {}


def validateLaneAssignments(
    laneNames:   List[str],
    cornerNames: List[str],
    laneColor:   str,
    propByName:  Dict[str, dict],
    label:       str,
) -> None:
    # Mapa número de carril → nombre de color
    _LANE_NUM = {"1": "blue", "2": "yellow", "3": "red"}

    allNames = list(laneNames) + list(cornerNames)
    for name in allNames:
        prop = propByName.get(name)
        if not prop:
            print(f"[boardFactory] Warning: '{name}' from {label} no encontrada en el archivo de props")
            continue

        raw = prop.get("lane") or prop.get("carril") or prop.get("Carril") or ""
        # Normalizar: "2" → "yellow", "blue" → "blue"
        lane_normalized = _LANE_NUM.get(str(raw).strip(), str(raw).strip().lower())
        if lane_normalized and lane_normalized != laneColor.lower():
            print(
                f"[boardFactory] Warning: '{name}' tiene carril '{raw}' ({lane_normalized}) "
                f"pero está listada en {label} ('{laneColor}')"
            )


# =========================
# GEOMETRY HELPERS
# =========================

def sideLengthFromPerimeter(perimeter: int) -> int:
    if perimeter < 4:
        return 2
    return perimeter // 4 + 1


def computeSideLengthForFit(tileCount: int) -> int:
    tileCount = max(tileCount, 4)
    sideFloat = (tileCount + 4) / 4.0
    return max(3, math.ceil(sideFloat))


def iterRingCoordinates(size: int):
    last = size - 1
    for col in range(size):
        yield (last, col)
    for row in range(last - 1, -1, -1):
        yield (row, last)
    for col in range(last - 1, -1, -1):
        yield (0, col)
    for row in range(1, last):
        yield (row, 0)


def computeRotation(row: int, col: int, size: int) -> int:
    last = size - 1
    if row == 0:    return 0
    if col == last: return 90
    if row == last: return 180
    if col == 0:    return 270
    return 0


def isCorner(row: int, col: int, size: int) -> bool:
    last = size - 1
    return (row in (0, last)) and (col in (0, last))


# =========================
# RING CONSTRUCTION
# =========================

def _safe_name(nombre: str) -> str:
    import re
    return re.sub(r'[^\w\-]', '_', nombre)


def createRingCells(
    size:         int,
    laneNames:    List[str],
    cornerNames:  List[str],
    laneColor:    str,
    tilesDir:     str,
    nullTileFile: str = NULL_TILE_FILE,
) -> Dict[Tuple[int, int], TileCell]:

    coords     = list(iterRingCoordinates(size))
    laneIter   = iter(laneNames)
    cornerIter = iter(cornerNames)
    ringCells: Dict[Tuple[int, int], TileCell] = {}

    for row, col in coords:
        cornerFlag = isCorner(row, col, size)
        name       = None

        if cornerFlag:
            if   row == 0      and col == 0:         rotation = 0
            elif row == 0      and col == size - 1:  rotation = 90
            elif row == size-1 and col == size - 1:  rotation = 180
            else:                                     rotation = 270
            try:   name = next(cornerIter)
            except StopIteration: name = None
        else:
            rotation = computeRotation(row, col, size)
            try:   name = next(laneIter)
            except StopIteration: name = None

        if name:
            safe_n   = _safe_name(name)
            fileName = f"casilla_{safe_n}_{rotation}.html"
            filePath = os.path.join(tilesDir, fileName)
            if not os.path.exists(filePath):
                print(
                    f"[boardFactory] Warning: '{fileName}' no encontrado para '{name}', "
                    f"usando NULL."
                )
                filePath = os.path.join(tilesDir, f"{nullTileFile}_{rotation}.html")
        else:
            filePath = os.path.join(tilesDir, f"{nullTileFile}_{rotation}.html")

        cell = TileCell(
            htmlPath  = filePath.replace("\\", "/"),
            rotation  = rotation,
            name      = name,
            lane      = laneColor,
            isCorner  = cornerFlag,
        )
        ringCells[(row, col)] = cell

    return ringCells


# =========================
# RENDER — INLINE HTML
# =========================

# Set global que acumula reglas @font-face de todas las casillas inlineadas.
# generateBoardHtml lo vacía antes de cada build y lo inyecta en el <head>.
_BOARD_FONT_CACHE: set = set()


def renderTileCell(cell: TileCell, cell_class: str = "") -> str:
    """
    Inlinea el HTML de una casilla dentro del <td> del tablero.

    Estrategia de rotación sin recorte
    ────────────────────────────────────
    Cada casilla se diseña siempre en orientación portrait (TILE_W × TILE_H,
    con TILE_W < TILE_H). Al incrustarla en el tablero hay dos tipos de <td>:

      rot 0 / 180  →  <td> es .horizontal: TILE_W × TILE_H  (portrait = encaja directo)
      rot 90 / 270 →  <td> es .vertical:   TILE_H × TILE_W  (landscape)

    Para el caso landscape usamos el truco clásico de doble wrapper:
      1. outer  (TILE_H × TILE_W)  — tamaño real del <td>, overflow:hidden
      2. canvas (TILE_W × TILE_H)  — tamaño portrait, centrado absolutamente
                                     dentro del outer, luego rotado
      El canvas rotado 90° ocupa visualmente TILE_H × TILE_W → llena el outer.

    CSS scoping
    ────────────
    Extraemos el <style> de la casilla y reemplazamos cada selector de clase
    (.tile, .tile__band, …) con un prefijo único (.t{uid} .tile, …) para que
    no colisione con otras casillas inlineadas en el mismo documento.
    """
    import re

    TILE_W = 150   # ancho portrait (px)
    TILE_H = 225   # alto  portrait (px)

    uid = abs(hash(cell.htmlPath)) % 10**8

    # ── Leer HTML de la casilla ──────────────────────────────────────────────
    if os.path.exists(cell.htmlPath):
        with open(cell.htmlPath, "r", encoding="utf-8") as f:
            raw = f.read()

        body_match  = re.search(r"<body[^>]*>(.*?)</body>",   raw, re.DOTALL | re.IGNORECASE)
        style_match = re.search(r"<style[^>]*>(.*?)</style>", raw, re.DOTALL | re.IGNORECASE)
        body_html  = body_match.group(1).strip()  if body_match  else raw
        style_raw  = style_match.group(1).strip() if style_match else ""

        # Scopear cada regla CSS: ".tile { … }" → ".s{uid} .tile { … }"
        # Las reglas @font-face se extraen y se devuelven por separado para
        # inyectarlas en el <head> del tablero (no dentro de un selector).
        def scope_css(css: str, prefix: str) -> tuple[str, str]:
            """Devuelve (css_scoped, font_face_rules)."""
            scoped  = []
            at_root = []   # @font-face, @keyframes, etc. — van al root
            for block in re.split(r'(?<=\})', css):
                block = block.strip()
                if not block:
                    continue
                brace = block.find('{')
                if brace == -1:
                    scoped.append(block)
                    continue
                selectors_str = block[:brace].strip()
                declarations  = block[brace:]
                if selectors_str.startswith('@'):
                    at_root.append(block)   # @font-face va fuera del scope
                    continue
                new_sels = []
                for sel in selectors_str.split(','):
                    sel = sel.strip()
                    if not sel or sel in ('html', 'body', 'html body', '*'):
                        continue
                    new_sels.append(f"{prefix} {sel}")
                if new_sels:
                    scoped.append(f"{', '.join(new_sels)} {declarations}")
            return '\n'.join(scoped), '\n'.join(at_root)

        prefix     = f".s{uid}"
        scoped_css, font_rules = scope_css(style_raw, prefix)
        scoped_style = f"<style>{scoped_css}</style>"
        # font_rules se pasa al caller via atributo del wrapper para que
        # generateBoardHtml las inyecte en el <head> una sola vez
        _BOARD_FONT_CACHE.add(font_rules)   # set global deduplica automáticamente

        # Añadir clase de scoping al div raíz (.tile)
        body_scoped = body_html.replace(
            'class="tile"', f'class="tile {prefix[1:]}"', 1
        )
        canvas_content = scoped_style + body_scoped

    else:
        lane_colors = {"blue": "#CDE6D0", "yellow": "#e6e6cd", "red": "#e6cdcd"}
        bg = lane_colors.get(cell.lane, "#eee")
        canvas_content = f'<div style="width:100%;height:100%;background:{bg};"></div>'

    rot = cell.rotation

    # ── Geometría según clase de celda ───────────────────────────────────────
    # Todas las casillas se diseñan en portrait: TILE_W × TILE_H (150 × 225).
    # El td puede ser corner (225×225), horizontal (150×225) o vertical (225×150).
    # Usamos un canvas que tiene las dimensiones del td, y dentro escalamos/
    # rotamos el tile portrait para que llene ese canvas exactamente.

    CORNER = TILE_H   # 225 — lado del td cuadrado de esquina

    if cell_class == "corner":
        # td: 225×225. Canvas también 225×225 — el tile (width/height 100%)
        # lo llena directamente. Solo rotamos.
        outer_w, outer_h   = CORNER, CORNER        # 225×225
        canvas_w, canvas_h = CORNER, CORNER        # 225×225
        transform = f"rotate({rot}deg)"
    elif rot in (90, 270):
        # td .vertical: 225w × 150h en el DOM.
        # Canvas portrait 150×225 centrado y rotado 90/270 → ocupa 225×150.
        outer_w, outer_h   = TILE_H, TILE_W        # 225×150
        canvas_w, canvas_h = TILE_W, TILE_H        # 150×225
        cx = (outer_w - canvas_w) / 2              #  37.5
        cy = (outer_h - canvas_h) / 2              # -37.5
        transform = f"translate({cx}px, {cy}px) rotate({rot}deg)"
    else:
        # td .horizontal: 150w × 225h — portrait encaja exactamente.
        outer_w, outer_h   = TILE_W, TILE_H        # 150×225
        canvas_w, canvas_h = TILE_W, TILE_H
        transform = f"rotate({rot}deg)"

    outer_style = (
        f"position:absolute; inset:0;"
        f"width:{outer_w}px; height:{outer_h}px;"
        f"overflow:hidden;"
    )
    canvas_style = (
        f"position:absolute;"
        f"width:{canvas_w}px; height:{canvas_h}px;"
        f"top:0; left:0;"
        f"transform:{transform};"
        f"transform-origin:center center;"
        f"overflow:hidden;"
    )

    return (
        f'<div class="tile-outer lane-{cell.lane}" style="{outer_style}">'
        f'<div class="s{uid}" style="{canvas_style}">'
        f'{canvas_content}'
        f'</div>'
        f'</div>'
    )


# =========================
# TABLE BUILDER
# =========================

def _cell_class(row: int, col: int, boardSize: int) -> str:
    """
    Clasifica cada celda del tablero.

    Las 4 esquinas del tablero son bloques 3×3 (uno por anillo concéntrico).
    Todas las celdas dentro de esos bloques son 'corner' (225×225 cuadradas),
    tengan o no contenido real.

    Fuera de los bloques de esquina, los bordes son 'horizontal' o 'vertical'
    según en qué lado del anillo estén. El interior es 'inner-empty'.
    """
    L  = boardSize - 1
    N  = 3   # número de anillos → tamaño del bloque de esquina

    # ── Bloques de esquina 3×3 ───────────────────────────────────────────────
    in_top    = row < N
    in_bottom = row > L - N
    in_left   = col < N
    in_right  = col > L - N

    if (in_top or in_bottom) and (in_left or in_right):
        return "corner"

    # ── Bordes del tablero (azul, exterior) ─────────────────────────────────
    if row == 0 or row == L:
        return "horizontal"
    if col == 0 or col == L:
        return "vertical"

    # ── Bordes anillo amarillo (offset 1) ────────────────────────────────────
    if row == 1 or row == L - 1:
        return "horizontal"
    if col == 1 or col == L - 1:
        return "vertical"

    # ── Bordes anillo rojo (offset 2) ────────────────────────────────────────
    if row == 2 or row == L - 2:
        return "horizontal"
    if col == 2 or col == L - 2:
        return "vertical"

    return "inner-empty"


def buildBoardTable(
    boardSize:  int,
    boardCells: Dict[Tuple[int, int], TileCell],
) -> str:
    htmlParts: List[str] = []
    htmlParts.append('<table class="board">')

    for row in range(boardSize):
        htmlParts.append("<tr>")
        for col in range(boardSize):
            cell      = boardCells.get((row, col))
            cls       = _cell_class(row, col, boardSize)
            classAttr = f' class="{cls}"'
            if cell:
                htmlParts.append(f"<td{classAttr}>{renderTileCell(cell, cls)}</td>")
            else:
                htmlParts.append(f"<td{classAttr}></td>")
        htmlParts.append("</tr>")

    htmlParts.append("</table>")
    return "\n".join(htmlParts)


# =========================
# PUBLIC API
# =========================

def generateBoardHtml(
    blueLaneNames:   List[str],
    yellowLaneNames: List[str],
    redLaneNames:    List[str],
    blueCornerNames: List[str],
    yellowCornerNames: List[str],
    redCornerNames:  List[str],
    tilesDir:        str  = DEFAULT_TILES_DIR,
    propsPath:       str  = DEFAULT_PROPS_PATH,
    nullTileFile:    str  = NULL_TILE_FILE,
    fit:             bool = False,
) -> str:

    propByName = loadProperties(propsPath)
    validateLaneAssignments(blueLaneNames,   blueCornerNames,   "blue",   propByName, "blue lane")
    validateLaneAssignments(yellowLaneNames, yellowCornerNames, "yellow", propByName, "yellow lane")
    validateLaneAssignments(redLaneNames,    redCornerNames,    "red",    propByName, "red lane")

    boardSize  = sideLengthFromPerimeter(BLUE_CANONICAL)
    blueSize   = boardSize
    yellowSize = max(boardSize - 2, 0)
    redSize    = max(boardSize - 4, 0)

    # Reset cache before this build so we start fresh
    _BOARD_FONT_CACHE.clear()

    boardCells: Dict[Tuple[int, int], TileCell] = {}

    if blueSize >= 3:
        blueRing = createRingCells(blueSize, blueLaneNames, blueCornerNames, "blue", tilesDir, nullTileFile)
        for (r, c), cell in blueRing.items():
            boardCells[(r, c)] = cell

    if yellowSize >= 3:
        yellowRing = createRingCells(yellowSize, yellowLaneNames, yellowCornerNames, "yellow", tilesDir, nullTileFile)
        for (r, c), cell in yellowRing.items():
            boardCells[(r + 1, c + 1)] = cell

    if redSize >= 3:
        redRing = createRingCells(redSize, redLaneNames, redCornerNames, "red", tilesDir, nullTileFile)
        for (r, c), cell in redRing.items():
            boardCells[(r + 2, c + 2)] = cell

    boardHtml = buildBoardTable(boardSize, boardCells)

    # ── Dimensiones de las celdas ──────────────────────────────────────────
    # Tile base: 150×150  |  corner/vertical/horizontal: 225 en la dimensión larga
    style = """
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }

    .board-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 1rem;
        background: #f5f5f0;
    }

    table.board {
        border-collapse: collapse;
        border: none;
    }

    table.board td {
        width:    150px;
        height:   150px;
        padding:  0;
        border:   1px solid #01010120;
        overflow: hidden;
        position: relative;
    }

    table.board td.corner {
        width:  225px !important;
        height: 225px !important;
    }

    /* lado horizontal del anillo: más ancho que alto */
    table.board td.horizontal {
        width:  150px !important;
        height: 225px !important;
    }

    /* lado vertical del anillo: más alto que ancho */
    table.board td.vertical {
        width:  225px !important;
        height: 150px !important;
    }

    table.board td.inner-empty {
        background: transparent;
        border-color: transparent;
    }

    .tile-wrapper {
        position: absolute;
        inset: 0;
    }
</style>
"""

    # ── Fuentes: inyectar @font-face una sola vez en el <head> ───────────────
    font_style = ""
    if _BOARD_FONT_CACHE:
        font_rules = "\n".join(r for r in _BOARD_FONT_CACHE if r.strip())
        font_style = f"<style>{font_rules}</style>\n"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Metropoly Board</title>
{font_style}{style}
</head>
<body>
<div class="board-container">
{boardHtml}
</div>
</body>
</html>"""

    return html


def saveBoardHtml(
    outputPath:       str,
    blueLaneNames:    List[str],
    yellowLaneNames:  List[str],
    redLaneNames:     List[str],
    blueCornerNames:  List[str],
    yellowCornerNames: List[str],
    redCornerNames:   List[str],
    tilesDir:         str  = DEFAULT_TILES_DIR,
    propsPath:        str  = DEFAULT_PROPS_PATH,
    nullTileFile:     str  = NULL_TILE_FILE,
    fit:              bool = False,
) -> str:
    html = generateBoardHtml(
        blueLaneNames=blueLaneNames,
        yellowLaneNames=yellowLaneNames,
        redLaneNames=redLaneNames,
        blueCornerNames=blueCornerNames,
        yellowCornerNames=yellowCornerNames,
        redCornerNames=redCornerNames,
        tilesDir=tilesDir,
        propsPath=propsPath,
        nullTileFile=nullTileFile,
        fit=fit,
    )

    os.makedirs(os.path.dirname(outputPath), exist_ok=True)
    with open(outputPath, "w", encoding="utf-8") as f:
        f.write(html)

    return outputPath