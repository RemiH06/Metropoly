import svgwrite
import json
from palette import get_colors
import base64

# Cargar las propiedades desde el archivo JSON
def cargar_propiedades(prop):
    with open(prop, 'r') as f:
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
            propiedad["tipo"],
            propiedad["posicion"]
        ))
    
    return propiedades

# Definir un objeto con las características de cada propiedad
class Propiedad:
    def __init__(self, nombre, color, carril, imagen, precio, renta_base, tipo, posicion):
        self.nombre = nombre
        self.color = color
        self.carril = carril
        self.imagen = imagen
        self.precio = precio
        self.renta_base = renta_base
        self.tipo = tipo
        self.posicion = posicion

# Función para obtener la fuente Kabel Heavy en base64
def get_font():
    with open('src/KabelHeavy.ttf', 'rb') as font_file:
        font_data = font_file.read()
        return base64.b64encode(font_data).decode('utf-8')

# Función para generar la casilla de propiedad (tablero)
def generar_casilla(propiedad):
    colors = get_colors()
    color_fondo = colors["basicBG"] if propiedad.carril == 1 else (colors["yellowBG"] if propiedad.carril == 2 else colors["redBG"])
    border_color = colors["borderBlack"]
    top_color = colors[propiedad.color]  # Usamos el color de la propiedad

    # Si la propiedad es de tipo cuadrado (posicion == 2), hacer casilla cuadrada
    if propiedad.posicion == 1:
        size_width = "150px"
        size_height = "225px"  # 1.5 veces el tamaño de la casilla regular
    else:
        size_width = "225px"
        size_height = "225px"  # Casilla cuadrada

    dwg = svgwrite.Drawing(f'repo/casillas/casilla_{propiedad.nombre}.svg', profile='full', size=(size_width, size_height))

    # Incluir la fuente desde el archivo de estilo CSS
    kabel = get_font()
    dwg.add(dwg.style(f"""
    @font-face {{
        font-family: 'KabelHeavy';
        src: url('data:font/ttf;base64,{kabel}') format('truetype');
    }}
    * {{
        font-family: 'KabelHeavy', sans-serif;
    }}
    """))

    # Fondo de la casilla
    dwg.add(dwg.rect(insert=(0, 0), size=(size_width, size_height), fill=color_fondo, stroke=border_color, stroke_width=4))

    if propiedad.posicion == 1:
        # Color superior con borde
        dwg.add(dwg.rect(insert=(0, 0), size=(size_width, "30px"), fill=top_color, stroke=border_color, stroke_width=2))
        # Nombre de la propiedad (centrado en la casilla)
        dwg.add(dwg.text(propiedad.nombre.upper(), insert=("75px", "20px"), font_size="12px", font_family="KabelHeavy", fill="white", text_anchor="middle"))
    elif propiedad.posicion == 2:
        # Borde superior y lateral con borde (cubriendo tanto arriba como a la izquierda)
        dwg.add(dwg.rect(insert=(0, 0), size=("30px", size_height), fill=top_color, stroke=border_color, stroke_width=2))  # Parte lateral izquierda
        dwg.add(dwg.rect(insert=(0, 0), size=(size_width, "30px"), fill=top_color, stroke=border_color, stroke_width=2))  # Parte superior
        # Nombre de la propiedad (centrado en la casilla)
        dwg.add(dwg.text(propiedad.nombre.upper(), insert=("112px", "20px"), font_size="12px", font_family="KabelHeavy", fill="white", text_anchor="middle"))

    # Precio en la parte inferior
    dwg.add(dwg.text(f"M{propiedad.precio}", insert=("75px", "205px"), font_size="14px", font_family="KabelHeavy", fill="black", text_anchor="middle"))

    # Guardar la casilla
    dwg.save()

# Función para generar la tarjeta de propiedad
def generar_tarjeta(propiedad):
    colors = get_colors()
    color_fondo = colors["basicBG"] if propiedad.carril == 1 else (colors["yellowBG"] if propiedad.carril == 2 else colors["redBG"])
    border_color = colors["borderBlack"]
    top_color = colors[propiedad.color]  # Usamos el color de la propiedad

    # Si la propiedad es de tipo cuadrado (posicion == 2), hacer tarjeta cuadrada
    size_width = "200px"
    size_height = "350px"  # Tamaño fijo de la tarjeta

    dwg = svgwrite.Drawing(f'repo/tarjetas/tarjeta_{propiedad.nombre}.svg', profile='full', size=(size_width, size_height))

    # Incluir la fuente desde el archivo de estilo CSS
    fuente_base64 = get_font()
    dwg.add(dwg.style(f"""
    @font-face {{
        font-family: 'KabelHeavy';
        src: url('data:font/ttf;base64,{fuente_base64}') format('truetype');
    }}
    * {{
        font-family: 'KabelHeavy', sans-serif;
    }}
    """))

    # Fondo de la tarjeta
    dwg.add(dwg.rect(insert=(0, 0), size=(size_width, size_height), fill=color_fondo, stroke=border_color, stroke_width=4))

    # Color superior con borde
    dwg.add(dwg.rect(insert=(0, 0), size=("200px", "40px"), fill=top_color, stroke=border_color, stroke_width=2))

    # Título de la propiedad (centrado en la parte superior)
    dwg.add(dwg.text(f"TITLE DEED", insert=("100px", "25px"), font_size="12px", font_family="KabelHeavy", fill="white", text_anchor="middle"))

    # Nombre de la propiedad (centrado en el centro de la tarjeta)
    dwg.add(dwg.text(propiedad.nombre.upper(), insert=("100px", "80px"), font_size="18px", font_family="KabelHeavy", fill="black", text_anchor="middle"))

    # Según el tipo, se ajustan las propiedades de la tarjeta
    if propiedad.tipo == 1:  # Propiedad
        dwg.add(dwg.text(f"RENT: ${propiedad.renta_base}K", insert=("100px", "180px"), font_size="14px", font_family="KabelHeavy", fill="black", text_anchor="middle"))
        dwg.add(dwg.text(f"Price: {propiedad.precio}K", insert=("100px", "200px"), font_size="14px", font_family="KabelHeavy", fill="black", text_anchor="middle"))
    elif propiedad.tipo == 2:  # Empresas
        dwg.add(dwg.text(f"Company Effect", insert=("100px", "180px"), font_size="14px", font_family="KabelHeavy", fill="black", text_anchor="middle"))
    elif propiedad.tipo == 3:  # Transporte
        dwg.add(dwg.text(f"Transport Effect", insert=("100px", "180px"), font_size="14px", font_family="KabelHeavy", fill="black", text_anchor="middle"))
    elif propiedad.tipo == 4:  # Lotería
        dwg.add(dwg.text(f"Lotto Prize", insert=("100px", "180px"), font_size="14px", font_family="KabelHeavy", fill="black", text_anchor="middle"))
    elif propiedad.tipo == 5:  # Minas
        dwg.add(dwg.text(f"Mine Effect", insert=("100px", "180px"), font_size="14px", font_family="KabelHeavy", fill="black", text_anchor="middle"))
    elif propiedad.tipo == 6:  # Casinos
        dwg.add(dwg.text(f"Casino Prize", insert=("100px", "180px"), font_size="14px", font_family="KabelHeavy", fill="black", text_anchor="middle"))
    elif propiedad.tipo == 7:  # Fortunas
        dwg.add(dwg.text(f"Fortune Effect", insert=("100px", "180px"), font_size="14px", font_family="KabelHeavy", fill="black", text_anchor="middle"))

    # Detalles de la propiedad (ubicados en la parte inferior)
    dwg.add(dwg.text(f"Mortgage Value: {propiedad.precio}K", insert=("100px", "250px"), font_size="12px", font_family="KabelHeavy", fill="black", text_anchor="middle"))

    # Guardar la tarjeta
    dwg.save()