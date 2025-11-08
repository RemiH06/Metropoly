from cardFactory import generar_casilla, generar_tarjeta, cargar_propiedades
from boardFactory import generateBoardSvg

# Cargar las propiedades y generar las imágenes
propiedades = cargar_propiedades('props/propiedades.json')

# Generar la casilla y la tarjeta para cada propiedad
for propiedad in propiedades:
    generar_casilla(propiedad)
    generar_tarjeta(propiedad)

# para respetar los carriles de 65/60/56
generateBoardSvg(
    outputPath="repo/tableros/board.svg",
    propsDir="props",
    useFit=False,
)

# para fitear con el tamaño óptimo
generateBoardSvg(
    outputPath="repo/tableros/board_fit.svg",
    propsDir="props",
    useFit=True,
)