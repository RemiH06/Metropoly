import os
import json
import math
from dataclasses import dataclass
from typing import Dict, Tuple, List, Optional

# =========================
# CONSTANTS
# =========================

TILE_WIDTH = 50
TILE_HEIGHT = TILE_WIDTH*1.5
CORNER_SIZE = TILE_HEIGHT

BLUE_CANONICAL = 40
YELLOW_CANONICAL = BLUE_CANONICAL-4
RED_CANONICAL = YELLOW_CANONICAL-4

NULL_TILE_FILE = "casilla_NULL"

DEFAULT_TILES_DIR = os.path.join("repo", "casillas")
DEFAULT_PROPS_PATH = os.path.join("props", "propiedades.json")


# =========================
# MODEL
# =========================

@dataclass
class TileCell:
    imagePath: str
    rotation: int  # degrees
    name: Optional[str]
    lane: str
    isCorner: bool


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
    laneNames: List[str],
    cornerNames: List[str],
    laneColor: str,
    propByName: Dict[str, dict],
    label: str,
) -> None:
    """
    Check propiedades.carril / propiedades.lane and propiedades.posicion / position.
    Only prints warnings (no exceptions).
    """
    allNames = list(laneNames) + list(cornerNames)

    for index, name in enumerate(allNames):
        prop = propByName.get(name)
        if not prop:
            print(f"[boardFactory] Warning: property '{name}' from {label} not found in propiedades.json")
            continue

        laneValue = (
            prop.get("lane")
            or prop.get("carril")
            or prop.get("Carril")
        )
        if laneValue and str(laneValue).lower() != laneColor.lower():
            print(
                f"[boardFactory] Warning: property '{name}' has lane '{laneValue}' "
                f"but is listed in {label} for lane '{laneColor}'"
            )

        positionValue = (
            prop.get("position")
            or prop.get("posicion")
            or prop.get("Posicion")
            or prop.get("posición")
            or prop.get("Posición")
        )
        if positionValue is not None and isinstance(positionValue, int):
            if positionValue != index:
                print(
                    f"[boardFactory] Warning: property '{name}' has position {positionValue} "
                    f"but appears at index {index} in {label}"
                )


# =========================
# GEOMETRY HELPERS
# =========================

def sideLengthFromPerimeter(perimeter: int) -> int:
    """Given a ring perimeter (4*n - 4) return side length n."""
    if perimeter < 4:
        return 2
    return perimeter // 4 + 1


def computeSideLengthForFit(tileCount: int) -> int:
    """
    For fit=True, compute the minimal side length n so that
    4*n - 4 >= tileCount, with n >= 3.
    """
    tileCount = max(tileCount, 4)
    sideFloat = (tileCount + 4) / 4.0
    sideLen = max(3, math.ceil(sideFloat))
    return sideLen


def iterRingCoordinates(size: int):
    """
    Yield all coordinates of a square ring of side 'size' in order,
    starting at bottom-left corner and going clockwise.
    """
    last = size - 1

    # bottom row: left -> right
    for col in range(size):
        yield (last, col)

    # right column: bottom-1 -> top
    for row in range(last - 1, -1, -1):
        yield (row, last)

    # top row: right-1 -> left
    for col in range(last - 1, -1, -1):
        yield (0, col)

    # left column: top+1 -> bottom-1
    for row in range(1, last):
        yield (row, 0)


def computeRotation(row: int, col: int, size: int) -> int:
    """Rotation so that each tile faces the center."""
    last = size - 1
    if row == 0:
        return 0       # top side
    if col == last:
        return 90      # right side (clockwise)
    if row == last:
        return 180     # bottom side
    if col == 0:
        return 270     # left side (counter-clockwise)
    return 0


def isCorner(row: int, col: int, size: int) -> bool:
    last = size - 1
    return (row in (0, last)) and (col in (0, last))


# =========================
# RING CONSTRUCTION
# =========================

def createRingCells(
    size: int,
    laneNames: List[str],
    cornerNames: List[str],
    laneColor: str,
    tilesDir: str,
    nullTileFile: str = NULL_TILE_FILE,
) -> Dict[Tuple[int, int], TileCell]:
    """
    Build a dict (row, col) -> TileCell for a ring.
    If there are too few names, fill with NULL.
    If there are too many, the extras are ignored.
    """
    coords = list(iterRingCoordinates(size))
    laneIter = iter(laneNames)
    cornerIter = iter(cornerNames)

    ringCells: Dict[Tuple[int, int], TileCell] = {}

    for row, col in coords:
        cornerFlag = isCorner(row, col, size)
        name = None

        # Asignar la rotación según la celda
        if cornerFlag:
            # Esquinas: asignamos las rotaciones 0°, 90°, 180° o 270° según la posición
            if row == 0 and col == 0:  # Esquina superior izquierda
                rotation = 0
            elif row == 0 and col == size - 1:  # Esquina superior derecha
                rotation = 90
            elif row == size - 1 and col == size - 1:  # Esquina inferior derecha
                rotation = 180
            elif row == size - 1 and col == 0:  # Esquina inferior izquierda
                rotation = 270
            try:
                name = next(cornerIter)
            except StopIteration:
                name = None
        else:
            # Celdas no esquinas: asignamos rotación según la posición
            rotation = computeRotation(row, col, size)
            try:
                name = next(laneIter)
            except StopIteration:
                name = None

        # Si hay nombre, generamos el archivo de la casilla con el postfijo de la rotación
        if name:
            fileName = f"casilla_{name}_{rotation}.svg"
            print(f"Generando archivo para: {fileName}")
            filePath = os.path.join(tilesDir, fileName)

            # Si no existe el archivo, usamos el archivo NULL
            if not os.path.exists(filePath):
                print(
                    f"[boardFactory] Warning: tile file '{fileName}' not found for property '{name}', "
                    f"using NULL tile."
                )
                filePath = os.path.join(tilesDir, f"{nullTileFile}_{rotation}.svg")
        else:
            filePath = os.path.join(tilesDir, f"{nullTileFile}_{rotation}.svg")

        # === 🔧 FIX: referencia las imágenes usando la ruta relativa '../casillas/' ===
        relPath = f"../casillas/{os.path.basename(filePath)}"

        # Crear el objeto de la celda
        cell = TileCell(
            imagePath=relPath.replace("\\", "/"),
            rotation=rotation,
            name=name,
            lane=laneColor,
            isCorner=cornerFlag,
        )
        ringCells[(row, col)] = cell

    return ringCells


def renderTileCell(cell: TileCell) -> str:
    alt = cell.name or "Empty"
    rotationClass = f"rot-{0}"
    laneClass = f"lane-{cell.lane}"
    return (
        f'<img src="{cell.imagePath}" alt="{alt}" '
        f'class="tile-image {rotationClass} {laneClass}"/>'
    )


def buildRingTable(
    size: int,
    ringCells: Dict[Tuple[int, int], TileCell],
    laneCssClass: str,
    innerTableHtml: Optional[str] = None,
) -> str:
    """
    Build the HTML <table> for one ring.
    If innerTableHtml is provided, it is nested in the center (one big cell with rowspan/colspan).
    """
    htmlParts: List[str] = []
    htmlParts.append(f'<table class="board-ring {laneCssClass}">')

    last = size - 1

    for row in range(size):
        # fila superior o inferior
        if row == 0 or row == last:
            htmlParts.append("<tr>")
            for col in range(size):
                cell = ringCells[(row, col)]
                tdClass = "large" if cell.isCorner else ""
                classAttr = f' class="{tdClass}"' if tdClass else ""
                htmlParts.append(f"<td{classAttr}>{renderTileCell(cell)}</td>")
            htmlParts.append("</tr>")
            continue

        # fila donde se inserta la tabla interior (para anillos azul/amarillo)
        if innerTableHtml is not None and row == 1:
            htmlParts.append("<tr>")

            leftCell = ringCells[(row, 0)]
            leftClass = "large" if leftCell.isCorner else ""
            leftAttr = f' class="{leftClass}"' if leftClass else ""
            htmlParts.append(f"<td{leftAttr}>{renderTileCell(leftCell)}</td>")

            colspan = size - 2
            rowspan = size - 2
            htmlParts.append(
                f'<td colspan="{colspan}" rowspan="{rowspan}" class="inner-ring-container">'
            )
            htmlParts.append(innerTableHtml)
            htmlParts.append("</td>")

            rightCell = ringCells[(row, last)]
            rightClass = "large" if rightCell.isCorner else ""
            rightAttr = f' class="{rightClass}"' if rightClass else ""
            htmlParts.append(f"<td{rightAttr}>{renderTileCell(rightCell)}</td>")

            htmlParts.append("</tr>")
            continue

        # filas intermedias
        htmlParts.append("<tr>")

        leftCell = ringCells[(row, 0)]
        leftClass = "large" if leftCell.isCorner else ""
        leftAttr = f' class="{leftClass}"' if leftClass else ""
        htmlParts.append(f"<td{leftAttr}>{renderTileCell(leftCell)}</td>")

        if innerTableHtml is None:
            # anillo más interno (rojo): rellenar interior
            for col in range(1, last):
                if (row, col) in ringCells:
                    cell = ringCells[(row, col)]
                    tdClass = "large" if cell.isCorner else ""
                    classAttr = f' class="{tdClass}"' if tdClass else ""
                    htmlParts.append(f"<td{classAttr}>{renderTileCell(cell)}</td>")
                else:
                    # celdas sin casilla: 150x150 por CSS
                    htmlParts.append('<td class="inner-empty"></td>')

        rightCell = ringCells[(row, last)]
        rightClass = "large" if rightCell.isCorner else ""
        rightAttr = f' class="{rightClass}"' if rightClass else ""
        htmlParts.append(f"<td{rightAttr}>{renderTileCell(rightCell)}</td>")

        htmlParts.append("</tr>")

    htmlParts.append("</table>")
    return "\n".join(htmlParts)


# =========================
# PUBLIC API
# =========================

def generateBoardHtml(
    blueLaneNames: List[str],
    yellowLaneNames: List[str],
    redLaneNames: List[str],
    blueCornerNames: List[str],
    yellowCornerNames: List[str],
    redCornerNames: List[str],
    tilesDir: str = DEFAULT_TILES_DIR,
    propsPath: str = DEFAULT_PROPS_PATH,
    nullTileFile: str = NULL_TILE_FILE,
    fit: bool = False,
) -> str:
    """
    Genera un documento HTML con un solo tablero NxN.

    - TODAS las celdas son de 150x150.
    - Únicamente la diagonal (0,0),(1,1),(2,2),(N-1,N-1),(N-2,N-2),(N-3,N-3)
      tendrá 225x225 (clase .large).
    - Los tres anillos (blue, yellow, red) se colocan como marcos concéntricos.
    """

    propByName = loadProperties(propsPath)

    # Sólo warnings de consistencia
    validateLaneAssignments(blueLaneNames, blueCornerNames, "blue", propByName, "blue lane")
    validateLaneAssignments(yellowLaneNames, yellowCornerNames, "yellow", propByName, "yellow lane")
    validateLaneAssignments(redLaneNames, redCornerNames, "red", propByName, "red lane")

    # ============ Tamaño del tablero ============

    # Cuando fit=False, usamos explícitamente N=17 como dijiste.
    # Si quieres luego hacemos que fit=True ajuste N dinámicamente.
    if not fit:
        boardSize = sideLengthFromPerimeter(BLUE_CANONICAL)  # 64 -> 17
    else:
        # Por ahora fit=True se comporta igual en tamaño.
        boardSize = sideLengthFromPerimeter(BLUE_CANONICAL)

    # tres anillos concéntricos: azul, amarillo, rojo
    blueSize = boardSize          # anillo exterior
    yellowSize = max(boardSize - 2, 0)  # desplazado 1
    redSize = max(boardSize - 4, 0)     # desplazado 2

    # Diccionario global (row, col) -> TileCell
    boardCells: Dict[Tuple[int, int], TileCell] = {}

    # ============ Anillo azul (exterior) ============
    if blueSize >= 3:
        blueRing = createRingCells(
            size=blueSize,
            laneNames=blueLaneNames,
            cornerNames=blueCornerNames,
            laneColor="blue",
            tilesDir=tilesDir,
            nullTileFile=nullTileFile,
        )
        offsetBlue = 0
        for (r, c), cell in blueRing.items():
            boardCells[(r + offsetBlue, c + offsetBlue)] = cell

    # ============ Anillo amarillo (medio) ============
    if yellowSize >= 3:
        yellowRing = createRingCells(
            size=yellowSize,
            laneNames=yellowLaneNames,
            cornerNames=yellowCornerNames,
            laneColor="yellow",
            tilesDir=tilesDir,
            nullTileFile=nullTileFile,
        )
        offsetYellow = 1
        for (r, c), cell in yellowRing.items():
            boardCells[(r + offsetYellow, c + offsetYellow)] = cell

    # ============ Anillo rojo (interno) ============
    if redSize >= 3:
        redRing = createRingCells(
            size=redSize,
            laneNames=redLaneNames,
            cornerNames=redCornerNames,
            laneColor="red",
            tilesDir=tilesDir,
            nullTileFile=nullTileFile,
        )
        offsetRed = 2
        for (r, c), cell in redRing.items():
            boardCells[(r + offsetRed, c + offsetRed)] = cell

    # ============ HTML de la tabla única ============
    boardHtml = buildBoardTable(boardSize, boardCells)

    style = """
<style>
    .board-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 1rem;
    }

    table.board {
        border-collapse: collapse;
        border: none;  /* Bordes transparentes */
    }

    table.board td {
        width: 150px;
        height: 150px;
        padding: 0;
        border: 1px solid transparent;  /* Bordes transparentes */
        overflow: hidden;  /* Asegura que no se salgan del borde */
        position: relative;  /* Necesario para que los SVGs puedan estar en un z-index mayor */
    }

    /* Celdas con clase .corner (225px x 225px) */
    table.board td.corner {
        width: 225px !important;
        height: 225px !important;
    }

    /* Celdas con clase .vertical (150px de ancho, 225px de alto) */
    table.board td.vertical {
        width: 225px !important;
        height: 150px !important;
    }

    /* Celdas con clase .horizontal (225px de ancho, 150px de alto) */
    table.board td.horizontal {
        width: 150px !important;
        height: 225px !important;
    }

    /* Ajustamos el SVG para que se ajuste dentro de la celda sin recortes */
    img.tile-image {
        display: block;
        width: 100%;
        height: 100%;
        object-fit: fill;  /* Cambié a fill para asegurar que el SVG cubra toda la celda */
        object-position: center;  /* Centra el contenido del SVG */
        margin: 0;
        padding: 0;
        transform-origin: center center;
    }

    /* Rotación de los SVGs */
    .tile-image.rot-0   { transform: rotate(0deg); }
    .tile-image.rot-90  { transform: rotate(90deg); }
    .tile-image.rot-180 { transform: rotate(180deg); }
    .tile-image.rot-270 { transform: rotate(270deg); }
</style>



    """

    html = f"""<!DOCTYPE html>
    <html lang="en">
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
    </html>
    """
    return html


def buildBoardTable(
    boardSize: int,
    boardCells: Dict[Tuple[int, int], TileCell]
) -> str:
    """
    Construye una tabla HTML estática con las celdas que tienen las clases:
    - .corner (225x225px)
    - .vertical (150x225px)
    - .horizontal (225x150px)
    """
    htmlParts: List[str] = []
    htmlParts.append('<table class="board">')

    last = boardSize - 1
    largeIndices = {0, 1, 2, last, last - 1, last - 2}  # Celdas diagonales

    for row in range(boardSize):
        htmlParts.append("<tr>")  # Fila

        # Para las filas con `corner`:
        if row < 3 or row >= boardSize - 3:
            # Primera y última fila (y sus equivalentes)
            for col in range(boardSize):
                cell = boardCells.get((row, col))

                # Esquinas: las tres primeras y tres últimas celdas con la clase `corner`
                if col < 3 or col >= boardSize - 3:
                    classes = ["corner"]
                else:
                    # El resto de las celdas en la fila con la clase `horizontal`
                    classes = ["horizontal"]

                classAttr = f' class="{" ".join(classes)}"'
                if cell:
                    htmlParts.append(f"<td{classAttr}>{renderTileCell(cell)}</td>")
                else:
                    htmlParts.append(f"<td{classAttr}></td>")  # Celdas vacías (sin casilla)
        else:
            # Para las filas intermedias, donde todo es `vertical` e `inner-empty`
            for col in range(boardSize):
                cell = boardCells.get((row, col))

                # Las tres primeras y últimas celdas de la fila con clase `vertical`
                if col < 3 or col >= boardSize - 3:
                    classes = ["vertical"]
                else:
                    # Las celdas intermedias tienen clase `inner-empty`
                    classes = ["inner-empty"]

                classAttr = f' class="{" ".join(classes)}"'
                if cell:
                    htmlParts.append(f"<td{classAttr}>{renderTileCell(cell)}</td>")
                else:
                    htmlParts.append(f"<td{classAttr}></td>")  # Celdas vacías (sin casilla)

        htmlParts.append("</tr>")  # Fin de la fila

    htmlParts.append("</table>")
    return "\n".join(htmlParts)


def saveBoardHtml(
    outputPath: str,
    blueLaneNames: List[str],
    yellowLaneNames: List[str],
    redLaneNames: List[str],
    blueCornerNames: List[str],
    yellowCornerNames: List[str],
    redCornerNames: List[str],
    tilesDir: str = DEFAULT_TILES_DIR,
    propsPath: str = DEFAULT_PROPS_PATH,
    nullTileFile: str = NULL_TILE_FILE,
    fit: bool = False,
) -> str:
    """
    Helper to directly generate and save the board HTML.
    Returns the output path.
    """
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
