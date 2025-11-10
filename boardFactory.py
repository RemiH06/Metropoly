# boardFactory.py

import os
import json
import math
from dataclasses import dataclass
from typing import Dict, Tuple, List, Optional

# =========================
# CONSTANTS
# =========================

TILE_WIDTH = 150
TILE_HEIGHT = 225
CORNER_SIZE = 225

BLUE_CANONICAL = 64
YELLOW_CANONICAL = 60
RED_CANONICAL = 56

NULL_TILE_FILE = "casilla_NULL.svg"

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

        if cornerFlag:
            try:
                name = next(cornerIter)
            except StopIteration:
                name = None
        else:
            try:
                name = next(laneIter)
            except StopIteration:
                name = None

        if name:
            fileName = f"casilla_{name}.svg"
            filePath = os.path.join(tilesDir, fileName)
            if not os.path.exists(filePath):
                print(
                    f"[boardFactory] Warning: tile file '{fileName}' not found for property '{name}', "
                    f"using NULL tile."
                )
                filePath = os.path.join(tilesDir, nullTileFile)
        else:
            filePath = os.path.join(tilesDir, nullTileFile)

        # === 🔧 FIX: reference SVGs using '../casillas/' relative path ===
        relPath = f"../casillas/{os.path.basename(filePath)}"

        rotation = computeRotation(row, col, size)
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
    rotationClass = f"rot-{cell.rotation}"
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
        # top or bottom row: full row of perimeter cells
        if row == 0 or row == last:
            htmlParts.append("<tr>")
            for col in range(size):
                cell = ringCells[(row, col)]
                htmlParts.append(f"<td>{renderTileCell(cell)}</td>")
            htmlParts.append("</tr>")
            continue

        # row that introduces the inner table
        if innerTableHtml is not None and row == 1:
            htmlParts.append("<tr>")

            # left perimeter
            leftCell = ringCells[(row, 0)]
            htmlParts.append(f"<td>{renderTileCell(leftCell)}</td>")

            # central cell: spans the inner square
            colspan = size - 2
            rowspan = size - 2
            htmlParts.append(
                f'<td colspan="{colspan}" rowspan="{rowspan}" class="inner-ring-container">'
            )
            htmlParts.append(innerTableHtml)
            htmlParts.append("</td>")

            # right perimeter
            rightCell = ringCells[(row, last)]
            htmlParts.append(f"<td>{renderTileCell(rightCell)}</td>")

            htmlParts.append("</tr>")
            continue

        # middle rows
        htmlParts.append("<tr>")

        leftCell = ringCells[(row, 0)]
        htmlParts.append(f"<td>{renderTileCell(leftCell)}</td>")

        if innerTableHtml is None:
            # innermost ring: fill interior cells with blanks or extra tiles if ever needed
            for col in range(1, last):
                if (row, col) in ringCells:
                    cell = ringCells[(row, col)]
                    htmlParts.append(f"<td>{renderTileCell(cell)}</td>")
                else:
                    htmlParts.append("<td></td>")

        rightCell = ringCells[(row, last)]
        htmlParts.append(f"<td>{renderTileCell(rightCell)}</td>")

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
    Return a full HTML document with the board rendered as nested tables.

    blueLaneNames / yellowLaneNames / redLaneNames:
        ["El Colli", "El Colli 2", ...]  (no 'casilla_' prefix, that is added here)

    blueCornerNames / yellowCornerNames / redCornerNames:
        same format but only corners (4 per ring; extras are ignored).

    fit = False:
        Use canonical ring sizes:
            blue  = 64 tiles
            yellow= 60 tiles
            red   = 56 tiles
        Excess tiles are ignored, missing tiles use NULL.

    fit = True:
        Adapt the side length of each ring to the number of tiles, so that
        4*n - 4 >= tileCount. The blue ring defines the outer board size.
    """
    propByName = loadProperties(propsPath)

    # validation against propiedades.json (only warnings)
    validateLaneAssignments(blueLaneNames, blueCornerNames, "blue", propByName, "blue lane")
    validateLaneAssignments(yellowLaneNames, yellowCornerNames, "yellow", propByName, "yellow lane")
    validateLaneAssignments(redLaneNames, redCornerNames, "red", propByName, "red lane")

    # choose perimeters
    if fit:
        bluePerimeter = 4 * computeSideLengthForFit(len(blueLaneNames) + len(blueCornerNames)) - 4
        yellowPerimeter = 4 * computeSideLengthForFit(len(yellowLaneNames) + len(yellowCornerNames)) - 4
        redPerimeter = 4 * computeSideLengthForFit(len(redLaneNames) + len(redCornerNames)) - 4
    else:
        bluePerimeter = BLUE_CANONICAL
        yellowPerimeter = YELLOW_CANONICAL
        redPerimeter = RED_CANONICAL

    blueSize = sideLengthFromPerimeter(bluePerimeter)
    yellowSize = sideLengthFromPerimeter(yellowPerimeter)
    redSize = sideLengthFromPerimeter(redPerimeter)

    # nesting constraint when fit=True: each inner ring must be smaller
    if fit:
        yellowSize = min(yellowSize, blueSize - 1)
        redSize = min(redSize, yellowSize - 1)

    # build ring cells
    blueCells = createRingCells(blueSize, blueLaneNames, blueCornerNames, "blue", tilesDir, nullTileFile)
    yellowCells = createRingCells(yellowSize, yellowLaneNames, yellowCornerNames, "yellow", tilesDir, nullTileFile)
    redCells = createRingCells(redSize, redLaneNames, redCornerNames, "red", tilesDir, nullTileFile)

    # nested tables: red inside yellow inside blue
    redTable = buildRingTable(redSize, redCells, "ring-red", innerTableHtml=None)
    yellowTable = buildRingTable(yellowSize, yellowCells, "ring-yellow", innerTableHtml=redTable)
    blueTable = buildRingTable(blueSize, blueCells, "ring-blue", innerTableHtml=yellowTable)

    style = """
    <style>
    .board-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 1rem;
    }
    table.board-ring {
        border-collapse: collapse;
    }
    table.board-ring td {
        padding: 0;
        border: 1px solid #010101;
    }
    img.tile-image {
        display: block;
    }
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
{blueTable}
</div>
</body>
</html>
"""
    return html


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
