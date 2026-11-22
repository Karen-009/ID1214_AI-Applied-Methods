import unittest

from pairing import Jev, recommend_for_description
from pairing.jev import _validate


class JevTests(unittest.TestCase):
    def setUp(self):
        self.jev = Jev(backend="mock")

    def test_mock_returns_all_scores_in_range(self):
        scores = self.jev.score("pork belly with chili glaze")
        for k in ("fat", "acidity", "sweetness", "saltiness",
                  "spiciness", "bitterness", "confidence"):
            self.assertTrue(0 <= scores[k] <= 1, k)

    def test_mock_detects_spicy(self):
        scores = self.jev.score("spicy chili curry")
        self.assertGreater(scores["spiciness"], 0.6)

    def test_unknown_dish_gives_low_confidence_and_question(self):
        result = recommend_for_description("grandma's special", jev=self.jev)
        self.assertEqual(result["status"], "clarify")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            _validate({"fat": 0.5})

    def test_validate_clamps(self):
        full = {k: 2.0 for k in ("fat", "acidity", "sweetness", "saltiness",
                                 "spiciness", "bitterness", "confidence")}
        self.assertEqual(_validate(full)["fat"], 1.0)

    def test_typesafe_backend_refuses_placeholder(self):
        import os
        os.environ["TYPESAFE_API_KEY"] = "REPLACE_ME"
        with self.assertRaises(RuntimeError):
            Jev(backend="typesafe")

    def test_typesafe_request_shape(self):
        from pairing.jev import _TypeSafeBackend, LEVELS
        body = _TypeSafeBackend.build_request("ribeye steak", "jev-latest")
        self.assertEqual(body["model"], "jev-latest")
        self.assertIn("ribeye steak", body["state"])
        for taste in LEVELS:
            q = body["questions"][taste]
            self.assertEqual(q["type"], "score")
            self.assertTrue(2 <= len(q["criteria"]) <= 10)
        self.assertEqual(body["questions"]["clear"]["type"], "noul")

    def test_typesafe_response_parsing(self):
        from pairing.jev import _TypeSafeBackend, LEVELS
        answers = {t: {"type": "score", "score": 3.0, "confidence": 0.8}
                   for t in LEVELS}
        answers["spiciness"] = {"type": "score", "score": 0.0, "confidence": 0.8}
        answers["clear"] = {"type": "noul", "noul": 0.5}
        scores = _validate(_TypeSafeBackend.parse_response(
            {"model": "jev-1.13.0", "answers": answers}))
        self.assertAlmostEqual(scores["fat"], 0.75)
        self.assertAlmostEqual(scores["spiciness"], 0.0)
        self.assertAlmostEqual(scores["confidence"], 0.4)

    def test_unknown_backend(self):
        with self.assertRaises(ValueError):
            Jev(backend="nope")


if __name__ == "__main__":
    unittest.main()
