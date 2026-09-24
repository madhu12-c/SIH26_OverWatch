import { useState } from 'react'
import { meta } from '../lib/data'
import { useAudit, can, clearAudit, log, VERBS } from '../lib/store'
import { SectionTitle, Stat } from '../components/Primitives'
import { ActivityItem } from '../components/Activity'
import { Icon } from '../components/Icons'

/*
 * The audit trail - problem-statement capability 7.
 *
 * Every sign-in, decision, dispute, retirement proposal, download and REFUSED
 * attempt is here: who, what, when, on which object. Refusals are logged on
 * purpose - a governance log that only records what was allowed hides the
 * most interesting events.
 *
 * In this prototype the log lives in the browser. In the real system it is an
 * append-only file where each entry carries the hash of the one before, so a
 * change anywhere shows.
 */

const FILTERS = [
  ['', 'All'],
  ['decisions', 'Decisions'],
  ['DISPUTE', 'Disputes'],
  ['RETIRE_PROPOSED', 'Retirements'],
  ['DENIED', 'Refused'],
  ['EXPORT', 'Downloads'],
  ['session', 'Sign-ins'],
]

const matches = (e, f) => !f
  || (f === 'decisions' && ['ACCEPT', 'REJECT', 'SKIP'].includes(e.verb))
  || (f === 'session' && ['SIGN_IN', 'SIGN_OUT'].includes(e.verb))
  || e.verb === f

export default function Audit({ session }) {
  const audit = useAudit()
  const [f, setF] = useState('')
  const shown = audit.filter((e) => matches(e, f))
  const n = (v) => audit.filter((e) => (Array.isArray(v) ? v.includes(e.verb) : e.verb === v)).length
  const mayClear = can(session, 'clear_log').ok

  const exportLog = () => {
    const blob = new Blob([JSON.stringify(audit.slice().reverse(), null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `nmcr_audit_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(a.href)
    log('AUDIT_EXPORT', { object: `${audit.length} events` })
  }

  return (
    <div>
      <SectionTitle
        eyebrow="Audit trail · governance"
        title="Who decided what, when, and on what"
        sub="Every action on the registry is recorded — including the ones a role was refused. Nothing is edited or removed."
      />

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
        <Stat value={audit.length} label="Events recorded" />
        <Stat value={n(['ACCEPT', 'REJECT'])} label="Match decisions" tone="good" />
        <Stat value={n('DISPUTE')} label="Disputes" tone="warn" />
        <Stat value={n('RETIRE_PROPOSED')} label="Retirements proposed" tone="warn" />
        <Stat value={n('DENIED')} label="Actions refused" tone="danger" />
      </div>

      <div className="card overflow-hidden">
        <div className="px-4 py-3 border-b border-line-soft flex flex-wrap items-center gap-2">
          {FILTERS.map(([id, label]) => (
            <button key={id || 'all'} onClick={() => setF(id)} aria-pressed={f === id}
                    className={`px-2.5 py-1 rounded border text-[12px] font-semibold
                      ${f === id ? 'bg-gov text-white border-gov' : 'border-line text-ink-dim hover:border-accent/60'}`}>
              {label}
            </button>
          ))}
          <div className="ml-auto flex gap-2">
            <button onClick={exportLog}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-line text-[12.5px]
                               font-semibold text-accent hover:bg-accent-dim">
              <Icon name="download" size={15} /> Export log
            </button>
            {mayClear && (
              <button onClick={() => { if (window.confirm('Reset the demo audit log? The reset itself is recorded.')) clearAudit() }}
                      className="px-3 py-1.5 rounded border border-line text-[12.5px] text-ink-faint hover:text-danger">
                Reset demo log
              </button>
            )}
          </div>
        </div>

        <ul className="px-5">
          {shown.map((e) => <ActivityItem key={e.id} e={e} />)}
          <li className="flex gap-3 py-2.5 text-[13px] text-ink-dim">
            <span className="mt-1.5 w-2 h-2 rounded-full shrink-0 bg-accent" />
            <span className="flex-1">
              <span className="font-semibold text-ink">Pipeline</span> produced {meta.unique_items} national codes
              from {meta.records} records
              <span className="block text-[12px] text-ink-faint">Deterministic run — same input, same output.</span>
            </span>
            <span className="text-[11px] font-mono text-ink-faint">{meta.generated}</span>
          </li>
        </ul>
        {!shown.length && <p className="px-5 pb-4 text-[13px] text-ink-faint">No events of this kind yet.</p>}
      </div>

      <p className="mt-4 text-[12.5px] text-ink-faint leading-relaxed max-w-3xl">
        Verbs recorded: {Object.values(VERBS).map((v) => v.text).join(' · ')}. In this prototype the log is
        kept in your browser. In the full system it is an append-only file where each entry carries the hash
        of the one before it, so any change shows.
      </p>
    </div>
  )
}
