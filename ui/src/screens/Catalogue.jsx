import { useMemo, useState } from 'react'
import { clusters } from '../lib/data'
import { ROLES } from '../lib/store'
import { CATEGORIES } from '../lib/analytics'
import { SectionTitle, Chip } from '../components/Primitives'
import { Icon } from '../components/Icons'

/*
 * The national catalogue - search by national code, by standard description,
 * or by any company's own code or wording. The last one is the point: a
 * storekeeper who types "BRG BALL DP GRV 6205" finds the national code even
 * though the catalogue itself never writes it that way.
 */

const BAND = { auto: ['good', 'auto-merged'], review: ['warn', 'in review'], single: ['faint', 'single record'] }

export default function Catalogue({ session, go }) {
  const own = ROLES[session.role]?.needsOrg ? session.org : null
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [onlyOwn, setOnlyOwn] = useState(false)

  const results = useMemo(() => {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean)
    return clusters.filter((c) => {
      if (category && c.category !== category) return false
      if (onlyOwn && own && !(c.cpses || []).includes(own)) return false
      if (!words.length) return true
      const hay = [c.national_code, c.std_description, c.category, c.unspsc_name,
        ...(c.members || []).flatMap((m) => [m.description, m.source_code, m.cpse])].join(' ').toLowerCase()
      return words.every((w) => hay.includes(w))
    })
  }, [q, category, onlyOwn, own])

  return (
    <div>
      <SectionTitle
        eyebrow="National catalogue"
        title="Find a national code — by any company's wording"
        sub="Search by national code, standard description, or a company's own code or description. Every result lists every company code linked to it."
      />

      <div className="card p-4 mb-5">
        <label className="relative block">
          <span className="sr-only">Search the catalogue</span>
          <Icon name="search" size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="e.g. 6205   ·   SS304 gasket   ·   BR-01454   ·   gate valve 150"
            className="w-full rounded border border-line bg-base-card pl-10 pr-3 py-2.5 text-[14px] text-ink
                       placeholder:text-ink-faint focus:border-accent"
          />
        </label>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="label mr-1">Category</span>
          {['', ...CATEGORIES].map((c) => (
            <button key={c || 'all'} onClick={() => setCategory(c)} aria-pressed={category === c}
                    className={`px-2.5 py-1 rounded border text-[12px] font-semibold capitalize
                      ${category === c ? 'bg-gov text-white border-gov' : 'border-line text-ink-dim hover:border-accent/60'}`}>
              {c || 'All'}
            </button>
          ))}
          {own && (
            <label className="ml-auto flex items-center gap-2 text-[12.5px] text-ink-dim cursor-pointer">
              <input type="checkbox" checked={onlyOwn} onChange={(e) => setOnlyOwn(e.target.checked)} />
              Only codes linked to {own}
            </label>
          )}
        </div>
      </div>

      <p className="text-[12.5px] text-ink-faint mb-2">
        {results.length} of {clusters.length} national codes
      </p>

      <div className="card overflow-hidden">
        <div className="scroll-x">
          <table className="w-full text-[13px]">
            <thead className="bg-base-raised">
              <tr className="border-b border-line">
                <th className="label text-left py-2.5 px-4">National code · description</th>
                <th className="label text-left py-2.5 px-3">Category</th>
                <th className="label text-left py-2.5 px-3">Linked companies</th>
                <th className="label text-right py-2.5 px-3">Records</th>
                <th className="label text-left py-2.5 px-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {results.map((c) => {
                const [tone, label] = BAND[c.band] ?? ['faint', c.band]
                return (
                  <tr key={c.national_code} onClick={() => go(`item/${c.national_code}`)}
                      className="border-b border-line-soft last:border-0 hover:bg-accent-dim/50 cursor-pointer">
                    <td className="py-3 px-4">
                      <button onClick={(e) => { e.stopPropagation(); go(`item/${c.national_code}`) }}
                              className="font-mono text-[12px] font-semibold text-accent hover:underline">
                        {c.national_code}
                      </button>
                      <span className="block text-ink mt-0.5">{c.std_description}</span>
                    </td>
                    <td className="py-3 px-3 text-ink-dim capitalize whitespace-nowrap">
                      {c.category}
                      <span className="block text-[11px] text-ink-faint normal-case">{c.unspsc_name}</span>
                    </td>
                    <td className="py-3 px-3">
                      <span className="flex flex-wrap gap-1">
                        {(c.cpses || []).map((x) => (
                          <span key={x} className={`font-mono text-[10.5px] font-semibold px-1.5 py-0.5 rounded border
                            ${x === own ? 'bg-saffron-bg text-saffron-ink border-saffron/50' : 'bg-base-raised text-ink-dim border-line-soft'}`}>
                            {x}
                          </span>
                        ))}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right font-mono tnum">{c.member_count}</td>
                    <td className="py-3 px-3"><Chip tone={tone}>{label}</Chip></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {!results.length && (
            <p className="p-6 text-center text-[13.5px] text-ink-dim">
              Nothing matches. If this material is new, check it at the{' '}
              <button onClick={() => go('gate')} className="text-accent font-semibold hover:underline">creation gate</button>.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
