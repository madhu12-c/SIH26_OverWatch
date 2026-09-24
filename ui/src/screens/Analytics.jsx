import { useState } from 'react'
import { rupees, rupeesExact } from '../lib/format'
import { ROLES, can } from '../lib/store'
import { CPSES, CATEGORIES, perCpse, byCategory, priceSpread, unitConflictsByCpse, refusals, totals } from '../lib/analytics'
import { SectionTitle, Stat } from '../components/Primitives'
import { ChartCard, BarList, Columns, Dumbbell } from '../components/Charts'

/*
 * Analytics, with filters that every chart obeys.
 *
 * Prices follow the federated rule even here: a company user sees its own
 * price in full and every other company only as an unnamed dot - the
 * benchmark without the attribution. Registrar and ministry see names.
 */

export default function Analytics({ session }) {
  const own = ROLES[session.role]?.needsOrg ? session.org : null
  const [cpse, setCpse] = useState('')
  const [category, setCategory] = useState('')
  const filter = { cpse: cpse || undefined, category: category || undefined }

  const t = totals(filter)
  const rows = perCpse({ category: filter.category })
  const spread = priceSpread(filter)
  const nameOf = (c) => (c === own ? 'own' : can(session, 'see_prices', { cpse: c }).ok)
  const seeAllSpend = !own

  return (
    <div>
      <SectionTitle
        eyebrow="Analytics"
        title="Duplication, prices, units and safety — across the registry"
        sub="Every chart is computed from the pipeline's output. Choose a company or a category to narrow them all."
      />

      {/* filters */}
      <div className="card px-4 py-3 mb-5 flex flex-wrap items-center gap-x-5 gap-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="label mr-1">Company</span>
          {['', ...CPSES].map((c) => (
            <button key={c || 'all'} onClick={() => setCpse(c)} aria-pressed={cpse === c}
                    className={`px-2.5 py-1 rounded border text-[12.5px] font-semibold
                      ${cpse === c ? 'bg-gov text-white border-gov' : 'border-line text-ink-dim hover:border-accent/60'}`}>
              {c || 'All'}{c && c === own ? ' (you)' : ''}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2">
          <span className="label">Category</span>
          <select value={category} onChange={(e) => setCategory(e.target.value)}
                  className="rounded border border-line bg-base-card px-2.5 py-1.5 text-[13px] text-ink capitalize">
            <option value="">All categories</option>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        {(cpse || category) && (
          <button onClick={() => { setCpse(''); setCategory('') }} className="text-[12.5px] text-accent hover:underline ml-auto">
            Clear filters
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <Stat value={t.records} label="Material records" sub={cpse || 'all companies'} />
        <Stat value={t.codes} label="National codes" tone="accent" />
        <Stat value={t.duplicates} label="Duplicate records" tone="warn" />
        <Stat value={spread.filter((s) => !s.suppressed).length} label="Items with a price benchmark" tone="good" />
      </div>

      <div className="grid xl:grid-cols-[1.4fr_1fr] gap-4 mb-4">
        <ChartCard title="Duplication by company"
                   sub={category ? `Category: ${category}` : 'All categories'}>
          <Columns
            groups={rows.map((r) => ({ label: r.cpse, records: r.records, codes: r.codes, inside: r.inside, shared: r.shared }))}
            series={[
              { key: 'records', label: 'Records', tone: 'accent' },
              { key: 'codes', label: 'National codes', tone: 'saffron' },
              { key: 'inside', label: 'Repeats inside', tone: 'warn' },
              { key: 'shared', label: 'Shared with others', tone: 'good' },
            ]}
          />
        </ChartCard>
        <ChartCard title="Records by category" sub={cpse ? `Company: ${cpse}` : 'All companies'}>
          <BarList data={byCategory(filter).map((c) => ({ label: c.category, value: c.records }))} />
        </ChartCard>
      </div>

      <ChartCard className="mb-4"
                 title="What each company pays for the same item"
                 sub={own
                   ? `Your price is named; other companies appear only as unnamed dots — a benchmark, never who got it.`
                   : 'Each dot is one company\'s average price. Green is the best price observed.'}>
        {spread.length ? (
          <Dumbbell rows={spread.slice(0, 8)} format={(v) => rupeesExact(v)} nameOf={nameOf} />
        ) : (
          <p className="text-[13px] text-ink-faint">No item bought by two or more companies in this filter.</p>
        )}
      </ChartCard>

      <div className="grid xl:grid-cols-3 gap-4 mb-4">
        <ChartCard title="Spend on shared items" sub={seeAllSpend ? 'By company' : 'Yours only — others are private'}>
          <BarList
            data={rows
              .filter((r) => seeAllSpend || r.cpse === own)
              .map((r) => ({ label: r.cpse, value: r.spend }))
              .sort((a, b) => b.value - a.value)}
            tone="accent"
            format={(v) => rupees(v)}
          />
        </ChartCard>
        <ChartCard title="Unit spelling conflicts" sub="Items where one company writes the unit two ways">
          <BarList data={unitConflictsByCpse()} tone="warn" />
        </ChartCard>
        <ChartCard title="Merges refused, by rule" sub="Safety vetoes across the registry">
          <BarList data={refusals()} tone="danger" />
        </ChartCard>
      </div>
    </div>
  )
}
