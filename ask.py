"""Describe a dish in plain text and get drink recommendations.

    python3 ask.py "pork belly with chili glaze"

Uses the Jev backend set in .env (JEV_BACKEND, default mock).
"""

import sys

from pairing import Jev, explain, recommend_for_description

if __name__ == "__main__":
    dish = " ".join(sys.argv[1:]) or input("Describe your dish: ")
    jev = Jev()
    result = recommend_for_description(dish, jev=jev)
    scores = ", ".join(f"{k} {v:.2f}" for k, v in result["jev_scores"].items())
    print(f"Jev ({jev.backend_name}): {scores}\n")
    print(explain(result))
