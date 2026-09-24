import { meta, clusters, savings, blockedByRule, uomConflicts } from './data'

/*
 * Every analytic on the dashboard and analytics screens, derived from
 * results.json in the browser. Nothing here is typed in by hand: change the
 * pipeline output and every chart moves with it.
 */

export const CPSES = meta.cpses || []

export const CATEGORIES = [...new Set(clusters.map((c) => c.category))].sort()

const inFilter = (c, f = {}) =>
  (!f.category || c.category === f.category) &&
  (!f.cpse || (c.members || []).some((m) => m.cpse === f.cpse))

/* Per company: how many records it holds, how many national codes those
   collapse to, how many are repeats INSIDE the company (the Phase 1 win, no
   data sharing needed) and how many items it shares with other companies (the
   Phase 2 win, joint buying). */
export function perCpse(filter = {}) {
  return CPSES.map((cpse) => {
    let records = 0, codes = 0, inside = 0, shared = 0
    for (const c of clusters) {
      if (filter.category && c.category !== filter.category) continue
      const mine = (c.members || []).filter((m) => m.cpse === cpse).length
      if (!mine) continue
      records += mine
      codes += 1
      inside += mine - 1
      if ((c.cpses || []).length > 1) shared += 1
    }
    const spend = savings
      .filter((s) => !filter.category || s.category === filter.category)
      .reduce((sum, s) => sum + (s.cpses.find((x) => x.cpse === cpse)?.value || 0), 0)
    return { cpse, records, codes, inside, shared, spend }
  })
}

export function byCategory(filter = {}) {
  const out = {}
  for (const c of clusters) {
    if (!inFilter(c, filter)) continue
    const k = c.category
    out[k] ??= { category: k, codes: 0, records: 0, unspsc: c.unspsc_name }
    out[k].codes += 1
    out[k].records += filter.cpse
      ? (c.members || []).filter((m) => m.cpse === filter.cpse).length
      : (c.members || []).length
  }
  return Object.values(out).sort((a, b) => b.records - a.records)
}

export function outcomes() {
  const refused = Object.values(blockedByRule || {}).reduce((s, n) => s + n, 0)
  return [
    { key: 'auto', label: 'Merged automatically', value: meta.auto_merged || 0, tone: 'good' },
    { key: 'review', label: 'Sent to a human', value: meta.review_pending || 0, tone: 'warn' },
    { key: 'blocked', label: 'Refused by a safety rule', value: refused, tone: 'danger' },
  ]
}

export function refusals() {
  return Object.entries(blockedByRule || {})
    .map(([rule, value]) => ({ label: rule.replace(/_/g, ' '), value }))
    .sort((a, b) => b.value - a.value)
}

/* Price across companies for each item bought by two or more. */
export function priceSpread(filter = {}) {
  return savings
    .filter((s) => !filter.category || s.category === filter.category)
    .filter((s) => !filter.cpse || s.cpses.some((x) => x.cpse === filter.cpse))
    .map((s) => ({
      code: s.national_code,
      label: s.description,
      suppressed: s.benchmark_suppressed,
      min: s.best_price,
      max: s.worst_price,
      spread: s.price_spread_pct,
      saving: s.saving_realistic,
      points: s.cpses.map((x) => ({ cpse: x.cpse, price: x.avg_price, qty: x.qty })),
    }))
    .sort((a, b) => (b.saving || 0) - (a.saving || 0))
}

/* Unit spellings that disagree inside one company - a problem that needs no
   other company's data to fix. */
export function unitConflictsByCpse() {
  const out = Object.fromEntries(CPSES.map((c) => [c, 0]))
  for (const c of uomConflicts || []) {
    for (const x of c.intra_cpse || []) {
      const who = typeof x === 'string' ? x : x.cpse
      if (who in out) out[who] += 1
    }
  }
  return CPSES.map((cpse) => ({ label: cpse, value: out[cpse] }))
}

export function totals(filter = {}) {
  const rows = perCpse(filter)
  const records = filter.cpse
    ? rows.find((r) => r.cpse === filter.cpse)?.records || 0
    : clusters.filter((c) => inFilter(c, filter)).reduce((s, c) => s + (c.members || []).length, 0)
  const codes = clusters.filter((c) => inFilter(c, filter)).length
  return { records, codes, duplicates: Math.max(0, records - codes) }
}
