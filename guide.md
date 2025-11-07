

{
    "nombre": "Nombre",
    "color": "red",
    "carril": 1,
    "imagen": "img.png",
    "precio": 1, 
    "renta_base": 100,
    "tipo": 1
    "posicion": 1
}

nombre: en string
color: uno de los disponibles en palette
carril: 1 para azul, 2 para amarillo y 3 para rojo (el fondo se ajusta automáticamente a basicBG para 1, yellowBG para 2 y redBG para 3. Agregué esos colores manualmente)
imagen: ponerla en src/img/
precio: número (representa millones, ej. 1 -> 1M)
renta_base: número (representa miles, ej. 100 -> 100k)
tipo: son los tipos de propiedades:
    1: Propiedad (las clásicas del monopoly + negocios)
    2: Empresas (las que tienen efectos y habilidades)
    3: Transporte (tren, aeropuerto y taxi)
    4: Lotería
    5: Minas
    6: Casinos
    7: Fortunas
posicion: 1 o 2, determina si es de tamaño regular (1) o cuadrada (2) (para las esquinas)