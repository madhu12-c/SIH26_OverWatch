import { meta, reviewQueue, savings } from '../lib/data'
import { rupees } from '../lib/format'
import { ROLES, sessionLabel, useAudit, decisionsFrom, pairKey, can } from '../lib/store'
import { perCpse, byCategory, outcomes, refusals, totals } from '../lib/analytics'
import { SectionTitle, Stat } from '../components/Primitives'
import { ChartCard, BarList, Columns, Donut } from '../components/Charts'
import { ActivityItem } from '../components/Activity'
import { Icon } from '../components/Icons'
import Evidence from '../components/Evidence'

/*
 * The dashboard, and it changes with the signed-in role.
 *
 * A registrar or ministry viewer sees the whole registry. A company reviewer
 * or procurement officer sees ITS OWN company's figures first, with the
 * national picture beside them - never another company's raw data. The task
 * list and the activity feed are live: approve a pair in the review queue and
 * both move here.
 */

export default function Dashboard({ session, go }) {
  const audit = useAudit()
  const decided = decisionsFrom(audit)
  const own = ROLES[session.role]?.needsOrg ? session.org : null

  const mine = reviewQueue.filter((p) => can(session, 'decide_pair', p).ok)
  const minePending = mine.filter((p) => !decided[pairKey(p)])
  const involving = own ? reviewQueue.filter((p) => p.a.cpse === own || p.b.cpse === own) : reviewQueue
  const decidedCount = Object.keys(decided).length
  const disputes = audit.filter((e) => e.verb === 'DISPUTE').length

  const t = totals(own ? { cpse: own } : {})
  const rows = perCpse()
  const ownRow = rows.find((r) => r.cpse === own)
  const refused = outcomes().find((o) => o.key === 'blocked').value
  const topSavings = savings
    .filter((s) => !own || s.cpses.some((x) => x.cpse === own))
    .filter((s) => !s.benchmark_suppressed)
    .sort((a, b) => b.saving_realistic - a.saving_realistic)
    .slice(0, 5)

  const date = new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

  return (
    <div>
      <SectionTitle
        eyebrow={`${ROLES[session.role].label}${own ? ` · ${own}` : ''} · ${date}`}
        title={`Welcome, ${sessionLabel(session)}`}
        sub={own
          ? `Figures for ${own} first; the national picture beside them. Other companies' raw data is never shown to you.`
          : 'The whole registry at a glance. Every figure is measured by the pipeline, not typed in.'}
      />

      {/* headline figures */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 mb-5">
        {own ? (
          <>
            <Stat value={t.records} label={`${own} material records`} />
            <Stat value={t.codes} label="National codes they map to" tone="accent" />
            <Stat value={ownRow?.inside ?? 0} label={`Repeats inside ${own}`} sub="fixable with no data sharing" tone="warn" />
            <Stat value={ownRow?.shared ?? 0} label="Items shared with other CPSEs" sub="candidates for joint buying" tone="good" />
            <Stat value={minePending.length} label="Pairs for you to decide" tone={minePending.length ? 'warn' : 'good'} />
            <Stat value={involving.length} label={`Pairs involving ${own}`} sub="registrar decides cross-company" />
          </>
        ) : (
          <>
            <Stat value={meta.records} label="Material records" sub={`${(meta.cpses || []).length} CPSEs`} />
            <Stat value={meta.unique_items} label="National codes issued" tone="accent" />
            <Stat value={t.duplicates} label="Duplicate records found" sub={`${((meta.duplication || 0) * 100).toFixed(0)}% of records`} tone="warn" />
            <Stat value={meta.auto_merged} label="Codes merged automatically" tone="good" />
            <Stat value={Math.max(0, (meta.review_pending || 0) - decidedCount)} label="Pairs awaiting a human" tone="warn" />
            <Stat value={refused} label="Unsafe merges refused" tone="danger" />
          </>
        )}
      </div>

      {/* tasks + activity */}
      <div className="grid xl:grid-cols-[1fr_1.1fr] gap-4 mb-4">
        <ChartCard title="Your tasks" sub="What your role can act on right now">
          <ul className="space-y-2.5">
            {tasks(session, { own, minePending, decidedCount, disputes, topSavings }).map((task) => (
              <li key={task.text}>
                <button onClick={() => go(task.to)}
                        className="w-full flex items-center gap-3 p-3 rounded border border-line hover:border-accent
                                   hover:bg-accent-dim text-left transition-colors group">
                  <span className={`w-9 h-9 rounded flex items-center justify-center shrink-0
                    ${task.tone === 'warn' ? 'bg-warn-bg text-warn' : task.tone === 'good' ? 'bg-good-bg text-good' : 'bg-accent-dim text-accent'}`}>
                    <Icon name={task.icon} size={18} />
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="block text-[14px] font-semibold text-heading">{task.text}</span>
                    <span className="block text-[12px] text-ink-faint">{task.sub}</span>
                  </span>
                  <Icon name="arrow" size={16} className="text-ink-faint group-hover:text-accent" />
                </button>
              </li>
            ))}
          </ul>
        </ChartCard>

        <ChartCard
          title="Recent activity"
          sub="Every sign-in and decision, as it happens"
          right={<button onClick={() => go('audit')} className="text-[12.5px] font-semibold text-accent hover:underline shrink-0">Audit trail →</button>}
        >
          {audit.length > 0 && (
            <ul>{audit.slice(0, 7).map((e) => <ActivityItem key={e.id} e={e} compact />)}</ul>
          )}
          {audit.length < 4 && (
            <p className="mt-3 rounded border border-dashed border-line px-3.5 py-3 text-[12.5px] text-ink-faint leading-relaxed">
              Approve a pair in the review queue, dispute a link in the catalogue, or download a mapping file —
              it appears here straight away, and in the audit trail.
            </p>
          )}
        </ChartCard>
      </div>

      <Evidence />

      {/* charts */}
      <div className="grid xl:grid-cols-[1.4fr_1fr] gap-4 mb-4">
        <ChartCard title="Records and national codes by company"
                   sub="The gap between the bars is duplication. Repeats inside a company need no data sharing to fix.">
          <Columns
            groups={rows.map((r) => ({ label: r.cpse, records: r.records, codes: r.codes, inside: r.inside }))}
            series={[
              { key: 'records', label: 'Material records', tone: 'accent' },
              { key: 'codes', label: 'National codes', tone: 'saffron' },
              { key: 'inside', label: 'Repeats inside the company', tone: 'warn' },
            ]}
          />
        </ChartCard>
        <ChartCard title="Where every candidate pair ended up" sub="Precision first: uncertain pairs go to a person">
          <Donut data={outcomes()} centre={outcomes().reduce((s, o) => s + o.value, 0)} centreLabel="decisions" />
        </ChartCard>
      </div>

      <div className="grid xl:grid-cols-2 gap-4 mb-4">
        <ChartCard title="Merges refused, by safety rule"
                   sub="A mismatch on any of these is an instant zero, however alike the text">
          <BarList data={refusals()} tone="danger" />
        </ChartCard>
        <ChartCard title="National codes by category" sub="Records per category, with UNSPSC classes">
          <BarList data={byCategory(own ? { cpse: own } : {}).map((c) => ({ label: `${c.category} · ${c.codes} codes`, value: c.records }))} />
        </ChartCard>
      </div>

      <ChartCard title={own ? `Top buying-together opportunities for ${own}` : 'Top buying-together opportunities'}
                 sub="Realistic saving at 40% capture. Items bought by fewer than 3 companies are hidden to protect prices."
                 right={<button onClick={() => go('savings')} className="text-[12.5px] font-semibold text-accent hover:underline shrink-0">Savings →</button>}>
        <div className="scroll-x">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-line">
                <th className="label text-left py-2 pr-4">Item</th>
                <th className="label text-left py-2 pr-4">Bought by</th>
                <th className="label text-right py-2 pr-4">Price spread</th>
                <th className="label text-right py-2">Realistic saving</th>
              </tr>
            </thead>
            <tbody>
              {topSavings.map((s) => (
                <tr key={s.national_code} className="border-b border-line-soft last:border-0">
                  <td className="py-2.5 pr-4">
                    <button onClick={() => go(`item/${s.national_code}`)} className="text-left">
                      <span className="block font-mono text-[11px] text-accent">{s.national_code}</span>
                      <span className="block text-ink">{s.description}</span>
                    </button>
                  </td>
                  <td className="py-2.5 pr-4 text-ink-dim">{s.cpse_count} CPSEs</td>
                  <td className="py-2.5 pr-4 text-right font-mono tnum text-danger">{s.price_spread_pct}%</td>
                  <td className="py-2.5 text-right font-mono tnum text-good font-semibold">{rupees(s.saving_realistic)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!topSavings.length && <p className="text-[13px] text-ink-faint py-2">No shared item with a visible benchmark.</p>}
        </div>
      </ChartCard>
    </div>
  )
}

function tasks(session, { own, minePending, decidedCount, disputes, topSavings }) {
  const role = session.role
  if (role === 'registrar') {
    return [
      { icon: 'review', to: 'review', tone: minePending.length ? 'warn' : 'good',
        text: `${minePending.length} cross-company pairs to decide`, sub: 'Links between two CPSEs are yours to issue' },
      { icon: 'flag', to: 'audit', tone: disputes ? 'warn' : 'accent',
        text: `${disputes} dispute${disputes === 1 ? '' : 's'} raised`, sub: 'A disputed link goes back to review' },
      { icon: 'gate', to: 'gate', text: 'Check a new material request', sub: 'The creation gate runs before any code is issued' },
      { icon: 'chart', to: 'analytics', text: 'Open analytics', sub: `${decidedCount} decisions taken in this session` },
    ]
  }
  if (role === 'reviewer') {
    return [
      { icon: 'review', to: 'review', tone: minePending.length ? 'warn' : 'good',
        text: minePending.length ? `${minePending.length} pairs inside ${own} to decide` : `No duplicates inside ${own} waiting — all clear`,
        sub: minePending.length ? 'Same-company duplicates are yours alone' : 'Cross-company links are decided by the registrar; you can still dispute them' },
      { icon: 'search', to: 'catalogue', text: `Check links to ${own} codes`, sub: 'Dispute any link you think is wrong' },
      { icon: 'migrate', to: 'migration', text: `Download ${own}'s mapping file`, sub: 'SAP-shaped: your code → national code' },
      { icon: 'units', to: 'units', text: 'Fix unit spellings', sub: 'Conflicts inside your own company' },
    ]
  }
  if (role === 'procurement') {
    const best = topSavings[0]
    return [
      { icon: 'rupee', to: 'analytics', tone: 'good',
        text: best ? `${rupees(best.saving_realistic)} saving on one item` : 'Price benchmarks', sub: best ? best.description : 'See where you pay above the best price' },
      { icon: 'chart', to: 'analytics', text: 'Compare your prices', sub: 'Other companies appear only as a benchmark' },
      { icon: 'migrate', to: 'migration', text: `Download ${own}'s mapping file`, sub: 'Codes to use in a joint tender' },
    ]
  }
  return [
    { icon: 'chart', to: 'analytics', text: 'Analytics across all CPSEs', sub: 'Duplication, prices, units, safety' },
    { icon: 'audit', to: 'audit', text: 'Read the audit trail', sub: 'Who decided what, and when' },
    { icon: 'search', to: 'catalogue', text: 'Browse the national catalogue', sub: `${meta.unique_items} national codes` },
  ]
}
