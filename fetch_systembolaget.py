"""Download Systembolaget's assortment and build data/systembolaget.db.

    python3 fetch_systembolaget.py                 # download (~100 MB)
    python3 fetch_systembolaget.py --from FILE     # use a saved products.json

Source: https://susbolaget.emrik.org/v1/products, a public mirror of
Systembolaget's product data (github.com/C4illin/systembolaget-data),
updated daily. Spirits, discontinued and sold-out products are skipped.
"""

import argparse
import json
import urllib.request
from datetime import datetime, timezone

from pairing.catalogue import DB_PATH, SOURCE_URL, build_db, load_catalogue
from pairing.jev import ssl_context

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", help="local products.json instead of downloading")
    args = ap.parse_args()

    if args.src:
        with open(args.src, encoding="utf-8") as f:
            products = json.load(f)
    else:
        print(f"Downloading {SOURCE_URL} ...")
        req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "ID1214-pairing"})
        with urllib.request.urlopen(req, timeout=300, context=ssl_context()) as resp:
            products = json.loads(resp.read())

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    n = build_db(products, fetched_at=now)
    usable = load_catalogue()
    by_type = {}
    for p in usable.values():
        by_type[p["type"]] = by_type.get(p["type"], 0) + 1
    print(f"Saved {n} products to {DB_PATH}")
    print(f"{len(usable)} have taste clocks and are used for pairing:")
    for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {t:15} {c}")
