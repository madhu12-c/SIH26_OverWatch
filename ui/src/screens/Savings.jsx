import { motion } from 'framer-motion'
import { savings, savingsSummary } from '../lib/data'
import { rupees, rupeesExact, num } from '../lib/format'
import { SectionTitle, Stat } from '../components/Primitives'

/*
 * Screen 05 - where a data-cleaning project becomes a money project.
 *
 * Two rules are visible in this screen and both are deliberate:
 *   BOTH FIGURES. Best-observed-price is the theoretical maximum. A
 *   procurement person knows nobody achieves it, so we show the conservative
 *   number too - which is what makes the optimistic one credible.
 *   BENCHMARK, NOT ATTRIBUTION. A company sees that a better price exists and
 *   how far above it they are. Not who achieved it.
 */

export default function Savings() {
  const items = savings || []

  return (
    <div className="max-w-4xl mx-auto">
      <SectionTitle
        eyebrow="Demand aggregation"
        title="The same item, bought separately, at different prices"
        sub="Once records resolve to one national code, purchase history can be grouped across companies — and the gap becomes visible for the first time."
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Stat value={savingsSummary.multi_cpse_items} label="Bought by 2+ CPSEs" />
        <Stat
          value={(savingsSummary.total_spend || 0) / 1e7}
          decimals={2} prefix="₹" suffix=" cr"
          label="Total spend"
        />
        <Stat
          value={(savingsSummary.saving_upper || 0) / 1e5}
          decimals={1} prefix="₹" suffix=" L"
          label="Upper bound" sub="if all achieved best price"
        />
        <Stat
          value={(savingsSummary.saving_realistic || 0) / 1e5}
          decimals={1} prefix="₹" suffix=" L"
          label="Realistic" sub="at 40% capture" tone="good"
        />
      </div>

      <div className="space-y-4">
        {items.slice(0, 6).map((item, idx) => (
          <motion.div
            key={item.national_code}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.08, duration: 0.35 }}
            className="card p-5"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2 mb-4">
              <div className="min-w-0">
                <p className="font-mono text-[11.5px] text-accent">{item.national_code}</p>
                <p className="font-mono text-[13px] mt-0.5 break-words">{item.description}</p>
              </div>
              <div className="text-right shrink-0">
                <p className="label">saving</p>
                <p className="text-[20px] font-semibold text-good tnum leading-none">
                  {rupees(item.saving_realistic)}
                </p>
                <p className="text-[11px] text-ink-faint mt-0.5">
                  {rupees(item.saving_upper)} upper
                </p>
              </div>
            </div>

            <div className="scroll-x">
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="border-b border-line">
                    <th className="label text-left py-1.5 pr-4">CPSE</th>
                    <th className="label text-right py-1.5 pr-4">Units</th>
                    <th className="label text-right py-1.5 pr-4">Avg price</th>
                    <th className="label text-right py-1.5">Value</th>
                  </tr>
                </thead>
                <tbody className="font-mono text-[12.5px]">
                  {item.cpses.map((c) => {
                    const best = c.avg_price === item.best_price
                    return (
                      <tr key={c.cpse} className="border-b border-line-soft last:border-0">
                        <td className={`py-1.5 pr-4 ${best ? 'text-good' : ''}`}>
                          {c.cpse}{best && <span className="ml-1.5 text-[10px]">best</span>}
                        </td>
                        <td className="py-1.5 pr-4 text-right tnum">{num(c.qty)}</td>
                        <td className={`py-1.5 pr-4 text-right tnum ${best ? 'text-good' : ''}`}>
                          {rupeesExact(c.avg_price)}
                        </td>
                        <td className="py-1.5 text-right tnum text-ink-dim">{rupees(c.value)}</td>
                      </tr>
                    )
                  })}
                  <tr className="border-t border-line">
                    <td className="py-1.5 pr-4 text-ink-dim">TOTAL</td>
                    <td className="py-1.5 pr-4 text-right tnum">{num(item.total_qty)}</td>
                    <td className="py-1.5 pr-4 text-right text-ink-faint text-[11.5px]">
                      spread {item.price_spread_pct}%
                    </td>
                    <td className="py-1.5 text-right tnum">{rupees(item.total_value)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="card p-4 mt-5 border-warn/30">
        <p className="text-[13px] text-ink-dim leading-relaxed">
          <span className="text-warn font-medium">Both numbers, always.</span>{' '}
          The upper bound assumes every company achieves the best price anyone in
          the group got — which never happens. Volunteering the conservative
          figure is what makes the optimistic one believable.
          {savingsSummary.benchmark_suppressed > 0 && (
            <>
              {' '}Benchmarks are suppressed below {savingsSummary.k_anonymity} CPSEs,
              because with two participants the minimum price <em>is</em> the other
              party's price.
            </>
          )}
        </p>
      </div>
    </div>
  )
}
