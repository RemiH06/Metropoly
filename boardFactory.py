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
DEFAULT_PROPS_PATH = os.path.join("props", "propiedades.json")


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
    """Load propiedades.json and return a dict indexed by property name."""
    if not os.path.exists(propsPath):
        return {}

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


def validateLaneAssignments(
    laneNames:   List[str],
    cornerNames: List[str],
    laneColor:   str,
    propByName:  Dict[str, dict],
    label:       str,
) -> None:
    allNames = list(laneNames) + list(cornerNames)
    for index, name in enumerate(allNames):
        prop = propByName.get(name)
        if not prop:
            print(f"[boardFactory] Warning: property '{name}' from {label} not found in props file")
            continue

        laneValue = prop.get("lane") or prop.get("carril") or prop.get("Carril")
        if laneValue and str(laneValue).lower() != laneColor.lower():
            print(
                f"[boardFactory] Warning: '{name}' has lane '{laneValue}' "
                f"but is listed in {label} for lane '{laneColor}'"
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

def renderTileCell(cell: TileCell) -> str:
    """
    Lee el HTML de la casilla y lo inlinea en el <td>.

    Técnica de rotación sin recorte (double-wrapper):
    ─────────────────────────────────────────────────
    El <td> tiene dimensiones fijas (p.ej. 150×225 para lados verticales).
    Para rotar 90°/270° el contenido de la casilla (que internamente siempre
    se diseña como portrait: ancho < alto) sin que se recorte, usamos:

        outer  → tamaño del <td>  (overflow:hidden, position:relative)
        inner  → tamaño INVERTIDO para 90/270 (position:absolute, centrado)
                 sobre el inner se aplica el rotate()
        content → el HTML de la casilla al 100% del inner

    Para 0°/180° no hace falta invertir dimensiones.
    Las dimensiones reales del <td> las conocemos según la clase:
        .corner     → 225×225  (cuadrado, rotación no importa)
        .horizontal → 150×225  (W×H en el DOM)
        .vertical   → 225×150  (W×H en el DOM)
        normal      → 150×150
    """
    import re

    # ── Leer y extraer body + style del HTML de la casilla ──────────────────
    if os.path.exists(cell.htmlPath):
        with open(cell.htmlPath, "r", encoding="utf-8") as f:
            raw = f.read()
        body_match  = re.search(r"<body[^>]*>(.*?)</body>",   raw, re.DOTALL | re.IGNORECASE)
        style_match = re.search(r"<style[^>]*>(.*?)</style>", raw, re.DOTALL | re.IGNORECASE)
        body_html   = body_match.group(1).strip()  if body_match  else raw
        style_html  = style_match.group(1).strip() if style_match else ""
        uid         = abs(hash(cell.htmlPath)) % 10**8
        scoped_style = f"<style>#{uid}-inner {{ {style_html} }}</style>"
        # re-scope el body al id del inner para que los selectores no colisionen
        body_html_scoped = re.sub(
            r'(class="tile")',
            rf'class="tile" data-uid="{uid}"',
            body_html,
        )
        inner_content = scoped_style + body_html_scoped
    else:
        lane_colors = {"blue": "#CDE6D0", "yellow": "#e6e6cd", "red": "#e6cdcd"}
        bg = lane_colors.get(cell.lane, "#eee")
        inner_content = f'<div style="width:100%;height:100%;background:{bg};"></div>'
        uid = 0

    rot = cell.rotation

    # ── Dimensiones del <td> según posición en el tablero ───────────────────
    # La casilla se diseña siempre como portrait (ancho < alto).
    # Para lados top/bottom (rot 0/180): el td es horizontal (W < H en pantalla
    # pero la casilla entra derecha).
    # Para lados left/right (rot 90/270): el td es vertical (W > H), hay que
    # invertir las dimensiones del inner antes de rotar.

    if rot in (90, 270):
        # El td es .vertical → 225px ancho × 150px alto en el DOM.
        # La casilla-portrait mide 150×225. Para que quepa sin recorte:
        #   inner: 225px × 150px  →  rotate(90/270)  →  ocupa 150×225 visual
        # pero eso sigue siendo igual al td (225W × 150H). Funciona.
        td_w, td_h   = 225, 150   # dimensiones reales del <td>
        inner_w, inner_h = td_h, td_w  # invertido: 150×225
        # Centramos el inner dentro del td
        offset_x = (td_w - inner_w) // 2   # (225-150)/2 = 37.5  → 0 si cuadrado
        offset_y = (td_h - inner_h) // 2   # (150-225)/2 = -37.5 → corregido con translate
        translate = f"translate({(td_w - inner_w) / 2}px, {(td_h - inner_h) / 2}px) rotate({rot}deg)"
    else:
        # rot 0 / 180: td es .horizontal → 150px ancho × 225px alto en el DOM
        td_w, td_h   = 150, 225
        inner_w, inner_h = td_w, td_h   # mismo tamaño
        translate = f"rotate({rot}deg)"

    inner_style = (
        f"position:absolute;"
        f"width:{inner_w}px; height:{inner_h}px;"
        f"top:50%; left:50%;"
        f"margin-top:-{inner_h//2}px; margin-left:-{inner_w//2}px;"
        f"transform: {translate};"
        f"transform-origin: center center;"
        f"overflow:hidden;"
    )

    outer_style = (
        "position:absolute; inset:0;"
        "overflow:hidden;"
    )

    return (
        f'<div class="tile-outer lane-{cell.lane}" style="{outer_style}">'
        f'  <div id="{uid}-inner" style="{inner_style}">'
        f'    {inner_content}'
        f'  </div>'
        f'</div>'
    )


# =========================
# TABLE BUILDER
# =========================

def buildBoardTable(
    boardSize:  int,
    boardCells: Dict[Tuple[int, int], TileCell],
) -> str:
    htmlParts: List[str] = []
    htmlParts.append('<table class="board">')

    last = boardSize - 1

    for row in range(boardSize):
        htmlParts.append("<tr>")

        if row < 3 or row >= boardSize - 3:
            for col in range(boardSize):
                cell = boardCells.get((row, col))
                classes = ["corner"] if (col < 3 or col >= boardSize - 3) else ["horizontal"]
                classAttr = f' class="{" ".join(classes)}"'
                if cell:
                    htmlParts.append(f"<td{classAttr}>{renderTileCell(cell)}</td>")
                else:
                    htmlParts.append(f"<td{classAttr}></td>")
        else:
            for col in range(boardSize):
                cell = boardCells.get((row, col))
                classes = ["vertical"] if (col < 3 or col >= boardSize - 3) else ["inner-empty"]
                classAttr = f' class="{" ".join(classes)}"'
                if cell:
                    htmlParts.append(f"<td{classAttr}>{renderTileCell(cell)}</td>")
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

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Metropoly Board</title>
{style}
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