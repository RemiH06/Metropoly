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
]

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
    # Distribuir en 8 grupos lo más uniformemente posible
    base, extra = divmod(n_props, 8)
    group_sizes = [base + (1 if i < extra else 0) for i in range(8)]

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

    # ── 3. Mapear posición absoluta → color azul ─────────────────────────────
    coords_blue = list(iterRingCoordinates(boardSize))
    RL = boardSize - 1

    lane_iter   = iter(blue_lane_names)
    corner_names = blue_df[
        (blue_df['carril'] == 1) & (blue_df['tipo'] == 2)
    ]['nombre'].tolist()
    corner_iter = iter(corner_names)

    abs_pos_to_blue_color: dict[tuple, str] = {}

    for r, c in coords_blue:
        is_diag = (r in (0, RL) and c in (0, RL))
        if is_diag:
            name = next(corner_iter, None)
        else:
            name = next(lane_iter, None)

        if not name:
            continue

        color = blue_name_color.get(name) or TIPO_COLOR.get(
            int(blue_df.loc[blue_df['nombre'] == name, 'tipo'].iloc[0])
            if name in blue_df['nombre'].values else 1,
            'blue'
        )
        abs_pos_to_blue_color[(r, c)] = color

    # ── 4. Para cada casilla amarilla/roja: heredar color del azul paralelo ──
    result: dict[str, str] = {}

    def get_parallel_color(abs_r: int, abs_c: int) -> str | None:
        """Color de la casilla azul perpendicular a esta posición."""
        if _in_corner_zone(abs_r, abs_c, L):
            return None  # zona de esquina → sin color de grupo
        if abs_r <= CORNER_N - 1:
            blue_coord = (0, abs_c)
        elif abs_r >= L - CORNER_N + 1:
            blue_coord = (L, abs_c)
        elif abs_c <= CORNER_N - 1:
            blue_coord = (abs_r, 0)
        elif abs_c >= L - CORNER_N + 1:
            blue_coord = (abs_r, L)
        else:
            return None
        return abs_pos_to_blue_color.get(blue_coord)

    # Amarillo (offset 1)
    yellow_df = blue_df[blue_df['carril'] == 2]
    yellow_non_corner = yellow_df[yellow_df['tipo'] != 2].reset_index(drop=True)
    yellow_corners_df = yellow_df[yellow_df['tipo'] == 2]
    coords_yellow = list(iterRingCoordinates(boardSize - 2))
    RL_y = boardSize - 3
    y_lane_iter   = iter(yellow_non_corner['nombre'].tolist())
    y_corner_iter = iter(yellow_corners_df['nombre'].tolist())

    for r, c in coords_yellow:
        is_diag = (r in (0, RL_y) and c in (0, RL_y))
        name = next(y_corner_iter, None) if is_diag else next(y_lane_iter, None)
        if not name:
            continue
        abs_r, abs_c = r + 1, c + 1
        rows = yellow_df.loc[yellow_df['nombre'] == name]
        if rows.empty:
            continue
        tipo = int(rows['tipo'].iloc[0])
        if tipo in ALWAYS_FIXED:
            result[name] = TIPO_COLOR[tipo]
        else:
            inherited = get_parallel_color(abs_r, abs_c)
            result[name] = inherited if inherited else TIPO_COLOR.get(tipo, 'gold')

    # Rojo (offset 2)
    red_df = blue_df[blue_df['carril'] == 3]
    red_non_corner = red_df[red_df['tipo'] != 2].reset_index(drop=True)
    red_corners_df = red_df[red_df['tipo'] == 2]
    coords_red = list(iterRingCoordinates(boardSize - 4))
    RL_r = boardSize - 5
    r_lane_iter   = iter(red_non_corner['nombre'].tolist())
    r_corner_iter = iter(red_corners_df['nombre'].tolist())

    for r, c in coords_red:
        is_diag = (r in (0, RL_r) and c in (0, RL_r))
        name = next(r_corner_iter, None) if is_diag else next(r_lane_iter, None)
        if not name:
            continue
        abs_r, abs_c = r + 2, c + 2
        rows = red_df.loc[red_df['nombre'] == name]
        if rows.empty:
            continue
        tipo = int(rows['tipo'].iloc[0])
        if tipo in ALWAYS_FIXED:
            result[name] = TIPO_COLOR[tipo]
        else:
            inherited = get_parallel_color(abs_r, abs_c)
            result[name] = inherited if inherited else TIPO_COLOR.get(tipo, 'lavender')

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