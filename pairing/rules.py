"""Pairing rules for the knowledge base.

Each rule reads the taste scores that Jev returns for a dish (fat,
acidity, sweetness, saltiness, spiciness, bitterness; each 0-1) and,
if its condition holds, states which drink attributes are preferred
or should be avoided.

Rule fields
-----------
id          short identifier, used in explanations and logs
when        dict {taste: threshold}; the rule fires when every listed
            dish score is >= its threshold. A threshold given as
            ("<", x) fires when the score is below x instead.
prefer      dict {drink attribute: weight}. Positive weight = a high
            value of that attribute is good; negative = a high value
            is bad. Weights are relative importance within the rule.
any_of      optional list of attributes where the drink only needs ONE
            to be high (the best of them counts). Used for "sweetness
            OR acidity" type rules.
cap         optional {drink attribute: (dish taste, margin, weight)}.
            Penalises a drink whose attribute exceeds the dish's taste
            score plus the margin. Used to keep sweetness in proportion.
because     natural-language reason, used for the explanation output
sources     keys into SOURCES.md

Thresholds of 0.6 ("high") are starting values. Tune them once you see
the range of scores Jev actually produces on the test dishes.
"""

HIGH = 0.6

RULES = [
    # ------------------------------------------------------------ fat
    {
        "id": "FAT_CUT",
        "when": {"fat": HIGH},
        "prefer": {"acidity": 0.8, "carbonation": 0.4},
        "because": "Acidity and bubbles cut through fat and refresh the palate.",
        "sources": ["winefolly", "cicerone", "beerandbrewing"],
    },
    {
        "id": "FAT_MATCH_BODY",
        "when": {"fat": HIGH},
        "prefer": {"body": 0.8},
        "because": "A rich dish needs a drink with enough body so it is not overwhelmed.",
        "sources": ["macneil"],
    },
    {
        "id": "FAT_SOFTENS_TANNIN",
        "when": {"fat": HIGH, "spiciness": ("<", 0.4)},
        "prefer": {"bitterness": 0.6},
        "because": "Fat and protein bind tannin, so a tannic or bitter drink feels softer with fatty food.",
        "sources": ["vt_enology", "acs_saad"],
    },
    # -------------------------------------------------------- acidity
    {
        "id": "ACID_MATCH",
        "when": {"acidity": HIGH},
        "prefer": {"acidity": 1.0},
        "because": "An acidic dish makes a low-acid drink taste flat, so the drink should be at least as acidic.",
        "sources": ["wset_notes", "winefolly"],
    },
    # ------------------------------------------------------ sweetness
    {
        "id": "SWEET_MATCH",
        "when": {"sweetness": HIGH},
        "prefer": {"sweetness": 1.5},
        "because": "A sweet dish makes a dry drink taste sour and thin; the drink should be at least as sweet.",
        "sources": ["winefolly", "wset_notes"],
    },
    {
        "id": "SWEET_AVOID_BITTER",
        "when": {"sweetness": HIGH},
        "prefer": {"bitterness": -0.8, "alcohol": -0.3},
        "because": "Sweetness in food magnifies bitterness, tannin and alcohol burn in the drink.",
        "sources": ["wset_notes"],
    },
    # ------------------------------------------------------ saltiness
    {
        "id": "SALT_ACID",
        "when": {"saltiness": HIGH},
        "prefer": {"acidity": 0.8, "carbonation": 0.3},
        "because": "Salt contrasts well with acidity and bubbles, and makes the drink taste fuller.",
        "sources": ["winefolly", "wset_notes"],
    },
    {
        "id": "SALT_SWEET",
        "when": {"saltiness": HIGH},
        "prefer": {"sweetness": 0.5},
        "because": "Salty food and a sweeter drink give a pleasant salty-sweet contrast.",
        "sources": ["winefolly"],
    },
    # ------------------------------------------------------ spiciness
    {
        "id": "SPICE_LOW_ALCOHOL",
        "when": {"spiciness": HIGH},
        "prefer": {"alcohol": -1.2},
        "because": "Alcohol dissolves capsaicin and intensifies chili heat, so a lower-alcohol drink is better.",
        "sources": ["wset_notes", "vinepair"],
    },
    {
        "id": "SPICE_AVOID_BITTER",
        "when": {"spiciness": HIGH},
        "prefer": {"bitterness": -1.0},
        "because": "Chili heat amplifies tannin and hop bitterness, which makes the drink feel harsh.",
        "sources": ["wset_notes", "byo"],
    },
    {
        "id": "SPICE_SWEET",
        "when": {"spiciness": HIGH},
        "prefer": {"sweetness": 1.0},
        "because": "A touch of sweetness softens chili heat.",
        "sources": ["wset_notes", "beerandbrewing"],
    },
    # ----------------------------------------------------- bitterness
    {
        "id": "BITTER_AVOID_BITTER",
        "when": {"bitterness": HIGH},
        "prefer": {"bitterness": -1.0},
        "because": "Bitter food and a bitter or tannic drink multiply each other's bitterness.",
        "sources": ["winefolly"],
    },
    {
        "id": "BITTER_SWEET",
        "when": {"bitterness": HIGH},
        "prefer": {"sweetness": 0.4},
        "because": "Sweetness and fruit in the drink soften bitterness in the dish.",
        "sources": ["winefolly"],
    },
    # ---------------------------------------------------- combinations
    {
        # The rule from the project proposal.
        "id": "FAT_SPICE_BALANCE",
        "when": {"fat": HIGH, "spiciness": HIGH},
        "prefer": {},
        "any_of": ["sweetness", "acidity"],
        "any_of_weight": 1.0,
        "because": "A fatty and spicy dish is balanced by a drink with high sweetness or high acidity.",
        "sources": ["proposal", "wset_notes", "winefolly"],
    },
    # -------------------------------------------------- savoury dishes
    {
        # Design choice by the team, not a rule stated directly in the
        # sources: it follows from "match the intensity" and keeps
        # dessert wines away from savoury main courses. 
        # The drink may be up to 0.35 sweeter than the dish; beyond
        # that it is penalised in proportion to the excess.
        "id": "SWEETNESS_IN_PROPORTION",
        "when": {},
        "prefer": {},
        "cap": {"sweetness": ("sweetness", 0.35, 2.0)},
        "because": "A drink that is much sweeter than the dish overwhelms it, so dessert wines suit desserts.",
        "sources": ["macneil", "byo"],
    },
    # -------------------------------------------------- overall intensity
    {
        "id": "LIGHT_DISH_LIGHT_DRINK",
        "when": {"fat": ("<", 0.4), "spiciness": ("<", 0.4), "saltiness": ("<", 0.5)},
        "prefer": {"body": -0.7, "alcohol": -0.3},
        "because": "A light, delicate dish is overpowered by a heavy drink; match the intensity.",
        "sources": ["byo", "macneil"],
    },
]
