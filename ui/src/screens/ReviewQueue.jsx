import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { reviewQueue, meta } from '../lib/data'
import { ROLES, can, log, useAudit, decisionsFrom, pairKey } from '../lib/store'
import { RecordCard, SectionTitle, Chip } from '../components/Primitives'
import SpecCompare from '../components/SpecCompare'

/*
 * The review queue - the actual product.
 *
 * The cataloguer is the only person who uses this system daily, and the
 * project fails if their experience is slow. So: keyboard only, all evidence
 * on one screen, five seconds per decision.
 *
 * Who decides depends on scope, the consent model in action:
 *   a pair inside one company      that company's reviewer
 *   a pair across two companies    the national registrar
 * Everyone else sees the queue read-only, and a refused decision is logged.
 *
 * Decisions live in the audit log, so they survive a reload and the
 * dashboard's counters move the moment one is taken.
 */

const VERB = { approved: 'ACCEPT', rejected: 'REJECT', skipped: 'SKIP' }
const LABEL = { ACCEPT: 'approved', REJECT: 'rejected', SKIP: 'skipped' }

export default function ReviewQueue({ session }) {
  const audit = useAudit()
  const decided = decisionsFrom(audit)
  const own = ROLES[session.role]?.needsOrg ? session.org : null

  const actionable = reviewQueue.filter((p) => can(session, 'decide_pair', p).ok)
  const others = reviewQueue.filter((p) => !can(session, 'decide_pair', p).ok &&
    (!own || p.a.cpse === own || p.b.cpse === own))
  const tabs = actionable.length
    ? [
        { id: 'mine', label: session.role === 'registrar' ? 'Cross-company — yours to decide' : `Inside ${own} — yours to decide`, list: actionable },
        { id: 'other', label: session.role === 'registrar' ? 'Inside one company — its reviewer decides' : `Involving ${own} — the registrar decides`, list: others },
      ]
    : [{ id: 'other', label: own ? `Pairs involving ${own} — view only` : 'All pairs — view only', list: others }]

  const [tab, setTab] = useState(tabs[0].id)
  const list = (tabs.find((t) => t.id === tab) ?? tabs[0]).list
  const [i, setI] = useState(() => Math.max(0, list.findIndex((p) => !decided[pairKey(p)])))
  const [note, setNote] = useState(null)
  const item = list[i]
  const rule = item ? can(session, 'decide_pair', item) : { ok: false }

  const decide = useCallback((verdict) => {
    if (!item) return
    const object = `${item.a.cpse} ${item.a.source_code} ↔ ${item.b.cpse} ${item.b.source_code}`
    const allowed = can(session, 'decide_pair', item)
    if (!allowed.ok) {
      log('DENIED', { object, note: allowed.why })
      setNote(allowed.why)
      return
    }
    log(VERB[verdict], { object, pair: pairKey(item), note: `score ${item.final}` })
    setNote(null)
    setI((n) => Math.min(n + 1, list.length))
  }, [item, session, list.length])

  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === 'INPUT' || e.ctrlKey || e.metaKey || e.altKey) return
      const k = e.key.toLowerCase()
      if (k === 'a') decide('approved')
      else if (k === 'r') decide('rejected')
      else if (k === 's') decide('skipped')
      else if (k === 'arrowleft') { setNote(null); setI((n) => Math.max(0, n - 1)) }
      else if (k === 'arrowright') { setNote(null); setI((n) => Math.min(list.length, n + 1)) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [decide, list.length])

  const done = list.filter((p) => decided[pairKey(p)]).length
  const state = item ? decided[pairKey(item)] : null

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <SectionTitle
          eyebrow="Review queue"
          title="Only the genuinely uncertain reach a human"
          sub={`High-confidence pairs merge automatically. Anything below the threshold — or with a safety field that could not be verified — comes here. Showing the ${reviewQueue.length} lowest-scoring of ${meta.review_pending}.`}
        />
        <div className="shrink-0 text-right">
          <p className="label">decided</p>
          <p className="font-mono text-[22px] tnum">{done}<span className="text-ink-faint">/{list.length}</span></p>
        </div>
      </div>

      {/* tabs */}
      <div className="flex flex-wrap gap-2 mb-4">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => { setTab(t.id); setI(0); setNote(null) }} aria-pressed={tab === t.id}
                  className={`px-3 py-1.5 rounded border text-[12.5px] font-semibold
                    ${tab === t.id ? 'bg-gov text-white border-gov' : 'border-line text-ink-dim hover:border-accent/60'}`}>
            {t.label} <span className="font-mono opacity-75">({t.list.length})</span>
          </button>
        ))}
      </div>

      <div className="card px-4 py-2.5 mb-5 flex flex-wrap items-center gap-x-5 gap-y-1.5">
        <span className="label">keyboard</span>
        <Key k="A" label="approve" tone="text-good" />
        <Key k="R" label="reject" tone="text-danger" />
        <Key k="S" label="skip" tone="text-ink-dim" />
        <Key k="← →" label="move" tone="text-ink-faint" />
        <span className="ml-auto text-[11.5px] text-ink-faint">every decision is written to the audit trail</span>
      </div>

      <AnimatePresence mode="wait">
        {item ? (
          <motion.div key={`${tab}-${i}`}
                      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}
                      transition={{ duration: 0.2 }}>
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <span className="text-[12px] text-ink-faint font-mono mr-1">pair {i + 1} of {list.length}</span>
              <Chip tone="warn">score {item.final}</Chip>
              <Chip tone="faint">specs {item.spec_sim}</Chip>
              <Chip tone="faint">text {item.text_sim}</Chip>
              {item.proc_sim != null && <Chip tone="faint">procurement {item.proc_sim}</Chip>}
              <Chip tone={item.a.cpse === item.b.cpse ? 'accent' : 'faint'}>
                {item.a.cpse === item.b.cpse ? `inside ${item.a.cpse}` : 'across companies'}
              </Chip>
              {state && <Chip tone={state === 'ACCEPT' ? 'good' : state === 'REJECT' ? 'danger' : 'faint'}>{LABEL[state]}</Chip>}
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
              <SpecCompare a={item.a} b={item.b} matched={item.matched_fields} ignored={item.ignored_fields}
                           blockedBy={null} hardFields={[]} play />
            </div>

            {(note || !rule.ok) && (
              <div className={`mb-3 px-4 py-2.5 rounded border text-[13px]
                ${note ? 'border-danger/40 bg-danger-bg text-danger' : 'border-line bg-base-raised text-ink-dim'}`}>
                {note ? `Refused and logged: ${note}` : `View only — ${rule.why}`}
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              <Btn onClick={() => decide('approved')} tone="good" off={!rule.ok}>A — Approve</Btn>
              <Btn onClick={() => decide('rejected')} tone="danger" off={!rule.ok}>R — Reject</Btn>
              <Btn onClick={() => decide('skipped')} tone="dim" off={!rule.ok}>S — Skip</Btn>
            </div>
          </motion.div>
        ) : (
          <motion.div key="done" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card p-8 text-center">
            <p className="text-[18px] font-semibold text-good mb-1">{list.length ? 'End of this list' : 'Nothing here for your role'}</p>
            <p className="text-[13.5px] text-ink-dim">{done} of {list.length} decided. Every decision is in the audit trail.</p>
            {list.length > 0 && (
              <button onClick={() => setI(0)}
                      className="mt-4 px-3 py-1.5 rounded border border-line text-[12px] text-ink-dim hover:text-ink hover:border-accent">
                ↻ Back to the first pair
              </button>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <p className="mt-6 text-[12.5px] text-ink-faint leading-relaxed max-w-3xl">
        A link between two CPSEs is issued by the national registrar, and either company can dispute it at any
        time; a pair inside one company is that company's own decision; only the company that owns a code can
        ever retire it. Every merge is reversible, because nothing is ever deleted.
      </p>
    </div>
  )
}

function Key({ k, label, tone }) {
  return (
    <span className="flex items-center gap-1.5">
      <kbd className="px-1.5 py-0.5 rounded border border-line bg-base-raised font-mono text-[11px] text-ink">{k}</kbd>
      <span className={`text-[12px] ${tone}`}>{label}</span>
    </span>
  )
}

function Btn({ children, onClick, tone, off }) {
  const tones = {
    good: 'border-good/50 text-good hover:bg-good-bg',
    danger: 'border-danger/50 text-danger hover:bg-danger-bg',
    dim: 'border-line text-ink-dim hover:text-ink',
  }
  return (
    <button onClick={onClick} aria-disabled={off}
            className={`px-4 py-2 rounded border text-[13px] font-medium transition-colors
              ${off ? 'border-line-soft text-ink-faint/70 cursor-not-allowed' : tones[tone]}`}>
      {children}
    </button>
  )
}
