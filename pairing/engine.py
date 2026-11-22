"""Forward-chaining inference engine for drink recommendations.

Input:  Jev output for one dish, e.g.
        {"fat": 0.8, "acidity": 0.2, "sweetness": 0.1, "saltiness": 0.5,
         "spiciness": 0.7, "bitterness": 0.1, "confidence": 0.85}
Output: either a clarifying question (low confidence) or the top-N
        drinks, each with the rules that support it.
"""

import os

from .drinks import DRINKS
from .jev import Jev, load_env
from .rules import RULES

load_env()
CONFIDENCE_THRESHOLD = float(os.environ.get("JEV_CONFIDENCE_THRESHOLD", "0.6"))
TASTES = ("fat", "acidity", "sweetness", "saltiness", "spiciness", "bitterness")


def _condition_holds(threshold, score):
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
        if all(_condition_holds(t, dish[taste]) for taste, t in rule["when"].items()):
            positive = [dish[taste] for taste, t in rule["when"].items()
                        if not isinstance(t, tuple)]
            activation = min(positive) if positive else 1.0
            fired.append((rule, activation))
    return fired


def _rule_score(rule, drink, dish):
    """How well one drink satisfies one rule, roughly in [-1, 1] per weight."""
    score = 0.0
    for attr, (taste, margin, weight) in rule.get("cap", {}).items():
        excess = drink[attr] - (dish[taste] + margin)
        if excess > 0:
            score -= weight * excess * 2
    for attr, weight in rule["prefer"].items():
        # Centre on 0.5 so that a mid value is neutral.
        score += weight * (drink[attr] - 0.5) * 2
    if rule.get("any_of"):
        best = max(drink[a] for a in rule["any_of"])
        score += rule.get("any_of_weight", 1.0) * (best - 0.5) * 2
    return score


def recommend(dish, top_n=3, exclude_types=()):
    """Rank all drinks for a dish.

    exclude_types lets the caller filter, e.g. ("beer",) or every
    alcoholic type for an alcohol-free dinner.
    """
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
    for name, drink in DRINKS.items():
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
        })
    ranked.sort(key=lambda d: d["score"], reverse=True)
    return {
        "status": "ok",
        "fired_rules": [r["id"] for r, _ in fired],
        "recommendations": ranked[:top_n],
    }


def recommend_for_description(description, jev=None, **kwargs):
    """Full pipeline: dish text -> Jev scores -> rules -> top drinks."""
    jev = jev or Jev()
    scores = jev.score(description)
    result = recommend(scores, **kwargs)
    result["jev_scores"] = scores
    return result


def explain(result):
    """Plain-text explanation, a placeholder for the NLP/generative step."""
    if result["status"] == "clarify":
        return result["question"]
    lines = []
    for i, rec in enumerate(result["recommendations"], 1):
        lines.append(f"{i}. {rec['drink']} ({rec['type']})")
        for reason in rec["reasons"]:
            lines.append(f"   - {reason}")
    return "\n".join(lines)
