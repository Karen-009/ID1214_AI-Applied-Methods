"""Describe a dish in plain text and get drink recommendations.

    python3 ask.py "pork belly with chili glaze"
    python3 ask.py --systembolaget --max-price 200 "pork belly with chili glaze"
    python3 ask.py --systembolaget --types beer,cider "fish tacos"
    python3 ask.py --systembolaget --types alcohol-free "fish tacos"
    python3 ask.py --systembolaget --types all "fish tacos"

By default --systembolaget ranks wine, beer and cider. Alcohol-free
drinks and mixed drinks (alcopops) only appear when asked for.

Uses the Jev backend set in .env (JEV_BACKEND, default mock).
--systembolaget ranks real products from data/systembolaget.db
(build it with: python3 fetch_systembolaget.py) instead of the
generic drink styles.
"""

import argparse

from pairing import Jev, explain, recommend_for_description

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dish", nargs="*")
    ap.add_argument("--systembolaget", action="store_true",
                    help="recommend real Systembolaget products")
    ap.add_argument("--max-price", type=float, help="SEK, with --systembolaget")
    ap.add_argument("--types", help="e.g. 'red wine,beer', 'alcohol-free' or 'all' "
                         "(default: wine, beer and cider)")
    ap.add_argument("--standard", action="store_true",
                    help="only the standard range (Fast sortiment)")
    ap.add_argument("-n", type=int, default=3, help="number of recommendations")
    args = ap.parse_args()

    dish = " ".join(args.dish) or input("Describe your dish: ")
    kwargs = {"top_n": args.n}
    if args.systembolaget:
        from pairing.catalogue import ALL_TYPES, DEFAULT_TYPES, load_catalogue
        if not args.types:
            types = DEFAULT_TYPES
        elif args.types.strip() == "all":
            types = ALL_TYPES
        else:
            types = {t.strip() for t in args.types.split(",")}
            unknown = types - ALL_TYPES
            if unknown:
                ap.error(f"unknown type(s) {sorted(unknown)}; choose from {sorted(ALL_TYPES)} or 'all'")
        kwargs["drinks"] = load_catalogue(max_price=args.max_price, types=types,
                                          standard_range_only=args.standard)
        kwargs["max_per_type"] = 1
    jev = Jev()
    result = recommend_for_description(dish, jev=jev, **kwargs)
    scores = ", ".join(f"{k} {v:.2f}" if isinstance(v, float) else f"{k} {v}"
                       for k, v in result["jev_scores"].items())
    print(f"Jev ({jev.backend_name}): {scores}\n")
    print(explain(result))
