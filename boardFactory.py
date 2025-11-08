import os
import json
import svgwrite

# --- config global simple ---

# si es True: usa el máximo posible de casillas por carril (hasta el límite canónico)
# si es False: fuerza 64 / 60 / 56 (rellenando con NULL si faltan)
fit = False

TILE_WIDTH = 150      # casilla regular
TILE_HEIGHT = 225
CORNER_SIZE = 225     # esquina (cuadrada)
CELL_SIZE = CORNER_SIZE  # tamaño base de celda en el tablero

TILE_DIR = "src/casillas"   # donde están los SVG: casilla_{nombre}.svg
NULL_TILE_FILE = "casilla_NULL.svg"


class Property:
    def __init__(self, name, color, lane, image, price, baseRent, cardType, position):
        self.name = name
        self.color = color
        self.lane = lane          # 1 = blue, 2 = yellow, 3 = red
        self.image = image
        self.price = price
        self.baseRent = baseRent
        self.cardType = cardType  # 1..7
        self.position = position  # 1 = regular, 2 = corner


# ---------- carga y organización ----------

def loadProperties(propsDir: str = "props") -> list[Property]:
    """Load all JSON files in propsDir and return a flat list of Property objects."""
    properties: list[Property] = []

    for filename in os.listdir(propsDir):
        if not filename.endswith(".json"):
            continue
        jsonPath = os.path.join(propsDir, filename)
        with open(jsonPath, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            properties.append(
                Property(
                    name=item["nombre"],
                    color=item["color"],
                    lane=item["carril"],
                    image=item["imagen"],
                    price=item["precio"],
                    baseRent=item["renta_base"],
                    cardType=item["tipo"],
                    position=item["posicion"],
                )
            )

    return properties


def splitTracks(properties: list[Property]):
    """
    Return 6 arrays:
      blueTrack, yellowTrack, redTrack, blueCorners, yellowCorners, redCorners
    """
    blueTrack: list[Property] = []
    yellowTrack: list[Property] = []
    redTrack: list[Property] = []

    blueCorners: list[Property] = []
    yellowCorners: list[Property] = []
    redCorners: list[Property] = []

    for prop in properties:
        if prop.position == 1:  # regular
            if prop.lane == 1:
                blueTrack.append(prop)
            elif prop.lane == 2:
                yellowTrack.append(prop)
            elif prop.lane == 3:
                redTrack.append(prop)
        elif prop.position == 2:  # corner
            if prop.lane == 1:
                blueCorners.append(prop)
            elif prop.lane == 2:
                yellowCorners.append(prop)
            elif prop.lane == 3:
                redCorners.append(prop)

    return (
        blueTrack,
        yellowTrack,
        redTrack,
        blueCorners,
        yellowCorners,
        redCorners,
    )


# ---------- helpers de tamaño / slots ----------

def computeTrackTotal(available: int, canonical: int, useFit: bool) -> int:
    """
    Decide cuántas casillas tendrá el anillo (incluyendo esquinas).

    - useFit False -> usa siempre el valor canónico (64 / 60 / 56).
      Si faltan casillas, se rellena con NULL.
    - useFit True  -> usa hasta 'available' (sin pasar de canonical),
      y lo fuerza a múltiplo de 4 para que haya 4 lados.
    """
    if not useFit:
        return canonical

    total = min(available, canonical)
    if total <= 0:
        return 0

    # múltiplo de 4
    total -= total % 4
    if total < 4:
        total = 4
    return total


def buildLaneSlots(
    trackList: list[Property],
    cornerList: list[Property],
    targetTotal: int,
) -> tuple[list[Property | None], int]:
    """
    Construye los slots lineales de un anillo (incluyendo esquinas).
    Devuelve (slots, sideLength).

    - targetTotal: número total de casillas del anillo (múltiplo de 4).
    - sideLength = targetTotal / 4.
    - corners en posiciones: 0, side-1, 2*side-1, 3*side-1.
    - el resto se rellena con trackList en orden; si faltan, quedan None.
      si sobran, se ignoran.
    """
    if targetTotal <= 0:
        return [], 0

    sideLength = max(1, targetTotal // 4)
    totalSlots = sideLength * 4

    slots: list[Property | None] = [None] * totalSlots

    # colocar esquinas (hasta 4)
    cornerPositions = [0, sideLength - 1, 2 * sideLength - 1, 3 * sideLength - 1]
    for i, pos in enumerate(cornerPositions):
        if i < len(cornerList) and pos < totalSlots:
            slots[pos] = cornerList[i]

    # rellenar con propiedades regulares
    trackIter = iter(trackList)
    for i in range(totalSlots):
        if slots[i] is None:
            try:
                slots[i] = next(trackIter)
            except StopIteration:
                # se queda None -> luego será NULL
                pass

    return slots, sideLength


def indexToCoord(
    index: int,
    sideLength: int,
    offsetCells: float,
) -> tuple[float, float]:
    """
    Convierte un índice del anillo (0..4*sideLength-1)
    a coordenadas (x, y) en pixeles usando celdas de CELL_SIZE.

    offsetCells centra anillos interiores.
    """
    side = sideLength
    i = index

    if side <= 0:
        return 0.0, 0.0

    # top: left -> right
    if i < side:
        x = (offsetCells + i) * CELL_SIZE
        y = offsetCells * CELL_SIZE
    # right: top -> bottom
    elif i < 2 * side:
        k = i - side
        x = (offsetCells + side - 1) * CELL_SIZE
        y = (offsetCells + k) * CELL_SIZE
    # bottom: right -> left
    elif i < 3 * side:
        k = i - 2 * side
        x = (offsetCells + side - 1 - k) * CELL_SIZE
        y = (offsetCells + side - 1) * CELL_SIZE
    # left: bottom -> top
    else:
        k = i - 3 * side
        x = offsetCells * CELL_SIZE
        y = (offsetCells + side - 1 - k) * CELL_SIZE

    return float(x), float(y)


def getTilePath(prop: Property | None, tileDir: str = TILE_DIR) -> str:
    """
    Devuelve el path relativo al SVG para la casilla correspondiente.
    Si no existe, o prop es None, usa la casilla NULL.
    """
    if prop is None:
        return f"{tileDir}/{NULL_TILE_FILE}"

    fileName = f"casilla_{prop.name}.svg"
    fsPath = os.path.join(tileDir, fileName)

    if not os.path.exists(fsPath):
        return f"{tileDir}/{NULL_TILE_FILE}"

    return f"{tileDir}/{fileName}"


# ---------- dibujo del tablero ----------

def drawTileImage(
    dwg: svgwrite.Drawing,
    prop: Property | None,
    x: float,
    y: float,
    isCorner: bool,
    tileDir: str = TILE_DIR,
):
    """
    Inserta una imagen de casilla en (x, y).
    - Si es esquina -> 225x225.
    - Si es regular -> 150x225 centrada horizontalmente dentro de la celda de 225x225.
    """
    href = getTilePath(prop, tileDir)

    if isCorner:
        width = CORNER_SIZE
        height = CORNER_SIZE
        insert = (x, y)
    else:
        width = TILE_WIDTH
        height = TILE_HEIGHT
        horizontalMargin = (CELL_SIZE - TILE_WIDTH) / 2.0
        insert = (x + horizontalMargin, y)

    dwg.add(
        dwg.image(
            href=href,
            insert=insert,
            size=(width, height),
        )
    )


def generateBoardSvg(
    outputPath: str = "repo/board.svg",
    propsDir: str = "props",
    tileDir: str = TILE_DIR,
    useFit: bool | None = None,
) -> None:
    """
    Construye el tablero completo como un solo SVG, usando
    los SVG de casilla en tileDir y los JSON de propsDir.

    - Azul: 64 casillas (carril externo)  (incluyendo esquinas)
    - Amarillo: 60 casillas (anillo intermedio)
    - Rojo: 56 casillas (anillo interno)
    - Si useFit es True, cada anillo intenta usar el máximo posible
      hasta su límite (64/60/56), respetando el orden azul > amarillo > rojo.
    - Si useFit es False, fuerza exactamente 64/60/56 rellanando con NULL.
    """
    if useFit is None:
        useFit = fit

    properties = loadProperties(propsDir)
    (
        blueTrack,
        yellowTrack,
        redTrack,
        blueCorners,
        yellowCorners,
        redCorners,
    ) = splitTracks(properties)

    # total disponibles por carril (regulares + esquinas)
    blueAvailable = len(blueTrack) + len(blueCorners)
    yellowAvailable = len(yellowTrack) + len(yellowCorners)
    redAvailable = len(redTrack) + len(redCorners)

    # valores canónicos
    blueCanonical = 64
    yellowCanonical = 60
    redCanonical = 56

    blueTotal = computeTrackTotal(blueAvailable, blueCanonical, useFit)
    yellowTotal = computeTrackTotal(yellowAvailable, yellowCanonical, useFit)
    redTotal = computeTrackTotal(redAvailable, redCanonical, useFit)

    # asegurar anidamiento azul >= amarillo >= rojo
    if yellowTotal > blueTotal:
        yellowTotal = blueTotal
    if redTotal > yellowTotal:
        redTotal = yellowTotal

    # forzar múltiplos de 4
    def adjustTotal(x: int) -> int:
        if x <= 0:
            return 0
        x -= x % 4
        return max(x, 4)

    blueTotal = adjustTotal(blueTotal)
    yellowTotal = adjustTotal(yellowTotal) if yellowTotal > 0 else 0
    redTotal = adjustTotal(redTotal) if redTotal > 0 else 0

    # construir slots por anillo
    blueSlots, blueSide = buildLaneSlots(blueTrack, blueCorners, blueTotal)
    yellowSlots, yellowSide = buildLaneSlots(yellowTrack, yellowCorners, yellowTotal)
    redSlots, redSide = buildLaneSlots(redTrack, redCorners, redTotal)

    outerSide = max(blueSide, yellowSide, redSide)
    if outerSide <= 0:
        # nada que dibujar
        return

    boardSizePx = outerSide * CELL_SIZE
    dwg = svgwrite.Drawing(
        outputPath,
        profile="full",
        size=(f"{boardSizePx}px", f"{boardSizePx}px"),
    )

    # offsets para centrar anillos interiores
    blueOffsetCells = 0.0
    yellowOffsetCells = (outerSide - yellowSide) / 2.0 if yellowSide > 0 else 0.0
    redOffsetCells = (outerSide - redSide) / 2.0 if redSide > 0 else 0.0

    # azul (externo)
    for i, prop in enumerate(blueSlots):
        x, y = indexToCoord(i, blueSide, blueOffsetCells)
        isCorner = prop is not None and prop.position == 2
        drawTileImage(dwg, prop, x, y, isCorner=isCorner, tileDir=tileDir)

    # amarillo (medio)
    for i, prop in enumerate(yellowSlots):
        x, y = indexToCoord(i, yellowSide, yellowOffsetCells)
        isCorner = prop is not None and prop.position == 2
        drawTileImage(dwg, prop, x, y, isCorner=isCorner, tileDir=tileDir)

    # rojo (interno)
    for i, prop in enumerate(redSlots):
        x, y = indexToCoord(i, redSide, redOffsetCells)
        isCorner = prop is not None and prop.position == 2
        drawTileImage(dwg, prop, x, y, isCorner=isCorner, tileDir=tileDir)

    dwg.save()
