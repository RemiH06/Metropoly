from cardFactory import generar_casilla, generar_tarjeta, cargar_propiedades

# Cargar las propiedades y generar las imágenes
propiedades = cargar_propiedades('propiedades.json')

# Generar la casilla y la tarjeta para cada propiedad
for propiedad in propiedades:
    generar_casilla(propiedad)
    generar_tarjeta(propiedad)
