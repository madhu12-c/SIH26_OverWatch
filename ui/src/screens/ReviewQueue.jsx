import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { reviewQueue } from '../lib/data'
import { RecordCard, SectionTitle, Chip } from '../components/Primitives'
import SpecCompare from '../components/SpecCompare'

/*
 * Screen 04 - the actual product.
 *
 * The cataloguer is the only person who uses this system daily, and the
 * project fails if their experience is slow. So: keyboard only, all evidence
 * on one screen, five seconds per decision.
 *
 * The person doing this work is not the person getting the benefit -
 * procurement gets the savings, the ministry gets the credit, the reviewer
 * gets a queue. That is how master-data projects die everywhere in the world,
 * and it is why this screen is built before the dashboard.
 */

export default function ReviewQueue() {
  const queue = reviewQueue || []
  const [i, setI] = useState(0)
  const [decisions, setDecisions] = useState({})

  const decide = useCallback((verdict) => {
    setDecisions((d) => ({ ...d, [i]: verdict }))
    setI((n) => Math.min(n + 1, queue.length))
  }, [i, queue.length])

  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === 'INPUT') return
      const k = e.key.toLowerCase()
      if (k === 'a') decide('approved')
      else if (k === 'r') decide('rejected')
      else if (k === 's') decide('skipped')
      else if (k === 'arrowleft') setI((n) => Math.max(0, n - 1))
      else if (k === 'arrowright') setI((n) => Math.min(queue.length, n + 1))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [decide, queue.length])

  const done = Object.keys(decisions).length
  const item = queue[i]

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-5">
        <SectionTitle
          eyebrow="Review queue"
          title="Only the genuinely uncertain reach a human"
          sub="High-confidence pairs merge automatically. Anything below the threshold — or with a safety field we could not verify — comes here."
        />
        <div className="shrink-0 text-right">
          <p className="label">progress</p>
          <p className="font-mono text-[20px] tnum">{done}<span className="text-ink-faint">/{queue.length}</span></p>
        </div>
      </div>

      {/* keyboard legend - the whole point of this screen */}
      <div className="card px-4 py-2.5 mb-5 flex flex-wrap items-center gap-x-5 gap-y-1.5">
        <span className="label">keyboard</span>
        <Key k="A" label="approve" tone="text-good" />
        <Key k="R" label="reject" tone="text-danger" />
        <Key k="S" label="skip" tone="text-ink-dim" />
        <Key k="← →" label="move" tone="text-ink-faint" />
        <span className="ml-auto text-[11.5px] text-ink-faint">no mouse required</span>
      </div>

      <AnimatePresence mode="wait">
        {item ? (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.22 }}
          >
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <Chip tone="warn">score {item.final}</Chip>
              <Chip tone="faint">specs {item.spec_sim}</Chip>
              <Chip tone="faint">text {item.text_sim}</Chip>
              {item.proc_sim != null && <Chip tone="faint">procurement {item.proc_sim}</Chip>}
            </div>

            {item.review_reason && (
              <div className="card px-4 py-2.5 mb-3 border-warn/40">
                <p className="text-[13px] text-warn">{item.review_reason}</p>
              </div>
            )}

            <div className="grid md:grid-cols-2 gap-3 mb-4">
              <RecordCard rec={item.a} />
              <RecordCard rec={item.b} />
            </div>

            <div className="mb-5">
              <SpecCompare
                a={item.a}
                b={item.b}
                matched={item.matched_fields}
                ignored={item.ignored_fields}
                blockedBy={null}
                hardFields={[]}
                play
              />
            </div>

            <div className="flex flex-wrap gap-2">
              <Btn onClick={() => decide('approved')} tone="good">A — Approve</Btn>
              <Btn onClick={() => decide('rejected')} tone="danger">R — Reject</Btn>
              <Btn onClick={() => decide('skipped')} tone="dim">S — Skip</Btn>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="done"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="card p-8 text-center"
          >
            <p className="text-[18px] font-semibold text-good mb-1">Queue cleared</p>
            <p className="text-[13.5px] text-ink-dim">
              {tally(decisions, 'approved')} approved ·{' '}
              {tally(decisions, 'rejected')} rejected ·{' '}
              {tally(decisions, 'skipped')} skipped
            </p>
            <button
              onClick={() => { setI(0); setDecisions({}) }}
              className="mt-4 px-3 py-1.5 rounded-md border border-line text-[12px]
                         text-ink-dim hover:text-ink hover:border-accent transition-colors"
            >
              ↻ Reset
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <p className="mt-6 text-[12.5px] text-ink-faint leading-relaxed max-w-2xl">
        Decisions here are local to this demo. In the real system every approval
        is logged with who, when and on what evidence — and every merge is
        reversible, because nothing is ever deleted. For a match between two
        different CPSEs, both sides must approve.
      </p>
    </div>
  )
}

const tally = (d, v) => Object.values(d).filter((x) => x === v).length

function Key({ k, label, tone }) {
  return (
    <span className="flex items-center gap-1.5">
      <kbd className="px-1.5 py-0.5 rounded border border-line bg-base-raised
                      font-mono text-[11px] text-ink">{k}</kbd>
      <span className={`text-[12px] ${tone}`}>{label}</span>
    </span>
  )
}

function Btn({ children, onClick, tone }) {
  const tones = {
    good: 'border-good/50 text-good hover:bg-good-bg',
    danger: 'border-danger/50 text-danger hover:bg-danger-bg',
    dim: 'border-line text-ink-dim hover:text-ink',
  }
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-md border text-[13px] font-medium
                  transition-colors ${tones[tone]}`}
    >
      {children}
    </button>
  )
}
