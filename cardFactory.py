import svgwrite
from palette import get_colors

# Definir un objeto con las características de cada propiedad
class Propiedad:
    def __init__(self, nombre, color, carril, imagen, precio, renta_base, tipo):
        self.nombre = nombre
        self.color = color
        self.carril = carril
        self.imagen = imagen
        self.precio = precio
        self.renta_base = renta_base
        self.tipo = tipo

# Función recursiva para generar las tarjetas de propiedades
def generar_tarjeta(propiedades, i=0):
    if i >= len(propiedades):
        return  # Condición de salida de la recursión
    
    propiedad = propiedades[i]
    colors = get_colors()
    
    # Usamos el color de la propiedad (por ejemplo, rojo) y lo extraemos de la paleta
    color_fondo = colors[propiedad.color]  # Propiedad que viene del color en la paleta
    
    # Crear el SVG de la tarjeta
    dwg = svgwrite.Drawing(f'repo/{propiedad.nombre}_tarjeta.svg', profile='tiny', size=("200px", "350px"))
    
    # Fondo de la tarjeta
    dwg.add(dwg.rect(insert=(0, 0), size=("200px", "350px"), fill=color_fondo, stroke="black", stroke_width=2))
    
    # Título de la propiedad
    dwg.add(dwg.text(propiedad.nombre, insert=(10, 30), font_size="16px", fill="white"))
    
    # Imagen de la propiedad (esto puede ser una referencia o un rectángulo como marcador)
    dwg.add(dwg.image(propiedad.imagen, insert=(10, 50), size=(180, 100)))
    
    # Precio y renta base
    dwg.add(dwg.text(f"Precio: {propiedad.precio}K", insert=(10, 170), font_size="12px", fill="white"))
    dwg.add(dwg.text(f"Renta base: {propiedad.renta_base}K", insert=(10, 190), font_size="12px", fill="white"))
    
    # Guardar el SVG
    dwg.save()
    
    # Llamada recursiva para la siguiente propiedad
    generar_tarjeta(propiedades, i + 1)

# Definir algunas propiedades de ejemplo
propiedades = [
    Propiedad("Caseta", "red", "rojo", "caseta.png", 2, 1, "empresa"),
    Propiedad("Hospital", "blue", "azul", "hospital.png", 5, 3, "empresa"),
    Propiedad("Compañía de luz", "green", "amarillo", "luz.png", 3, 2, "empresa")
]

# Llamar a la función para generar todas las tarjetas
generar_tarjeta(propiedades)
