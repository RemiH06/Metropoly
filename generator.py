from cardFactory import generar_casilla, generar_tarjeta, cargar_propiedades
from boardFactory import saveBoardHtml

# Cargar las propiedades y generar las imágenes
propiedades = cargar_propiedades('props/propiedades.json')

# Generar la casilla y la tarjeta para cada propiedad
for propiedad in propiedades:
    generar_casilla(propiedad)
    generar_tarjeta(propiedad)

# para respetar los carriles de 65/60/56
blueLane = ["Mediterranean Avenue", "Baltic Avenue", "El Colli", "El Colli 2"]
yellowLane = ["El Colli 3", "Casa"]  # ejemplo
redLane = ["El Colli"]               # ejemplo

blueCorners = ["Casa", "El Colli", "El Colli 2", "El Colli 3"]
yellowCorners = ["Casa", "Casa", "Casa", "Casa"]
redCorners = ["Casa", "Casa", "Casa", "Casa"]

outputPath = "repo/tableros/tablero_metropoly.html"

saveBoardHtml(
    outputPath=outputPath,
    blueLaneNames=blueLane,
    yellowLaneNames=yellowLane,
    redLaneNames=redLane,
    blueCornerNames=blueCorners,
    yellowCornerNames=yellowCorners,
    redCornerNames=redCorners,
    fit=False,  # o True si quieres que se adapte al número de casillas
)