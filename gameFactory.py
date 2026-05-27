"""
gameFactory.py
==============
Ensambla el directorio de juego completo listo para imprimir.

Estructura de salida:
  juego_completo/
  ├── tablero/
  │   └── tablero_metropoly.html
  ├── tarjetas/
  │   └── *.html  (una por propiedad)
  ├── fortunas/
  │   ├── azul/    *.html
  │   ├── amarillo/ *.html
  │   └── rojo/    *.html
  ├── billetes/
  │   ├── BILLETES IMPRESIÓN.pdf
  │   └── OROS IMPRESIÓN.pdf
  ├── instructivo/
  │   └── instructivo_metropoly.html
  └── indice.html   ← página de inicio con links a todo

Uso:
  python gameFactory.py              # solo ensambla
  python gameFactory.py --force      # regenera todo antes de ensamblar
  python gameFactory.py --skip-gen   # salta la generación, solo copia
"""

import os
import shutil
import argparse
import subprocess
from pathlib import Path

_HERE = Path(__file__).parent
_OUT  = _HERE / "juego_completo"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _mkdir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def _copy(src: Path, dst: Path):
    """Copia src → dst, crea directorios intermedios si faltan."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def _copy_dir(src: Path, dst: Path, pattern: str = "*.html"):
    """Copia todos los archivos que coincidan con pattern de src a dst."""
    _mkdir(dst)
    copied = 0
    for f in sorted(src.glob(pattern)):
        shutil.copy2(f, dst / f.name)
        copied += 1
    return copied


def _run(cmd: list, label: str):
    print(f"  [gameFactory] {label}...")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=_HERE)
    if result.returncode != 0:
        print(f"  ⚠️  Error en {label}:")
        print(result.stderr[-500:] if result.stderr else "(sin stderr)")
    return result.returncode == 0


# ─────────────────────────────────────────────────────────────────────────────
# GENERADORES
# ─────────────────────────────────────────────────────────────────────────────

def regenerar_todo(force: bool = False):
    """Corre generator.py y fortunaFactory.py para asegurar que todo está al día."""
    args = ["python", "generator.py"]
    if force:
        args.append("--force")
    _run(args, "generator.py")

    args2 = ["python", "fortunaFactory.py"]
    if force:
        args2.append("--force")
    _run(args2, "fortunaFactory.py")

    _run(["python", "instructivoFactory.py"], "instructivoFactory.py")


# ─────────────────────────────────────────────────────────────────────────────
# ÍNDICE HTML
# ─────────────────────────────────────────────────────────────────────────────

def _build_index(stats: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Metropoly — Directorio de juego</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow:wght@400;600&family=Barlow+Condensed:wght@600;700&display=swap');
  :root {{
    --bg: #0C0608; --bg2: #140A0C; --bg3: #1E1014;
    --text: #F0DEC8; --text2: #907060; --border: #3A1C20;
    --gold: #C8901A; --gold2: #E8A820; --crimson: #901828;
    --glow-gold: 0 0 10px rgba(200,144,26,.5);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg); color: var(--text);
    font-family: 'Barlow', sans-serif;
    min-height: 100vh;
  }}
  .hero {{
    text-align: center; padding: 60px 40px 40px;
    background: radial-gradient(circle at 50% 0%, rgba(144,24,40,.2) 0%, transparent 60%);
  }}
  .hero h1 {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: clamp(60px, 12vw, 120px);
    color: var(--gold2); text-shadow: var(--glow-gold);
    line-height: 1;
  }}
  .hero p {{
    color: var(--text2); font-size: 14px;
    letter-spacing: .15em; text-transform: uppercase;
    margin-top: 10px;
  }}
  .rings {{
    display: flex; gap: 12px; justify-content: center; margin: 24px 0;
  }}
  .ring {{
    width: 14px; height: 14px; border-radius: 50%; border: 2.5px solid;
  }}
  .ring.b {{ border-color: #1E88E5; background: rgba(30,136,229,.2); }}
  .ring.y {{ border-color: var(--gold2); background: rgba(232,168,32,.2); }}
  .ring.r {{ border-color: var(--crimson); background: rgba(144,24,40,.2); }}

  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 16px; padding: 40px;
    max-width: 1100px; margin: 0 auto;
  }}
  .section-card {{
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: 10px; overflow: hidden;
    transition: border-color .2s, box-shadow .2s;
    text-decoration: none; color: inherit; display: block;
  }}
  .section-card:hover {{
    border-color: var(--gold); box-shadow: var(--glow-gold);
  }}
  .sc-header {{
    padding: 20px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 14px;
  }}
  .sc-icon {{ font-size: 32px; }}
  .sc-title {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 18px; font-weight: 700;
    color: var(--gold2); text-transform: uppercase;
    letter-spacing: .05em;
  }}
  .sc-sub {{
    font-size: 11px; color: var(--text2);
    letter-spacing: .1em; text-transform: uppercase;
    margin-top: 2px;
  }}
  .sc-body {{ padding: 16px; }}
  .sc-stat {{
    display: flex; justify-content: space-between;
    border-bottom: 1px solid var(--bg3);
    padding: 6px 0; font-size: 13px; color: var(--text2);
  }}
  .sc-stat:last-child {{ border-bottom: none; }}
  .sc-stat strong {{ color: var(--text); }}
  .sc-links {{ padding: 12px 16px; display: flex; flex-wrap: wrap; gap: 8px; }}
  .sc-link {{
    background: var(--bg3); border: 1px solid var(--border);
    border-radius: 4px; padding: 4px 10px;
    font-size: 11px; color: var(--text2);
    text-decoration: none; letter-spacing: .05em;
    transition: border-color .2s, color .2s;
  }}
  .sc-link:hover {{ border-color: var(--gold); color: var(--gold); }}

  footer {{
    text-align: center; padding: 32px;
    font-size: 11px; color: var(--border);
    letter-spacing: .1em; text-transform: uppercase;
  }}
</style>
</head>
<body>
<div class="hero">
  <h1>METROPOLY</h1>
  <div class="rings">
    <div class="ring b"></div>
    <div class="ring y"></div>
    <div class="ring r"></div>
  </div>
  <p>Directorio de juego completo · ZMG Edition · listo para imprimir</p>
</div>

<div class="grid">

  <a class="section-card" href="tablero/tablero_metropoly.html">
    <div class="sc-header">
      <div class="sc-icon">🗺️</div>
      <div>
        <div class="sc-title">Tablero</div>
        <div class="sc-sub">Carril azul · amarillo · rojo</div>
      </div>
    </div>
    <div class="sc-body">
      <div class="sc-stat"><span>Casillas azul</span><strong>40</strong></div>
      <div class="sc-stat"><span>Casillas amarillo</span><strong>36</strong></div>
      <div class="sc-stat"><span>Casillas rojo</span><strong>32</strong></div>
      <div class="sc-stat"><span>Total</span><strong>108 casillas</strong></div>
    </div>
  </a>

  <div class="section-card">
    <div class="sc-header">
      <div class="sc-icon">🏠</div>
      <div>
        <div class="sc-title">Tarjetas</div>
        <div class="sc-sub">Propiedades · empresas · tipos</div>
      </div>
    </div>
    <div class="sc-body">
      <div class="sc-stat"><span>Total tarjetas</span><strong>{stats.get('tarjetas', 0)}</strong></div>
      <div class="sc-stat"><span>Propiedades (tipo 1)</span><strong>{stats.get('props', 0)}</strong></div>
      <div class="sc-stat"><span>Empresas</span><strong>{stats.get('empresas', 0)}</strong></div>
      <div class="sc-stat"><span>Otros tipos</span><strong>{stats.get('otros', 0)}</strong></div>
    </div>
    <div class="sc-links">
      <a class="sc-link" href="tarjetas/">Ver directorio →</a>
    </div>
  </div>

  <div class="section-card">
    <div class="sc-header">
      <div class="sc-icon">🎴</div>
      <div>
        <div class="sc-title">Fortunas</div>
        <div class="sc-sub">3 barajas · niveles 1–5</div>
      </div>
    </div>
    <div class="sc-body">
      <div class="sc-stat"><span>Azul</span><strong>{stats.get('fortunas_azul', 0)} cartas</strong></div>
      <div class="sc-stat"><span>Amarillo</span><strong>{stats.get('fortunas_amarillo', 0)} cartas</strong></div>
      <div class="sc-stat"><span>Rojo</span><strong>{stats.get('fortunas_rojo', 0)} cartas</strong></div>
    </div>
    <div class="sc-links">
      <a class="sc-link" href="fortunas/azul/">Azul →</a>
      <a class="sc-link" href="fortunas/amarillo/">Amarillo →</a>
      <a class="sc-link" href="fortunas/rojo/">Rojo →</a>
    </div>
  </div>

  <div class="section-card">
    <div class="sc-header">
      <div class="sc-icon">💵</div>
      <div>
        <div class="sc-title">Billetes</div>
        <div class="sc-sub">Dinero · oro · para imprimir</div>
      </div>
    </div>
    <div class="sc-body">
      <div class="sc-stat"><span>$25M por jugador</span><strong>9 denominaciones</strong></div>
      <div class="sc-stat"><span>Oro</span><strong>6 denominaciones</strong></div>
      <div class="sc-stat"><span>Formato</span><strong>PDF imprimible</strong></div>
    </div>
    <div class="sc-links">
      <a class="sc-link" href="billetes/BILLETES IMPRESIÓN.pdf">Billetes →</a>
      <a class="sc-link" href="billetes/OROS IMPRESIÓN.pdf">Oros →</a>
    </div>
  </div>

  <a class="section-card" href="instructivo/instructivo_metropoly.html">
    <div class="sc-header">
      <div class="sc-icon">📖</div>
      <div>
        <div class="sc-title">Instructivo</div>
        <div class="sc-sub">Reglas completas · 17 secciones</div>
      </div>
    </div>
    <div class="sc-body">
      <div class="sc-stat"><span>Objetivo</span><strong>100 de oro</strong></div>
      <div class="sc-stat"><span>Jugadores</span><strong>2–9 (+banco)</strong></div>
      <div class="sc-stat"><span>Dinero inicial</span><strong>$25,000,000</strong></div>
    </div>
  </a>

</div>

<footer>Metropoly · ZMG Edition · iroFactory</footer>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# ENSAMBLADO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def ensamblar():
    print("[gameFactory] Ensamblando directorio de juego...")

    # Limpiar y crear estructura
    if _OUT.exists():
        shutil.rmtree(_OUT)
    for sub in ["tablero", "tarjetas", "fortunas/azul", "fortunas/amarillo",
                "fortunas/rojo", "billetes", "instructivo"]:
        _mkdir(_OUT / sub)

    stats = {}

    # ── Tablero ────────────────────────────────────────────────────────────
    tablero_src = _HERE / "repo" / "tableros" / "tablero_metropoly.html"
    if tablero_src.exists():
        _copy(tablero_src, _OUT / "tablero" / "tablero_metropoly.html")
        print(f"  ✓ Tablero")
    else:
        print(f"  ⚠️  Tablero no encontrado: {tablero_src}")

    # ── Tarjetas ───────────────────────────────────────────────────────────
    tarjetas_src = _HERE / "repo" / "tarjetas"
    n = _copy_dir(tarjetas_src, _OUT / "tarjetas")
    stats["tarjetas"] = n
    print(f"  ✓ Tarjetas: {n} archivos")

    # Calcular estadísticas de tarjetas desde CSV
    try:
        import pandas as pd
        df = pd.read_csv(_HERE / "props" / "zmg.csv")
        stats["props"]    = int((df["tipo"] == 1).sum())
        stats["empresas"] = int(df["tipo"].isin([2, 16]).sum())
        stats["otros"]    = int(~df["tipo"].isin([1, 2, 16]).sum())
    except Exception:
        pass

    # ── Fortunas ───────────────────────────────────────────────────────────
    fortunas_src = _HERE / "repo" / "fortunas"
    n1 = _copy_dir(fortunas_src, _OUT / "fortunas" / "azul",    "fortuna_1_*.html")
    n2 = _copy_dir(fortunas_src, _OUT / "fortunas" / "amarillo","fortuna_2_*.html")
    n3 = _copy_dir(fortunas_src, _OUT / "fortunas" / "rojo",    "fortuna_3_*.html")
    stats["fortunas_azul"]    = n1
    stats["fortunas_amarillo"] = n2
    stats["fortunas_rojo"]    = n3
    print(f"  ✓ Fortunas: {n1} azul · {n2} amarillo · {n3} rojo")

    # ── Billetes ───────────────────────────────────────────────────────────
    feria_src = _HERE / "src" / "feria"
    billetes_copied = 0
    for nombre in ["BILLETES IMPRESIÓN.pdf", "OROS IMPRESIÓN.pdf"]:
        src = feria_src / nombre
        if src.exists():
            _copy(src, _OUT / "billetes" / nombre)
            billetes_copied += 1
        else:
            print(f"  ⚠️  Billete no encontrado: {src}")
    print(f"  ✓ Billetes: {billetes_copied}/2 PDFs")

    # ── Instructivo ────────────────────────────────────────────────────────
    inst_src = _HERE / "repo" / "instructivo" / "instructivo_metropoly.html"
    if inst_src.exists():
        _copy(inst_src, _OUT / "instructivo" / "instructivo_metropoly.html")
        print(f"  ✓ Instructivo")
    else:
        print(f"  ⚠️  Instructivo no encontrado: {inst_src}")

    # ── Índice ─────────────────────────────────────────────────────────────
    index_html = _build_index(stats)
    (_OUT / "indice.html").write_text(index_html, encoding="utf-8")
    print(f"  ✓ Índice generado")

    # ── Resumen ────────────────────────────────────────────────────────────
    total = sum(1 for _ in _OUT.rglob("*") if _.is_file())
    print(f"\n[gameFactory] ✅ Directorio listo: juego_completo/ ({total} archivos)")
    print(f"[gameFactory] Abre juego_completo/indice.html para empezar")
    return _OUT


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ensambla el directorio de juego completo")
    parser.add_argument("--force",    action="store_true", help="Regenera todo antes de ensamblar")
    parser.add_argument("--skip-gen", action="store_true", help="Salta la generación, solo copia")
    args = parser.parse_args()

    if not args.skip_gen:
        print("[gameFactory] Regenerando assets...")
        regenerar_todo(force=args.force)

    ensamblar()