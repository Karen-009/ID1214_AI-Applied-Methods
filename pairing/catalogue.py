"""Systembolaget catalogue: real products as drink profiles.

Data source: the public mirror of Systembolaget's assortment at
https://susbolaget.emrik.org/v1/products (project C4illin/systembolaget-data
on GitHub), stored locally in data/systembolaget.db by
fetch_systembolaget.py.

The database keeps Systembolaget's raw facts. This module turns each
product into the same six 0-1 attributes as pairing/drinks.py, so the
rule engine can rank real bottles exactly as it ranks the generic
drink styles.

Mapping (Systembolaget's taste clocks run 0-12):

    body         clock Body / 12
    sweetness    clock Sweetness / 12, else sugar g/100 ml / 10
                 (red wine has no sweetness clock)
    acidity      clock Fruitacid / 12
    bitterness   clock Roughness (tannin, red wine) or Bitter (beer) / 12
    alcohol      ABV / 15  (drinks.py: 1 = about 15 % or more)
    carbonation  from the category (sparkling wine, beer, cider ...)

Systembolaget compares the clocks within a product group, so "full
body" (12) on a beer is not as full as 12 on a wine. Body for beer,
cider and other non-wine drinks is therefore scaled by BODY_SCALE,
which puts the fullest beer level with a full red wine rather than
above every wine.

A clock that Systembolaget has not measured is missing, not zero, so it
falls back to a default for the drink type (TYPE_DEFAULTS). Products
with no taste clocks at all are skipped: there is nothing to reason on.
"""

import json
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "systembolaget.db"
SOURCE_URL = "https://susbolaget.emrik.org/v1/products"

CLOCKS = ("Body", "Sweetness", "Fruitacid", "Roughness", "Bitter")



def drink_type(cat1, cat2, cat3):
    """Systembolaget category -> the type names used in drinks.py."""
    cat2, cat3 = cat2 or "", cat3 or ""
    if cat1 == "Alkoholfritt":
        return "alcohol-free"
    if cat1 == "Öl":
        return "beer"
    if cat1 == "Cider & blanddrycker":
        return "cider" if cat2 == "Cider" else "mixed drink"
    if cat1 == "Vin":
        if cat2 == "Rött vin":
            return "red wine"
        if cat2 == "Vitt vin":
            return "dessert wine" if cat3 == "Sött" else "white wine"
        if cat2 == "Mousserande vin":
            return "sparkling wine"
        if cat2 == "Rosévin":
            return "rosé wine"
        if cat2 == "Starkvin":
            return "fortified wine"
    return None  # glögg, vermouth, wine boxes, spirits ... not used


# Used when a clock is missing. Rough typical values per type.
TYPE_DEFAULTS = {
    "red wine":       {"acidity": 0.55, "bitterness": 0.55, "body": 0.6},
    "white wine":     {"acidity": 0.65, "bitterness": 0.05, "body": 0.4},
    "dessert wine":   {"acidity": 0.6,  "bitterness": 0.05, "body": 0.6},
    "sparkling wine": {"acidity": 0.7,  "bitterness": 0.05, "body": 0.35},
    "rosé wine":      {"acidity": 0.6,  "bitterness": 0.1,  "body": 0.35},
    "fortified wine": {"acidity": 0.45, "bitterness": 0.3,  "body": 0.8},
    "beer":           {"acidity": 0.25, "bitterness": 0.4,  "body": 0.5},
    "cider":          {"acidity": 0.6,  "bitterness": 0.05, "body": 0.35},
    "mixed drink":    {"acidity": 0.5,  "bitterness": 0.05, "body": 0.3},
    "alcohol-free":   {"acidity": 0.5,  "bitterness": 0.1,  "body": 0.35},
}


# Body clock -> 0-1 for non-wine drinks (see module docstring).
BODY_SCALE = {"beer": 0.75, "cider": 0.75, "mixed drink": 0.75, "alcohol-free": 0.75}

# Beer has no acidity clock. Sour beers are clearly acidic but, with
# fruit and lactose, rarely as sharp as a crisp white wine.
SOUR_BEER_ACIDITY = 0.65


def _carbonation(dtype, cat2, cat3, name):
    name = (name or "").lower()
    cat2, cat3 = cat2 or "", cat3 or ""
    if dtype == "sparkling wine":
        return 0.5 if ("frizzante" in name or "pétillant" in name) else 0.85
    if dtype == "beer":
        return 0.7
    if dtype in ("cider", "mixed drink"):
        return 0.75
    if dtype == "alcohol-free":
        if any(w in cat2 for w in ("Mousserande", "Öl", "Cider", "Must")):
            return 0.75
        return 0.0
    return 0.0



# Systembolaget's usage text names the food a product suits, in a fixed
# vocabulary: "till rätter av fläsk-, lamm- eller nötkött", "till fisk
# eller skaldjur", "till vegetariskt". "Ljust kött" (light meat) covers
# pork, veal and chicken; "mörkt kött" (dark meat) beef, lamb and game.
# Mapped to Jev's protein categories for the SYSTEMBOLAGET_SUGGESTS rule.
SUITS_PATTERNS = {
    "red meat":   r"nötkött|nöt-|\bnöt\b|lamm|vilt|mörkt kött",
    "pork":       r"fläsk|ljust kött",
    "poultry":    r"kyckling|fågel|ljust kött",
    "fish":       r"fisk|skaldjur|ostron",
    "vegetarian": r"vegetari",
}


def suited_proteins(usage):
    """Systembolaget usage text -> sorted list of protein categories."""
    text = (usage or "").lower()
    return sorted(p for p, pat in SUITS_PATTERNS.items() if re.search(pat, text))



def _clamp(x):
    return min(1.0, max(0.0, float(x)))


def profile(row):
    """One database row -> drink profile dict, or None if unusable."""
    dtype = drink_type(row["category1"], row["category2"], row["category3"])
    if dtype is None:
        return None
    clocks = {c: row[f"clock_{c.lower()}"] for c in CLOCKS}
    if all(v is None for v in clocks.values()):
        return None
    d = TYPE_DEFAULTS[dtype]

    def clock(name, default):
        v = clocks[name]
        return default if v is None else _clamp(v / 12)

    if clocks["Sweetness"] is not None:
        sweetness = _clamp(clocks["Sweetness"] / 12)
    else:
        sweetness = _clamp((row["sugar_g_per_100ml"] or 0) / 10)

    tannin_or_hops = [v for v in (clocks["Roughness"], clocks["Bitter"]) if v is not None]
    bitterness = _clamp(max(tannin_or_hops) / 12) if tannin_or_hops else d["bitterness"]

    acidity = clock("Fruitacid", d["acidity"])
    if dtype == "beer" and row["category2"] == "Syrlig öl" and clocks["Fruitacid"] is None:
        acidity = SOUR_BEER_ACIDITY

    return {
        "type": dtype,
        "sweetness": round(sweetness, 3),
        "acidity": round(acidity, 3),
        "bitterness": round(bitterness, 3),
        "body": round(clock("Body", d["body"]) * BODY_SCALE.get(dtype, 1.0), 3),
        "alcohol": round(_clamp((row["abv"] or 0) / 15), 3),
        "carbonation": _carbonation(dtype, row["category2"], row["category3"], row["name"]),
        "suits": suited_proteins(row["usage"]),
        # Lower-case, for the "classic" field of the rules.
        "grapes": sorted({g.lower() for g in json.loads(row["grapes"] or "[]")}),
        "style": " / ".join(c for c in (row["category2"], row["category3"]) if c).lower(),
        # Extra facts, passed through to the recommendation output.
        "info": {
            "product_number": row["product_number"],
            "price": row["price"],
            "producer": row["producer"],
            "volume_ml": row["volume_ml"],
            "abv": row["abv"],
            "country": row["country"],
            "category": " / ".join(c for c in (row["category2"], row["category3"]) if c),
            "assortment": row["assortment"],
            "usage": row["usage"],
        },
    }


# Ranked unless the caller asks for other types. Alcohol-free drinks and
# mixed drinks (alcopops) are left out by default: they are the sweetest,
# fizziest and lowest-alcohol products, so several rules reward them and
# they would crowd out wine and beer for most dishes. Ask for them
# explicitly, e.g. types={"alcohol-free"} for an alcohol-free dinner.
DEFAULT_TYPES = frozenset({"red wine", "white wine", "sparkling wine", "rosé wine",
                           "fortified wine", "dessert wine", "beer", "cider"})
ALL_TYPES = frozenset(TYPE_DEFAULTS)

# Preferred serving size per type when the same product comes in
# several sizes (bottle, can, magnum, bag-in-box).
_PREFERRED_ML = {"beer": 330, "cider": 330, "mixed drink": 330}


def load_catalogue(path=None, max_price=None, types=DEFAULT_TYPES,
                   standard_range_only=False):
    """Load usable products as {display name: profile}.

    types                e.g. {"beer", "cider"}; default DEFAULT_TYPES
                         (wine, beer, cider); None or ALL_TYPES = everything
    max_price            in SEK for the chosen size
    standard_range_only  only "Fast sortiment" (in most shops)
    """
    path = Path(path or DB_PATH)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run: python3 fetch_systembolaget.py")
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM products").fetchall()
    con.close()

    best = {}  # article -> (size penalty, name, profile)
    for row in rows:
        if standard_range_only and row["assortment"] != "Fast sortiment":
            continue
        p = profile(row)
        if p is None or (types and p["type"] not in types):
            continue
        price = p["info"]["price"]
        if max_price is not None and price > max_price:
            continue
        target = _PREFERRED_ML.get(p["type"], 750)
        penalty = abs((row["volume_ml"] or 0) - target)
        key = row["article"]
        if key not in best or penalty < best[key][0]:
            best[key] = (penalty, row["name"], p)

    catalogue = {}
    for _, name, p in best.values():
        label = f"{name} ({p['info']['volume_ml']:g} ml, {p['info']['price']:g} kr)"
        p["info"]["standard_size"] = p["info"]["volume_ml"] == _PREFERRED_ML.get(p["type"], 750)
        catalogue[label] = p
    return catalogue



SCHEMA = """
CREATE TABLE products (
    product_number     TEXT PRIMARY KEY,  -- one per size
    article            TEXT,              -- shared by all sizes
    name               TEXT NOT NULL,
    producer           TEXT,
    category1          TEXT,
    category2          TEXT,
    category3          TEXT,
    country            TEXT,
    origin             TEXT,
    volume_ml          REAL,
    price              REAL,
    abv                REAL,
    sugar_g_per_100ml  REAL,
    clock_body         INTEGER,  -- NULL = not measured
    clock_sweetness    INTEGER,
    clock_fruitacid    INTEGER,
    clock_roughness    INTEGER,
    clock_bitter       INTEGER,
    taste              TEXT,
    usage              TEXT,     -- Systembolaget's serving / pairing text
    taste_symbols      TEXT,     -- JSON list, e.g. ["Lamm", "Nöt"]
    grapes             TEXT,     -- JSON list
    assortment         TEXT,
    is_organic         INTEGER,
    image_url          TEXT
);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
"""


def _row(p):
    clocks = {c["key"].replace("TasteClock", ""): c["value"]
              for c in (p.get("tasteClocks") or [])}
    name = " ".join(x for x in (p.get("productNameBold"), p.get("productNameThin")) if x)
    origin = ", ".join(x for x in (p.get("originLevel1"), p.get("originLevel2")) if x)
    images = p.get("images") or []
    return (
        p["productNumber"], p.get("productNumberShort"), name, p.get("producerName"),
        p.get("categoryLevel1"), p.get("categoryLevel2"), p.get("categoryLevel3"),
        p.get("country"), origin or None, p.get("volume"), p.get("price"),
        p.get("alcoholPercentage"), p.get("sugarContentGramPer100ml"),
        *(clocks.get(c) for c in CLOCKS),
        p.get("taste"), p.get("usage"),
        json.dumps(p.get("tasteSymbols") or [], ensure_ascii=False),
        json.dumps(p.get("grapes") or [], ensure_ascii=False),
        p.get("assortmentText"), int(bool(p.get("isOrganic"))),
        images[0]["imageUrl"] if images else None,
    )


def build_db(products, path=None, fetched_at=""):
    """Write the products that are for sale (no spirits) to SQLite.

    Writes to a temporary file first, so a failed run never leaves a
    half-built database behind.
    """
    path = Path(path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    con.executescript(SCHEMA)
    keep = [p for p in products
            if p.get("categoryLevel1") != "Sprit"
            and not p.get("isDiscontinued")
            and not p.get("isCompletelyOutOfStock")
            and p.get("productNumber")]
    con.executemany(f"INSERT OR REPLACE INTO products VALUES ({','.join('?' * 25)})",
                    [_row(p) for p in keep])
    con.executemany("INSERT INTO meta VALUES (?, ?)",
                    [("source", SOURCE_URL), ("fetched_at", fetched_at)])
    con.commit()
    con.close()
    tmp.replace(path)
    return len(keep)
