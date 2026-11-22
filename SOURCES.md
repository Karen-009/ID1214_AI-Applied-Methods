# Sources for the pairing rules

Keys match the `sources` field of each rule in `pairing/rules.py`.

Several of these are wine-media and study-note sources, not
peer-reviewed research. For the report, cite the book and textbook
sources where possible and describe the rest as practitioner guidelines.
The sources disagree on a few points; those are noted below.

| Key | Source | Used for |
|---|---|---|
| `harrington` | Harrington, R. J. (2007). *Food and Wine Pairing: A Sensory Experience*. Wiley. ISBN 978-0-471-79407-3 | Background: sweet, sour, salty and bitter interactions (cite as the main textbook) |
| `winefolly` | Puckette, M. "6 Essential Basics to Food and Wine Pairing". Wine Folly. https://winefolly.com/tutorial/food-and-wine-pairing/ | Acid cuts fat/salt; wine sweeter than food; bitter + bitter clash; salt vs. acid and sweet |
| `macneil` | MacNeil, K. "The 10 rules of food and wine pairing". Decanter. https://www.decanter.com/learn/food/recipes-2/food-and-wine/the-10-rules-of-food-and-wine-pairing-by-karen-macneil-289376/ | Match richness/intensity |
| `wset` | WSET. "Four rules to masterful food and wine pairing". https://wsetglobal.com/knowledge-centre/blog/2023/july/13/four-rules-to-masterful-food-and-wine-pairing | Food high in salt, acid, sugar, fat or chilli changes how wine tastes |
| `wset_notes` | WSET Level 2 food-and-wine principles as summarised in Decanter: https://www.decanter.com/learn/wset/chinese-food-and-wine-matching-wset-level-2-296275/ and https://open-exam-prep.com/study-guides/wset-level-2/storage-service/food-and-wine | Sweetness/umami harden wine; salt softens it; chilli amplifies alcohol and tannin; low-acid wine tastes flat with acidic food |
| `vt_enology` | Virginia Tech Enology. "Food and Wine" (2007). https://enology.fst.vt.edu/downloads/FoodandWine7Nov2007.pdf | Fat and protein bind tannin; salt and acid interactions |
| `acs_saad` | American Chemical Society, Axial. "Chemistry of food and wine pairings" (2022), on Saad et al. (2021). https://axial.acs.org/2022/11/22/chemistry-of-food-and-wine-pairings/ | Lipids soften tannin bitterness (look up the original Saad et al. paper for the report) |
| `vinepair` | VinePair. "The one thing to remember when pairing alcohol with spicy foods". https://vinepair.com/articles/spicy-food-alcohol-pairing-explainer/ | Capsaicin dissolves in alcohol; high ABV intensifies heat |
| `cicerone` | Cicerone Certification Program. "Beer and Food". https://www.cicerone.org/sites/default/files/resources/Beer_and_Food_English.pdf | Carbonation cuts fat |
| `beerandbrewing` | Craft Beer & Brewing, beer dictionary: food pairing. https://beerandbrewing.com/dictionary/9jYnWqXy1G | Hop bitterness cuts fat; malt sweetness balances chilli |
| `byo` | Brew Your Own. "Tips from pros: pairing food & beer". https://byo.com/articles/tips-from-pros-pairing-food-beer/ | Match intensity; bitterness and high ABV boost chilli heat |
| `proposal` | Our project proposal (2 Nov 2026) | FAT_SPICE_BALANCE rule |

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
- The thresholds (0.6 = "high") and the rule weights were tuned by hand
  on the examples in `demo.py`.
