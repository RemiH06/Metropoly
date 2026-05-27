![Made with Python](https://forthebadge.com/images/badges/made-with-python.svg)
![Build with Love](http://ForTheBadge.com/images/badges/built-with-love.svg)

```
███╗   ███╗███████╗████████╗██████╗  ██████╗ ██████╗  ██████╗ ██╗  ██╗   ██╗
████╗ ████║██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗██║  ╚██╗ ██╔╝
██╔████╔██║█████╗     ██║   ██████╔╝██║   ██║██████╔╝██║   ██║██║   ╚████╔╝ 
██║╚██╔╝██║██╔══╝     ██║   ██╔══██╗██║   ██║██╔═══╝ ██║   ██║██║    ╚██╔╝  
██║ ╚═╝ ██║███████╗   ██║   ██║  ██║╚██████╔╝██║     ╚██████╔╝███████╗██║   
╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝      ╚═════╝ ╚══════╝╚═╝    
        by Hex (@RemiH06)          version 1.0
```

## 🎲 Metropoly

A Monopoly-style board game generator set in the **Guadalajara Metropolitan Area (ZMG)**. Generates all game assets — board, property cards, fortune cards, rulebook — as print-ready HTML files.

> **Demo** → [RemiH06.github.io/Metropoly](https://RemiH06.github.io/Metropoly)

You can custom your own board just by modifying the csv!

---

### Features

- 🗺️ **3-ring concentric board** — blue (40 tiles), yellow (36), red (32)
- 🏠 **106 tiles** across 16 distinct types (properties, companies, trains, airports, casinos, taxis, fortune tiles, exchange houses and more)
- 🎴 **119 fortune cards** split into 3 decks by lane (levels 1–5)
- 🏢 **12 companies** with unique effects — from Caseta de Zapotlanejo to Pemex López Mateos
- 🎨 **Automatic color system** — 13 color groups assigned by price order
- 📖 **Full rulebook** with 17 sections and custom visual theme
- 📦 **`gameFactory`** — assembles the complete print-ready directory in one command
- 🖼️ **Optional image scraper** via Selenium — enriches tiles with local photography

---

### Project structure

```
Metropoly/
├── props/
│   ├── zmg.csv              ← all tile data
│   └── fortunas.csv         ← 119 fortune cards
├── src/
│   ├── palette.html         ← game color palette
│   ├── board_config.json    ← board configuration
│   ├── KabelHeavy.ttf       ← font (not included, see setup)
│   ├── gw/                  ← character sprites gw_{lane}{level}.png (not included)
│   ├── feria/               ← printable bill PDFs (not included)
│   └── img/                 ← scraped images (generated, gitignored)
├── repo/
│   ├── casillas/            ← generated tile HTMLs
│   ├── tarjetas/            ← generated card HTMLs
│   ├── fortunas/            ← generated fortune card HTMLs
│   ├── tableros/            ← generated board HTML
│   └── instructivo/         ← generated rulebook HTML
├── generator.py             ← main entry point
├── cardFactory.py           ← generates tiles and property cards
├── boardFactory.py          ← generates the board HTML
├── fortunaFactory.py        ← generates fortune cards
├── colorResolver.py         ← positional color assignment system
├── instructivoFactory.py    ← generates the rulebook
├── gameFactory.py           ← assembles the complete game directory
└── patch.py                 ← chromedriver downloader (optional)
```

---

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/RemiH06/Metropoly.git
   cd Metropoly
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **(Windows only)** Make sure Visual C++ redistributable DLLs are installed. If not, grab the latest `vc_redist.exe` from [this link](https://learn.microsoft.com/en-GB/cpp/windows/latest-supported-vc-redist?view=msvc-170) and reboot.

4. **Add optional assets** to `src/`:

   | Asset | Path | Notes |
   |-------|------|-------|
   | Game font | `src/KabelHeavy.ttf` | Optional — falls back to Century Gothic |
   | Character sprites | `src/gw/gw_{lane}{level}.png` | 15 files (lanes 1–3, levels 1–5) |
   | Printable bills | `src/feria/BILLETES IMPRESIÓN.pdf` | Pre-existing asset |
   | Gold tokens | `src/feria/OROS IMPRESIÓN.pdf` | Pre-existing asset |

---

### Usage

#### Generate the full game

```bash
python generator.py
```

Smart cache — only regenerates what changed.

```bash
python generator.py --force      # regenerate everything
```

#### Generate fortune cards

```bash
python fortunaFactory.py
python fortunaFactory.py --force
```

#### Generate the rulebook

```bash
python instructivoFactory.py
```

#### Assemble the complete print directory

```bash
python gameFactory.py              # regenerate + assemble
python gameFactory.py --force      # force full regeneration
python gameFactory.py --skip-gen   # copy only, skip generation
```

Output structure:

```
juego_completo/
├── indice.html        ← open this to start
├── tablero/
├── tarjetas/
├── fortunas/
│   ├── azul/
│   ├── amarillo/
│   └── rojo/
├── billetes/
└── instructivo/
```

---

### Optional: Image scraper

Metropoly can automatically scrape images for each tile using Selenium. This is entirely optional — tiles render fine with a color background if no image is found.

**Requirements:**

- Google Chrome installed
- Selenium ≥ 4.10.0 (includes automatic driver management)

  ```bash
  pip install selenium --upgrade
  ```

- ChromeDriver binary available at [github.com/dreamshao/chromedriver](https://github.com/dreamshao/chromedriver) — place it in the `webdriver/` folder

**Run with parallel workers:**

```bash
python generator.py --workers 3
```

Images are cached in `src/img/{tile_name}/` — the scraper only fetches tiles that don't have an image yet.

---

### Tile CSV (`props/zmg.csv`)

| column | description |
|--------|-------------|
| `nombre` | Tile name |
| `color` | Group color (`brown`, `lightBlue`, … , `deepBlue`) or type color |
| `carril` | Lane: 1 = blue · 2 = yellow · 3 = red |
| `imagen` | Image override name (empty = auto scrape) |
| `precio` | Purchase price |
| `renta_base` | Base rent (or duration in turns for businesses) |
| `tipo` | Tile type (see table below) |

#### Tile types

| type | name | description |
|------|------|-------------|
| 1 | Property | Residential/commercial, supports offices and towers |
| 2 | Company | Fixed price 2M, dice-based rent, unique effect |
| 3 | Train | Rent doubles per additional train owned |
| 4 | Airport | Fixed rent per airport owned |
| 5 | Lottery | — |
| 6 | Mine | Risk/reward with a die roll |
| 7 | Casino | Poker hand triggered on landing |
| 8 | Business | Expires after N turns |
| 9 | Taxi | Fixed rent, Pemex bonus |
| 10 | Fortune | Draw a card from the lane's deck |
| 11 | Jail | Puente Grande — costs and fortune loss |
| 12 | Hospital | IMSS — medical fees |
| 13 | Start | — |
| 14 | Exchange house | Convert money ↔ gold |
| 15 | Payday | 200K × number of properties owned |
| 16 | Company + Start | Caseta de Zapotlanejo — company and start tile combined |

---

### Samples

| Blue tile | Yellow tile | Red tile |
|-----------|-------------|----------|
| [Colonia Moderna](repo/casillas/casilla_Colonia_Moderna_0.html) | [Plaza del Sol](repo/casillas/casilla_Plaza_del_Sol_0.html) | [Colapso del Periférico](repo/casillas/casilla_Colapso_del_Periférico_0.html) |

| Property card | Company card | Special card |
|---------------|--------------|--------------|
| [Colonia Moderna](repo/tarjetas/tarjeta_Colonia_Moderna.html) | [Telcel Jalisco](repo/tarjetas/tarjeta_Telcel_Jalisco.html) | [Casa de Cambio Centro](repo/tarjetas/tarjeta_Casa_de_Cambio_Centro.html) |

| Blue fortune | Yellow fortune | Red fortune |
|--------------|----------------|-------------|
| [Carta de Pistola](repo/fortunas/fortuna_1_Carta_de_Pistola.html) | [Dados Cargados](repo/fortunas/fortuna_2_Dados_Cargados.html) | [Banca Popular](repo/fortunas/fortuna_3_Banca_Popular.html) |

---

### License

MIT License — see [LICENSE](LICENSE) for details.

> Game assets (sprites, bills, fonts) are not included in this repository and remain property of their respective authors.