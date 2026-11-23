# Dinner hosting assistant

ID1214 Artificial Intelligence and Applied Methods, KTH.
Simon Lindh Wågström and Karen Li.

You describe a dish in plain text and get a drink to serve with it,
together with the reasons for the choice.

1. **Jev** (TypeSafe AI) scores the dish on six tastes (fat, acidity,
   sweetness, saltiness, spiciness, bitterness), gives a confidence,
   and names the main protein.
2. A **forward-chaining expert system** (`pairing/`) fires the pairing
   rules that match those scores and ranks drinks by how well they fit.
   The drinks are either generic styles or real products from
   Systembolaget.
3. The result lists the top drinks and the rules behind each one. If
   Jev is unsure about the dish, the system asks a question instead.

| File | Role |
|---|---|
| `pairing/rules.py` | Rule base |
| `pairing/drinks.py`, `pairing/catalogue.py` | Fact base: generic drink styles and the Systembolaget catalogue |
| `pairing/engine.py` | Inference engine and explanation |
| `pairing/jev.py` | Jev client (TypeSafe API, or a keyword mock) |
| `SOURCES.md` | Where each rule comes from, and our own design choices |

## Setup

Python 3.9 or later. No packages are required (`certifi` helps if
HTTPS fails on macOS).

```bash
cp .env.example .env
```

Set `JEV_BACKEND=typesafe` and `JEV_API_KEY` in `.env` to use the
real Jev. With the default `mock` backend everything runs offline.

To rank real Systembolaget products, build the database once (about
100 MB to download):

```bash
python3 fetch_systembolaget.py
```

## Usage

```bash
python3 ask.py "pork belly with chili glaze"
python3 ask.py --systembolaget --max-price 200 "pork belly with chili glaze"
python3 demo.py
python3 eval_live.py
python3 -m unittest
```

`demo.py` runs a few hand-scored dishes without Jev. `eval_live.py`
runs 100 test dishes through Jev and writes a summary to `results/`.
