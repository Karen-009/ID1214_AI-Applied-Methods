import { useEffect, useRef, useState } from 'react';
import type { Drink, JevReading, NeedRow, Pick, RankResponse } from './types';

const PICK_LABEL: Record<Pick, string> = {
  top: 'Top pick',
  premium: 'Premium pick',
  value: 'Good value',
  more: 'Also good',
};

type OkResult = Extract<RankResponse, { status: 'ok' }>;
type State =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ok'; data: OkResult }
  | { kind: 'clarify'; question: string; jev: JevReading | null }
  | { kind: 'error'; message: string };

const kr = (n: number) => (Number.isInteger(n) ? `${n} kr` : `${n.toFixed(2)} kr`);
const ml = (n: number) => `${n} ml`;
const pct = (n: number) => `${n.toFixed(1)} %`;

function verdict(drinks: Drink[], needs: NeedRow[]): string {
  if (drinks.length === 0) return '';
  const allOk = drinks.map((_, i) => needs.every((r) => r.cells[i]?.ok));
  const parts: string[] = [];
  const nOk = allOk.filter(Boolean).length;
  if (needs.length === 0) parts.push('No rule fired strongly, so the order is a close call.');
  else if (nOk === drinks.length) parts.push(`All ${drinks.length} meet every need, so the order comes down to small differences in score.`);
  else parts.push(`${nOk} of ${drinks.length} meet every need.`);
  const top = drinks[0];
  if (!top.inStock) {
    const alt = drinks.slice(1).find((d) => d.inStock);
    parts.push(`${top.name} has to be ordered${alt ? `; ${alt.name} is in the regular range` : ''}.`);
  }
  const value = drinks.find((d) => d.pick === 'value');
  if (value) {
    parts.push(`${value.name} is the best value: almost as good a match for ${kr(+(top.price - value.price).toFixed(2))} less.`);
  }
  return parts.join(' ');
}

function clockLine(d: Drink) {
  const c = d.clocks;
  const bits: string[] = [];
  if (c.sweetness != null && c.sweetness >= 4) bits.push(`Sweetness ${c.sweetness}`);
  if (c.body != null) bits.push(`Body ${c.body}`);
  if (c.tannin != null && d.type === 'wine') bits.push(`Tannin ${c.tannin}`);
  if (c.bitter != null && d.type === 'beer') bits.push(`Bitter ${c.bitter}`);
  if (c.acidity != null) bits.push(`Acidity ${c.acidity}`);
  if (!d.inStock) bits.push('Order item');
  return bits.join(' · ');
}

function Bottle({ d, className }: { d: Drink; className?: string }) {
  return (
    <a href={d.url} target="_blank" rel="noopener" title={`Open ${d.name} on systembolaget.se`} className={className} style={{ display: 'block', width: 'max-content' }}>
      {d.imageUrl ? <img src={d.imageUrl} alt={`${d.name} on systembolaget.se`} loading="lazy" /> : <div className="noimg" aria-label={d.name} />}
    </a>
  );
}

function Desktop({ data }: { data: OkResult }) {
  const { drinks, needs } = data;
  return (
    <div className="desktop">
      <table className="needs">
        <colgroup>
          <col style={{ width: drinks.length > 4 ? 230 : 280 }} />
          {drinks.map((d) => <col key={d.productNumber} />)}
        </colgroup>
        <thead>
          <tr>
            <th className="need" />
            {drinks.map((d, i) => (
              <th key={d.productNumber} className={`head${i === 0 ? ' first' : ''}`}>
                <span className={`pick pick-${d.pick}`}>{PICK_LABEL[d.pick]}</span>
                <Bottle d={d} className="bottle" />
                <a className="name" href={d.url} target="_blank" rel="noopener" title={d.name}>{d.name}</a>
                <div className="short">{d.origin}</div>
                <div className="hprice">{kr(d.price)} <span>{ml(d.volumeMl)}</span></div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {needs.map((r) => (
            <tr key={r.rule}>
              <td className="need"><div className="k">{r.label}</div>{r.need}</td>
              {r.cells.map((c, i) => (
                <td key={i} className={`cell${i === 0 ? ' first' : ''}`}>
                  {c.value}
                  <span className={`mark${c.ok ? '' : ' no'}`}>{c.ok ? '✓' : '✗'}</span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="verdict">{verdict(drinks, needs)}</p>
      <span className="foot">
        Needs come from Jev's taste scores and the pairing rules. Clock values are Systembolaget's 1–12 scale. Click a bottle to open it on systembolaget.se.
      </span>
    </div>
  );
}

function Phone({ data }: { data: OkResult }) {
  const [top, ...rest] = data.drinks;
  const steps = [...new Set(data.needs.map((r) => r.need))];
  if (!top) return null;
  return (
    <div className="phone">
      <section className="top">
        <Bottle d={top} />
        <div className="body">
          <span className="meta">{PICK_LABEL[top.pick]} · {top.origin} · {top.style}</span>
          <span className="tname">{top.name}</span>
          {top.reasons[0] && <span className="why">{top.reasons.slice(0, 2).join(' ')}</span>}
          <div className="nums"><b>{kr(top.price)}</b><span>{ml(top.volumeMl)}</span><span>{pct(top.abv)}</span></div>
          <span className="meta">{clockLine(top)}</span>
          <a className="nr" style={{ marginTop: 0 }} href={top.url} target="_blank" rel="noopener">Nr {top.productNumber} on systembolaget.se ↗</a>
        </div>
      </section>
      {rest.map((d) => (
        <div className="row" key={d.productNumber}>
          <span className="n">{d.rank}</span>
          <Bottle d={d} />
          <div style={{ minWidth: 0 }}>
            <div className="rname">{d.name}</div>
            <div className="rwhy"><span className={`pick pick-${d.pick}`}>{PICK_LABEL[d.pick]}</span> · {d.style} · {pct(d.abv)}{d.inStock ? '' : ' · order item'}</div>
          </div>
          <div className="rprice"><div>{kr(d.price)}</div><div>{ml(d.volumeMl)}</div></div>
        </div>
      ))}
      {steps.length > 0 && (
        <details className="how">
          <summary>How it ranked</summary>
          <ol>{steps.map((s) => <li key={s}>{s}</li>)}</ol>
        </details>
      )}
      <div className="pfoot">Tap a bottle to open it on systembolaget.se. Prices, clocks and photos from Systembolaget; scores from Jev ({data.jev.backend}).</div>
    </div>
  );
}

export default function App() {
  const initial = new URLSearchParams(location.search).get('dish') ?? '';
  const [dish, setDish] = useState(initial);
  const [state, setState] = useState<State>({ kind: 'idle' });
  const reqId = useRef(0);

  async function rank(text: string) {
    const q = text.trim();
    if (!q) return;
    const id = ++reqId.current;
    setState({ kind: 'loading' });
    const url = new URL(location.href);
    url.searchParams.set('dish', q);
    history.replaceState(null, '', url);
    try {
      const res = await fetch('/api/rank', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dish: q }),
      });
      const data = (await res.json()) as RankResponse;
      if (id !== reqId.current) return;
      if (data.status === 'ok') setState({ kind: 'ok', data });
      else if (data.status === 'clarify') setState({ kind: 'clarify', question: data.question, jev: data.jev });
      else setState({ kind: 'error', message: data.message });
    } catch {
      if (id !== reqId.current) return;
      setState({ kind: 'error', message: 'Could not reach the pairing server. Is python server.py running?' });
    }
  }

  useEffect(() => {
    if (initial) rank(initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="page">
      <div className="wrap">
        <form className="form" onSubmit={(e) => { e.preventDefault(); rank(dish); }}>
          <label htmlFor="dish">What are you eating?</label>
          <div className="field">
            <input
              id="dish"
              type="text"
              value={dish}
              onChange={(e) => setDish(e.target.value)}
              placeholder="Describe the dish, e.g. lamb stew with rosemary"
              autoComplete="off"
              enterKeyHint="go"
              autoFocus
            />
            <button type="submit" disabled={state.kind === 'loading'} aria-label="Rank drinks">
              <span className="label">{state.kind === 'loading' ? 'Ranking…' : 'Rank drinks →'}</span>
              <span className="arrow">→</span>
            </button>
          </div>
          <div className="hintrow">
            <span className="long">Write it the way you'd say it: main ingredient, how it's cooked, the sauce.</span>
            <span className="shorthint">Ingredient, how it's cooked, the sauce.</span>
          </div>
        </form>

        {state.kind === 'idle' && <p className="status">Type a dish and press Enter. You'll get up to six drinks from Systembolaget's range, with the reasons for each.</p>}
        {state.kind === 'loading' && <p className="status">Reading the dish and checking the rules…</p>}
        {state.kind === 'error' && <p className="status error">{state.message}</p>}
        {state.kind === 'clarify' && (
          <p className="status"><strong>Need a bit more:</strong> {state.question}</p>
        )}
        {state.kind === 'ok' && state.data.drinks.length === 0 && <p className="status">No drinks passed the rules for this dish.</p>}
        {state.kind === 'ok' && state.data.drinks.length > 0 && (
          <>
            <Desktop data={state.data} />
            <Phone data={state.data} />
          </>
        )}
      </div>
    </div>
  );
}
