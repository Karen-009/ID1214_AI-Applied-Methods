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
        for name in top(dish(spiciness=0.9)):
            self.assertLess(DRINKS[name]["alcohol"], 0.6, name)
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

    def test_exclude_types(self):
        alcoholic = {d["type"] for d in DRINKS.values()} - {"alcohol-free"}
        names = top(dish(fat=0.8), n=3)
        filtered = [r["drink"] for r in recommend(
            dish(fat=0.8), exclude_types=alcoholic)["recommendations"]]
        self.assertTrue(all(DRINKS[n]["type"] == "alcohol-free" for n in filtered))
        self.assertTrue(names)


if __name__ == "__main__":
    unittest.main()
