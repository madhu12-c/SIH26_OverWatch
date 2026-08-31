import { motion } from 'framer-motion'
import { meta, blockedByRule, savingsSummary } from '../lib/data'
import { rupees, fieldLabel } from '../lib/format'
import { Stat, SectionTitle, CountUp } from '../components/Primitives'

/* Screen 01 - the scale of the problem, and what came out the other side.
   Also the per-CPSE dashboard view: a company sees ITS OWN numbers and a
   group benchmark, never another company's raw data. */

export default function Overview() {
  const rules = Object.entries(blockedByRule || {})
  const totalBlocked = rules.reduce((s, [, n]) => s + n, 0)

  return (
    <div className="max-w-5xl mx-auto">
      <SectionTitle
        eyebrow={`${(meta.cpses || []).join(' · ')}`}
        title="One Nation, One Material Code"
        sub="Material masters from five CPSEs, resolved to a single national code per physical item — with every original code retained and mapped."
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <Stat value={meta.records} label="Raw material codes" sub="across 5 CPSEs" />
        <Stat value={meta.unique_items} label="Unique materials" tone="good" />
        <Stat
          value={(meta.duplication || 0) * 100}
          decimals={1}
          suffix="%"
          label="Duplication eliminated"
          tone="good"
        />
        <Stat
          value={(savingsSummary.saving_realistic || 0) / 1e5}
          decimals={1}
          prefix="₹"
          suffix=" L"
          label="Saving identified"
          sub="at 40% capture"
        />
      </div>

      {/* One panel rather than three cards. These three numbers are one fact -
          what the pipeline did with every candidate - and splitting them into
          separate cards of a different width to the row above made them read
          as unrelated. */}
      <div className="card overflow-hidden mb-6">
        <div className="px-4 pt-3 pb-2 border-b border-line-soft">
          <p className="label">Where every candidate ended up</p>
        </div>
        <div className="grid sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-line-soft">
          <Cell value={meta.auto_merged} tone="good"
                label="Auto-merged" sub="high confidence, reversible" />
          <Cell value={meta.review_pending} tone="warn"
                label="In review queue" sub="a human decides" />
          <Cell value={totalBlocked} tone="danger"
                label="Merges refused" sub="blocked by a veto field" />
        </div>
      </div>

      {/* The refusals. Everyone shows merges; nobody shows what they refused,
          and the refusals are the more convincing half. */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
        className="card p-5 mb-4"
      >
        <div className="flex items-baseline justify-between mb-4">
          <div>
            <p className="label text-danger mb-1">Safety interlock</p>
            <h3 className="text-[17px] font-semibold">What we refused to merge</h3>
          </div>
          <div className="text-[28px] font-semibold text-danger tnum leading-none">
            <CountUp to={totalBlocked} />
          </div>
        </div>

        <div className="space-y-2">
          {rules.map(([rule, n], i) => (
            <motion.div
              key={rule}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 + i * 0.06, duration: 0.3 }}
              className="flex items-center gap-3"
            >
              <span className="text-[12.5px] text-ink-dim w-40 shrink-0 truncate">
                {fieldLabel(rule)}
              </span>
              <div className="flex-1 h-1.5 rounded-full bg-base-raised overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-danger"
                  initial={{ width: 0 }}
                  animate={{ width: `${(n / Math.max(...rules.map((r) => r[1]))) * 100}%` }}
                  transition={{ delay: 0.35 + i * 0.06, duration: 0.5, ease: 'easeOut' }}
                />
              </div>
              <span className="font-mono text-[13px] tnum w-10 text-right">{n}</span>
            </motion.div>
          ))}
        </div>

        <p className="mt-4 pt-4 border-t border-line-soft text-[13.5px] text-ink-dim leading-relaxed">
          A grade or pressure-rating mismatch is a veto — an instant zero however
          well everything else agrees. In a refinery that difference is a leak,
          not a data-quality issue.
        </p>
      </motion.div>

      <div className="grid md:grid-cols-2 gap-3">
        <Panel
          title="Accuracy"
          rows={[
            ['Precision', meta.precision != null ? `${(meta.precision * 100).toFixed(1)}%` : 'run evaluate.py'],
            ['Recall', meta.recall != null ? `${(meta.recall * 100).toFixed(1)}%` : 'run evaluate.py'],
            ['Records extracted', `${meta.extracted} / ${meta.records}`],
          ]}
          note="Measured against a known answer key — which exists only because we generated the dataset. That makes the number circular, and the honest figure comes from a hand-labelled real hold-out."
        />
        <Panel
          title="Demand aggregation"
          rows={[
            ['Total spend', rupees(savingsSummary.total_spend)],
            ['Upper bound saving', rupees(savingsSummary.saving_upper)],
            ['At 40% capture', rupees(savingsSummary.saving_realistic)],
          ]}
          note={`${savingsSummary.benchmark_suppressed || 0} item(s) suppressed under k-anonymity — with fewer than 3 CPSEs the best price IS the other party's price.`}
        />
      </div>
    </div>
  )
}

function Cell({ value, label, sub, tone }) {
  const ink = { good: 'text-good', warn: 'text-warn', danger: 'text-danger' }
  const dot = { good: 'bg-good', warn: 'bg-warn', danger: 'bg-danger' }
  return (
    <div className="px-4 py-4">
      <div className="flex items-center gap-2 mb-1">
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dot[tone] || 'bg-line'}`} />
        <span className="text-[12.5px] font-medium text-ink-dim">{label}</span>
      </div>
      <div className={`text-[30px] font-semibold leading-none tracking-tight ${ink[tone] || 'text-ink'}`}>
        <CountUp to={value} />
      </div>
      {sub && <div className="mt-1.5 text-[11.5px] text-ink-faint">{sub}</div>}
    </div>
  )
}

function Panel({ title, rows, note }) {
  return (
    <div className="card p-5">
      <p className="label mb-3">{title}</p>
      <div className="space-y-2">
        {rows.map(([k, v]) => (
          <div key={k} className="flex items-baseline justify-between gap-3">
            <span className="text-[13px] text-ink-dim">{k}</span>
            <span className="font-mono text-[14px] tnum">{v}</span>
          </div>
        ))}
      </div>
      {note && (
        <p className="mt-3 pt-3 border-t border-line-soft text-[12px] text-ink-faint leading-relaxed">
          {note}
        </p>
      )}
    </div>
  )
}
