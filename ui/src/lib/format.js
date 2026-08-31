// Indian rupee formatting - lakh and crore, not million and billion. A
// ministry audience reads Rs 3.3 cr instantly and $400K not at all.
export function rupees(amount) {
  if (amount == null) return '—'
  const n = Number(amount)
  if (Math.abs(n) >= 1e7) return `₹${(n / 1e7).toFixed(2)} cr`
  if (Math.abs(n) >= 1e5) return `₹${(n / 1e5).toFixed(1)} L`
  if (Math.abs(n) >= 1e3) return `₹${(n / 1e3).toFixed(1)}k`
  return `₹${n.toFixed(0)}`
}

export function rupeesExact(amount) {
  if (amount == null) return '—'
  return '₹' + Number(amount).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

export function pct(value, digits = 1) {
  if (value == null) return '—'
  return `${(Number(value) * 100).toFixed(digits)}%`
}

export function num(value) {
  if (value == null) return '—'
  return Number(value).toLocaleString('en-IN')
}

// 25.0 reads as 25 in a specification. Trailing .0 looks like noise.
export function spec(value) {
  if (value == null || value === '') return '—'
  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : String(value)
  }
  return String(value).replace(/_/g, ' ')
}

export function fieldLabel(name) {
  return String(name).replace(/_/g, ' ')
}

// Score bands mirror scorer.py exactly. If those thresholds move, move these.
export const AUTO_MERGE = 0.90
export const REVIEW_LOW = 0.70

export function band(score) {
  if (score == null) return 'none'
  if (score >= AUTO_MERGE) return 'auto'
  if (score >= REVIEW_LOW) return 'review'
  return 'low'
}

export const bandColor = {
  auto: 'text-good',
  review: 'text-warn',
  low: 'text-ink-faint',
  none: 'text-ink-faint',
}

export const bandLabel = {
  auto: 'auto-merge',
  review: 'needs review',
  low: 'kept separate',
  none: '—',
}
