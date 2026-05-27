"""
colorResolver.py
================
Resuelve el color de cada casilla cuando su color es 'auto'.

Lógica:
  - El tablero tiene 3 anillos concéntricos (azul, amarillo, rojo).
  - Cada lado del tablero tiene un arreglo de colores de grupo, definido
    por las propiedades del carril azul ordenadas por precio.
  - Las casillas de los carriles amarillo y rojo heredan el color de la
    casilla azul que está en la misma posición perpendicular.
  - Los bloques 3×3 de esquina NO reciben color de grupo — mantienen
    el color base de su carril (basicBG / yellowBG / redBG).

Arreglo de colores de grupo (8 grupos, el azul es la fuente de verdad):
  brown, lightBlue, pink, orange, red, yellow, green, deepBlue

Tipos que NUNCA reciben color de grupo (usan color fijo por tipo):
  tipo 2  (empresas)   → chineseRed
  tipo 3  (trenes)     → brown
  tipo 4  (aeropuertos)→ teal
  tipo 7  (casinos)    → purple
  tipo 9  (taxis)      → teal
  tipo 10 (fortunas)   → lavender
  tipo 14 (casa cambio)→ gold
  tipo 15 (día de paga)→ lightGreen
  tipo 13 (salida)     → green
  tipo 5  (lotería)    → yellow
  tipo 6  (minas)      → chineseRed
  tipo 11 (cárcel)     → chineseRed
  tipo 12 (hospital)   → chineseRed
"""

import os
import pandas as pd
from boardFactory import (
    iterRingCoordinates, sideLengthFromPerimeter, BLUE_CANONICAL
)

_HERE = os.path.dirname(os.path.abspath(__file__))

# ── Colores fijos por tipo ─────────────────────────────────────────────────
TIPO_COLOR = {
    2:  'chineseRed',
    3:  'brown',
    4:  'teal',
    5:  'yellow',
    6:  'chineseRed',
    7:  'purple',
    9:  'teal',
    10: 'lavender',
    11: 'chineseRed',
    12: 'chineseRed',
    13: 'green',
    14: 'gold',
    15: 'lightGreen',
}

# ── Arreglo de 8 colores de grupo ─────────────────────────────────────────
GROUP_COLORS = [
    'brown',
    'lightBlue',
    'pink',
    'orange',
    'red',
    'yellow',
    'green',
    'deepBlue',
    'teal',
    'lavender',
    'purple',
    'lightGreen',
    'white',
]


def _group_sizes(n: int) -> list[int]:
    """
    Distribuye n propiedades en grupos de 4,
    con el primero y último de 3 si hay suficientes grupos.
    Nunca recicla colores — lanza error si n > len(GROUP_COLORS)*4+2.

    Ejemplos:
      n=10 → [3, 4, 3]
      n=31 → [3, 4, 4, 4, 4, 4, 4, 4, 4, 3]  (wait, eso es 38)
      n=31 → [3, 4, 4, 4, 4, 4, 4, 4, 4]  ... calculemos bien

    Lógica:
      - Si n <= 3: un solo grupo de n
      - Primer y último grupo = 3, resto = 4
      - n = 3 + 4*(k-2) + 3 → k = (n-6)/4 + 2 grupos si n>=6
      - Si no es divisible exactamente, ajustar último grupo
    """
    if n == 0:
        return []
    if n <= 3:
        return [n]
    if n <= 7:
        # dos grupos: primero 3, último el resto
        return [3, n - 3]

    # Grupos intermedios de 4
    # primer=3, último=3, medio=(n-6) propiedades en grupos de 4
    middle = n - 6
    full, rem = divmod(middle, 4)

def _group_sizes(n: int) -> list[int]:
    """
    Distribuye n propiedades en grupos de exactamente 3 o 4:
      - Primer grupo: 3
      - Último grupo: 3
      - Grupos intermedios: 4 (alguno puede ser 3 si hay residuo)
    Nunca excede 4 por grupo, nunca recicla colores.
    """
    if n == 0:
        return []
    if n <= 3:
        return [n]
    if n <= 7:
        # Dos grupos: primero 3, último lo que quede
        last = n - 3
        return [3, last] if last <= 4 else [3, 4]

    # Calcular cuántos grupos necesitamos
    # Todos los grupos son 3 o 4; mínimo n//4, máximo n//3
    # Queremos que primero y último sean exactamente 3
    # Resolvemos: 3 + 4*(k-2) + 3 <= n <= 3 + 4*(k-2) + ... → k grupos
    # Simplificado: k = ceil((n-6)/4) + 2
    import math
    k = math.ceil((n - 6) / 4) + 2

    max_n = 3 + 4 * (len(GROUP_COLORS) - 2) + 3
    assert n <= max_n, \
        f"Demasiadas propiedades ({n}), máximo soportado: {max_n}"
    assert k <= len(GROUP_COLORS), \
        f"Demasiados grupos ({k}) para {len(GROUP_COLORS)} colores"

    # Distribuir n en k grupos con primero=último=3, resto 3 o 4
    middle_total = n - 6          # propiedades para los k-2 grupos del medio
    middle_k     = k - 2          # grupos del medio
    base, extra  = divmod(middle_total, middle_k)
    # base es 3 o 4; si base > 4 necesitamos más grupos (raro)
    middle_sizes = [base + (1 if i < extra else 0) for i in range(middle_k)]

    sizes = [3] + middle_sizes + [3]
    assert sum(sizes) == n, f"sum={sum(sizes)} != n={n}, sizes={sizes}"
    assert max(sizes) <= 4,  f"Grupo demasiado grande: {sizes}"
    assert len(sizes) <= len(GROUP_COLORS), \
        f"Demasiados grupos ({len(sizes)}) para {len(GROUP_COLORS)} colores"
    return sizes



# ── Tamaño del bloque de esquina ──────────────────────────────────────────
CORNER_N = 3


def _in_corner_zone(r: int, c: int, board_L: int) -> bool:
    """True si la coordenada está dentro de un bloque 3×3 de esquina."""
    return (r < CORNER_N or r > board_L - CORNER_N) and \
           (c < CORNER_N or c > board_L - CORNER_N)


def build_color_index(
    blue_lane_names: list[str],
    blue_df: pd.DataFrame,
) -> dict[str, str]:
    """
    Construye un dict nombre→color para todas las casillas del tablero.

    Proceso:
    1. Ordenar las propiedades (tipo 1) del carril azul por precio.
    2. Asignar colores de grupo secuencialmente (grupos de 2-3 propiedades
       según la distribución natural de 8 grupos en 20 propiedades).
    3. Mapear cada posición del tablero a su color propagado.

    Parámetros:
      blue_lane_names: lista ordenada de nombres del carril azul (ya sin esquinas)
      blue_df: DataFrame completo del CSV

    Retorna:
      dict nombre→color para todas las casillas que tenían color='auto'
    """
    boardSize = sideLengthFromPerimeter(BLUE_CANONICAL)
    L = boardSize - 1

    # ── 1. Asignar colores de grupo a propiedades azules por precio ──────────
    # Solo tipo 1 (propiedades) reciben colores de grupo
    props_azul = blue_df[
        (blue_df['carril'] == 1) & (blue_df['tipo'] == 1)
    ].sort_values('precio').reset_index(drop=True)

    n_props = len(props_azul)
    group_sizes = _group_sizes(n_props)

    prop_color_map: dict[str, str] = {}
    idx = 0
    for g, size in enumerate(group_sizes):
        color = GROUP_COLORS[g]
        for _ in range(size):
            if idx < n_props:
                prop_color_map[props_azul.loc[idx, 'nombre']] = color
                idx += 1

    # ── Colores fijos por tipo — solo para azul; rojo/amarillo heredan posición ─
    # Tipos que SIEMPRE usan color fijo independientemente del carril:
    ALWAYS_FIXED = {2, 3, 4, 7, 9, 14, 15}
    # Tipos que usan color fijo solo en carril azul (en amarillo/rojo heredan posición):
    BLUE_FIXED_ONLY = {5, 6, 10, 11, 12, 13}

    fixed_color_map: dict[str, str] = {}
    for _, row in blue_df[blue_df['carril'] == 1].iterrows():
        tipo = int(row['tipo'])
        if tipo in TIPO_COLOR:
            fixed_color_map[row['nombre']] = TIPO_COLOR[tipo]

    # Color de cada casilla azul (tipo 1 → grupo, resto → tipo fijo)
    blue_name_color: dict[str, str] = {}
    for name in blue_lane_names:
        if name in prop_color_map:
            blue_name_color[name] = prop_color_map[name]
        elif name in fixed_color_map:
            blue_name_color[name] = fixed_color_map[name]
        else:
            # Buscar tipo en el dataframe
            rows = blue_df[blue_df['nombre'] == name]
            if not rows.empty:
                tipo = int(rows.iloc[0]['tipo'])
                blue_name_color[name] = TIPO_COLOR.get(tipo, 'lavender')

    # ── 3. Azul: añadir al resultado ─────────────────────────────────────────
    result: dict[str, str] = {}

    # ── 4. Amarillo y rojo: color fijo por tipo, sin heredar del azul ───────
    result: dict[str, str] = {}

    for carril_df, fallback in [(blue_df[blue_df['carril']==2], 'gold'),
                                 (blue_df[blue_df['carril']==3], 'lavender')]:
        for _, row in carril_df.iterrows():
            tipo = int(row['tipo'])
            result[row['nombre']] = TIPO_COLOR.get(tipo, fallback)

    # Azul también
    for name, color in blue_name_color.items():
        result[name] = color

    # ── 5. Fallback: cualquier casilla del CSV no resuelta ────────────────────
    for _, row in blue_df.iterrows():
        name = row['nombre']
        if name in result:
            continue
        tipo = int(row['tipo'])
        if tipo in ALWAYS_FIXED or tipo in BLUE_FIXED_ONLY:
            result[name] = TIPO_COLOR.get(tipo, 'lavender')
        else:
            result[name] = TIPO_COLOR.get(tipo, 'blue')

    return result