"""HTTP JSON API for the dinner pairing web app (stdlib only).

    python3 server.py [--port 8000]

POST /api/rank   body RankRequest -> RankResponse (see web/src/types.ts)
GET  /api/health -> {"ok": true, "backend": ...}
"""

import argparse
import hashlib
import json
import math
import re
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pairing import Jev, recommend_for_description
from pairing.catalogue import ALL_TYPES, DB_PATH, DEFAULT_TYPES, load_catalogue
from pairing.engine import _rule_score
from pairing.jev import TASTES
from pairing.rules import RULES

RULES_BY_ID = {r["id"]: r for r in RULES}
MAX_BODY = 64 * 1024
LOCAL_ORIGIN = re.compile(r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$")

_jev = None
_catalogues = {}
_lock = threading.Lock()


class BadRequest(Exception):
    pass


def _image_url(base):
    """The DB stores the CDN path without size; the CDN needs e.g. _400.png."""
    if not base:
        return None
    return base if base.endswith(".png") else base + "_400.png"


def get_jev():
    global _jev
    if _jev is None:
        _jev = Jev()
    return _jev


def get_catalogue(max_price, types):
    key = (max_price, frozenset(types))
    with _lock:
        if key not in _catalogues:
            _catalogues[key] = load_catalogue(max_price=max_price, types=set(types))
        return _catalogues[key]


# ------------------------------------------------------------ formatting

def _style(cat2, cat3):
    cat2, cat3 = cat2 or "", cat3 or ""
    if cat2 == "Rött vin":
        return "Red"
    if cat2 == "Vitt vin":
        return "Sweet white" if "Sött" in cat3 else "White"
    if cat2 == "Mousserande vin":
        return "Sparkling"
    if cat2 == "Rosévin":
        return "Rosé"
    if cat2 == "Cider":
        return "Cider"
    if cat2 == "Starkvin":
        return "Fortified"
    return cat2 or cat3 or "Other"


def _origin(origin, country):
    if origin:
        last = origin.split(",")[-1].strip()
        if last:
            return last
    return country or ""


def _clock(v):
    return None if v is None else int(round(v))


def _fetch_rows(product_numbers):
    if not product_numbers:
        return {}
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        q = ",".join("?" * len(product_numbers))
        rows = con.execute(
            f"SELECT * FROM products WHERE product_number IN ({q})",
            list(product_numbers)).fetchall()
    finally:
        con.close()
    return {r["product_number"]: dict(r) for r in rows}


def _jev_reading(jev, scores):
    return {
        "backend": jev.backend_name,
        "scores": {t: float(scores[t]) for t in TASTES},
        "protein": scores.get("protein", "unknown"),
        "confidence": float(scores.get("confidence", 0)),
    }


# ------------------------------------------------------------ needs table

ATTR_LABEL = {"acidity": "Acidity", "sweetness": "Sweetness", "body": "Body",
              "alcohol": "Alcohol", "carbonation": "Bubbles"}


def _rule_attrs(rule):
    attrs = []
    for src in (rule.get("floor", {}), rule.get("ceiling", {}), rule.get("cap", {}),
                rule.get("prefer", {}), rule.get("match", {})):
        for a in src:
            if a not in attrs:
                attrs.append(a)
    return attrs, list(rule.get("any_of", []))


def _attr_label(attr, all_beer):
    if attr == "bitterness":
        return "Bitterness" if all_beer else "Tannin / bitter"
    return ATTR_LABEL.get(attr, attr.capitalize())


def _rule_label(rule, all_beer):
    attrs, any_of = _rule_attrs(rule)
    parts = []
    if any_of:
        names = [_attr_label(a, all_beer) for a in any_of]
        parts.append(names[0] + "".join(" or " + n.lower() for n in names[1:]))
    parts += [_attr_label(a, all_beer) for a in attrs if a not in any_of]
    if parts:
        return " + ".join(parts)
    if rule.get("suits_protein"):
        return "Food match"
    if rule.get("classic"):
        return "Classic pairing"
    return rule["id"]


def _attr_value(attr, drink):
    """Display value of one attribute for one drink: (text)."""
    row, prof = drink["row"], drink["profile"]
    if attr == "alcohol":
        return "–" if row.get("abv") is None else f"{row['abv']:g} %"
    if attr == "carbonation":
        return "Yes" if prof.get("carbonation", 0) >= 0.5 else "No"
    if attr == "bitterness":
        if prof.get("type") == "beer":
            v = row.get("clock_bitter")
            return "–" if v is None else str(int(round(v)))
        v = row.get("clock_roughness")
        return "None" if not v else str(int(round(v)))
    col = {"acidity": "clock_fruitacid", "sweetness": "clock_sweetness",
           "body": "clock_body"}.get(attr)
    v = row.get(col) if col else None
    return "–" if v is None else str(int(round(v)))


def _cell_value(rule, drink):
    attrs, any_of = _rule_attrs(rule)
    names = any_of + [a for a in attrs if a not in any_of]
    if names:
        return " / ".join(_attr_value(a, drink) for a in names)
    if rule.get("suits_protein") or rule.get("classic"):
        return "Yes" if drink["rule_ok"][rule["id"]] else "No"
    return "–"


def _needs(fired_ids, drinks, dish):
    all_beer = all(d["profile"].get("type") == "beer" for d in drinks) if drinks else False
    needs = []
    for rid in fired_ids:
        rule = RULES_BY_ID.get(rid)
        if rule is None:
            continue
        scores = [_rule_score(rule, d["profile"], dish) for d in drinks]
        if all(abs(s) < 1e-9 for s in scores):
            continue  # no effect on any shown drink
        # food-match rows are Yes/No: "Yes" (and ✓) only if the rule added score;
        # attribute rows pass unless the rule pulled the drink down
        yes_no = bool(rule.get("suits_protein") or rule.get("classic"))
        for d, s in zip(drinks, scores):
            d["rule_ok"][rid] = s > 0 if yes_no else s >= 0
        needs.append({
            "rule": rid,
            "label": _rule_label(rule, all_beer),
            "need": rule["because"],
            "cells": [{"value": _cell_value(rule, d), "ok": d["rule_ok"][rid]}
                      for d in drinks],
        })
        if len(needs) == 6:
            break
    return needs


# ------------------------------------------------------------ main logic

MAX_SHOWN = 6
GOOD_SHARE = 0.85     # a "good" match scores at least 85 % of the best
NEAR_TOP = 0.92       # within 8 % of the best score counts as equally good
JITTER = 0.04         # seeded noise among near-ties, as a share of the best score
PREMIUM_PRICE = 1.25  # premium costs at least 25 % more than the top pick ...
PREMIUM_MAX = 3.0     # ... but at most 3 times as much
PREMIUM_EXTRA = 600   # ... and at most 600 kr more
PREMIUM_SHARE = 0.90  # and must score at least 90 % of the best
VALUE_PRICE = 0.80    # good value costs at least 20 % less than the top pick
VALUE_SAVING = 0.08   # score share a value pick may give up per e-fold cheaper per litre
VALUE_JITTER = 0.03   # seeded noise among value candidates
MAX_PER_PRODUCER = 1  # diversity caps within one list
MAX_PER_GRAPE = 2
SIMILARITY = 0.3      # weight of "unlike what is already shown" for the rest
POOL = 200            # how many of the best are considered for the rest


def _info(rec):
    return rec.get("info") or {}


def _price(rec):
    return float(_info(rec).get("price") or 0)


def _per_litre(rec):
    return _price(rec) / ((_info(rec).get("volume_ml") or 750) / 1000)


def _gumbel(seed, rec):
    """Seeded Gumbel noise: the same seed and drink always give the same
    value. Adding it to the score and taking the best samples among
    near-equal drinks (the Gumbel-max trick)."""
    if seed is None:
        return 0.0
    h = int(hashlib.md5(f"{seed}|{rec['drink']}".encode()).hexdigest()[:12], 16)
    u = (h + 0.5) / 16 ** 12
    return -math.log(-math.log(u))


def _producer(rec):
    return _info(rec).get("producer") or None


def _grape(rec):
    grapes = rec.get("grapes") or ()
    return grapes[0] if grapes else None


def _similarity(a, b):
    """0-1: same taste profile, grape and style count as similar."""
    sim = 0.0
    if a.get("attrs") and b.get("attrs"):
        diff = sum(abs(x - y) for x, y in zip(a["attrs"], b["attrs"])) / len(a["attrs"])
        sim += 0.5 * (1 - diff)
    if _grape(a) and _grape(a) == _grape(b):
        sim += 0.25
    if a.get("style") and a.get("style") == b.get("style"):
        sim += 0.25
    return sim


def _pick(ranked, n=MAX_SHOWN, seed=None):
    """Choose up to n drinks by role: top, premium (pricier), two value
    (cheaper) and more.

    Equally good drinks are sampled with seeded noise, so similar dishes
    get different bottles while the same dish always gets the same
    answer. Within one list there is at most one bottle per producer and
    two per grape, and the rest are chosen to differ from what is shown
    (maximal marginal relevance)."""
    names, unique = set(), []
    for r in ranked:
        if r["drink"] not in names:
            names.add(r["drink"])
            unique.append(r)
    ranked = unique
    if not ranked:
        return [], []
    best = ranked[0]["score"]
    if best <= 0:
        return ranked[:n], ["top"] + ["more"] * (min(n, len(ranked)) - 1)
    noise = {r["drink"]: _gumbel(seed, r) for r in ranked[:POOL * 5]}

    def jittered(r):
        return r["score"] + JITTER * best * noise.get(r["drink"], 0.0)

    chosen = []
    producers, grapes = {}, {}

    def fits(r):
        p, g = _producer(r), _grape(r)
        return ((p is None or producers.get(p, 0) < MAX_PER_PRODUCER)
                and (g is None or grapes.get(g, 0) < MAX_PER_GRAPE))

    def take(r, role):
        chosen.append((r, role))
        if _producer(r):
            producers[_producer(r)] = producers.get(_producer(r), 0) + 1
        if _grape(r):
            grapes[_grape(r)] = grapes.get(_grape(r), 0) + 1

    def first_fitting(cands):
        taken = {id(c) for c, _ in chosen}
        cands = [c for c in cands if id(c) not in taken]
        return next((c for c in cands if fits(c)), cands[0] if cands else None)

    # top: a near-tie, stocked in most shops and in the standard size first
    tier = [r for r in ranked if r["score"] >= NEAR_TOP * best]
    tier.sort(key=lambda r: (_info(r).get("assortment") != "Fast sortiment",
                             not _info(r).get("standard_size", True), -jittered(r)))
    top = tier[0]
    take(top, "top")
    tp, tpl = _price(top), _per_litre(top)
    good = [r for r in ranked if r is not top and r["score"] >= GOOD_SHARE * best]

    if tp > 0:
        # premium: a clear but sensible step up in price
        high = min(PREMIUM_MAX * tp, tp + PREMIUM_EXTRA)
        pricier = [r for r in good if PREMIUM_PRICE * tp <= _price(r) <= high
                   and r["score"] >= PREMIUM_SHARE * best]
        pricier.sort(key=lambda r: -jittered(r))
        r = first_fitting(pricier)
        if r:
            take(r, "premium")

        # value: trade a little score for a lower price per litre
        def utility(r):
            u = r["score"] / best - VALUE_SAVING * math.log(_per_litre(r) / tpl)
            return u + VALUE_JITTER * noise.get(r["drink"], 0.0)
        cheaper = [r for r in good if 0 < _price(r) <= VALUE_PRICE * tp]
        cheaper.sort(key=lambda r: (not _info(r).get("standard_size", True), -utility(r)))
        for _ in range(2):
            r = first_fitting(cheaper)
            if r:
                take(r, "value")

    # the rest: good and unlike what is already shown
    pool = sorted(good, key=lambda r: -jittered(r))[:POOL]
    while len(chosen) < n:
        taken = {id(c) for c, _ in chosen}
        cands = [r for r in pool if id(r) not in taken]
        if not cands:
            break
        shown = [c for c, _ in chosen]

        def mmr(r):
            return (jittered(r) / best
                    - SIMILARITY * max(_similarity(r, c) for c in shown))
        fitting = [r for r in cands if fits(r)] or cands
        take(max(fitting, key=mmr), "more")
    if len(chosen) < n:
        # few good matches: fill in rank order
        taken = {id(c) for c, _ in chosen}
        for r in ranked:
            if len(chosen) >= n:
                break
            if id(r) not in taken:
                take(r, "more")
    return [r for r, _ in chosen], [role for _, role in chosen]


def _parse_request(req):
    if not isinstance(req, dict):
        raise BadRequest("Body must be a JSON object")
    dish = req.get("dish")
    if not isinstance(dish, str) or not dish.strip():
        raise BadRequest("'dish' must be a non-empty string")
    max_price = req.get("maxPrice")
    if max_price is not None:
        if isinstance(max_price, bool) or not isinstance(max_price, (int, float)):
            raise BadRequest("'maxPrice' must be a number")
        max_price = float(max_price)
    types = req.get("types")
    if types is None:
        types = DEFAULT_TYPES
    else:
        if (not isinstance(types, list) or not types
                or not all(isinstance(t, str) for t in types)):
            raise BadRequest("'types' must be a non-empty list of strings")
        types = {t.strip() for t in types}
        unknown = types - ALL_TYPES
        if unknown:
            raise BadRequest(f"unknown type(s) {sorted(unknown)}")
    return dish.strip(), max_price, frozenset(types)


def rank(req, jev=None):
    """RankRequest dict -> RankResponse dict. Raises BadRequest on bad input."""
    dish_text, max_price, types = _parse_request(req)
    jev = jev or get_jev()
    catalogue = get_catalogue(max_price, types)
    if not catalogue:
        return {"status": "error", "message": "No drinks match those filters."}
    result = recommend_for_description(dish_text, jev=jev, top_n=len(catalogue),
                                       drinks=catalogue)
    scores = result.get("jev_scores")
    if result["status"] == "clarify":
        return {"status": "clarify", "question": result["question"],
                "jev": _jev_reading(jev, scores) if scores else None}

    recs, roles = _pick(result["recommendations"], seed=dish_text.lower())
    rows = _fetch_rows([r["info"]["product_number"] for r in recs])
    drinks, out = [], []
    for i, rec in enumerate(recs, 1):
        info = rec["info"]
        pn = info["product_number"]
        row = rows.get(pn, {})
        drinks.append({"row": row, "profile": catalogue[rec["drink"]], "rule_ok": {}})
        assortment = row.get("assortment", info.get("assortment"))
        out.append({
            "rank": i,
            "productNumber": pn,
            "name": row.get("name") or rec["drink"],
            "producer": row.get("producer"),
            "type": rec["type"],
            "style": _style(row.get("category2"), row.get("category3")),
            "origin": _origin(row.get("origin"), row.get("country") or info.get("country")),
            "country": row.get("country") or info.get("country"),
            "volumeMl": float(row.get("volume_ml") or info.get("volume_ml") or 0),
            "price": float(row.get("price") or info.get("price") or 0),
            "abv": float(row.get("abv") if row.get("abv") is not None else (info.get("abv") or 0)),
            "assortment": assortment,
            "inStock": assortment != "Ordervaror",
            "imageUrl": _image_url(row.get("image_url")),
            "url": "https://www.systembolaget.se/" + str(pn),
            "clocks": {"body": _clock(row.get("clock_body")),
                       "sweetness": _clock(row.get("clock_sweetness")),
                       "acidity": _clock(row.get("clock_fruitacid")),
                       "tannin": _clock(row.get("clock_roughness")),
                       "bitter": _clock(row.get("clock_bitter"))},
            "score": rec["score"],
            "reasons": rec["reasons"][:3],
            "rules": rec["rules"],
            "equallyGood": bool(rec.get("equally_good", 0)),
            "pick": roles[i - 1],
        })
    needs = _needs(result["fired_rules"], drinks, scores)
    return {"status": "ok", "jev": _jev_reading(jev, scores),
            "drinks": out, "needs": needs}


# ------------------------------------------------------------ HTTP

class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        origin = self.headers.get("Origin", "")
        if LOCAL_ORIGIN.match(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path.split("?")[0] == "/api/health":
            self._send(200, {"ok": True, "backend": get_jev().backend_name})
        else:
            self._send(404, {"status": "error", "message": "Not found"})

    def do_POST(self):
        if self.path.split("?")[0] != "/api/rank":
            return self._send(404, {"status": "error", "message": "Not found"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                raise BadRequest("Missing or oversized request body")
            try:
                req = json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                raise BadRequest("Body is not valid JSON")
            self._send(200, rank(req))
        except BadRequest as e:
            self._send(400, {"status": "error", "message": str(e)})
        except Exception:
            import traceback
            traceback.print_exc(file=sys.stderr)
            self._send(500, {"status": "error", "message": "Internal server error"})

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    get_jev()
    get_catalogue(None, DEFAULT_TYPES)  # warm the default catalogue
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Listening on http://{args.host}:{args.port} (jev: {get_jev().backend_name})",
          file=sys.stderr)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
