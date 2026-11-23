"""Forward-chaining inference engine for drink recommendations.

Input:  Jev output for one dish, e.g.
        {"fat": 0.8, "acidity": 0.2, "sweetness": 0.1, "saltiness": 0.5,
         "spiciness": 0.7, "bitterness": 0.1, "confidence": 0.85}
Output: either a clarifying question (low confidence) or the top-N
        drinks, each with the rules that support it.
"""

import hashlib
import os

from .drinks import ATTRIBUTES, DRINKS
from .jev import TASTES, Jev, load_env
from .rules import RULES

load_env()
CONFIDENCE_THRESHOLD = float(os.environ.get("JEV_CONFIDENCE_THRESHOLD", "0.6"))

# Attributes that are absent in most drinks. "Bubbles cut fat" means a
# sparkling drink gets a bonus, not that every still wine is penalised,
# so these are scored from 0 instead of centred on 0.5.
BONUS_ONLY = {"carbonation"}


def _condition_holds(threshold, score):
    if isinstance(threshold, (set, frozenset)):
        return score in threshold  # category, e.g. protein in {"fish"}
    if isinstance(threshold, tuple):
        op, value = threshold
        return score < value if op == "<" else score >= value
    return score >= threshold


def fire_rules(dish):
    """Return the rules whose conditions hold, with an activation 0-1.

    Activation grows with how strongly the dish shows the tastes the
    rule tests for, so a dish with fat 0.95 pushes harder than 0.61.
    """
    fired = []
    for rule in RULES:
        if all(_condition_holds(t, dish.get(taste, "unknown"))
               for taste, t in rule["when"].items()):
            positive = [dish[taste] for taste, t in rule["when"].items()
                        if isinstance(t, (int, float))]
            activation = min(positive) if positive else 1.0
            fired.append((rule, activation))
    return fired


def _is_classic(drink, classic):
    """Does the drink have one of the rule's grapes or style categories?

    Only catalogue products carry grapes and a style (catalogue.py);
    the generic drinks in drinks.py never match.
    """
    if classic.get("grapes") and set(drink.get("grapes", ())) & classic["grapes"]:
        return True
    style = drink.get("style", "")
    return any(s in style for s in classic.get("styles", ()))


def _bound(bound, dish):
    """A floor or ceiling: a fixed number or the dish's score for a taste."""
    return dish[bound] if isinstance(bound, str) else bound


def _limit(gap, weight):
    """Full weight once a floor/ceiling is met (gap >= 0), nothing extra
    beyond it; falls off below and turns negative 1/3 short of it. "At
    least as acidic as the dish" is a threshold, not "the more the
    better", which made the most extreme bottles win for many dishes."""
    return weight * max(-1.0, min(1.0, 1 + 3 * gap))


def _rule_score(rule, drink, dish):
    """How well one drink satisfies one rule, roughly in [-1, 1] per weight."""
    score = 0.0
    for attr, (bound, weight) in rule.get("floor", {}).items():
        score += _limit(drink[attr] - _bound(bound, dish), weight)
    for attr, (bound, weight) in rule.get("ceiling", {}).items():
        score += _limit(_bound(bound, dish) - drink[attr], weight)
    for attr, (taste, margin, weight) in rule.get("cap", {}).items():
        excess = drink[attr] - (dish[taste] + margin)
        if excess > 0:
            score -= weight * excess * 2
    for attr, weight in rule["prefer"].items():
        if attr in BONUS_ONLY:
            # Having it helps (or hurts, for a negative weight);
            # lacking it is neutral.
            score += weight * drink[attr]
        else:
            # Centre on 0.5 so that a mid value is neutral.
            score += weight * (drink[attr] - 0.5) * 2
    for attr, (taste, weight) in rule.get("match", {}).items():
        # Best when the drink's attribute equals the dish's taste score;
        # falls off on both sides (too light or too heavy).
        score += weight * (1 - 2 * abs(drink[attr] - dish[taste]))
    if rule.get("suits_protein") and dish.get("protein") in drink.get("suits", ()):
        score += rule["suits_protein"]
    classic = rule.get("classic")
    if classic and _is_classic(drink, classic):
        score += classic["weight"]
    if rule.get("any_of"):
        best = max(drink[a] for a in rule["any_of"])
        score += _limit(best - rule["any_of_floor"], rule.get("any_of_weight", 1.0))
    return score


def recommend(dish, top_n=3, exclude_types=(), drinks=None, max_per_type=None,
              seed=None):
    """Rank all drinks for a dish.

    drinks        the fact base to rank: the generic styles in drinks.py
                  (default) or real products from catalogue.load_catalogue()
    exclude_types lets the caller filter, e.g. ("beer",) or every
                  alcoholic type for an alcohol-free dinner.
    max_per_type  e.g. 1 = at most one beer, one red wine ... in the top
                  N, so thousands of similar products don't fill the list.
    seed          e.g. the dish description. Equally good products are
                  then shuffled with this seed: the same dish always gets
                  the same answer, different dishes get different picks.
    """
    drinks = DRINKS if drinks is None else drinks
    missing = [t for t in TASTES if t not in dish]
    if missing:
        raise ValueError(f"Dish is missing taste scores: {missing}")

    if dish.get("confidence", 1.0) < CONFIDENCE_THRESHOLD:
        return {
            "status": "clarify",
            "question": "I'm not sure how this dish tastes. Is it mainly rich, "
                        "spicy, sweet, sour, salty or bitter? Could you describe "
                        "the main ingredients and how it is cooked?",
        }

    fired = fire_rules(dish)
    ranked = []
    for name, drink in drinks.items():
        if drink["type"] in exclude_types:
            continue
        total = 0.0
        support = []
        for rule, activation in fired:
            s = activation * _rule_score(rule, drink, dish)
            total += s
            support.append((rule, s))
        support.sort(key=lambda x: x[1], reverse=True)
        ranked.append({
            "drink": name,
            "type": drink["type"],
            "score": round(total, 3),
            "reasons": [r["because"] for r, s in support if s > 0.05][:3],
            "rules": [r["id"] for r, s in support if s > 0.05],
            "info": drink.get("info", {}),
            # for the diversity step in server._pick
            "attrs": [drink.get(a, 0) for a in ATTRIBUTES],
            "grapes": drink.get("grapes", ()),
            "style": drink.get("style", ""),
        })
    # Many products share the same taste clocks and so the same score.
    # Equal scores are broken by what helps a host: a product in
    # Systembolaget's standard range (stocked in most shops) and in the
    # standard size (75 cl wine, 33 cl beer). After that the knowledge
    # base has no preference, so with a seed the order is a seeded
    # shuffle (a hash of seed + name). Without one it is the lower price
    # per litre, then the name, so the order never depends on how the
    # database happens to be stored. Generic drinks have no info.
    def tie_break(rec):
        info = rec["info"] or {}
        if seed is not None:
            last = (hashlib.md5(f"{seed}|{rec['drink']}".encode()).hexdigest(),)
        else:
            per_litre = (info.get("price") or 0) / ((info.get("volume_ml") or 1000) / 1000)
            last = (per_litre, rec["drink"])
        return (-rec["score"], info.get("assortment") != "Fast sortiment",
                not info.get("standard_size", True), *last)
    ranked.sort(key=tie_break)
    score_counts = {}
    for rec in ranked:
        score_counts[rec["score"]] = score_counts.get(rec["score"], 0) + 1
    top, per_type = [], {}
    for rec in ranked:
        if len(top) == top_n:
            break
        if max_per_type and per_type.get(rec["type"], 0) >= max_per_type:
            continue
        per_type[rec["type"]] = per_type.get(rec["type"], 0) + 1
        rec["equally_good"] = score_counts[rec["score"]] - 1
        top.append(rec)
    return {
        "status": "ok",
        "fired_rules": [r["id"] for r, _ in fired],
        "recommendations": top,
    }


def recommend_for_description(description, jev=None, **kwargs):
    """Full pipeline: dish text -> Jev scores -> rules -> top drinks."""
    jev = jev or Jev()
    scores = jev.score(description)
    kwargs.setdefault("seed", description)
    result = recommend(scores, **kwargs)
    result["jev_scores"] = scores
    return result


def explain(result):
    """Format a result as plain text for the terminal."""
    if result["status"] == "clarify":
        return result["question"]
    lines = []
    for i, rec in enumerate(result["recommendations"], 1):
        lines.append(f"{i}. {rec['drink']} ({rec['type']})")
        info = rec.get("info") or {}
        if info:
            facts = [info.get("category"), info.get("country"),
                     f"{info['abv']:g} %" if info.get("abv") is not None else None,
                     f"nr {info['product_number']}"]
            lines.append("   " + ", ".join(f for f in facts if f))
        for reason in rec["reasons"]:
            lines.append(f"   - {reason}")
        if info.get("usage"):
            lines.append(f"   Systembolaget: {info['usage']}")
        if rec.get("equally_good", 0) >= 10:
            lines.append(f"   ({rec['equally_good']} other products score the same; "
                         "chosen among them for availability.)")
    return "\n".join(lines)
