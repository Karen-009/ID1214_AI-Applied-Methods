# Sources for the pairing rules

Keys match the `sources` field of each rule in `pairing/rules.py`.

Several of these are wine-media sources rather than peer-reviewed
research. The sources disagree on a few points; those are noted below.

| Key | Source | Used for |
|---|---|---|
| `harrington` | Harrington, R. J. (2007). *Food and Wine Pairing: A Sensory Experience*. Wiley. ISBN 978-0-471-79407-3 | Background: sweet, sour, salty and bitter interactions |
| `winefolly` | Puckette, M. "6 Essential Basics to Food and Wine Pairing". Wine Folly. https://winefolly.com/tutorial/food-and-wine-pairing/ | Acid cuts fat/salt; wine sweeter than food; bitter + bitter clash; salt vs. acid and sweet |
| `macneil` | MacNeil, K. "The 10 rules of food and wine pairing". Decanter. https://www.decanter.com/learn/food/recipes-2/food-and-wine/the-10-rules-of-food-and-wine-pairing-by-karen-macneil-289376/ | Match richness/intensity |
| `wset` | WSET. "Four rules to masterful food and wine pairing". https://wsetglobal.com/knowledge-centre/blog/2023/july/13/four-rules-to-masterful-food-and-wine-pairing | Food high in salt, acid, sugar, fat or chilli changes how wine tastes |
| `wset_notes` | WSET Level 2 food-and-wine principles as summarised in Decanter: https://www.decanter.com/learn/wset/chinese-food-and-wine-matching-wset-level-2-296275/ and https://open-exam-prep.com/study-guides/wset-level-2/storage-service/food-and-wine | Sweetness/umami harden wine; salt softens it; chilli amplifies alcohol and tannin; low-acid wine tastes flat with acidic food |
| `vt_enology` | Virginia Tech Enology. "Food and Wine" (2007). https://enology.fst.vt.edu/downloads/FoodandWine7Nov2007.pdf | Fat and protein bind tannin; salt and acid interactions |
| `acs_saad` | American Chemical Society, Axial. "Chemistry of food and wine pairings" (2022), on Saad et al. (2021). https://axial.acs.org/2022/11/22/chemistry-of-food-and-wine-pairings/ | Lipids soften tannin bitterness |
| `vinepair` | VinePair. "The one thing to remember when pairing alcohol with spicy foods". https://vinepair.com/articles/spicy-food-alcohol-pairing-explainer/ | Capsaicin dissolves in alcohol; high ABV intensifies heat |
| `cicerone` | Cicerone Certification Program. "Beer and Food". https://www.cicerone.org/sites/default/files/resources/Beer_and_Food_English.pdf | Carbonation cuts fat |
| `beerandbrewing` | Craft Beer & Brewing, beer dictionary: food pairing. https://beerandbrewing.com/dictionary/9jYnWqXy1G | Hop bitterness cuts fat; malt sweetness balances chilli |
| `byo` | Brew Your Own. "Tips from pros: pairing food & beer". https://byo.com/articles/tips-from-pros-pairing-food-beer/ | Match intensity; bitterness and high ABV boost chilli heat |
| `tamura` | Tamura, T. et al. (2009). "Iron is an essential cause of fishy aftertaste formation in wine and seafood pairing". *Journal of Agricultural and Food Chemistry*, 57(18), 8550–8556 | FISH_AVOID_TANNIN: red wine with fish gives a fishy, metallic aftertaste. The study points to iron in the wine as the cause; red wines tend to be the problem, so the rule uses tannin as the observable proxy |
| `proposal` | Our project proposal (2 Nov 2026) | FAT_SPICE_BALANCE rule |
| `systembolaget` | Systembolaget's product data: the serving suggestion ("Serveras till …") for each product, via the susbolaget.emrik.org mirror of the product API | SYSTEMBOLAGET_SUGGESTS: products Systembolaget itself recommends for the dish's protein |

## Where the sources disagree

- **Spicy food and hop bitterness.** BYO says bitterness boosts chilli
  heat. Some beer writers say an IPA "calms" curry. We follow BYO and
  WSET (avoid bitterness with heat).
- **Spicy food and high-alcohol red.** Wine Folly's informal test found a
  full-bodied, high-alcohol red worked with spicy food. This goes against
  WSET and VinePair. We follow the majority (low alcohol).
- **ABV cut-off for spicy food.** Sources give 13 %, 13.5 % or 14 %. The
  rule uses a continuous penalty instead of a hard cut-off.
- **Salt and acidity.** Wine Folly says salt contrasts well with acidity.
  The VT handout says salt can make wine taste more acidic. We keep
  SALT_ACID but at a lower weight.

## Our own design choices (not taken directly from a source)

- `SWEETNESS_IN_PROPORTION`, which keeps dessert wines away from savoury
  dishes, follows from "match the intensity" but is our own formulation.
- All drink attribute values in `pairing/drinks.py` are hand-assigned
  estimates from typical style descriptions.
- The thresholds and the rule weights were tuned by hand on the
  examples in `demo.py` and on live Jev output. "High" started at 0.6
  and was lowered to 0.5 because Jev's scores rarely reach the top of
  the scale. Fat and saltiness need 0.6 (`ABOVE_MIDDLE`) instead: their
  middle level ("moderately rich", "normally seasoned") describes most
  main courses, and at 0.5 the salt rules fired for 83 of the 100
  evaluation dishes (`eval_live.py`), so acidic sparkling wine won
  almost every dish.
- `LIGHT_PROTEIN_AVOID_HEAVY` (poultry and vegetarian dishes avoid
  tannic drinks) is our formulation of "match the intensity"; it was
  added after the evaluation sent Amarone to roast chicken. A first
  version also penalised alcohol, but then 5% ciders beat every wine
  (cider was the top pick for 32 of the 40 poultry and vegetarian
  dishes), so it only penalises tannin.
- Limiting `FAT_SOFTENS_TANNIN` to red meat (via Jev's protein
  category) is our choice: the sources describe the effect for red meat,
  and without the limit the rule sent tannic reds to salmon.
- `FAT_CUT` and `SALT_ACID` count acidity *or* bubbles (`any_of`, the
  better of the two), since the sources give them as alternatives.
  When both were added up, acidic sparkling wine beat every equally
  acidic still white, and one cava was in the top 3 for 30 of the 100
  evaluation dishes.
- `FAT_MATCH_BODY` matches the drink's body to the dish's fat (`match`)
  instead of rewarding more body without limit. Before, the fullest
  product of each type won every rich dish; among beers this was always
  the same sour beer (top 3 for 32 of 100 dishes).
- `SYSTEMBOLAGET_SUGGESTS` (weight 0.4) reads the serving text with
  simple patterns (`suited_proteins` in `pairing/catalogue.py`). "Ljust
  kött" counts as pork and poultry, and "mörkt kött" as red meat. The
  taste clocks alone cannot tell products apart: 6,118 drinks share only
  2,407 profiles. In the 100-dish evaluation (stored Jev scores replayed),
  the share of top picks that Systembolaget suggests for the dish's protein
  rose from 37 to 79. Distinct drinks in the top 3 rose from 69 to 85.
- `RED_MEAT_STRUCTURE` asks for some tannin and body for any red meat
  that is not spicy. It is a gentler version of `FAT_SOFTENS_TANNIN` and
  is our own extension of the VT handout. Without it, lean red meat
  (moose, reindeer, tartare) fired no taste rule, 2,600+ products tied,
  and an 11.9 kr lager won. Red wine is now the top pick for 14 of the 20
  red-meat dishes, up from 9.
- **Classic grape and style rules** (`FISH_CRISP_WHITE`,
  `FISH_WHEAT_OR_PILSNER`, `LIGHT_MEAT_CLASSICS`, `RED_MEAT_CLASSIC_REDS`,
  `RED_MEAT_ROASTED_MALT`, `ACID_DISH_ITALIAN_RED`, `SPICE_AROMATIC_WHITE`)
  turn widely taught pairings into rules. They use Systembolaget's grape
  list (filled for about a third of the products) and style category
  (e.g. "Vitt vin / Friskt & Fruktigt"). The grape lists are our choice,
  based on the pairing charts in Wine Folly and Harrington. The beer
  styles are based on the Cicerone guide. The weight is small (0.3), so they only decide between
  products that fit the dish's tastes equally well. In the evaluation, a
  classic rule supports 61 of the 100 top picks, and distinct drinks in
  the top 3 rose from 85 to 109.
- Equal scores are broken by what helps a host, in this order:
  Systembolaget's standard range ("Fast sortiment", stocked in most
  shops), then the standard size (75 cl wine, 33 cl beer). After that the
  knowledge base has no preference, so the remaining order is a **seeded
  shuffle**: a hash of the dish description and the product name. The
  same dish always gets the same answer, but different dishes do not all
  get the same "first" product. Without a seed, the order is the lower
  price per litre, then the name. Before, ties fell to database row
  order. Simply taking the cheapest product made 25 cl bottles and an
  11.9 kr lager win. The explanation says when 10 or more products score
  the same.
- **Known gap:** mild dishes (fat and salt in the middle, no strong
  taste) still leave large ties. Examples are roast pork loin (291
  products), roast chicken (187), moules marinières (547) and margherita
  pizza (390). The classic rules shrank these from 500 to 2,900, but
  within a group like "Pinot Noir or Chardonnay" the shuffle decides. The
  next steps would be asking Jev about cooking method and sauce, or
  asking the host about budget and preferences.
- Bubbles only add to a drink's score and never subtract from still
  drinks (`BONUS_ONLY` in `pairing/engine.py`).
- Systembolaget product mapping (`pairing/catalogue.py`): beer and cider
  body is scaled by 0.75, because Systembolaget's taste clocks compare
  products within one product group; sour beer acidity is set to 0.65
  because beer has no acidity clock.
