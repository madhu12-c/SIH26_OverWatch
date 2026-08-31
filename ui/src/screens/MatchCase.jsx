import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { cases } from '../lib/data'
import { CountUp, Meter, RecordCard, SectionTitle, Chip } from '../components/Primitives'
import SpecCompare from '../components/SpecCompare'

/*
 * Screen 02 - the argument. Everything else is context.
 *
 * The sequence matters more than the content. The audience has to see the
 * text score land FIRST, sit with it, and only then watch the specifications
 * agree field by field. Reveal it all at once and the point evaporates.
 */

const STEPS = [
  { at: 200, id: 'cards' },
  { at: 1400, id: 'text' },
  { at: 3200, id: 'specs' },   // deliberate pause - the text number has to sit
  { at: 4600, id: 'score' },
]

export default function MatchCase() {
  const c = cases.match
  const reduce = useReducedMotion()
  const [step, setStep] = useState(0)
  const [run, setRun] = useState(0)

  useEffect(() => {
    if (reduce) { setStep(STEPS.length); return }   // show it all at once
    setStep(0)
    const timers = STEPS.map((s, i) => setTimeout(() => setStep(i + 1), s.at))
    return () => timers.forEach(clearTimeout)
  }, [run, reduce])

  if (!c) return <Empty />

  const show = (id) => step >= STEPS.findIndex((s) => s.id === id) + 1

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-start justify-between gap-4 mb-5">
        <SectionTitle
          eyebrow="Case 01 — different words, same item"
          title="Two companies. No shared brand. One bearing."
        />
        <button
          onClick={() => setRun((r) => r + 1)}
          className="shrink-0 mt-1 px-3 py-1.5 rounded-md border border-line
                     text-[12px] text-ink-dim hover:text-ink hover:border-accent
                     transition-colors"
        >
          ↻ Replay
        </button>
      </div>

      {/* the two records */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={show('cards') ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.4 }}
        className="grid md:grid-cols-2 gap-3 mb-5"
      >
        <RecordCard rec={c.a} />
        <RecordCard rec={c.b} />
      </motion.div>

      {/* text similarity - lands alone, and is allowed to sit */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={show('text') ? { opacity: 1 } : {}}
        transition={{ duration: 0.4 }}
        className="card p-4 mb-5"
      >
        <Meter
          value={c.text_sim}
          tone="warn"
          label="Text similarity — what a conventional matcher sees"
          show={show('text')}
          sub="Not low. A text-only matcher would probably accept this pair — which sounds like good news until the next screen."
        />
      </motion.div>

      {/* the specifications */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={show('specs') ? { opacity: 1 } : {}}
        transition={{ duration: 0.3 }}
        className="mb-5"
      >
        <p className="label mb-2">Extracted specifications</p>
        <SpecCompare
          a={c.a}
          b={c.b}
          matched={c.matched_fields}
          ignored={c.ignored_fields}
          blockedBy={c.blocked_by}
          hardFields={c.hard_fields}
          play={show('specs')}
        />
      </motion.div>

      {/* the score */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={show('score') ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.45 }}
        className="card p-5"
      >
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="label mb-1">Match score</p>
            <div className="text-[42px] leading-none font-semibold text-good tracking-tight">
              {show('score') ? <CountUp to={c.final} decimals={3} /> : '—'}
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <Chip tone="good">specs {c.spec_sim}</Chip>
            <Chip tone="warn">text {c.text_sim}</Chip>
            {c.proc_sim != null && <Chip tone="accent">procurement {c.proc_sim}</Chip>}
          </div>
        </div>

        <p className="mt-4 pt-4 border-t border-line-soft text-[14px] text-ink-dim leading-relaxed">
          <span className="text-ink font-medium">6205 is an ISO designation.</span>{' '}
          Any manufacturer's 6205 is 25 mm bore, 52 mm outer diameter, 15 mm wide.
          The model derived those dimensions from the designation on the record
          that never stated them — and marked them at lower confidence because
          it derived rather than read them.{' '}
          <span className="text-ink font-medium">Brand is ignored entirely</span>,
          which is exactly what lets SKF and FAG resolve to one item.
        </p>
      </motion.div>
    </div>
  )
}

function Empty() {
  return (
    <div className="max-w-xl mx-auto card p-6 text-center">
      <p className="text-ink-dim">
        No match case in <code className="font-mono text-accent">results.json</code>.
      </p>
      <p className="mt-2 text-[13px] text-ink-faint">
        Run <code className="font-mono">python src/results.py</code> — or{' '}
        <code className="font-mono">--stub</code> before the pipeline has run.
      </p>
    </div>
  )
}
