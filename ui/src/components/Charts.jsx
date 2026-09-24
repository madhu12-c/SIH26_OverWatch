import { motion } from 'framer-motion'
import { CountUp } from './Primitives'

/*
 * Charts drawn by hand in SVG and CSS - no chart library, so the single-file
 * build stays small, works offline, and every colour comes from the theme
 * tokens (and so follows high-contrast mode).
 */

const TONE = {
  accent: 'rgb(var(--accent))',
  good: 'rgb(var(--good))',
  warn: 'rgb(var(--warn))',
  danger: 'rgb(var(--danger))',
  saffron: 'rgb(var(--saffron))',
  gov: 'rgb(var(--gov-soft))',
  faint: 'rgb(var(--ink-faint))',
}
const SERIES = ['accent', 'saffron', 'good', 'danger', 'warn', 'faint']

/* Card with a title bar, the frame every chart sits in. */
export function ChartCard({ title, sub, right, children, className = '' }) {
  return (
    <section className={`card flex flex-col ${className}`}>
      <div className="flex items-start justify-between gap-3 px-5 pt-4 pb-3 border-b border-line-soft">
        <div className="min-w-0">
          <h3 className="text-[15px] font-bold text-heading leading-snug">{title}</h3>
          {sub && <p className="text-[12px] text-ink-faint mt-0.5 leading-snug">{sub}</p>}
        </div>
        {right}
      </div>
      <div className="p-5 flex-1">{children}</div>
    </section>
  )
}

/* Horizontal bars - ranked lists: refusals by rule, codes by category. */
export function BarList({ data, tone = 'accent', format = (v) => v, max }) {
  const top = max ?? Math.max(1, ...data.map((d) => d.value))
  return (
    <div className="space-y-2.5">
      {data.map((d, i) => (
        <div key={d.label} className="grid grid-cols-[minmax(0,9.5rem)_1fr_auto] items-center gap-3">
          <span className="text-[12.5px] text-ink-dim truncate first-letter:uppercase" title={d.label}>{d.label}</span>
          <div className="h-2.5 rounded-sm bg-base-raised overflow-hidden">
            <motion.div
              className="h-full rounded-sm"
              style={{ background: TONE[d.tone || tone] }}
              initial={{ width: 0 }}
              animate={{ width: `${(d.value / top) * 100}%` }}
              transition={{ delay: 0.1 + i * 0.05, duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
            />
          </div>
          <span className="font-mono text-[12.5px] tnum text-ink text-right min-w-[3ch]">{format(d.value)}</span>
        </div>
      ))}
      {!data.length && <p className="text-[13px] text-ink-faint">Nothing to show for this filter.</p>}
    </div>
  )
}

/* Grouped columns - one group per company, one bar per measure. */
export function Columns({ groups, series, height = 190, format = (v) => v }) {
  // Round the axis to a step of 1, 2 or 5 x 10^n, so the ticks read 0 10 20
  // 30 40 rather than 0 8 16 23 31.
  const peak = Math.max(1, ...groups.flatMap((g) => series.map((s) => g[s.key] || 0)))
  const raw = peak / 4
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw)
  const max = step * 4
  const ticks = [0, 1, 2, 3, 4].map((k) => k * step)
  return (
    <div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-3">
        {series.map((s, i) => (
          <span key={s.key} className="flex items-center gap-1.5 text-[12px] text-ink-dim">
            <span className="w-2.5 h-2.5 rounded-sm" style={{ background: TONE[s.tone || SERIES[i]] }} />
            {s.label}
          </span>
        ))}
      </div>
      <div className="relative flex gap-2" style={{ height }}>
        <div className="flex flex-col-reverse justify-between text-[10.5px] font-mono text-ink-faint tnum pr-1 pb-5">
          {ticks.map((t) => <span key={t} className="leading-none">{format(t)}</span>)}
        </div>
        <div className="relative flex-1 flex items-end justify-around gap-2 border-b border-line pb-0">
          {ticks.slice(1).map((t) => (
            <span key={t} className="absolute inset-x-0 border-t border-dashed border-line-soft"
                  style={{ bottom: `${(t / max) * (height - 20)}px` }} />
          ))}
          {groups.map((g, gi) => (
            <div key={g.label} className="relative flex flex-col items-center flex-1 max-w-[110px]">
              <div className="flex items-end gap-1 w-full justify-center" style={{ height: height - 20 }}>
                {series.map((s, si) => {
                  const v = g[s.key] || 0
                  return (
                    <motion.div
                      key={s.key}
                      title={`${g.label} · ${s.label}: ${format(v)}`}
                      className="w-full max-w-[22px] rounded-t-sm relative group"
                      style={{ background: TONE[s.tone || SERIES[si]] }}
                      initial={{ height: 0 }}
                      animate={{ height: `${(v / max) * (height - 20)}px` }}
                      transition={{ delay: 0.1 + gi * 0.06 + si * 0.03, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                    >
                      <span className="absolute -top-4 left-1/2 -translate-x-1/2 text-[10px] font-mono tnum text-ink-dim">
                        {v ? format(v) : ''}
                      </span>
                    </motion.div>
                  )
                })}
              </div>
              <span className="absolute -bottom-5 text-[11.5px] font-semibold text-ink-dim">{g.label}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="h-5" />
    </div>
  )
}

/* Donut - a whole split into parts. The centre carries the total. */
export function Donut({ data, size = 170, thickness = 26, centre, centreLabel }) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1
  const r = (size - thickness) / 2
  const c = 2 * Math.PI * r
  // Where each slice starts, worked out before rendering rather than by
  // mutating a running total inside the map.
  const starts = data.reduce((acc, d, i) => [...acc, i ? acc[i - 1] + (data[i - 1].value / total) * c : 0], [])
  return (
    <div className="flex flex-wrap items-center gap-5">
      <div className="relative shrink-0" style={{ width: size, height: size }}>
        <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgb(var(--base-raised))" strokeWidth={thickness} />
          {data.map((d, i) => {
            const len = (d.value / total) * c
            return (
              <motion.circle
                key={d.label}
                cx={size / 2} cy={size / 2} r={r} fill="none"
                stroke={TONE[d.tone || SERIES[i]]} strokeWidth={thickness}
                strokeDasharray={`${Math.max(0, len - 2)} ${c}`}
                strokeDashoffset={-starts[i]}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.15 + i * 0.12, duration: 0.4 }}
              />
            )
          })}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-[24px] font-bold text-heading leading-none tnum">
            {typeof centre === 'number' ? <CountUp to={centre} /> : centre}
          </span>
          {centreLabel && <span className="text-[11px] text-ink-faint mt-1 max-w-[90px] leading-tight">{centreLabel}</span>}
        </div>
      </div>
      <ul className="space-y-2 min-w-[210px] flex-1">
        {data.map((d, i) => (
          <li key={d.label} className="flex items-center gap-2.5 text-[12.5px]">
            <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: TONE[d.tone || SERIES[i]] }} />
            <span className="text-ink-dim flex-1 leading-snug">{d.label}</span>
            <span className="font-mono tnum text-ink">{d.value}</span>
            <span className="font-mono tnum text-ink-faint w-10 text-right">{Math.round((d.value / total) * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/* Price range per item: a line from the best to the worst price, one dot
   per company. Where a company may not see another's price, the dot is
   drawn but not named - the benchmark without the attribution. */
export function Dumbbell({ rows, format, nameOf }) {
  return (
    <div className="space-y-4">
      {rows.map((r, i) => {
        const span = Math.max(1, r.max - r.min)
        const pos = (v) => `${((v - r.min) / span) * 100}%`
        return (
          <div key={r.code}>
            <div className="flex items-baseline justify-between gap-3 mb-1.5">
              <span className="text-[12.5px] text-ink truncate font-mono" title={r.label}>{r.label}</span>
              <span className="text-[11.5px] font-semibold text-danger shrink-0 tnum">
                {r.suppressed ? 'benchmark hidden' : `${r.spread}% spread`}
              </span>
            </div>
            {r.suppressed ? (
              <div className="h-7 rounded-sm bg-base-raised border border-dashed border-line flex items-center px-3
                              text-[11.5px] text-ink-faint">
                Fewer than 3 companies buy this item — the best price would reveal another company's price.
              </div>
            ) : (
              <div className="relative h-7 mx-2">
                <div className="absolute top-1/2 inset-x-0 h-px bg-line" />
                <motion.div
                  className="absolute top-1/2 h-1.5 -mt-[3px] rounded-full bg-danger/25"
                  style={{ left: 0 }}
                  initial={{ width: 0 }}
                  animate={{ width: '100%' }}
                  transition={{ delay: 0.1 + i * 0.05, duration: 0.5 }}
                />
                {r.points.map((p) => {
                  const named = nameOf(p.cpse)
                  const best = p.price === r.min
                  return (
                    <span key={p.cpse}
                          title={named ? `${p.cpse} ${format(p.price)}` : 'another CPSE'}
                          className={`absolute top-1/2 -translate-x-1/2 -translate-y-1/2 block w-3.5 h-3.5
                                      rounded-full border-2 border-base-card
                                      ${named ? (best ? 'bg-good' : 'bg-accent') : 'bg-ink-faint'}`}
                          style={{ left: pos(p.price) }} />
                  )
                })}
              </div>
            )}
            {!r.suppressed && <PriceNote r={r} format={format} nameOf={nameOf} />}
          </div>
        )
      })}
    </div>
  )
}

function PriceNote({ r, format, nameOf }) {
  const best = r.points.find((p) => p.price === r.min)
  const worst = r.points.find((p) => p.price === r.max)
  const own = r.points.find((p) => nameOf(p.cpse) === 'own')
  const who = (p) => (nameOf(p.cpse) ? p.cpse : 'another CPSE')
  return (
    <p className="mt-1 text-[11.5px] text-ink-faint flex flex-wrap gap-x-4 gap-y-0.5">
      <span><span className="text-good font-semibold">Best</span> {who(best)} {format(best.price)}</span>
      <span><span className="text-danger font-semibold">Highest</span> {who(worst)} {format(worst.price)}</span>
      {own && <span><span className="text-accent font-semibold">Yours</span> {format(own.price)}</span>}
    </p>
  )
}
