import { useState } from 'react'
import { clusters, savings, uomConflicts } from '../lib/data'
import { prettyField, spec, rupeesExact } from '../lib/format'
import { ROLES, can, log, useAudit } from '../lib/store'
import { Chip } from '../components/Primitives'
import { Icon } from '../components/Icons'

/*
 * One national code: the golden record, how strongly the linked records agree
 * on each field, and every company code linked underneath - with the actions
 * the consent model allows the signed-in role:
 *
 *   dispute a link    any company whose code is in it
 *   retire a code     only the company that owns that code
 *
 * A refused action is not hidden - it is shown, and logged, so the rule is
 * visible rather than assumed.
 */

export default function Item({ code, session, go }) {
  const c = clusters.find((x) => x.national_code === code)
  const audit = useAudit()
  const [flash, setFlash] = useState(null)
  const own = ROLES[session.role]?.needsOrg ? session.org : null

  if (!c) {
    return (
      <div className="card p-8 text-center">
        <p className="text-ink-dim">No national code <span className="font-mono">{code}</span>.</p>
        <button onClick={() => go('catalogue')} className="mt-3 text-accent font-semibold hover:underline">Back to the catalogue</button>
      </div>
    )
  }

  const price = savings.find((s) => s.national_code === code)
  const units = (uomConflicts || []).find((u) => u.national_code === code)
  const disputed = audit.some((e) => e.verb === 'DISPUTE' && e.object === code)
  const retired = new Set(audit.filter((e) => e.verb === 'RETIRE_PROPOSED' && e.code === code).map((e) => e.source))

  const act = (action, target, verb, detail, ok) => {
    const rule = can(session, action, target)
    if (!rule.ok) {
      log('DENIED', { object: detail.object, note: rule.why })
      setFlash({ tone: 'danger', text: rule.why })
      return
    }
    log(verb, detail)
    setFlash({ tone: 'good', text: ok })
  }

  const dispute = () => act('dispute', { cpses: c.cpses }, 'DISPUTE',
    { object: code, note: `${own ?? 'A company'} says these are not all the same item. The link returns to review.` },
    'Dispute recorded. The link goes back to a human, with your objection in the audit trail.')

  const retire = (m) => act('retire', { cpse: m.cpse }, 'RETIRE_PROPOSED',
    { object: `${m.cpse} ${m.source_code}`, code, source: m.source_code,
      note: 'Proposed by its owner. The code stays readable and mapped; nothing is deleted.' },
    `Retirement of ${m.source_code} proposed. It stays mapped and readable — nothing is deleted.`)

  return (
    <div>
      <button onClick={() => go('catalogue')} className="text-[12.5px] text-accent hover:underline mb-3 inline-flex items-center gap-1">
        ← Catalogue
      </button>

      {/* header */}
      <section className="card overflow-hidden mb-4">
        <div className="bg-gov text-white px-5 py-4 relative">
          <div className="absolute inset-y-0 left-0 w-1.5 bg-saffron" />
          <p className="font-mono text-[13px] text-saffron font-semibold">{c.national_code}</p>
          <h1 className="text-[20px] sm:text-[22px] font-bold leading-snug mt-1">{c.std_description}</h1>
          <p className="text-[12.5px] text-white/75 mt-1">
            UNSPSC {c.unspsc} · {c.unspsc_name} · {c.member_count} records from {c.cpse_count} companies
          </p>
        </div>
        <div className="px-5 py-3 flex flex-wrap items-center gap-2 border-b border-line-soft">
          <Chip tone={c.band === 'auto' ? 'good' : c.band === 'review' ? 'warn' : 'faint'}>
            {c.band === 'auto' ? 'auto-merged' : c.band === 'review' ? 'in review' : c.band}
          </Chip>
          <Chip tone="accent">confidence {c.confidence}</Chip>
          {disputed && <Chip tone="warn">disputed — back in review</Chip>}
          <div className="ml-auto flex gap-2">
            {session.role === 'reviewer' && (
              <button onClick={dispute}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-warn/50 text-warn
                                 text-[12.5px] font-semibold hover:bg-warn-bg">
                <Icon name="flag" size={15} /> Dispute this link
              </button>
            )}
          </div>
        </div>
        {flash && (
          <div className={`px-5 py-2.5 text-[13px] ${flash.tone === 'good' ? 'bg-good-bg text-good' : 'bg-danger-bg text-danger'}`}>
            {flash.text}
          </div>
        )}
      </section>

      <div className="grid xl:grid-cols-[1fr_1.35fr] gap-4">
        {/* golden record */}
        <section className="card p-5">
          <h2 className="text-[15px] font-bold text-heading mb-1">Golden record</h2>
          <p className="text-[12px] text-ink-faint mb-4">
            Best value per field across the linked records, and how many of them agree.
          </p>
          <div className="space-y-3">
            {Object.entries(c.attributes || {}).map(([k, v]) => {
              const agree = c.field_agreement?.[k] ?? 0
              const ignored = k === 'brand' || k === 'part_number'
              return (
                <div key={k}>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-[12px] text-ink-faint">{prettyField(k)}{ignored && ' · never used to match'}</span>
                    <span className={`font-mono text-[13px] ${ignored ? 'text-ink-faint line-through' : 'text-ink'}`}>{spec(v)}</span>
                  </div>
                  <div className="mt-1 h-1.5 rounded-sm bg-base-raised overflow-hidden">
                    <div className={`h-full ${agree >= 0.9 ? 'bg-good' : agree >= 0.7 ? 'bg-warn' : 'bg-ink-faint'}`}
                         style={{ width: `${agree * 100}%` }} />
                  </div>
                </div>
              )
            })}
          </div>
          {units && (
            <p className="mt-4 pt-3 border-t border-line-soft text-[12.5px] text-ink-dim">
              <span className="font-semibold text-warn">Units:</span> written {units.variant_count} ways
              ({units.variants.map((x) => x.raw).join(', ')}), all meaning <b>{units.resolved_label}</b>.
            </p>
          )}
        </section>

        {/* linked codes */}
        <section className="card overflow-hidden">
          <div className="px-5 pt-4 pb-3 border-b border-line-soft">
            <h2 className="text-[15px] font-bold text-heading">Linked company codes</h2>
            <p className="text-[12px] text-ink-faint mt-0.5">
              Every original code stays active in its own company's system. Only the owner can retire one.
            </p>
          </div>
          <div className="scroll-x">
            <table className="w-full text-[12.5px]">
              <thead className="bg-base-raised">
                <tr className="border-b border-line">
                  <th className="label text-left py-2 px-4">Company · code</th>
                  <th className="label text-left py-2 px-3">As written by the company</th>
                  <th className="label text-left py-2 px-3">Unit</th>
                  <th className="label text-right py-2 px-4">Action</th>
                </tr>
              </thead>
              <tbody>
                {c.members.map((m) => {
                  const mine = m.cpse === own
                  const isRetired = retired.has(m.source_code)
                  return (
                    <tr key={m.record_id} className={`border-b border-line-soft last:border-0 ${mine ? 'bg-saffron-bg/60' : ''}`}>
                      <td className="py-2.5 px-4 whitespace-nowrap">
                        <span className="font-mono font-semibold text-accent">{m.cpse}</span>
                        <span className="block font-mono text-[11.5px] text-ink-dim">{m.source_code}</span>
                      </td>
                      <td className="py-2.5 px-3 font-mono text-[12px] text-ink">{m.description}</td>
                      <td className="py-2.5 px-3 font-mono text-ink-dim">{m.uom}</td>
                      <td className="py-2.5 px-4 text-right whitespace-nowrap">
                        {isRetired ? (
                          <Chip tone="warn">retire proposed</Chip>
                        ) : session.role === 'reviewer' ? (
                          <button onClick={() => retire(m)}
                                  className={`text-[12px] font-semibold px-2 py-1 rounded border
                                    ${mine ? 'border-danger/50 text-danger hover:bg-danger-bg' : 'border-line text-ink-faint hover:text-ink'}`}>
                            Retire
                          </button>
                        ) : (
                          <span className="text-[11.5px] text-ink-faint">active</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {price && (
        <section className="card p-5 mt-4">
          <h2 className="text-[15px] font-bold text-heading mb-1">What each company pays</h2>
          <p className="text-[12px] text-ink-faint mb-3">
            {price.benchmark_suppressed
              ? 'Fewer than 3 companies buy this item, so the benchmark is hidden — the best price would reveal another company\'s price.'
              : `Price spread ${price.price_spread_pct}%. Other companies' prices are shown only to roles allowed to see them.`}
          </p>
          {!price.benchmark_suppressed && (
            <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-2">
              {price.cpses.map((x) => {
                const visible = can(session, 'see_prices', { cpse: x.cpse }).ok
                const best = x.avg_price === price.best_price
                // The best price is the benchmark: its value is shown to
                // everyone, its owner only to roles allowed to see it.
                return (
                  <div key={x.cpse} className={`rounded border px-3 py-2.5 ${best ? 'border-good/50 bg-good-bg' : 'border-line'}`}>
                    <p className="font-mono text-[11.5px] font-semibold text-ink-dim">{visible ? x.cpse : 'Another CPSE'}</p>
                    <p className="font-mono text-[15px] tnum text-ink mt-0.5">{visible || best ? rupeesExact(x.avg_price) : '—'}</p>
                    <p className="text-[11px] text-ink-faint">{best ? 'best price (benchmark)' : visible ? `${x.qty} bought` : 'private'}</p>
                  </div>
                )
              })}
            </div>
          )}
        </section>
      )}
    </div>
  )
}
