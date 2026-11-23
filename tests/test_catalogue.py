import tempfile
import unittest
from pathlib import Path

from pairing import recommend
from pairing.catalogue import build_db, drink_type, load_catalogue

ATTRS = ("sweetness", "acidity", "bitterness", "body", "alcohol", "carbonation")


def product(nr, name, cat1, cat2, cat3=None, clocks=None, price=100.0,
            volume=750, abv=13.0, sugar=None, short=None, **extra):
    p = {"productNumber": nr, "productNumberShort": short or nr,
         "productNameBold": name, "categoryLevel1": cat1, "categoryLevel2": cat2,
         "categoryLevel3": cat3, "price": price, "volume": volume,
         "alcoholPercentage": abv, "sugarContentGramPer100ml": sugar,
         "tasteClocks": [{"key": f"TasteClock{k}", "value": v}
                         for k, v in (clocks or {}).items()],
         "assortmentText": "Fast sortiment", "usage": "Till kött."}
    p.update(extra)
    return p


PRODUCTS = [
    product("1", "Big Red", "Vin", "Rött vin", clocks={"Body": 10, "Roughness": 9, "Fruitacid": 7},
            sugar=0.2, abv=14.5),
    product("2", "Crisp White", "Vin", "Vitt vin", "Torrt",
            clocks={"Body": 4, "Sweetness": 1, "Fruitacid": 10}),
    product("3", "Sweet Riesling", "Vin", "Vitt vin", "Sött",
            clocks={"Body": 7, "Sweetness": 10, "Fruitacid": 8}, abv=8),
    product("4", "Hoppy IPA", "Öl", "Ale", clocks={"Body": 7, "Bitter": 11},
            price=30, volume=330, abv=6.5),
    product("4b", "Hoppy IPA", "Öl", "Ale", clocks={"Body": 7, "Bitter": 11},
            price=90, volume=1000, abv=6.5, short="4"),  # same beer, bigger size
    product("10", "Thick Sour", "Öl", "Syrlig öl", clocks={"Body": 12, "Sweetness": 5, "Bitter": 1},
            price=50, volume=440, abv=4.5),
    product("5", "No Clocks Red", "Vin", "Rött vin"),           # skipped: no clocks
    product("6", "Old Vodka", "Sprit", "Vodka", clocks={"Body": 3}),  # skipped: spirits
    product("8", "Sweet Juice", "Alkoholfritt", "Alkoholfritt Must",
            clocks={"Body": 3, "Sweetness": 11, "Fruitacid": 8}, abv=0, price=40),
    product("9", "Alcopop", "Cider & blanddrycker", "Blanddryck",
            clocks={"Body": 3, "Sweetness": 10, "Fruitacid": 6}, abv=4.5, price=20),
    product("7", "Gone", "Vin", "Rött vin", clocks={"Body": 5}, isDiscontinued=True),
]


class CatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / "sb.db"
        cls.saved = build_db(PRODUCTS, path=cls.db)
        cls.cat = load_catalogue(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def by_name(self, name):
        return next(p for label, p in self.cat.items() if label.startswith(name))

    def test_spirits_and_discontinued_not_saved(self):
        self.assertEqual(self.saved, 9)

    def test_products_without_clocks_skipped(self):
        names = " ".join(self.cat)
        self.assertNotIn("No Clocks", names)
        self.assertNotIn("Vodka", names)

    def test_one_size_per_product(self):
        ipas = [label for label in self.cat if label.startswith("Hoppy IPA")]
        self.assertEqual(len(ipas), 1)
        self.assertIn("330 ml", ipas[0])

    def test_profiles_in_range(self):
        for p in self.cat.values():
            for a in ATTRS:
                self.assertTrue(0 <= p[a] <= 1, (a, p[a]))

    def test_clock_mapping(self):
        red = self.by_name("Big Red")
        self.assertEqual(red["type"], "red wine")
        self.assertAlmostEqual(red["body"], 10 / 12, places=3)
        self.assertAlmostEqual(red["bitterness"], 9 / 12, places=3)  # tannin
        self.assertLess(red["sweetness"], 0.05)                      # from sugar
        self.assertAlmostEqual(self.by_name("Hoppy IPA")["bitterness"], 11 / 12, places=3)
        self.assertEqual(self.by_name("Sweet Riesling")["type"], "dessert wine")

    def test_beer_body_scaled_below_wine(self):
        # Clocks are relative within a product group: a 12/12 beer is
        # not fuller than a 10/12 red wine.
        self.assertLess(self.by_name("Thick Sour")["body"], self.by_name("Big Red")["body"])
        self.assertAlmostEqual(self.by_name("Thick Sour")["acidity"], 0.65)

    def test_types(self):
        self.assertEqual(drink_type("Öl", "Ale", None), "beer")
        self.assertEqual(drink_type("Vin", "Mousserande vin", None), "sparkling wine")
        self.assertIsNone(drink_type("Sprit", "Vodka", None))

    def test_default_types_hide_alcohol_free_and_alcopops(self):
        names = " ".join(self.cat)
        self.assertNotIn("Sweet Juice", names)
        self.assertNotIn("Alcopop", names)
        everything = " ".join(load_catalogue(self.db, types=None))
        self.assertIn("Sweet Juice", everything)
        self.assertIn("Alcopop", everything)
        only = load_catalogue(self.db, types={"alcohol-free"})
        self.assertEqual({p["type"] for p in only.values()}, {"alcohol-free"})

    def test_price_filter(self):
        cheap = load_catalogue(self.db, max_price=50)
        self.assertTrue(all(p["info"]["price"] <= 50 for p in cheap.values()))

    def test_engine_ranks_real_products(self):
        steak = {"fat": 0.8, "acidity": 0.2, "sweetness": 0.1, "saltiness": 0.5,
                 "spiciness": 0.1, "bitterness": 0.2, "confidence": 0.9,
                 "protein": "red meat"}
        top = recommend(steak, drinks=self.cat)["recommendations"][0]
        self.assertTrue(top["drink"].startswith("Big Red"))
        self.assertEqual(top["info"]["product_number"], "1")

        dessert = {"fat": 0.4, "acidity": 0.2, "sweetness": 0.9, "saltiness": 0.1,
                   "spiciness": 0.0, "bitterness": 0.1, "confidence": 0.9}
        top = recommend(dessert, drinks=self.cat)["recommendations"][0]
        self.assertTrue(top["drink"].startswith("Sweet Riesling"))

    def test_max_per_type(self):
        dish = {"fat": 0.5, "acidity": 0.5, "sweetness": 0.3, "saltiness": 0.5,
                "spiciness": 0.1, "bitterness": 0.1, "confidence": 0.9}
        recs = recommend(dish, top_n=4, drinks=self.cat, max_per_type=1)["recommendations"]
        types = [r["type"] for r in recs]
        self.assertEqual(len(types), len(set(types)))


if __name__ == "__main__":
    unittest.main()
