import { useEffect, useMemo, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { reviewRecords, meta } from '../lib/data'
import { ROLES, can, log, useAudit, decisionsFrom, pairKey } from '../lib/store'
import { RecordCard, SectionTitle, Chip } from '../components/Primitives'
import SpecCompare from '../components/SpecCompare'
import { prettyField } from '../lib/format'

/*
 * The review queue - the actual product.
 *
 * The cataloguer is the only person who uses this system daily, and the
 * project fails if their experience is slow. So: keyboard only, all evidence
 * on one screen, five seconds per decision.
 *
 * ONE RECORD AT A TIME, NOT A WALL OF PAIRS. A terse line ("GASKET SS316
 * 4IN") fits several catalogue items, and judged pair by pair most of those
 * look like false alarms. The question a cataloguer actually answers is
 * "which of these is it?", so the queue shows one record with its best
 * candidates, ranked by how many facts were confirmed (scorer.review_rank).
 * On the 15,000-record run the right match is first for about half of
 * records and in the top three for about four in five.
 *
 * Who decides depends on scope, the consent model in action:
 *   a pair inside one company      that company's reviewer
 *   a pair across two companies    the national registrar
 * Everyone else sees the queue read-only, and a refused decision is logged.
 *
 * Every decision is still a decision on a PAIR, written to the audit log, so
 * the dashboard's counters and the audit trail read it unchanged.
 */

const SHOW = 3
const LABEL = { ACCEPT: 'same item', REJECT: 'different', SKIP: 'skipped' }
const TONE = { ACCEPT: 'good', REJECT: 'danger', SKIP: 'faint' }

export default function ReviewQueue({ session }) {
  const audit = useAudit()
  const decided = decisionsFrom(audit)
  const own = ROLES[session.role]?.needsOrg ? session.org : null

  // Each tab keeps the records that still have a candidate for it.
  const tabs = useMemo(() => {
    const keep = (pred) => reviewRecords
      .map((r) => ({ ...r, cands: r.candidates.filter(pred) }))
      .filter((r) => r.cands.length)
    const mine = keep((c) => can(session, 'decide_pair', c).ok)
    const others = keep((c) => !can(session, 'decide_pair', c).ok && (!own || c.a.cpse === own || c.b.cpse === own))
    return mine.length
      ? [
          { id: 'mine', label: session.role === 'registrar' ? 'Cross-company — yours to decide' : `Inside ${own} — yours to decide`, list: mine },
          { id: 'other', label: session.role === 'registrar' ? 'Inside one company — its reviewer decides' : `Involving ${own} — the registrar decides`, list: others },
        ]
      : [{ id: 'other', label: own ? `Records involving ${own} — view only` : 'All records — view only', list: others }]
  }, [session, own])

  const [tab, setTab] = useState(tabs[0].id)
  const list = (tabs.find((t) => t.id === tab) ?? tabs[0]).list
  const open = (r) => r.cands.filter((c) => !decided[pairKey(c)])
  const [i, setI] = useState(() => Math.max(0, list.findIndex((r) => open(r).length)))
  const [focus, setFocus] = useState(0)
  const [note, setNote] = useState(null)
  const rec = list[i]

  // The candidates on screen: the best three still undecided, or - once all
  // are decided - the first three, so the outcome stays visible.
  const shown = rec ? (open(rec).length ? open(rec) : rec.cands).slice(0, SHOW) : []
  const later = rec ? Math.max(0, open(rec).length - SHOW) : 0
  const rule = shown[0] ? can(session, 'decide_pair', shown[0]) : { ok: false }

  const record = useCallback((verb, c, why) => {
    const allowed = can(session, 'decide_pair', c)
    const object = `${c.a.cpse} ${c.a.source_code} ↔ ${c.b.cpse} ${c.b.source_code}`
    if (!allowed.ok) {
      log('DENIED', { object, note: allowed.why })
      setNote(allowed.why)
      return false
    }
    log(verb, { object, pair: pairKey(c), note: `${why} · score ${c.final}, ${c.confirmed} facts confirmed` })
    return true
  }, [session])

  const decide = useCallback((action, k) => {
    if (!rec || !shown.length) return
    setNote(null)
    let ok = true
    if (action === 'one') {
      if (k >= shown.length) return
      shown.forEach((c, j) => {
        ok = record(j === k ? 'ACCEPT' : 'REJECT', c, j === k ? 'chosen as the same item' : `not the same - candidate ${k + 1} chosen`) && ok
      })
    } else if (action === 'all') {
      shown.forEach((c) => { ok = record('ACCEPT', c, 'all shown candidates are the same item') && ok })
    } else if (action === 'none') {
      shown.forEach((c) => { ok = record('REJECT', c, 'none of the candidates is the same item') && ok })
    } else if (action === 'skip') {
      shown.forEach((c) => { ok = record('SKIP', c, 'skipped for now') && ok })
    }
    if (!ok) return
    setFocus(0)
    setI((n) => (later > 0 ? n : Math.min(n + 1, list.length)))
  }, [rec, shown, later, record, list.length])

  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === 'INPUT' || e.ctrlKey || e.metaKey || e.altKey) return
      const k = e.key.toLowerCase()
      if (k === '1' || k === '2' || k === '3') decide('one', Number(k) - 1)
      else if (k === 'a') decide('all')
      else if (k === 'r' || k === 'n') decide('none')
      else if (k === 's') decide('skip')
      else if (k === 'arrowdown') setFocus((f) => Math.min(f + 1, shown.length - 1))
      else if (k === 'arrowup') setFocus((f) => Math.max(f - 1, 0))
      else if (k === 'arrowleft') { setNote(null); setFocus(0); setI((n) => Math.max(0, n - 1)) }
      else if (k === 'arrowright') { setNote(null); setFocus(0); setI((n) => Math.min(list.length, n + 1)) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [decide, list.length, shown.length])

  const pairs = list.reduce((n, r) => n + r.cands.length, 0)
  const done = list.reduce((n, r) => n + r.cands.filter((c) => decided[pairKey(c)]).length, 0)
  const focused = shown[Math.min(focus, shown.length - 1)]
  const quality = meta.review_queue_quality

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <SectionTitle
          eyebrow="Review queue"
          title="Only the genuinely uncertain reach a human"
          sub={`One record at a time, with its best candidates first — ranked by how many facts were confirmed, not by a score that ties. ${meta.review_records ?? list.length} records hold ${meta.review_pending} pairs a person must see; everything confident merged on its own.`}
        />
        <div className="shrink-0 text-right">
          <p className="label">pairs decided</p>
          <p className="font-mono text-[22px] tnum">{done}<span className="text-ink-faint">/{pairs}</span></p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => { setTab(t.id); setI(0); setFocus(0); setNote(null) }} aria-pressed={tab === t.id}
                  className={`px-3 py-1.5 rounded border text-[12.5px] font-semibold
                    ${tab === t.id ? 'bg-gov text-white border-gov' : 'border-line text-ink-dim hover:border-accent/60'}`}>
            {t.label} <span className="font-mono opacity-75">({t.list.length})</span>
          </button>
        ))}
      </div>

      <div className="card px-4 py-2.5 mb-5 flex flex-wrap items-center gap-x-5 gap-y-1.5">
        <span className="label">keyboard</span>
        <Key k="1 2 3" label="this one, not the others" tone="text-good" />
        <Key k="A" label="all shown are the same" tone="text-good" />
        <Key k="R" label="none of these" tone="text-danger" />
        <Key k="S" label="skip" tone="text-ink-dim" />
        <Key k="↑ ↓" label="compare" tone="text-ink-faint" />
        <Key k="← →" label="record" tone="text-ink-faint" />
      </div>

      <AnimatePresence mode="wait">
        {rec ? (
          <motion.div key={`${tab}-${i}-${rec.cands.length - open(rec).length}`}
                      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}
                      transition={{ duration: 0.18 }}>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="text-[12px] text-ink-faint font-mono mr-1">record {i + 1} of {list.length}</span>
              <Chip tone="faint">{rec.cands.length} candidate{rec.cands.length === 1 ? '' : 's'}</Chip>
              {later > 0 && <Chip tone="faint">{later} more after these</Chip>}
            </div>

            <p className="label mb-1.5">Which of these is this item?</p>
            <RecordCard rec={rec.record} />

            <div className="mt-3 space-y-2">
              {shown.map((c, k) => {
                const state = decided[pairKey(c)]
                const cf = c.counterfactual?.kind === 'unverified' ? c.counterfactual : null
                return (
                  <button key={pairKey(c)} onClick={() => setFocus(k)}
                          className={`w-full text-left card px-4 py-3 transition-colors
                            ${k === focus ? 'border-accent ring-1 ring-accent/30' : 'hover:border-accent/50'}`}>
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <kbd className="px-1.5 py-0.5 rounded border border-line bg-base-raised font-mono text-[11px] text-ink">{k + 1}</kbd>
                      <span className="text-[11.5px] font-semibold text-accent">{c.b.cpse}</span>
                      <span className="text-[11px] font-mono text-ink-faint">{c.b.source_code}</span>
                      <Chip tone={c.confirmed >= 3 ? 'good' : 'faint'}>{c.confirmed} facts confirmed</Chip>
                      <Chip tone="warn">score {c.final}</Chip>
                      <Chip tone={c.a.cpse === c.b.cpse ? 'accent' : 'faint'}>
                        {c.a.cpse === c.b.cpse ? `inside ${c.a.cpse}` : 'across companies'}
                      </Chip>
                      {state && <Chip tone={TONE[state]}>{LABEL[state]}</Chip>}
                    </div>
                    <p className="font-mono text-[13px] text-ink break-words">{c.b.description}</p>
                    {(c.review_reason || cf) && (
                      <p className="mt-1 text-[12px] text-ink-dim">
                        {c.review_reason && <span className="text-warn">{c.review_reason.replace(/_/g, ' ')}. </span>}
                        {cf && (
                          <span>
                            Confirm {cf.fields.map((f) => prettyField(f).toLowerCase()).join(' and ')} and it
                            scores <span className="font-mono">{cf.score}</span>.
                          </span>
                        )}
                      </p>
                    )}
                  </button>
                )
              })}
            </div>

            {focused && (
              <div className="mt-4 mb-5">
                <p className="label mb-2">Field by field — this record against candidate {Math.min(focus, shown.length - 1) + 1}</p>
                <SpecCompare a={focused.a} b={focused.b} matched={focused.matched_fields} ignored={focused.ignored_fields}
                             blockedBy={null} hardFields={[]} play />
              </div>
            )}

            {(note || !rule.ok) && (
              <div className={`mb-3 px-4 py-2.5 rounded border text-[13px]
                ${note ? 'border-danger/40 bg-danger-bg text-danger' : 'border-line bg-base-raised text-ink-dim'}`}>
                {note ? `Refused and logged: ${note}` : `View only — ${rule.why}`}
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              {shown.map((c, k) => (
                <Btn key={k} onClick={() => decide('one', k)} tone="good" off={!rule.ok}>{k + 1} — This one</Btn>
              ))}
              <Btn onClick={() => decide('all')} tone="good" off={!rule.ok}>A — All the same</Btn>
              <Btn onClick={() => decide('none')} tone="danger" off={!rule.ok}>R — None of these</Btn>
              <Btn onClick={() => decide('skip')} tone="dim" off={!rule.ok}>S — Skip</Btn>
            </div>
          </motion.div>
        ) : (
          <motion.div key="done" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card p-8 text-center">
            <p className="text-[18px] font-semibold text-good mb-1">{list.length ? 'End of this list' : 'Nothing here for your role'}</p>
            <p className="text-[13.5px] text-ink-dim">{done} of {pairs} pairs decided. Every decision is in the audit trail.</p>
            {list.length > 0 && (
              <button onClick={() => setI(0)}
                      className="mt-4 px-3 py-1.5 rounded border border-line text-[12px] text-ink-dim hover:text-ink hover:border-accent">
                ↻ Back to the first record
              </button>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <p className="mt-6 text-[12.5px] text-ink-faint leading-relaxed max-w-3xl">
        Candidates are ranked by how many facts were confirmed on both sides.
        {quality?.true_match_in_top3 != null && meta.run && meta.run !== 'demo'
          ? ` On this run the right match is first for ${Math.round(quality.true_match_first * 100)}% of records and in the top three for ${Math.round(quality.true_match_in_top3 * 100)}%.`
          : ' On the 15,000-record run the right match is first for about half of records and in the top three for about four in five.'}
        {' '}A link between two CPSEs is issued by the national registrar, and either company can dispute it at any
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
