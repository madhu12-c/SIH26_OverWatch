import { VERBS } from '../lib/store'

/* One line per audit event: when, who, what, on which object. Used by the
   dashboard's activity feed and the audit trail. */

function when(ts) {
  const d = new Date(ts)
  const today = new Date()
  const time = d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  if (d.toDateString() === today.toDateString()) return time
  return `${d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })} ${time}`
}

const DOT = {
  good: 'bg-good', danger: 'bg-danger', warn: 'bg-warn', accent: 'bg-accent', faint: 'bg-ink-faint',
}

export function ActivityItem({ e, compact = false }) {
  const v = VERBS[e.verb] ?? { text: e.verb.toLowerCase(), tone: 'faint' }
  return (
    <li className="flex gap-3 py-2.5 border-b border-line-soft last:border-0">
      <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${DOT[v.tone]}`} />
      <div className="min-w-0 flex-1">
        <p className="text-[13px] text-ink leading-snug">
          <span className="font-semibold">{e.actor}</span> {v.text}
          {e.object && <span className="font-mono text-[12px] text-ink-dim"> · {e.object}</span>}
        </p>
        {!compact && e.note && <p className="text-[12px] text-ink-faint mt-0.5 leading-snug">{e.note}</p>}
      </div>
      <span className="text-[11px] font-mono text-ink-faint tnum shrink-0">{when(e.ts)}</span>
    </li>
  )
}
