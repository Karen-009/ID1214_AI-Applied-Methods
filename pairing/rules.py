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
            ("<", x) fires when the score is below x instead. The key
            "protein" takes a set, e.g. {"fish"}: the rule fires when
            Jev's main-protein category is in the set ("unknown" never
            matches).
prefer      dict {drink attribute: weight}, "the more the better" (or
            worse, for a negative weight). No rule uses it any more: it
            made the most extreme bottles (Eiswein, the most tannic
            Barolo) win for many different dishes, so floors and
            ceilings replaced it.
floor       optional {drink attribute: (bound, weight)}. The drink should
            have at least this much; bound is a number or a dish taste
            (e.g. "acidity" = at least as acidic as the dish). Full weight
            once met and nothing extra above it, less (down to -weight)
            the further below. See engine._limit.
ceiling     the same, for "at most this much" (tannin with fish, alcohol
            with chili).
any_of      optional list of attributes where the drink only needs one
            to reach any_of_floor (the best of them counts), weighted by
            any_of_weight. Used for "acidity or bubbles" rules.
match       optional {drink attribute: (dish taste, weight)}. Rewards a
            drink whose attribute is close to the dish's taste score and
            penalises it on both sides, e.g. body that matches richness.
suits_protein  optional weight. Adds the weight when the drink's
            "suits" list (parsed from Systembolaget's serving text, see
            catalogue.py) contains the dish's protein. Generic drinks in
            drinks.py have no such list and get nothing.
cap         optional {drink attribute: (dish taste, margin, weight)}.
            Penalises a drink whose attribute exceeds the dish's taste
            score plus the margin. Used to keep sweetness in proportion.
classic     optional {"grapes": set, "styles": list, "weight": w}. Adds
            the weight when the drink's grape list or Systembolaget
            style category matches.
because     natural-language reason, used for the explanation output
sources     keys into SOURCES.md

HIGH is the middle of Jev's scale. Fat and saltiness use ABOVE_MIDDLE,
because their middle level ("moderately rich", "normally seasoned")
describes most main courses. See SOURCES.md for how these were tuned.
"""

HIGH = 0.5
ABOVE_MIDDLE = 0.6  # for fat and saltiness, see above

RULES = [
    # ------------------------------------------------------------ fat
    {
        # Acidity OR bubbles: with both added up, sparkling wine beat
        # every equally acidic still white for any rich dish.
        "id": "FAT_CUT",
        "when": {"fat": ABOVE_MIDDLE},
        "prefer": {},
        "any_of": ["acidity", "carbonation"],
        "any_of_floor": 0.6,
        "any_of_weight": 0.8,
        "because": "Acidity and bubbles cut through fat and refresh the palate.",
        "sources": ["winefolly", "cicerone", "beerandbrewing"],
    },
    {
        # Match, not maximise: "more body is always better" made the
        # fullest product of each type win every rich dish.
        "id": "FAT_MATCH_BODY",
        "when": {"fat": ABOVE_MIDDLE},
        "prefer": {},
        "match": {"body": ("fat", 0.8)},
        "because": "A rich dish needs a drink with enough body so it is not overwhelmed.",
        "sources": ["macneil"],
    },
    {
        # Only for red meat: without the protein check this rule also
        # sent tannic reds to fatty fish such as salmon.
        "id": "FAT_SOFTENS_TANNIN",
        "when": {"fat": ABOVE_MIDDLE, "spiciness": ("<", 0.4), "protein": {"red meat"}},
        "prefer": {},
        "floor": {"bitterness": (0.5, 0.6)},
        "because": "Fat and protein in red meat bind tannin, so a tannic red feels softer with it.",
        "sources": ["vt_enology", "acs_saad"],
    },
    {
        # Lean red meat (moose, reindeer, tartare) still binds tannin,
        # so ask for some structure, more gently than FAT_SOFTENS_TANNIN.
        "id": "RED_MEAT_STRUCTURE",
        "when": {"spiciness": ("<", 0.4), "protein": {"red meat"}},
        "prefer": {},
        "floor": {"bitterness": (0.4, 0.3), "body": (0.5, 0.2)},
        "because": "Protein in red meat binds tannin, so a red with some structure suits it.",
        "sources": ["vt_enology"],
    },
    # -------------------------------------------------------- protein
    {
        "id": "FISH_AVOID_TANNIN",
        "when": {"protein": {"fish"}},
        "prefer": {},
        "ceiling": {"bitterness": (0.35, 1.0)},
        "because": "Tannic red wine with fish or seafood can leave a metallic, fishy aftertaste.",
        "sources": ["tamura", "winefolly"],
    },
    {
        # Pork is left out: it suits both whites and lighter reds.
        "id": "LIGHT_PROTEIN_AVOID_HEAVY",
        "when": {"protein": {"poultry", "vegetarian"}},
        "prefer": {},
        "ceiling": {"bitterness": (0.45, 0.8)},
        "because": "Chicken and vegetarian dishes are milder than red meat; a tannic red overpowers them.",
        "sources": ["winefolly", "macneil"],
    },
    {
        # Breaks ties between the many products with identical taste
        # clocks, using Systembolaget's own suggestion for each product.
        "id": "SYSTEMBOLAGET_SUGGESTS",
        "when": {"protein": {"red meat", "pork", "poultry", "fish", "vegetarian"}},
        "prefer": {},
        "suits_protein": 0.4,
        "because": "Systembolaget suggests this product for this kind of dish.",
        "sources": ["systembolaget"],
    },
    # -------------------------------------------------------- acidity
    {
        "id": "ACID_MATCH",
        "when": {"acidity": HIGH},
        "prefer": {},
        "floor": {"acidity": ("acidity", 1.0)},
        "because": "An acidic dish makes a low-acid drink taste flat, so the drink should be at least as acidic.",
        "sources": ["wset_notes", "winefolly"],
    },
    # ------------------------------------------------------ sweetness
    {
        "id": "SWEET_MATCH",
        "when": {"sweetness": HIGH},
        "prefer": {},
        "floor": {"sweetness": ("sweetness", 1.5)},
        "because": "A sweet dish makes a dry drink taste sour and thin; the drink should be at least as sweet.",
        "sources": ["winefolly", "wset_notes"],
    },
    {
        "id": "SWEET_AVOID_BITTER",
        "when": {"sweetness": HIGH},
        "prefer": {},
        "ceiling": {"bitterness": (0.4, 0.8), "alcohol": (0.9, 0.3)},
        "because": "Sweetness in food magnifies bitterness, tannin and alcohol burn in the drink.",
        "sources": ["wset_notes"],
    },
    # ------------------------------------------------------ saltiness
    {
        "id": "SALT_ACID",
        "when": {"saltiness": ABOVE_MIDDLE},
        "prefer": {},
        "any_of": ["acidity", "carbonation"],
        "any_of_floor": 0.5,
        "any_of_weight": 0.8,
        "because": "Salt contrasts well with acidity and bubbles, and makes the drink taste fuller.",
        "sources": ["winefolly", "wset_notes"],
    },
    {
        "id": "SALT_SWEET",
        "when": {"saltiness": ABOVE_MIDDLE},
        "prefer": {},
        "floor": {"sweetness": (0.2, 0.5)},
        "because": "Salty food and a sweeter drink give a pleasant salty-sweet contrast.",
        "sources": ["winefolly"],
    },
    # ------------------------------------------------------ spiciness
    {
        "id": "SPICE_LOW_ALCOHOL",
        "when": {"spiciness": HIGH},
        "prefer": {},
        "ceiling": {"alcohol": (0.83, 1.2)},
        "because": "Alcohol dissolves capsaicin and intensifies chili heat, so a lower-alcohol drink is better.",
        "sources": ["wset_notes", "vinepair"],
    },
    {
        "id": "SPICE_AVOID_BITTER",
        "when": {"spiciness": HIGH},
        "prefer": {},
        "ceiling": {"bitterness": (0.35, 1.0)},
        "because": "Chili heat amplifies tannin and hop bitterness, which makes the drink feel harsh.",
        "sources": ["wset_notes", "byo"],
    },
    {
        "id": "SPICE_SWEET",
        "when": {"spiciness": HIGH},
        "prefer": {},
        "floor": {"sweetness": (0.25, 1.0)},
        "because": "A touch of sweetness softens chili heat.",
        "sources": ["wset_notes", "beerandbrewing"],
    },
    # ----------------------------------------------------- bitterness
    {
        "id": "BITTER_AVOID_BITTER",
        "when": {"bitterness": HIGH},
        "prefer": {},
        "ceiling": {"bitterness": (0.35, 1.0)},
        "because": "Bitter food and a bitter or tannic drink multiply each other's bitterness.",
        "sources": ["winefolly"],
    },
    {
        "id": "BITTER_SWEET",
        "when": {"bitterness": HIGH},
        "prefer": {},
        "floor": {"sweetness": (0.2, 0.4)},
        "because": "Sweetness and fruit in the drink soften bitterness in the dish.",
        "sources": ["winefolly"],
    },
    # ---------------------------------------------------- combinations
    {
        # The rule from the project proposal.
        "id": "FAT_SPICE_BALANCE",
        "when": {"fat": ABOVE_MIDDLE, "spiciness": HIGH},
        "prefer": {},
        "any_of": ["sweetness", "acidity"],
        "any_of_floor": 0.6,
        "any_of_weight": 1.0,
        "because": "A fatty and spicy dish is balanced by a drink with high sweetness or high acidity.",
        "sources": ["proposal", "wset_notes", "winefolly"],
    },
    # -------------------------------------------------- savoury dishes
    {
        # Our own rule, following from "match the intensity": the drink
        # may be up to 0.35 sweeter than the dish, beyond that it is
        # penalised in proportion to the excess.
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
        "prefer": {},
        "ceiling": {"body": (0.5, 0.7), "alcohol": (0.85, 0.3)},
        "because": "A light, delicate dish is overpowered by a heavy drink; match the intensity.",
        "sources": ["byo", "macneil"],
    },
    # ------------------------------------------------ classic pairings
    # Grape and style rules, using Systembolaget's grape list and style
    # category. The weight is small (0.3), so they only decide between
    # drinks that suit the dish's tastes equally well.
    {
        "id": "FISH_CRISP_WHITE",
        "when": {"protein": {"fish"}, "spiciness": ("<", HIGH)},
        "prefer": {},
        "classic": {"grapes": {"sauvignon blanc", "albariño", "alvarinho", "riesling",
                               "grüner veltliner", "vermentino", "melon de bourgogne",
                               "picpoule", "assyrtiko", "verdejo", "chenin blanc"},
                    "styles": ["vitt vin / friskt & fruktigt"],
                    "weight": 0.3},
        "because": "Fish and shellfish are classically served with a crisp, unoaked white.",
        "sources": ["winefolly", "harrington"],
    },
    {
        "id": "FISH_WHEAT_OR_PILSNER",
        "when": {"protein": {"fish"}, "spiciness": ("<", HIGH)},
        "prefer": {},
        "classic": {"styles": ["veteöl", "pilsner"], "weight": 0.3},
        "because": "Among beers, a wheat beer or pilsner is the classic match for fish and seafood.",
        "sources": ["cicerone"],
    },
    {
        "id": "LIGHT_MEAT_CLASSICS",
        "when": {"protein": {"poultry", "pork"}, "spiciness": ("<", HIGH)},
        "prefer": {},
        "classic": {"grapes": {"pinot noir", "gamay", "chardonnay", "chenin blanc",
                               "riesling", "viognier"},
                    "styles": ["rött vin / mjukt & bärigt"],
                    "weight": 0.3},
        "because": "Chicken and pork are classically served with Pinot Noir, Gamay or a fuller white such as Chardonnay.",
        "sources": ["winefolly", "macneil"],
    },
    {
        "id": "RED_MEAT_CLASSIC_REDS",
        "when": {"protein": {"red meat"}, "spiciness": ("<", HIGH)},
        "prefer": {},
        "classic": {"grapes": {"cabernet sauvignon", "syrah", "shiraz", "malbec",
                               "nebbiolo", "tempranillo", "mourvèdre", "monastrell",
                               "merlot"},
                    "styles": ["rött vin / kryddigt & mustigt"],
                    "weight": 0.3},
        "because": "Beef, lamb and game are classically served with structured reds such as Cabernet, Syrah or Nebbiolo.",
        "sources": ["winefolly", "vt_enology"],
    },
    {
        "id": "RED_MEAT_ROASTED_MALT",
        "when": {"protein": {"red meat"}, "spiciness": ("<", HIGH)},
        "prefer": {},
        "classic": {"styles": ["porter & stout", "brown ale", "mörk lager"], "weight": 0.3},
        "because": "Among beers, the roasted malt of a porter, stout or dark lager echoes grilled and roasted meat.",
        "sources": ["cicerone"],
    },
    {
        # Tomato dishes: pizza, bolognese, parmigiana.
        "id": "ACID_DISH_ITALIAN_RED",
        "when": {"acidity": HIGH, "protein": {"red meat", "pork", "vegetarian"},
                 "sweetness": ("<", HIGH)},
        "prefer": {},
        "classic": {"grapes": {"sangiovese", "barbera"}, "weight": 0.3},
        "because": "Acidic dishes such as tomato sauces need an equally high-acid red such as Sangiovese or Barbera.",
        "sources": ["winefolly", "wset_notes"],
    },
    {
        "id": "SPICE_AROMATIC_WHITE",
        "when": {"spiciness": HIGH},
        "prefer": {},
        "classic": {"grapes": {"riesling", "gewürztraminer", "chenin blanc", "muscat",
                               "moscato", "torrontés"},
                    "styles": ["vitt vin / druvigt & blommigt"],
                    "weight": 0.3},
        "because": "Spicy food is classically paired with an aromatic, often off-dry white such as Riesling or Gewürztraminer.",
        "sources": ["winefolly", "wset_notes"],
    },
]
