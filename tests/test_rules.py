import unittest

from pairing import recommend
from pairing.drinks import DRINKS, ATTRIBUTES
from pairing.rules import RULES

BASE = {"fat": 0.3, "acidity": 0.3, "sweetness": 0.3, "saltiness": 0.3,
        "spiciness": 0.1, "bitterness": 0.1, "confidence": 0.9}


def dish(**overrides):
    return {**BASE, **overrides}


def top(d, n=3):
    return [r["drink"] for r in recommend(d, top_n=n)["recommendations"]]


class KnowledgeBaseTests(unittest.TestCase):
    def test_every_drink_has_all_attributes_in_range(self):
        for name, d in DRINKS.items():
            for a in ATTRIBUTES:
                self.assertTrue(0 <= d[a] <= 1, f"{name}.{a}")

    def test_every_rule_has_reason_and_source(self):
        for r in RULES:
            self.assertTrue(r["because"] and r["sources"], r["id"])


class PairingTests(unittest.TestCase):
    def test_low_confidence_asks_question(self):
        self.assertEqual(recommend(dish(confidence=0.3))["status"], "clarify")

    def test_spicy_dish_gets_no_high_alcohol_or_bitter_drink(self):
        # A ceiling (about 12.5 %), not "the lower the better".
        for name in top(dish(spiciness=0.9)):
            self.assertLessEqual(DRINKS[name]["alcohol"], 0.83, name)
            self.assertLess(DRINKS[name]["bitterness"], 0.4, name)

    def test_dessert_gets_sweet_drink(self):
        for name in top(dish(sweetness=0.9)):
            self.assertGreaterEqual(DRINKS[name]["sweetness"], 0.6, name)

    def test_savoury_dish_gets_no_dessert_wine(self):
        for name in top(dish(fat=0.8, saltiness=0.6, sweetness=0.05)):
            self.assertNotEqual(DRINKS[name]["type"], "dessert wine", name)

    def test_fatty_spicy_rule_from_proposal(self):
        result = recommend(dish(fat=0.8, spiciness=0.8))
        self.assertIn("FAT_SPICE_BALANCE", result["fired_rules"])
        best = DRINKS[result["recommendations"][0]["drink"]]
        self.assertGreater(max(best["sweetness"], best["acidity"]), 0.6)

    def test_tannin_rule_only_for_red_meat(self):
        steak = recommend(dish(fat=0.8, protein="red meat"))
        salmon = recommend(dish(fat=0.8, protein="fish"))
        self.assertIn("FAT_SOFTENS_TANNIN", steak["fired_rules"])
        self.assertNotIn("FAT_SOFTENS_TANNIN", salmon["fired_rules"])
        self.assertNotIn("FAT_SOFTENS_TANNIN", recommend(dish(fat=0.8))["fired_rules"])

    def test_fish_gets_no_tannic_drink(self):
        result = recommend(dish(fat=0.6, saltiness=0.5, protein="fish"))
        self.assertIn("FISH_AVOID_TANNIN", result["fired_rules"])
        for rec in result["recommendations"]:
            self.assertLess(DRINKS[rec["drink"]]["bitterness"], 0.4, rec["drink"])

    def test_red_meat_gets_red_wine(self):
        top_drink = recommend(dish(fat=0.8, saltiness=0.5, sweetness=0.05,
                                   protein="red meat"))["recommendations"][0]
        self.assertEqual(top_drink["type"], "red wine")

    def test_light_protein_gets_no_heavy_red(self):
        for protein in ("poultry", "vegetarian"):
            result = recommend(dish(fat=0.8, protein=protein))
            self.assertIn("LIGHT_PROTEIN_AVOID_HEAVY", result["fired_rules"])
            for rec in result["recommendations"]:
                d = DRINKS[rec["drink"]]
                self.assertFalse(d["bitterness"] >= 0.6 and d["alcohol"] >= 0.6,
                                 f"{protein}: {rec['drink']}")

    def test_normally_seasoned_is_not_salty(self):
        # Jev's middle levels ("normally seasoned", "moderately rich")
        # must not trigger the salt and fat rules.
        fired = recommend(dish(fat=0.5, saltiness=0.5))["fired_rules"]
        for rule in ("SALT_ACID", "SALT_SWEET", "FAT_CUT", "FAT_MATCH_BODY"):
            self.assertNotIn(rule, fired)
        fired = recommend(dish(fat=0.75, saltiness=0.75))["fired_rules"]
        self.assertIn("SALT_ACID", fired)
        self.assertIn("FAT_CUT", fired)

    def test_acid_or_bubbles_and_matched_body(self):
        from pairing.engine import _rule_score
        rules = {r["id"]: r for r in RULES}
        d = dish(fat=0.75)
        base = {"sweetness": 0.1, "bitterness": 0.1, "alcohol": 0.8}
        still = {**base, "acidity": 0.9, "body": 0.6, "carbonation": 0.0}
        bubbly = {**still, "carbonation": 0.85}
        # Acidity or bubbles: an equally acidic still wine is not beaten.
        self.assertGreaterEqual(_rule_score(rules["FAT_CUT"], still, d),
                                _rule_score(rules["FAT_CUT"], bubbly, d))
        # Body is matched, so a drink heavier than the dish scores lower.
        heavy = {**still, "body": 1.0}
        matched = {**still, "body": 0.75}
        self.assertGreater(_rule_score(rules["FAT_MATCH_BODY"], matched, d),
                           _rule_score(rules["FAT_MATCH_BODY"], heavy, d))

    def test_suited_proteins_from_usage_text(self):
        from pairing.catalogue import suited_proteins
        self.assertEqual(suited_proteins("Serveras till rätter av fläsk-, lamm- eller nötkött."),
                         ["pork", "red meat"])
        self.assertEqual(suited_proteins("till mörkt kött"), ["red meat"])
        self.assertEqual(suited_proteins("till ljust kött"), ["pork", "poultry"])
        self.assertEqual(suited_proteins("till skaldjur"), ["fish"])
        # "nötdesserter" are nut desserts, not beef.
        self.assertEqual(suited_proteins("till nötdesserter och hårdostar"), [])
        self.assertEqual(suited_proteins(None), [])

    def test_systembolaget_suggestion_boosts_matching_drink(self):
        base = {**DRINKS["Pinot Noir"], "info": {}}
        drinks = {"suggested": {**base, "suits": ["fish"]},
                  "not suggested": {**base, "suits": ["red meat"]}}
        result = recommend(dish(protein="fish"), drinks=drinks)
        self.assertIn("SYSTEMBOLAGET_SUGGESTS", result["fired_rules"])
        recs = result["recommendations"]
        self.assertEqual(recs[0]["drink"], "suggested")
        self.assertGreater(recs[0]["score"], recs[1]["score"])

    def test_tie_break_prefers_standard_range_and_size(self):
        base = {**DRINKS["Pinot Noir"], "suits": []}
        def product(assortment, ml, price):
            return {**base, "info": {"assortment": assortment, "volume_ml": ml,
                                     "price": price, "standard_size": ml == 750}}
        drinks = {
            "A small bottle": product("Fast sortiment", 375, 50),
            "B order item": product("Ordervaror", 750, 80),
            "C standard": product("Fast sortiment", 750, 120),
            "D cheaper standard": product("Fast sortiment", 750, 100),
        }
        recs = recommend(dish(), top_n=4, drinks=drinks)["recommendations"]
        self.assertEqual([r["drink"] for r in recs],
                         ["D cheaper standard", "C standard", "A small bottle", "B order item"])
        self.assertTrue(all(r["equally_good"] == 3 for r in recs))

    def test_lean_red_meat_gets_structure(self):
        result = recommend(dish(fat=0.2, saltiness=0.5, sweetness=0.05, protein="red meat"))
        self.assertIn("RED_MEAT_STRUCTURE", result["fired_rules"])
        self.assertNotIn("FAT_SOFTENS_TANNIN", result["fired_rules"])
        self.assertEqual(result["recommendations"][0]["type"], "red wine")

    def test_seeded_shuffle_among_ties(self):
        base = {**DRINKS["Pinot Noir"], "suits": [], "info": {}}
        drinks = {f"wine {i}": dict(base) for i in range(20)}
        def first(seed):
            return recommend(dish(), drinks=drinks, seed=seed)["recommendations"][0]["drink"]
        # Same dish -> same answer; different dishes -> not always the same.
        self.assertEqual(first("roast chicken"), first("roast chicken"))
        self.assertGreater(len({first(f"dish {i}") for i in range(10)}), 1)
        # A seed never lifts a lower-scoring drink above a better one.
        drinks["best"] = {**base, "suits": ["fish"]}
        for i in range(10):
            self.assertEqual(recommend(dish(protein="fish"), drinks=drinks,
                                       seed=f"dish {i}")["recommendations"][0]["drink"], "best")

    def test_classic_grape_and_style_rules(self):
        base = {**DRINKS["Sauvignon Blanc"], "suits": [], "info": {}}
        drinks = {"albariño": {**base, "grapes": ["albariño"], "style": "vitt vin"},
                  "crisp style": {**base, "grapes": [], "style": "vitt vin / friskt & fruktigt"},
                  "other": {**base, "grapes": ["gewürztraminer"], "style": "vitt vin"}}
        recs = recommend(dish(protein="fish"), top_n=3, drinks=drinks)["recommendations"]
        self.assertEqual(recs[-1]["drink"], "other")
        self.assertIn("FISH_CRISP_WHITE", recs[0]["rules"])
        # Spicy food turns it around: the aromatic grape is the classic.
        recs = recommend(dish(spiciness=0.7), drinks=drinks)["recommendations"]
        self.assertEqual(recs[0]["drink"], "other")

    def test_floor_gives_nothing_extra_above_it(self):
        from pairing.engine import _rule_score
        rules = {r["id"]: r for r in RULES}
        d = dish(acidity=0.6)
        drink = {**DRINKS["Sauvignon Blanc"]}
        enough = _rule_score(rules["ACID_MATCH"], {**drink, "acidity": 0.65}, d)
        extreme = _rule_score(rules["ACID_MATCH"], {**drink, "acidity": 1.0}, d)
        flat = _rule_score(rules["ACID_MATCH"], {**drink, "acidity": 0.3}, d)
        self.assertEqual(enough, extreme)
        self.assertLess(flat, enough)

    def test_exclude_types(self):
        alcoholic = {d["type"] for d in DRINKS.values()} - {"alcohol-free"}
        names = top(dish(fat=0.8), n=3)
        filtered = [r["drink"] for r in recommend(
            dish(fat=0.8), exclude_types=alcoholic)["recommendations"]]
        self.assertTrue(all(DRINKS[n]["type"] == "alcohol-free" for n in filtered))
        self.assertTrue(names)


if __name__ == "__main__":
    unittest.main()
