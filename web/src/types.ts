// API contract between server.py (Python) and the web app.
// POST /api/rank  body: RankRequest  ->  RankResponse (always HTTP 200 unless the request is malformed)

export interface RankRequest {
  dish: string;
  maxPrice?: number;          // kr, optional
  types?: string[];           // e.g. ["wine","beer","cider"]; default = engine DEFAULT_TYPES
}

export type Taste = 'fat' | 'acidity' | 'sweetness' | 'saltiness' | 'spiciness' | 'bitterness';

export interface JevReading {
  backend: string;                    // Jev().backend_name, e.g. "mock" or "typesafe"
  scores: Record<Taste, number>;      // 0..1
  protein: string;                    // red meat / pork / poultry / fish / vegetarian / unknown
  confidence: number;                 // 0..1
}

export interface Clocks {             // Systembolaget taste clocks, 1..12, null = not measured
  body: number | null;
  sweetness: number | null;
  acidity: number | null;
  tannin: number | null;              // clock_roughness
  bitter: number | null;
}

export interface Drink {
  rank: number;                       // 1-based
  productNumber: string;
  name: string;
  producer: string | null;
  type: string;                       // engine type: wine / beer / cider / ...
  style: string;                      // short human style, e.g. "Red", "Sweet white", "Cider"
  origin: string;                     // short origin, e.g. "Bandol" or country if no region
  country: string | null;
  volumeMl: number;
  price: number;                      // kr
  abv: number;                        // percent, e.g. 13.5
  assortment: string | null;          // raw, e.g. "Fast sortiment" / "Ordervaror"
  inStock: boolean;                   // assortment is not an order item
  imageUrl: string | null;            // Systembolaget CDN image
  url: string;                        // https://www.systembolaget.se/<productNumber>
  clocks: Clocks;
  score: number;
  reasons: string[];                  // engine "because" texts, ≤3
  rules: string[];                    // rule ids that pushed it up
  equallyGood: boolean;
  pick: Pick;
}

// Why a drink is shown. Order in the response: top, premium?, value×0–2, more…
//   top      highest score
//   premium  best good match that costs more than the top pick
//   value    good match (≥85 % of top score) cheaper than the top pick
//   more     next highest scores, up to 6 drinks in total
export type Pick = 'top' | 'premium' | 'value' | 'more';

// One row of the "needs vs has" table: one fired rule.
export interface NeedRow {
  rule: string;                       // rule id
  label: string;                      // short criterion, e.g. "Acidity", "Alcohol", "Tannin", "Food match"
  need: string;                       // the rule's "because" text
  cells: { value: string; ok: boolean }[];   // one per drink, same order as drinks
}

export type RankResponse =
  | { status: 'clarify'; question: string; jev: JevReading | null }
  | { status: 'ok'; jev: JevReading; drinks: Drink[]; needs: NeedRow[] }
  | { status: 'error'; message: string };
