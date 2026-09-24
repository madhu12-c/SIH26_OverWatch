import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { cases } from '../lib/data'
import { Meter, RecordCard, SectionTitle } from '../components/Primitives'
import SpecCompare from '../components/SpecCompare'

/*
 * Screen 03 - the reverse case, and the punchline.
 *
 * Screen 02 showed a pair that SHOULD merge scoring 0.833 on text. This one
 * shows a pair that must NEVER merge scoring HIGHER. The ordering is
 * inverted, and an inverted ordering cannot be fixed by tuning a threshold -
 * which is the whole reason we do not match on text.
 */

const STEPS = [
  { at: 200, id: 'cards' },
  { at: 1200, id: 'text' },
  { at: 2800, id: 'specs' },
  { at: 4200, id: 'trap' },
]

export default function BlockCase() {
  const c = cases.block
  const m = cases.match
  const reduce = useReducedMotion()
  const [step, setStep] = useState(0)
  const [run, setRun] = useState(0)

  useEffect(() => {
    if (reduce) { setStep(STEPS.length); return }   // show it all at once
    setStep(0)
    const timers = STEPS.map((s, i) => setTimeout(() => setStep(i + 1), s.at))
    return () => timers.forEach(clearTimeout)
  }, [run, reduce])

  if (!c) return null
  const show = (id) => step >= STEPS.findIndex((s) => s.id === id) + 1

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-start justify-between gap-4 mb-5">
        <SectionTitle
          eyebrow="Case 02 — same words, different item"
          title="One character apart. Never interchangeable."
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

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={show('cards') ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.4 }}
        className="grid md:grid-cols-2 gap-3 mb-5"
      >
        <RecordCard rec={c.a} accent="danger" />
        <RecordCard rec={c.b} accent="danger" />
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={show('text') ? { opacity: 1 } : {}}
        transition={{ duration: 0.4 }}
        className="card p-4 mb-5"
      >
        <Meter
          value={c.text_sim}
          tone="danger"
          label="Text similarity — a text matcher would merge these"
          show={show('text')}
          sub="Nearly identical. Every text-based approach — edit distance, TF-IDF, embeddings — scores this pair as a confident match."
        />
      </motion.div>

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

      {/* the punchline - the inversion, and why no threshold survives it */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={show('trap') ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.45 }}
        className="card p-5 border-danger/40"
      >
        <p className="label text-danger mb-3">The threshold trap</p>

        <div className="space-y-2 mb-4">
          <Row
            label="Should merge"
            desc="SKF vs FAG — the same bearing"
            value={m?.text_sim}
            tone="text-warn"
          />
          <Row
            label="Must never merge"
            desc="SS316 vs SS304 — different steel"
            value={c.text_sim}
            tone="text-danger"
          />
        </div>

        <p className="text-[14px] text-ink-dim leading-relaxed mb-4">
          The pair that must <em>not</em> merge scores{' '}
          <span className="text-ink font-medium">higher</span> than the pair that
          should. The ordering is inverted — and no threshold can fix an inverted
          ordering.
        </p>

        <div className="scroll-x">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-line">
                <th className="label text-left py-2 pr-4">Threshold</th>
                <th className="label text-left py-2 pr-4">The bearing</th>
                <th className="label text-left py-2">The gasket</th>
              </tr>
            </thead>
            <tbody className="font-mono text-[12.5px]">
              <tr className="border-b border-line-soft">
                <td className="py-2 pr-4 tnum">0.80</td>
                <td className="py-2 pr-4 text-good">merged ✓</td>
                <td className="py-2 text-danger">merged ✕ leak</td>
              </tr>
              <tr className="border-b border-line-soft">
                <td className="py-2 pr-4 tnum">0.90</td>
                <td className="py-2 pr-4 text-danger">missed ✕</td>
                <td className="py-2 text-danger">merged ✕ leak</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 tnum">0.99</td>
                <td className="py-2 pr-4 text-danger">missed ✕</td>
                <td className="py-2 text-ink-faint">blocked ✓</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p className="mt-4 pt-4 border-t border-line-soft text-[14px] leading-relaxed">
          <span className="text-ink font-medium">
            There is no setting that gets both right.
          </span>{' '}
          So we stop tuning the threshold and change what is being measured.
          SS316 contains molybdenum and SS304 does not — in corrosive service the
          wrong one pits and leaks. Material grade is a veto field: a mismatch is
          an instant zero, whatever the text says.
        </p>
      </motion.div>
    </div>
  )
}

function Row({ label, desc, value, tone }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2 px-3 rounded-md bg-base-raised">
      <div className="min-w-0">
        <div className="text-[12.5px] text-ink">{label}</div>
        <div className="text-[11.5px] text-ink-faint truncate">{desc}</div>
      </div>
      <div className={`font-mono text-xl font-semibold tnum shrink-0 ${tone}`}>
        {value ?? '—'}
      </div>
    </div>
  )
}
