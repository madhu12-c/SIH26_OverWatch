import { useState } from 'react'
import { clusters, uomFamilies } from '../lib/data'
import { ROLES, can, log, useAudit } from '../lib/store'
import { CPSES } from '../lib/analytics'
import { SectionTitle, Stat, Chip } from '../components/Primitives'
import { Icon } from '../components/Icons'

/*
 * Migration: each company's own codes, mapped to national codes, as a file
 * its SAP team can load.
 *
 * The file is SAP-SHAPED - material number, 40-character description, base
 * unit, material group, plus the national code in a custom field - because
 * that is what a load template expects. There is no live SAP connection and
 * the page says so.
 *
 * Nothing is applied blindly. Only auto-merged codes are "safe to apply";
 * anything in review or disputed is held, with the reason.
 */

const unitOf = (() => {
  const map = {}
  for (const f of uomFamilies || []) for (const v of f.variants || []) map[v.raw] = f.canonical
  return (raw) => map[raw] || raw
})()

export default function Migration({ session }) {
  const own = ROLES[session.role]?.needsOrg ? session.org : null
  const [cpse, setCpse] = useState(own || CPSES[0])
  const [msg, setMsg] = useState(null)
  const audit = useAudit()
  const disputed = new Set(audit.filter((e) => e.verb === 'DISPUTE').map((e) => e.object))

  // A few dozen rows - recomputed on every render, so a dispute raised on
  // another page shows here as "held" straight away.
  const rows = clusters.flatMap((c) =>
    (c.members || []).filter((m) => m.cpse === cpse).map((m) => {
      const status = disputed.has(c.national_code) ? 'disputed'
        : c.band === 'auto' ? 'safe' : c.band === 'review' ? 'held' : 'new'
      return { ...m, code: c.national_code, std: c.std_description, unspsc: c.unspsc, status }
    }))

  const count = (s) => rows.filter((r) => r.status === s).length
  const allowed = can(session, 'export', { cpse })

  const download = () => {
    if (!allowed.ok) {
      log('DENIED', { object: `${cpse} mapping file`, note: allowed.why })
      setMsg({ tone: 'danger', text: allowed.why })
      return
    }
    const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
    const head = ['MATNR', 'MAKTX', 'MEINS', 'MATKL', 'ZZNMC', 'ZZSTATUS', 'ORIGINAL_DESCRIPTION']
    const lines = rows.map((r) => [r.source_code, r.std.slice(0, 40), unitOf(r.uom), r.unspsc, r.code,
      { safe: 'APPLY', held: 'HOLD-REVIEW', disputed: 'HOLD-DISPUTED', new: 'APPLY-NEW' }[r.status], r.description].map(esc).join(','))
    const blob = new Blob(['﻿' + [head.join(','), ...lines].join('\r\n')], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `NMC_mapping_${cpse}_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(a.href)
    log('EXPORT', { object: `${cpse} mapping file`, note: `${rows.length} rows: ${count('safe') + count('new')} to apply, ${count('held') + count('disputed')} held.` })
    setMsg({ tone: 'good', text: `Downloaded ${rows.length} rows for ${cpse}. Held rows are marked and must not be loaded yet.` })
  }

  const STATUS = {
    safe: ['good', 'safe to apply'],
    new: ['accent', 'new code, no duplicate'],
    held: ['warn', 'held — in review'],
    disputed: ['danger', 'held — disputed'],
  }

  return (
    <div>
      <SectionTitle
        eyebrow="Migration"
        title="Each company's codes, mapped — ready for its SAP team"
        sub="A dry run first: what would change, what is safe, what is held and why. The download is a SAP-shaped load file. There is no live SAP connection in this prototype."
      />

      <div className="card px-4 py-3 mb-5 flex flex-wrap items-center gap-2">
        <span className="label mr-1">Company</span>
        {CPSES.map((c) => {
          const locked = own && c !== own
          return (
            <button key={c} onClick={() => !locked && setCpse(c)} disabled={locked} aria-pressed={cpse === c}
                    title={locked ? 'You can open only your own company' : undefined}
                    className={`px-3 py-1 rounded border text-[12.5px] font-semibold font-mono
                      ${cpse === c ? 'bg-gov text-white border-gov'
                        : locked ? 'border-line-soft text-ink-faint/60 cursor-not-allowed'
                        : 'border-line text-ink-dim hover:border-accent/60'}`}>
              {c}
            </button>
          )
        })}
        {own && <span className="text-[12px] text-ink-faint ml-2">Signed in for {own} — other companies are locked.</span>}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <Stat value={rows.length} label={`${cpse} codes in the file`} />
        <Stat value={count('safe') + count('new')} label="Safe to apply" tone="good" />
        <Stat value={count('held')} label="Held — in review" tone="warn" />
        <Stat value={count('disputed')} label="Held — disputed" tone="danger" />
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-3 border-b border-line-soft flex flex-wrap items-center gap-3">
          <div>
            <h2 className="text-[15px] font-bold text-heading">Dry run for {cpse}</h2>
            <p className="text-[12px] text-ink-faint">Nothing is deleted. The company's code stays; the national code is added beside it.</p>
          </div>
          <button onClick={download}
                  className="ml-auto inline-flex items-center gap-2 bg-gov text-white text-[13px] font-semibold
                             px-3.5 py-2 rounded hover:bg-gov-soft">
            <Icon name="download" size={16} /> Download SAP load file (CSV)
          </button>
        </div>
        {msg && (
          <div className={`px-5 py-2.5 text-[13px] ${msg.tone === 'good' ? 'bg-good-bg text-good' : 'bg-danger-bg text-danger'}`}>
            {msg.text}
          </div>
        )}
        <div className="scroll-x">
          <table className="w-full text-[12.5px]">
            <thead className="bg-base-raised">
              <tr className="border-b border-line">
                <th className="label text-left py-2 px-4">{cpse} code</th>
                <th className="label text-left py-2 px-3">As written</th>
                <th className="label text-left py-2 px-3">Unit</th>
                <th className="label text-left py-2 px-3">National code</th>
                <th className="label text-left py-2 px-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const [tone, label] = STATUS[r.status]
                const u = unitOf(r.uom)
                return (
                  <tr key={r.record_id} className="border-b border-line-soft last:border-0">
                    <td className="py-2.5 px-4 font-mono font-semibold text-ink whitespace-nowrap">{r.source_code}</td>
                    <td className="py-2.5 px-3 font-mono text-[12px] text-ink-dim">{r.description}</td>
                    <td className="py-2.5 px-3 font-mono whitespace-nowrap">
                      {r.uom === u ? u : <><span className="text-ink-faint line-through">{r.uom}</span> → {u}</>}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-accent whitespace-nowrap">{r.code}</td>
                    <td className="py-2.5 px-4"><Chip tone={tone}>{label}</Chip></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
