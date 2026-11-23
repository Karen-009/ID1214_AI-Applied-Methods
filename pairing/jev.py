"""Jev: the decision model that turns a dish description into taste scores.

Every backend returns the same dict:

    {"fat": 0-1, "acidity": 0-1, "sweetness": 0-1, "saltiness": 0-1,
     "spiciness": 0-1, "bitterness": 0-1, "confidence": 0-1,
     "protein": "red meat" | "pork" | "poultry" | "fish" | "vegetarian"
                | "unknown"}

The six tastes are numbers; protein is a category, because what the
main ingredient is (not only how it tastes) decides some pairings,
e.g. tannic red wine suits beef but clashes with fish. Since all
backends return the same format, the rule engine does not care which
one produced the scores.

Backends (pick one with JEV_BACKEND in .env):

    mock      Keyword heuristic. Used in the tests and as a baseline
              to compare Jev against.
    typesafe  The real Jev, via TypeSafe AI's API (JEV_API_KEY).
"""

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path

TASTES = ("fat", "acidity", "sweetness", "saltiness", "spiciness", "bitterness")

# Main protein categories, with the wording used in the question to Jev.
PROTEINS = {
    "red meat": "beef, lamb, venison or other red meat",
    "pork": "pork, ham, bacon or sausage",
    "poultry": "chicken, turkey or other poultry",
    "fish": "fish or seafood",
    "vegetarian": "no meat or fish (vegetables, cheese, eggs, legumes, grains or a dessert)",
}
# Below this probability the protein is reported as "unknown", and the
# rules that depend on it do not fire.
PROTEIN_MIN_PROBABILITY = 0.5


def load_env(path=None):
    """Read KEY=VALUE lines from .env into os.environ.

    A minimal loader so the project needs no extra package. Variables
    already set in the shell win over the file.
    """
    path = Path(path) if path else Path(__file__).resolve().parent.parent / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _validate(scores):
    """Check that a backend returned all scores in range, and clamp them."""
    missing = [k for k in (*TASTES, "confidence") if k not in scores]
    if missing:
        raise ValueError(f"Jev response is missing: {missing}")
    out = {k: min(1.0, max(0.0, float(scores[k]))) for k in (*TASTES, "confidence")}
    protein = scores.get("protein", "unknown")
    out["protein"] = protein if protein in PROTEINS else "unknown"
    return out


class _MockBackend:
    """Keyword-based scores. Crude, but enough to run the rest of the system."""

    KEYWORDS = {
        "fat": ["butter", "cream", "cheese", "pork belly", "bacon", "fried",
                "duck", "ribeye", "steak", "salmon", "avocado", "coconut milk"],
        "acidity": ["lemon", "lime", "vinegar", "vinaigrette", "tomato",
                    "pickled", "yoghurt", "yogurt", "citrus", "lingonberr"],
        "sweetness": ["sugar", "honey", "caramel", "chocolate", "pie", "cake",
                      "dessert", "glaze", "syrup", "jam", "vanilla", "fruit"],
        "saltiness": ["salt", "cured", "soy", "anchov", "parmesan", "feta",
                      "olive", "bacon", "gravlax", "ham", "herring"],
        "spiciness": ["chili", "chilli", "jalapeño", "jalapeno", "curry",
                      "sriracha", "pepper", "spicy", "wasabi", "harissa"],
        "bitterness": ["radicchio", "endive", "coffee", "dark chocolate", "kale",
                       "rocket", "arugula", "grapefruit", "charred", "walnut"],
    }

    PROTEIN_KEYWORDS = {
        "red meat": ["beef", "steak", "ribeye", "lamb", "venison", "moose", "elk",
                     "bourguignon", "burger", "meatball", "reindeer"],
        "pork": ["pork", "ham", "bacon", "sausage", "chorizo"],
        "poultry": ["chicken", "turkey", "duck", "goose"],
        "fish": ["fish", "salmon", "gravlax", "cod", "tuna", "herring", "shrimp",
                 "prawn", "mussel", "oyster", "crab", "lobster", "seafood"],
        "vegetarian": ["vegetarian", "vegan", "tofu", "lentil", "salad", "cake",
                       "pie", "pancake", "dessert", "risotto", "halloumi"],
    }

    def score(self, description):
        text = description.lower()
        scores, hits_total = {}, 0
        scores["protein"] = next((p for p, words in self.PROTEIN_KEYWORDS.items()
                                  if any(w in text for w in words)), "unknown")
        for taste, words in self.KEYWORDS.items():
            hits = sum(1 for w in words if w in text)
            hits_total += hits
            # 0 hits -> 0.1, 1 hit -> 0.65 (just "high"), 2+ -> 0.85+
            scores[taste] = 0.1 if hits == 0 else min(1.0, 0.45 + 0.2 * hits)
        # Few recognised words -> low confidence -> engine asks a question.
        scores["confidence"] = min(0.95, 0.3 + 0.2 * hits_total)
        return scores


# Five ordered levels per taste, lowest first. Jev returns a
# probability-weighted level index 0-4, which is divided by 4 to get 0-1.
LEVELS = {
    "fat": ["Lean, almost no fat or oil", "A little fat", "Moderately rich",
            "Rich and fatty", "Very rich, dominated by fat, butter, cream or oil"],
    "acidity": ["No sourness", "Slightly tangy", "Noticeably acidic",
                "Clearly sour or sharp", "Very sour, e.g. strong vinegar or citrus"],
    "sweetness": ["Not sweet at all", "A hint of sweetness", "Moderately sweet",
                  "Clearly sweet", "Very sweet, like a dessert"],
    "saltiness": ["Unsalted", "Lightly salted", "Normally seasoned",
                  "Clearly salty", "Very salty, e.g. cured, brined or soy-heavy"],
    "spiciness": ["No chili heat", "Mild warmth", "Medium heat",
                  "Hot", "Very hot, strong chili burn"],
    "bitterness": ["No bitterness", "Slightly bitter notes", "Noticeably bitter",
                   "Clearly bitter", "Very bitter, e.g. charred or bitter greens dominate"],
}


def ssl_context():
    """Python from python.org on macOS ships without root certificates,
    which gives CERTIFICATE_VERIFY_FAILED. Use certifi's bundle if it
    is installed, otherwise the system default."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _protein_key(protein):
    return "protein_" + protein.replace(" ", "_")


class _TypeSafeBackend:
    """Jev via TypeSafe AI's System One API (https://docs.typesafe.ai).

    One request asks twelve questions about the dish description:
    one "score" question per taste, one yes/no ("noul") question about
    whether the description is clear enough to judge, and one yes/no
    question per protein category. The protein is the category with the
    highest probability, or "unknown" if none reaches
    PROTEIN_MIN_PROBABILITY.

    confidence = mean of the six score confidences, multiplied by the
    probability that the description is clear. Tune the threshold
    (JEV_CONFIDENCE_THRESHOLD) after looking at real responses.
    """

    def __init__(self):
        self.url = os.environ.get("JEV_API_URL", "https://api.typesafe.ai/v1/systemone")
        self.key = (os.environ.get("JEV_API_KEY") or os.environ.get("TYPESAFE_API_KEY") or "").strip()
        self.model = os.environ.get("JEV_MODEL", "jev-latest")
        self.timeout = float(os.environ.get("JEV_TIMEOUT_SECONDS", "15"))
        if not self.key or "REPLACE_ME" in self.key:
            raise RuntimeError("Set JEV_API_KEY in .env (create a key at "
                               "https://console.typesafe.ai/keys), or use JEV_BACKEND=mock.")

    @staticmethod
    def build_request(description, model="jev-latest"):
        questions = {
            taste: {
                "type": "score",
                "instructions": f"How strong is the {taste} of this dish as eaten",
                "criteria": levels,
            }
            for taste, levels in LEVELS.items()
        }
        for protein, wording in PROTEINS.items():
            questions[_protein_key(protein)] = {
                "type": "noul",
                "instructions": f"The main protein of this dish is {wording}",
            }
        questions["clear"] = {
            "type": "noul",
            "instructions": "The text describes a specific dish clearly enough "
                            "to judge how it tastes",
        }
        return {"model": model, "state": f"Dish: {description}", "questions": questions}

    @staticmethod
    def parse_response(body):
        answers = body["answers"]
        scores, confidences = {}, []
        for taste, levels in LEVELS.items():
            a = answers[taste]
            scores[taste] = float(a["score"]) / (len(levels) - 1)
            confidences.append(float(a.get("confidence", 1.0)))
        clear = float(answers["clear"]["noul"])
        scores["confidence"] = (sum(confidences) / len(confidences)) * clear
        probs = {p: float(answers[_protein_key(p)]["noul"])
                 for p in PROTEINS if _protein_key(p) in answers}
        best = max(probs, key=probs.get) if probs else None
        scores["protein"] = (best if best and probs[best] >= PROTEIN_MIN_PROBABILITY
                             else "unknown")
        return scores

    def score(self, description):
        req = urllib.request.Request(
            self.url,
            data=json.dumps(self.build_request(description, self.model)).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout,
                                        context=ssl_context()) as resp:
                return self.parse_response(json.loads(resp.read()))
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            raise RuntimeError(f"TypeSafe API error {e.code}: {detail}") from None


_BACKENDS = {"mock": _MockBackend, "typesafe": _TypeSafeBackend}


class Jev:
    def __init__(self, backend=None):
        load_env()
        name = (backend or os.environ.get("JEV_BACKEND", "mock")).lower()
        if name not in _BACKENDS:
            raise ValueError(f"Unknown JEV_BACKEND {name!r}; use {list(_BACKENDS)}")
        self.backend_name = name
        self._backend = _BACKENDS[name]()

    def score(self, description):
        """Dish description -> validated taste scores + confidence."""
        return _validate(self._backend.score(description))
