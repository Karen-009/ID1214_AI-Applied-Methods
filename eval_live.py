"""Run the eval dishes through the live Jev and the Systembolaget catalogue.

    python3 eval_live.py                 # all 100, max 250 kr
    python3 eval_live.py --max-price 400 --workers 8

Writes results/eval_<timestamp>.json and prints a summary:
protein accuracy, and flags for pairings that break a basic rule:
  TANNIC_RED_NOT_RED_MEAT  top pick is a tannic red, but the dish is
                           fish, poultry or vegetarian
  DESSERT_WINE_SAVOURY     top pick is a dessert wine, dish sweetness < 0.4
  HIGH_ALC_SPICY           spicy dish (>= 0.5), top pick >= 14% ABV
"""

import argparse
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from eval_dishes import DISHES
from pairing import Jev, recommend
from pairing.catalogue import load_catalogue

TANNIC = 0.6  # drink bitterness (tannin) at or above this counts as tannic


def flags_for(expected, scores, top, drinks):
    out = []
    if not top:
        return out
    d = drinks[top["drink"]]
    if (top["type"] == "red wine" and d.get("bitterness", 0) >= TANNIC
            and expected in ("fish", "poultry", "vegetarian")):
        out.append("TANNIC_RED_NOT_RED_MEAT")
    if top["type"] == "dessert wine" and scores["sweetness"] < 0.4:
        out.append("DESSERT_WINE_SAVOURY")
    abv = (top.get("info") or {}).get("abv") or 0
    if scores["spiciness"] >= 0.5 and abv >= 14:
        out.append("HIGH_ALC_SPICY")
    return out


def run_one(jev, drinks, dish, expected):
    t = time.time()
    try:
        scores = jev.score(dish)
    except Exception as e:  # keep going if one call fails
        return {"dish": dish, "expected": expected, "error": str(e)}
    result = recommend(scores, top_n=3, drinks=drinks, max_per_type=1,
                       seed=dish)
    recs = result.get("recommendations", [])
    return {
        "dish": dish,
        "expected": expected,
        "protein": scores["protein"],
        "scores": scores,
        "status": result["status"],
        "fired_rules": result.get("fired_rules", []),
        "top3": [{"drink": r["drink"], "type": r["type"], "score": r["score"],
                  "abv": (r.get("info") or {}).get("abv")} for r in recs],
        "flags": flags_for(expected, scores, recs[0] if recs else None, drinks),
        "seconds": round(time.time() - t, 1),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-price", type=float, default=250)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--backend", help="override JEV_BACKEND, e.g. mock")
    args = ap.parse_args()

    jev = Jev(backend=args.backend)
    drinks = load_catalogue(max_price=args.max_price)
    print(f"Jev backend: {jev.backend_name}, {len(drinks)} drinks <= {args.max_price} kr")

    with ThreadPoolExecutor(args.workers) as pool:
        rows = list(pool.map(lambda d: run_one(jev, drinks, *d), DISHES))

    out_dir = Path("results")
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"eval_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(rows, indent=1, ensure_ascii=False))

    ok = [r for r in rows if "error" not in r]
    errors = [r for r in rows if "error" in r]
    print(f"\n{len(ok)} dishes scored, {len(errors)} errors -> {path}")
    for r in errors:
        print(f"  ERROR {r['dish']}: {r['error'][:120]}")

    correct = sum(r["protein"] == r["expected"] for r in ok)
    print(f"\nProtein accuracy: {correct}/{len(ok)}")
    by_cat = Counter(r["expected"] for r in ok)
    for cat in by_cat:
        c = sum(r["protein"] == r["expected"] for r in ok if r["expected"] == cat)
        print(f"  {cat:11} {c}/{by_cat[cat]}")
    for r in ok:
        if r["protein"] != r["expected"]:
            print(f"  MISS {r['dish']}: expected {r['expected']}, got {r['protein']}")

    clarify = [r for r in ok if r["status"] == "clarify"]
    print(f"\nAsked to clarify (low confidence): {len(clarify)}")
    for r in clarify:
        print(f"  {r['dish']} (confidence {r['scores']['confidence']:.2f})")

    print("\nTop pick type by protein:")
    for cat in by_cat:
        types = Counter(r["top3"][0]["type"] for r in ok
                        if r["expected"] == cat and r["top3"])
        print(f"  {cat:11} " + ", ".join(f"{t} {n}" for t, n in types.most_common()))

    flagged = [r for r in ok if r["flags"]]
    print(f"\nFlagged pairings: {len(flagged)}")
    for r in flagged:
        print(f"  {','.join(r['flags'])}: {r['dish']} -> {r['top3'][0]['drink']}")

    print("\nTop drinks overall (any of top 3):")
    for name, n in Counter(x["drink"] for r in ok for x in r["top3"]).most_common(10):
        print(f"  {n:3}  {name}")
