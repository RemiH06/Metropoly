import svgwrite
import json
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

# Cargar las propiedades desde el archivo JSON
def cargar_propiedades(props):
    with open(props, 'r') as f:
        propiedades_data = json.load(f)
    
    propiedades = []
    for propiedad in propiedades_data:
        propiedades.append(Propiedad(
            propiedad["nombre"],
            propiedad["color"],
            propiedad["carril"],
            propiedad["imagen"],
            propiedad["precio"],
            propiedad["renta_base"],
            propiedad["tipo"]
        ))
    
    return propiedades

# Función para generar la casilla de propiedad (tablero)
def generar_casilla(propiedad):
    colors = get_colors()
    color_fondo = colors["basicBG"]
    border_color = colors["borderBlack"]
    top_color = colors[propiedad.color]  # Usamos el color de la propiedad

    dwg = svgwrite.Drawing(f'repo/casillas/casilla_{propiedad.nombre}.svg', profile='tiny', size=("150px", "150px"))

    # Fondo de la casilla
    dwg.add(dwg.rect(insert=(0, 0), size=("150px", "150px"), fill=color_fondo, stroke=border_color, stroke_width=4))

    # Color superior con borde
    dwg.add(dwg.rect(insert=(0, 0), size=("150px", "30px"), fill=top_color, stroke=border_color, stroke_width=2))

    # Nombre de la propiedad (centrado en la casilla)
    dwg.add(dwg.text(propiedad.nombre.upper(), insert=("75px", "20px"), font_size="12px", font_family="Arial Black", fill="white", text_anchor="middle"))

    # Precio en la parte inferior
    dwg.add(dwg.text(f"{propiedad.precio}M", insert=("75px", "130px"), font_size="14px", font_family="Arial", fill="black", text_anchor="middle"))

    # Guardar la casilla
    dwg.save()

# Función para generar la tarjeta de propiedad
def generar_tarjeta(propiedad):
    colors = get_colors()
    color_fondo = colors["basicBG"]
    border_color = colors["borderBlack"]
    top_color = colors[propiedad.color]  # Usamos el color de la propiedad

    dwg = svgwrite.Drawing(f'repo/tarjetas/tarjeta_{propiedad.nombre}.svg', profile='tiny', size=("200px", "350px"))

    # Fondo de la tarjeta
    dwg.add(dwg.rect(insert=(0, 0), size=("200px", "350px"), fill=color_fondo, stroke=border_color, stroke_width=4))

    # Color superior con borde
    dwg.add(dwg.rect(insert=(0, 0), size=("200px", "40px"), fill=top_color, stroke=border_color, stroke_width=2))

    # Título de la propiedad (centrado en la parte superior)
    dwg.add(dwg.text(f"", insert=("100px", "25px"), font_size="12px", font_family="Arial Black", fill="white", text_anchor="middle"))

    # Nombre de la propiedad (centrado en el centro de la tarjeta)
    dwg.add(dwg.text(propiedad.nombre.upper(), insert=("100px", "80px"), font_size="18px", font_family="Arial", fill="black", text_anchor="middle"))

    # Precio y renta base (centrado)
    dwg.add(dwg.text(f"RENT: ${propiedad.renta_base}K", insert=("100px", "180px"), font_size="14px", font_family="Arial", fill="black", text_anchor="middle"))
    dwg.add(dwg.text(f"Price: {propiedad.precio}M", insert=("100px", "200px"), font_size="14px", font_family="Arial", fill="black", text_anchor="middle"))

    # Detalles de la propiedad (ubicados en la parte inferior)
    dwg.add(dwg.text(f"Mortgage Value: {(propiedad.precio)*.8}M", insert=("100px", "250px"), font_size="12px", font_family="Arial", fill="black", text_anchor="middle"))

    # Guardar la tarjeta
    dwg.save()