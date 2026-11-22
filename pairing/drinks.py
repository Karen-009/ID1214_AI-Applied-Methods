"""Drink profiles for the knowledge base.

Every drink is described on six attributes, each scored 0-1:

    sweetness    residual sugar / perceived sweetness
    acidity      perceived sourness / freshness
    bitterness   tannin (wine) or hop bitterness (beer) -- both add
                 bitter/astringent sensations that react the same way
                 to spicy, sweet and bitter food
    body         weight and intensity in the mouth
    alcohol      0 = alcohol-free, 1 = about 15 % ABV or more
    carbonation  0 = still, 1 = very sparkling

The values are hand-assigned estimates based on typical style
descriptions (see SOURCES.md). They are a first version and should be
reviewed and adjusted as testing shows where they are off.
"""

ATTRIBUTES = ("sweetness", "acidity", "bitterness", "body", "alcohol", "carbonation")

DRINKS = {
    # --- White and sparkling wine ---
    "Champagne (brut)": {
        "type": "sparkling wine",
        "sweetness": 0.10, "acidity": 0.85, "bitterness": 0.05,
        "body": 0.35, "alcohol": 0.55, "carbonation": 0.90,
    },
    "Prosecco (extra dry)": {
        "type": "sparkling wine",
        "sweetness": 0.30, "acidity": 0.60, "bitterness": 0.05,
        "body": 0.25, "alcohol": 0.45, "carbonation": 0.80,
    },
    "Riesling (off-dry)": {
        "type": "white wine",
        "sweetness": 0.50, "acidity": 0.85, "bitterness": 0.05,
        "body": 0.30, "alcohol": 0.30, "carbonation": 0.00,
    },
    "Sauvignon Blanc": {
        "type": "white wine",
        "sweetness": 0.05, "acidity": 0.85, "bitterness": 0.05,
        "body": 0.35, "alcohol": 0.60, "carbonation": 0.00,
    },
    "Gewürztraminer": {
        "type": "white wine",
        "sweetness": 0.45, "acidity": 0.35, "bitterness": 0.10,
        "body": 0.65, "alcohol": 0.65, "carbonation": 0.00,
    },
    "Chardonnay (oaked)": {
        "type": "white wine",
        "sweetness": 0.10, "acidity": 0.45, "bitterness": 0.10,
        "body": 0.80, "alcohol": 0.80, "carbonation": 0.00,
    },
    "Rosé (dry)": {
        "type": "rosé wine",
        "sweetness": 0.10, "acidity": 0.65, "bitterness": 0.10,
        "body": 0.35, "alcohol": 0.55, "carbonation": 0.00,
    },
    # --- Red wine ---
    "Pinot Noir": {
        "type": "red wine",
        "sweetness": 0.05, "acidity": 0.70, "bitterness": 0.30,
        "body": 0.40, "alcohol": 0.60, "carbonation": 0.00,
    },
    "Beaujolais (Gamay)": {
        "type": "red wine",
        "sweetness": 0.10, "acidity": 0.70, "bitterness": 0.20,
        "body": 0.30, "alcohol": 0.45, "carbonation": 0.00,
    },
    "Cabernet Sauvignon": {
        "type": "red wine",
        "sweetness": 0.05, "acidity": 0.55, "bitterness": 0.85,
        "body": 0.85, "alcohol": 0.85, "carbonation": 0.00,
    },
    "Zinfandel": {
        "type": "red wine",
        "sweetness": 0.20, "acidity": 0.45, "bitterness": 0.50,
        "body": 0.80, "alcohol": 0.95, "carbonation": 0.00,
    },
    # --- Sweet and fortified wine ---
    "Sauternes": {
        "type": "dessert wine",
        "sweetness": 0.95, "acidity": 0.65, "bitterness": 0.05,
        "body": 0.85, "alcohol": 0.70, "carbonation": 0.00,
    },
    "Moscato d'Asti": {
        "type": "dessert wine",
        "sweetness": 0.80, "acidity": 0.55, "bitterness": 0.00,
        "body": 0.20, "alcohol": 0.10, "carbonation": 0.50,
    },
    "Port (ruby)": {
        "type": "fortified wine",
        "sweetness": 0.85, "acidity": 0.40, "bitterness": 0.50,
        "body": 0.95, "alcohol": 1.00, "carbonation": 0.00,
    },
    # --- Beer ---
    "Pilsner": {
        "type": "beer",
        "sweetness": 0.15, "acidity": 0.25, "bitterness": 0.45,
        "body": 0.30, "alcohol": 0.25, "carbonation": 0.80,
    },
    "IPA": {
        "type": "beer",
        "sweetness": 0.15, "acidity": 0.25, "bitterness": 0.85,
        "body": 0.55, "alcohol": 0.45, "carbonation": 0.70,
    },
    "Wheat beer (witbier)": {
        "type": "beer",
        "sweetness": 0.25, "acidity": 0.40, "bitterness": 0.15,
        "body": 0.40, "alcohol": 0.25, "carbonation": 0.85,
    },
    "Stout": {
        "type": "beer",
        "sweetness": 0.35, "acidity": 0.20, "bitterness": 0.65,
        "body": 0.85, "alcohol": 0.35, "carbonation": 0.40,
    },
    # --- Cider and alcohol-free ---
    "Apple cider (dry)": {
        "type": "cider",
        "sweetness": 0.20, "acidity": 0.75, "bitterness": 0.15,
        "body": 0.30, "alcohol": 0.25, "carbonation": 0.70,
    },
    "Lingonberry sparkling (alcohol-free)": {
        "type": "alcohol-free",
        "sweetness": 0.60, "acidity": 0.65, "bitterness": 0.10,
        "body": 0.20, "alcohol": 0.00, "carbonation": 0.75,
    },
    "Elderflower cordial with soda (alcohol-free)": {
        "type": "alcohol-free",
        "sweetness": 0.65, "acidity": 0.45, "bitterness": 0.00,
        "body": 0.15, "alcohol": 0.00, "carbonation": 0.80,
    },
    "Alcohol-free lager": {
        "type": "alcohol-free",
        "sweetness": 0.25, "acidity": 0.20, "bitterness": 0.35,
        "body": 0.25, "alcohol": 0.00, "carbonation": 0.80,
    },
}
