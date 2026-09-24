import { useState } from 'react'
import { motion } from 'framer-motion'
import { uomSummary, uomFamilies, uomConflicts, uom } from '../lib/data'
import { SectionTitle, Stat, Chip, CountUp } from '../components/Primitives'

/*
 * Screen 07 - units of measurement.
 *
 * The PS Background names units explicitly, alongside cryptic descriptions, as
 * a reason two masters cannot be compared. It is a small feature with an
 * outsized effect: comparing a price across two records is meaningless until
 * both sides agree what one unit IS.
 *
 * The argument on this screen is the FOLD - six spellings collapsing into one
 * unit. Showing the six side by side is what makes it land; a sentence saying
 * "we normalise units" does not.
 */

/* One canonical unit, with every raw spelling that folds into it. The arrow
   carries the argument, so the variants and the result sit on one line rather
   than in two stacked lists. */
function Family({ fam, delay }) {
  const total = fam.variants.reduce((n, v) => n + v.count, 0)
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35 }}
      className="card p-4"
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="label">{fam.label}</span>
        <span className="ml-auto text-[11px] text-ink-faint font-mono tnum">
          {total} records
        </span>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex flex-wrap gap-1.5 flex-1 min-w-0">
          {fam.variants.map((v, i) => (
            <motion.span
              key={v.raw}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: delay + 0.05 * i, duration: 0.25 }}
              className="inline-flex items-baseline gap-1 px-2 py-1 rounded-md
                         bg-base-raised border border-line-soft"
            >
              <span className="font-mono text-[12px] text-ink-dim">{v.raw}</span>
              <span className="font-mono text-[10px] text-ink-faint tnum">{v.count}</span>
            </motion.span>
          ))}
        </div>

        <svg width="22" height="12" viewBox="0 0 22 12" className="shrink-0 text-line"
             aria-hidden="true">
          <path d="M0 6h18M14 2l4 4-4 4" fill="none" stroke="currentColor"
                strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>

        <div className="shrink-0 px-3 py-1.5 rounded-lg bg-accent-dim border border-accent/25">
          <span className="font-mono text-[17px] font-semibold text-accent">
            {fam.canonical}
          </span>
        </div>
      </div>
    </motion.div>
  )
}

export default function Units() {
  const [open, setOpen] = useState(uomConflicts?.[0]?.national_code ?? null)

  if (!uomFamilies.length) {
    return (
      <div className="max-w-5xl mx-auto">
        <SectionTitle
          eyebrow="Units of measurement"
          title="Not generated yet"
          sub="Run python src/uom.py, then python src/results.py."
        />
      </div>
    )
  }

  const s = uomSummary
  const autoResolvable = (s.codes_with_conflict ?? 0) - (s.cross_family_conflicts ?? 0)

  return (
    <div className="max-w-5xl mx-auto">
      <SectionTitle
        eyebrow="Units of measurement"
        title={`${s.variants_seen} spellings for ${s.canonical_units} actual units`}
        sub="Nobody was wrong. There was never an enforced cataloguing standard, so every storekeeper wrote what they were used to. Until these agree, no price across two CPSEs can be compared."
      />

      <div className="grid sm:grid-cols-2 gap-3 mb-3">
        {uomFamilies.map((f, i) => (
          <Family key={f.canonical} fam={f} delay={0.05 + i * 0.1} />
        ))}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <Stat value={s.codes_with_conflict} label="codes affected"
              sub={`of ${s.codes_total} national codes`} tone="warn" />
        <Stat value={autoResolvable} label="auto-resolvable"
              sub="same unit, different spelling" tone="good" />
        <Stat value={s.intra_cpse_conflicts} label="inside one CPSE"
              sub="no coordination needed" tone="accent" />
        <Stat value={s.cross_family_conflicts} label="need a human"
              sub="disagree across unit families"
              tone={s.cross_family_conflicts ? 'danger' : 'good'} />
      </div>

      {/* The abstention. A dictionary that guesses is worse than one that
          stops, because the guess is invisible once it is inside an issued
          national code - and volunteering the limit is what makes the rest
          of the screen believable. */}
      {(uom.ambiguous?.length > 0 || uom.unrecognised?.length > 0) && (
        <div className="card p-4 mb-6 border-warn/30 bg-warn-bg/40">
          <div className="flex items-center gap-2 mb-2">
            <Chip tone="warn">not folded</Chip>
            <span className="text-[12.5px] font-medium text-ink">
              Ambiguous — a human decides
            </span>
          </div>
          {uom.ambiguous?.map((a) => (
            <p key={a.raw} className="text-[12.5px] text-ink-dim leading-relaxed">
              <span className="font-mono text-ink font-semibold">{a.raw}</span>
              {' '}appears {a.count}× and means {a.note}. It reads as{' '}
              <span className="font-mono">{a.readings[0]}</span> here only because it
              sits beside METER on pipe. Picking one silently would put a wrong unit
              inside every national code that carries it.
            </p>
          ))}
          {uom.unrecognised?.length > 0 && (
            <p className="text-[12px] text-ink-faint mt-2">
              unrecognised: {uom.unrecognised.map((u) => u.raw).join(', ')}
            </p>
          )}
        </div>
      )}

      <div className="mb-3 flex items-baseline gap-2">
        <span className="label">Conflicts by national code</span>
        <span className="text-[11px] text-ink-faint">worst first</span>
      </div>

      <div className="space-y-2">
        {uomConflicts.map((c, idx) => {
          const isOpen = open === c.national_code
          return (
            <motion.div
              key={c.national_code}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(idx * 0.03, 0.3), duration: 0.3 }}
              className="card overflow-hidden"
            >
              <button
                onClick={() => setOpen(isOpen ? null : c.national_code)}
                className="w-full text-left px-4 py-3 hover:bg-base-raised transition-colors"
              >
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span className="font-mono text-[11.5px] text-accent">
                    {c.national_code}
                  </span>
                  <Chip tone={c.cross_family ? 'danger' : 'good'}>
                    {c.variant_count} spellings → {c.resolved_to ?? 'human'}
                  </Chip>
                  {c.intra_cpse?.length > 0 && (
                    <span className="text-[11px] text-warn">
                      {c.intra_cpse.join(', ')} disagree{c.intra_cpse.length === 1 ? 's' : ''} with
                      {c.intra_cpse.length === 1 ? ' itself' : ' themselves'}
                    </span>
                  )}
                </div>
                <p className="font-mono text-[12.5px] text-ink-dim break-words">
                  {c.description}
                </p>
              </button>

              {isOpen && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  transition={{ duration: 0.25 }}
                  className="border-t border-line-soft"
                >
                  <div className="scroll-x">
                    <table className="w-full text-[12.5px]">
                      <thead>
                        <tr className="bg-base-raised">
                          <th className="text-left py-2 px-4 label">spelling</th>
                          <th className="text-left py-2 pr-4 label">records</th>
                          <th className="text-left py-2 pr-4 label">used by</th>
                        </tr>
                      </thead>
                      <tbody className="font-mono">
                        {c.variants.map((v) => (
                          <tr key={v.raw} className="border-t border-line-soft">
                            <td className="py-2 px-4 text-ink whitespace-nowrap">{v.raw}</td>
                            <td className="py-2 pr-4 text-ink-faint tnum">{v.count}</td>
                            <td className="py-2 pr-4 text-ink-dim">{v.cpses.join(', ')}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="px-4 py-2.5 text-[11.5px] text-ink-faint border-t border-line-soft">
                    {c.cross_family
                      ? 'These disagree across unit families, which is a data error rather than a spelling difference. A human decides.'
                      : <>Resolved to <span className="font-mono text-ink">{c.resolved_to}</span> — the standard abbreviation, not the most frequent spelling. Standardising to whichever form happens to be commonest means the answer changes the next time a CPSE uploads.</>}
                  </p>
                  {c.pack_size_flag && (
                    <p className="px-4 py-2.5 text-[11.5px] text-danger border-t border-line-soft bg-danger-bg/40">
                      Possible pack-size mismatch: {c.pack_size_flag.low.cpse} pays ₹
                      {c.pack_size_flag.low.price} and {c.pack_size_flag.high.cpse} pays ₹
                      {c.pack_size_flag.high.price} — {c.pack_size_flag.ratio}× apart for the
                      same stated unit. One side is probably pricing a box.
                    </p>
                  )}
                </motion.div>
              )}
            </motion.div>
          )
        })}
      </div>

      <p className="mt-6 text-[12.5px] text-ink-dim leading-relaxed max-w-2xl">
        <CountUp to={s.intra_cpse_conflicts} /> of these sit inside a single company,
        which means that company can fix them without asking anyone. That is the
        cheapest cleanup available anywhere in this dataset.
      </p>
    </div>
  )
}
