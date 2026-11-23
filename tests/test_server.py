import unittest

import server
from pairing import Jev


class RankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jev = Jev(backend="mock")  # no network

    def check(self, dish):
        r = server.rank({"dish": dish}, jev=self.jev)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["jev"]["backend"], "mock")
        self.assertTrue(1 <= len(r["drinks"]) <= 6)
        self.assertEqual(r["drinks"][0]["pick"], "top")
        top_price = r["drinks"][0]["price"]
        for d in r["drinks"]:
            if d["pick"] == "premium":
                self.assertGreater(d["price"], top_price)
            if d["pick"] == "value":
                self.assertLess(d["price"], top_price)
        self.assertLessEqual(sum(d["pick"] == "value" for d in r["drinks"]), 2)
        self.assertLessEqual(sum(d["pick"] == "premium" for d in r["drinks"]), 1)
        self.assertEqual(len({d["productNumber"] for d in r["drinks"]}), len(r["drinks"]))
        for i, d in enumerate(r["drinks"], 1):
            self.assertEqual(d["rank"], i)
            self.assertEqual(d["url"], "https://www.systembolaget.se/" + d["productNumber"])
            self.assertIn("tannin", d["clocks"])
            self.assertLessEqual(len(d["reasons"]), 3)
        self.assertTrue(r["needs"])
        self.assertLessEqual(len(r["needs"]), 6)
        for n in r["needs"]:
            self.assertEqual(len(n["cells"]), len(r["drinks"]))
            for c in n["cells"]:
                self.assertIsInstance(c["value"], str)
                self.assertIsInstance(c["ok"], bool)
        return r

    def test_ribeye(self):
        self.check("grilled ribeye with garlic butter")

    def test_pork_belly(self):
        self.check("pork belly with chili glaze")

    def test_clarify(self):
        r = server.rank({"dish": "grandma's special"}, jev=self.jev)
        self.assertEqual(r["status"], "clarify")
        self.assertIn("question", r)

    def test_bad_requests(self):
        for bad in ({}, {"dish": "  "}, {"dish": 3}, [], {"dish": "x", "types": ["nope"]}):
            with self.assertRaises(server.BadRequest):
                server.rank(bad, jev=self.jev)


class YesNoCellsTest(unittest.TestCase):
    def test_no_is_never_marked_ok(self):
        from pairing.jev import Jev
        r = server.rank({"dish": "grilled ribeye with garlic butter"}, jev=Jev(backend="mock"))
        for row in r["needs"]:
            for c in row["cells"]:
                if c["value"] == "No" and row["label"] in ("Food match", "Classic pairing"):
                    self.assertFalse(c["ok"], row)
                if c["value"] == "Yes" and row["label"] in ("Food match", "Classic pairing"):
                    self.assertTrue(c["ok"], row)


class PickTest(unittest.TestCase):
    def rec(self, name, score, price, ml=750):
        return {"drink": name, "score": score,
                "info": {"price": price, "volume_ml": ml, "standard_size": ml == 750}}

    def test_roles(self):
        ranked = [self.rec("a", 2.0, 300), self.rec("b", 1.95, 700), self.rec("c", 1.9, 150),
                  self.rec("d", 1.8, 120), self.rec("e", 1.75, 100, ml=3000),
                  self.rec("f", 1.0, 50), self.rec("g", 0.9, 400)]
        recs, roles = server._pick(ranked)
        self.assertEqual([r["drink"] for r in recs], ["a", "b", "c", "d", "e", "f"])
        self.assertEqual(roles, ["top", "premium", "value", "value", "more", "more"])

    def test_small_price_gap_is_not_a_role(self):
        ranked = [self.rec("a", 2.0, 16.5, 330), self.rec("b", 2.0, 18.5, 330),
                  self.rec("c", 1.9, 14.9, 330)]
        _, roles = server._pick(ranked)
        self.assertEqual(roles, ["top", "more", "more"])

    def test_no_candidates(self):
        recs, roles = server._pick([self.rec("a", 1.0, 100), self.rec("b", 0.2, 50)])
        self.assertEqual(roles, ["top", "more"])

    def test_same_name_shown_once(self):
        ranked = [self.rec("a", 2.0, 300), self.rec("a", 2.0, 280, 330), self.rec("b", 1.9, 300)]
        recs, _ = server._pick(ranked)
        self.assertEqual([r["drink"] for r in recs], ["a", "b"])

    def test_seed_varies_near_ties_only(self):
        # 20 drinks within NEAR_TOP of the best, one clearly behind them
        ranked = [self.rec(f"w{i}", 2.0 - i * 0.005, 300) for i in range(20)]
        ranked.append(self.rec("low", 1.0, 300))
        tops = {server._pick(ranked, seed=f"dish {k}")[0][0]["drink"] for k in range(10)}
        self.assertGreater(len(tops), 1)
        self.assertNotIn("low", tops)
        again = [r["drink"] for r in server._pick(ranked, seed="ragu")[0]]
        self.assertEqual(again, [r["drink"] for r in server._pick(ranked, seed="ragu")[0]])

    def test_one_bottle_per_producer(self):
        ranked = [self.rec(f"x{i}", 2.0 - i * 0.01, 300) for i in range(6)]
        for i, r in enumerate(ranked):
            r["info"]["producer"] = "Same" if i < 4 else f"Other {i}"
        recs, _ = server._pick(ranked, n=3)
        self.assertEqual([r["drink"] for r in recs], ["x0", "x4", "x5"])

    def test_premium_is_a_sensible_step_up(self):
        ranked = [self.rec("a", 2.0, 100), self.rec("lux", 1.95, 2000),
                  self.rec("step", 1.9, 200)]
        recs, roles = server._pick(ranked)
        self.assertEqual(recs[roles.index("premium")]["drink"], "step")


if __name__ == "__main__":
    unittest.main()
