"""Run the pairing rules on a few hand-scored example dishes.

The scores are set by hand, so the demo runs without a Jev API key.
Use ask.py to score a dish with Jev.
"""

from pairing import recommend, explain

DISHES = {
    "Pork belly with chili glaze": {
        "fat": 0.85, "acidity": 0.20, "sweetness": 0.45, "saltiness": 0.55,
        "spiciness": 0.75, "bitterness": 0.10, "confidence": 0.90,
        "protein": "pork"},
    "Cured salmon (gravlax) with mustard sauce": {
        "fat": 0.60, "acidity": 0.35, "sweetness": 0.40, "saltiness": 0.70,
        "spiciness": 0.10, "bitterness": 0.10, "confidence": 0.85,
        "protein": "fish"},
    "Ribeye steak": {
        "fat": 0.80, "acidity": 0.05, "sweetness": 0.05, "saltiness": 0.50,
        "spiciness": 0.10, "bitterness": 0.20, "confidence": 0.90,
        "protein": "red meat"},
    "Apple pie with vanilla sauce": {
        "fat": 0.45, "acidity": 0.35, "sweetness": 0.90, "saltiness": 0.10,
        "spiciness": 0.05, "bitterness": 0.05, "confidence": 0.90},
    "Green salad with lemon vinaigrette": {
        "fat": 0.30, "acidity": 0.80, "sweetness": 0.10, "saltiness": 0.30,
        "spiciness": 0.05, "bitterness": 0.35, "confidence": 0.85},
    "Grilled radicchio with walnuts": {
        "fat": 0.45, "acidity": 0.20, "sweetness": 0.10, "saltiness": 0.30,
        "spiciness": 0.05, "bitterness": 0.80, "confidence": 0.80},
    "Unclear dish": {
        "fat": 0.40, "acidity": 0.40, "sweetness": 0.40, "saltiness": 0.40,
        "spiciness": 0.40, "bitterness": 0.40, "confidence": 0.30},
}

if __name__ == "__main__":
    for name, scores in DISHES.items():
        result = recommend(scores)
        print(f"== {name}")
        if result["status"] == "ok":
            print("   fired:", ", ".join(result["fired_rules"]))
        print(explain(result))
        print()
