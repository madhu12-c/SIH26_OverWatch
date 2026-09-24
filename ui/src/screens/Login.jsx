import { useState } from 'react'
import { motion } from 'framer-motion'
import { meta, savingsSummary, real } from '../lib/data'
import { ROLES, signIn } from '../lib/store'
import { CountUp } from '../components/Primitives'
import { Icon } from '../components/Icons'

/*
 * The sign-in page. There is no server, so there are no accounts: signing in
 * PICKS A ROLE, and the page says so. What the role changes is real - which
 * pairs you may decide, which codes you may retire, whose prices you may
 * see - and that is the consent model shown working rather than described.
 */

const ROLE_ICON = { registrar: 'gate', reviewer: 'review', procurement: 'rupee', ministry: 'chart' }

export default function Login() {
  const cpses = meta.cpses || []
  const [role, setRole] = useState('registrar')
  const [org, setOrg] = useState(cpses.includes('CPCL') ? 'CPCL' : cpses[0])
  const r = ROLES[role]
  const who = r.needsOrg ? `${org} ${r.short}` : r.label
  const userId = `${(r.needsOrg ? `${org}.${r.short}` : r.short).toLowerCase().replace(/\s+/g, '')}@nmcr.demo`

  const submit = (e) => {
    e.preventDefault()
    signIn(role, org)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-5 py-8">
      <div className="grid lg:grid-cols-[1.25fr_1fr] gap-6 items-start">
        {/* about the registry */}
        <section className="relative overflow-hidden rounded-xl bg-gov text-white">
          <div className="jaali absolute inset-0" aria-hidden="true" />
          <div className="absolute inset-y-0 left-0 w-1.5 bg-saffron" aria-hidden="true" />
          <div className="relative p-6 sm:p-8">
            <p className="text-[11.5px] font-bold uppercase tracking-[0.1em] text-saffron">
              Problem statement SIH26099 · set by MoPNG · CPCL
            </p>
            <h1 className="mt-2.5 text-[28px] sm:text-[34px] font-bold leading-[1.1] tracking-tight">
              One Nation, One Material Code
            </h1>
            <p lang="hi" className="font-deva text-[17px] text-white/85 mt-1">एक राष्ट्र, एक सामग्री कोड</p>
            <p className="mt-4 text-[15px] leading-relaxed text-white/85 max-w-xl">
              Every CPSE writes the same item its own way, under its own code. The registry compares
              what an item <em>is</em> — size, grade, rating — not how it is spelled, issues one national
              code per item, and links every company's own code to it.{' '}
              <span className="text-white font-medium">No company's code is changed or deleted.</span>
            </p>

            <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Kpi value={meta.records} label="Material records" />
              <Kpi value={meta.unique_items} label="National codes" />
              <Kpi value={(meta.duplication || 0) * 100} decimals={1} suffix="%" label="Duplication found" />
              <Kpi value={(savingsSummary.saving_realistic || 0) / 1e5} decimals={1} prefix="₹" suffix=" L"
                   label="Saving identified" />
            </div>

            <ol className="mt-7 grid sm:grid-cols-2 gap-x-6 gap-y-3.5">
              {[
                ['Upload', 'A CPSE uploads its material list. Original lines are kept exactly as written.'],
                ['Read', 'Each line is read into facts: type, size, grade, pressure class.'],
                ['Compare', 'One mismatch in a critical fact refuses the merge, however alike the words.'],
                ['Link', 'One national code per item. Every company keeps its own code underneath.'],
              ].map(([t, d], i) => (
                <li key={t} className="flex gap-3">
                  <span className="w-7 h-7 shrink-0 rounded-full bg-saffron text-[#061C40] text-[13px] font-bold
                                   flex items-center justify-center">{i + 1}</span>
                  <span>
                    <span className="block text-[14px] font-semibold">{t}</span>
                    <span className="block text-[12.5px] text-white/75 leading-snug">{d}</span>
                  </span>
                </li>
              ))}
            </ol>
          </div>
          <div className="relative border-t border-white/15 px-6 sm:px-8 py-2.5 text-[12px] text-white/70">
            Figures measured on {meta.records} synthetic test records.
            {real.lines ? ` ${real.lines} real tender lines from Oil India and NTPC are being labelled for the real-world test.` : ''}
          </div>
        </section>

        {/* sign in */}
        <motion.form
          onSubmit={submit}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="card overflow-hidden"
          aria-labelledby="signin"
        >
          <div className="px-6 pt-5 pb-4 border-b border-line-soft">
            <h2 id="signin" className="text-[20px] font-bold text-heading flex items-center gap-2">
              <Icon name="lock" size={20} className="text-accent" /> Sign in
            </h2>
            <p className="mt-1 text-[12.5px] text-ink-dim leading-relaxed">
              Demo sign-in. This prototype has no real accounts — choosing a role shows what that role is
              allowed to do.
            </p>
          </div>

          <div className="px-6 py-5 space-y-5">
            <fieldset>
              <legend className="text-[13px] font-semibold text-ink mb-2">1. Choose your role</legend>
              <div className="grid gap-2">
                {Object.entries(ROLES).map(([id, x]) => {
                  const on = id === role
                  return (
                    <label key={id}
                           className={`flex gap-3 items-start p-3 rounded border cursor-pointer transition-colors
                             ${on ? 'border-accent bg-accent-dim' : 'border-line hover:border-accent/50 hover:bg-base-raised'}`}>
                      <input type="radio" name="role" value={id} checked={on} onChange={() => setRole(id)}
                             className="sr-only" />
                      <span className={`w-9 h-9 shrink-0 rounded flex items-center justify-center
                        ${on ? 'bg-accent text-onaccent' : 'bg-base-raised text-ink-dim'}`}>
                        <Icon name={ROLE_ICON[id]} size={18} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-2">
                          <span className="text-[14px] font-semibold text-heading">{x.label}</span>
                          {on && <Icon name="check" size={16} className="text-accent" strokeWidth={2.4} />}
                        </span>
                        <span className="block text-[12.5px] text-ink-dim leading-snug mt-0.5">{x.blurb}</span>
                      </span>
                    </label>
                  )
                })}
              </div>
            </fieldset>

            {r.needsOrg && (
              <fieldset>
                <legend className="text-[13px] font-semibold text-ink mb-2">2. Choose your company</legend>
                <div className="flex flex-wrap gap-2">
                  {cpses.map((c) => (
                    <button type="button" key={c} onClick={() => setOrg(c)} aria-pressed={org === c}
                            className={`px-3.5 py-1.5 rounded border text-[13px] font-semibold font-mono
                              ${org === c ? 'bg-gov text-white border-gov' : 'border-line text-ink-dim hover:border-accent/60'}`}>
                      {c}
                    </button>
                  ))}
                </div>
              </fieldset>
            )}

            <div className="grid sm:grid-cols-2 gap-3">
              <label className="block">
                <span className="text-[12px] font-semibold text-ink-dim">User ID</span>
                <input readOnly value={userId}
                       className="mt-1 w-full rounded border border-line bg-base-raised px-3 py-2 font-mono text-[12.5px] text-ink" />
              </label>
              <label className="block">
                <span className="text-[12px] font-semibold text-ink-dim">Password</span>
                <input readOnly value="not needed in the demo"
                       className="mt-1 w-full rounded border border-line bg-base-raised px-3 py-2 text-[12.5px] text-ink-faint" />
              </label>
            </div>

            <div className="rounded border border-line-soft bg-base-raised px-3.5 py-3">
              <p className="text-[12px] font-semibold text-ink mb-1.5">As {who} you can</p>
              <ul className="space-y-1">
                {r.rights.map((x) => (
                  <li key={x} className="flex gap-2 text-[12.5px] text-ink-dim">
                    <Icon name="check" size={14} className="text-good mt-0.5" strokeWidth={2.4} /> {x}
                  </li>
                ))}
              </ul>
            </div>

            <button type="submit"
                    className="w-full inline-flex items-center justify-center gap-2 bg-gov text-white font-semibold
                               text-[14.5px] py-3 rounded hover:bg-gov-soft transition-colors">
              Sign in as {who} <Icon name="arrow" size={17} strokeWidth={2.2} />
            </button>
          </div>
        </motion.form>
      </div>
    </div>
  )
}

function Kpi({ value, label, decimals = 0, prefix, suffix }) {
  return (
    <div className="rounded bg-white/[0.08] border border-white/15 px-3.5 py-3">
      <div className="text-[22px] font-bold leading-none tracking-tight">
        <CountUp to={value} decimals={decimals} prefix={prefix} suffix={suffix} />
      </div>
      <div className="mt-1.5 text-[11.5px] text-white/80">{label}</div>
    </div>
  )
}
