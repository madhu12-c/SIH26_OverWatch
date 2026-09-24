import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { gate, gateScenarios } from '../lib/data'
import { SectionTitle, Chip } from '../components/Primitives'

/*
 * Screen 08 - the creation gate.
 *
 * Every other screen cleans up the past. This one is the only forward-looking
 * thing in the build, and it is the answer to the question a ministry judge
 * always asks: you cleaned our data, what stops it getting dirty again?
 *
 * THE HONEST FRAMING, which is stronger than claiming invention: every ERP
 * already has a duplicate check on code creation. SAP has one. It fails on
 * this data because it searches SPELLING - the stored record reads
 * GSKT SPRL WND SS316 4IN and the storekeeper types "spiral wound gasket 316",
 * so nothing comes back and a new code is born. We are not adding a check
 * that does not exist; we are replacing one that does not work.
 *
 * The verdict worth demonstrating is NEW, not EXISTS. A gate that only says
 * "already catalogued" is a search box. A gate that says "new - and this is
 * NOT your SS304 or SS316 gasket, the grade differs" is the safety interlock
 * pointed forwards, and nothing else in the room will have it.
 */

const TONE = {
  EXISTS: { chip: 'good', ink: 'text-good', bar: 'bg-good', bg: 'bg-good-bg',
            edge: 'border-good/30', title: 'Already catalogued' },
  REVIEW: { chip: 'warn', ink: 'text-warn', bar: 'bg-warn', bg: 'bg-warn-bg',
            edge: 'border-warn/30', title: 'Send to a cataloguer' },
  NEW:    { chip: 'accent', ink: 'text-accent', bar: 'bg-accent', bg: 'bg-accent-dim',
            edge: 'border-accent/30', title: 'Genuinely new' },
  // An underspecified record is not a new item, it is an unfinished one. It
  // gets its own verdict so it can never fall through into a minted code.
  INCOMPLETE: { chip: 'warn', ink: 'text-warn', bar: 'bg-warn', bg: 'bg-warn-bg',
                edge: 'border-warn/30', title: 'Not enough specification' },
}

function Attr({ name, value, matched }) {
  return (
    <div className="flex items-baseline gap-2 py-[3px]">
      <span className={`shrink-0 w-3 text-[11px] font-mono ${matched ? 'text-good' : 'text-line'}`}>
        {matched ? '✓' : '·'}
      </span>
      <span className="font-mono text-[11.5px] text-ink-faint w-[128px] shrink-0 truncate">
        {name}
      </span>
      <span className="font-mono text-[12px] text-ink break-words">{String(value)}</span>
    </div>
  )
}

export default function Gate() {
  const [active, setActive] = useState(0)

  if (!gateScenarios.length) {
    return (
      <div className="max-w-5xl mx-auto">
        <SectionTitle
          eyebrow="Creation gate"
          title="Not generated yet"
          sub="Run python src/gate.py --scenarios, then python src/results.py."
        />
      </div>
    )
  }

  const s = gateScenarios[active]
  const tone = TONE[s.verdict] ?? TONE.REVIEW
  const matched = new Set(s.best?.matched_fields ?? [])
  const ignored = new Set(s.best?.ignored_fields ?? [])
  const attrs = Object.entries(s.extracted?.attributes ?? {})

  return (
    <div className="max-w-5xl mx-auto">
      <SectionTitle
        eyebrow="Creation gate"
        title="The check that runs before a new code is issued"
        sub="Every ERP already has a duplicate check. It searches spelling, so on this data it finds nothing and a new code is created. This one compares specifications — and when it admits a new item, it says what that item is not."
      />

      {/* Scenario picker. Each is a real description; the first two are taken
          straight from materials.csv rather than written for the stage. */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {gateScenarios.map((sc, i) => (
          <button
            key={sc.id}
            onClick={() => setActive(i)}
            className={`px-3 py-1.5 rounded-lg text-[12.5px] border transition-colors
              ${i === active
                ? 'bg-accent-dim border-accent/30 text-ink font-medium'
                : 'bg-base-card border-line text-ink-faint hover:text-ink-dim hover:bg-base-raised'}`}
          >
            <span className={`font-mono text-[10px] mr-1.5
                              ${i === active ? 'text-accent' : 'opacity-60'}`}>
              {String(i + 1).padStart(2, '0')}
            </span>
            {sc.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={s.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.25 }}
        >
          <p className="text-[13px] text-ink-dim mb-3 leading-relaxed max-w-2xl">{s.note}</p>

          {/* The incoming description, shown the way it is typed. */}
          <div className="card p-0 overflow-hidden mb-3">
            <div className="px-4 py-2 bg-base-raised border-b border-line-soft flex items-center gap-2">
              <span className="label">incoming description</span>
              <span className="ml-auto text-[11px] text-ink-faint">
                a storekeeper is about to create a code for this
              </span>
            </div>
            <p className="px-4 py-3.5 font-mono text-[14px] text-ink break-words">
              {s.input}
            </p>
          </div>

          {/* Verdict. */}
          <div className={`card p-0 overflow-hidden mb-3 ${tone.edge}`}>
            <span className={`block h-[3px] ${tone.bar}`} />
            <div className={`px-4 py-3.5 ${tone.bg}`}>
              <div className="flex flex-wrap items-center gap-2 mb-1.5">
                <Chip tone={tone.chip}>{s.verdict}</Chip>
                <span className={`text-[14px] font-semibold ${tone.ink}`}>{tone.title}</span>
                <span className="ml-auto text-[11px] text-ink-faint font-mono tnum">
                  {s.compared_against} codes checked
                </span>
              </div>
              <p className="text-[13px] text-ink leading-relaxed">{s.message}</p>
              {s.missing_hard?.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
                  <span className="label">not verified</span>
                  {s.missing_hard.map((f) => (
                    <span key={f} className="font-mono text-[11px] px-1.5 py-[2px] rounded
                                             bg-base-card border border-warn/30 text-warn">
                      {f.replace(/_/g, ' ')}
                    </span>
                  ))}
                  <span className="text-[11px] text-ink-faint">
                    — a safety field nobody extracted is a field nobody checked
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-3">
            {/* What we read out of the text, with no model call. */}
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-2.5">
                <span className="label">extracted</span>
                <span className="text-[10.5px] font-mono text-ink-faint px-1.5 py-[1px]
                                 rounded bg-base-raised border border-line-soft">
                  {s.extracted?.method}
                </span>
                <span className="ml-auto text-[11px] text-ink-faint">
                  {s.extracted?.category}
                </span>
              </div>
              {attrs.length === 0 && (
                <p className="text-[12px] text-ink-faint">nothing extracted</p>
              )}
              {attrs.map(([k, v]) => (
                <Attr key={k} name={k} value={v}
                      matched={matched.has(k) && !ignored.has(k)} />
              ))}
              {ignored.size > 0 && (
                <p className="mt-2.5 pt-2.5 border-t border-line-soft text-[11.5px] text-ink-faint">
                  ignored in matching:{' '}
                  <span className="font-mono">{[...ignored].join(', ')}</span> — brand and
                  part number never count toward a match, which is what lets two
                  manufacturers resolve to one item.
                </p>
              )}
            </div>

            {/* The best candidate, if any survived. */}
            <div className="card p-4">
              <span className="label">best candidate</span>
              {s.best && s.best.final > 0 ? (
                <div className="mt-2.5">
                  <div className="flex items-baseline gap-2 mb-1">
                    <span className="font-mono text-[11.5px] text-accent">
                      {s.best.national_code}
                    </span>
                    <span className={`ml-auto font-mono text-[19px] font-semibold tnum ${tone.ink}`}>
                      {s.best.final?.toFixed(3)}
                    </span>
                  </div>
                  <p className="font-mono text-[12px] text-ink-dim break-words mb-3">
                    {s.best.std_description}
                  </p>
                  <div className="grid grid-cols-2 gap-2 text-[11.5px]">
                    <div className="well px-2.5 py-1.5">
                      <div className="label mb-0.5">text</div>
                      <div className="font-mono tnum text-ink-dim">{s.best.text_sim}</div>
                    </div>
                    <div className="well px-2.5 py-1.5">
                      <div className="label mb-0.5">specs</div>
                      <div className="font-mono tnum text-ink">{s.best.spec_sim}</div>
                    </div>
                  </div>
                  <p className="mt-2.5 text-[11.5px] text-ink-faint">
                    held by {s.best.cpse_count} CPSE{s.best.cpse_count === 1 ? '' : 's'}
                    {s.best.cpses?.length ? ` — ${s.best.cpses.join(', ')}` : ''}
                  </p>
                </div>
              ) : (
                <p className="mt-2.5 text-[12.5px] text-ink-dim leading-relaxed">
                  {s.verdict === 'INCOMPLETE'
                    ? 'No candidate was even considered. Nothing is scored, and no code is issued, until the description carries enough to compare — matching an underspecified record against the catalogue would be guessing.'
                    : 'Nothing in the catalogue survived the safety rules. A new national code is issued, and the near misses are recorded beside it.'}
                </p>
              )}
            </div>
          </div>

          {/* THE POINT OF THE SCREEN. Everyone can show a match. Showing what
              the system refused to match, at the moment of creation, is what
              a refinery audience recognises. */}
          {s.distinguished_from?.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, duration: 0.3 }}
              className="card mt-3 overflow-hidden border-danger/25"
            >
              <div className="px-4 py-2.5 bg-danger-bg border-b border-danger/20">
                <div className="flex flex-wrap items-center gap-2">
                  <Chip tone="danger">not the same item</Chip>
                  <span className="text-[12.5px] text-ink">
                    Close enough that a fuzzy matcher would have merged these
                  </span>
                </div>
              </div>
              {s.distinguished_from.map((b) => (
                <div key={b.national_code}
                     className="px-4 py-3 border-b border-line-soft last:border-0">
                  <div className="flex flex-wrap items-baseline gap-2 mb-1">
                    <span className="font-mono text-[11.5px] text-accent">
                      {b.national_code}
                    </span>
                    <span className="font-mono text-[11.5px] text-danger font-semibold">
                      {b.blocked_by?.replace(/_/g, ' ')} — {b.reason}
                    </span>
                    <span className="ml-auto text-[11px] text-ink-faint font-mono tnum">
                      text {b.text_sim}
                    </span>
                  </div>
                  <p className="font-mono text-[12px] text-ink-dim break-words">
                    {b.std_description}
                  </p>
                </div>
              ))}
              <p className="px-4 py-2.5 text-[11.5px] text-ink-faint bg-base-raised">
                A hard field mismatch is an instant zero regardless of how well
                everything else lines up. In a refinery the grade is not a detail —
                it decides whether the part survives the service.
              </p>
            </motion.div>
          )}
        </motion.div>
      </AnimatePresence>

      <div className="mt-6 grid sm:grid-cols-2 gap-3">
        <div className="well p-3.5">
          <span className="label">where it runs</span>
          <p className="mt-1.5 text-[12.5px] text-ink-dim leading-relaxed">
            The registry publishes the catalogue downward and the check runs inside
            the CPSE against a local copy. No price, vendor or quantity leaves the
            company, and it works with the network down. Only the issuing of a
            genuinely new code travels back up.
          </p>
        </div>
        <div className="well p-3.5">
          <span className="label">what it costs</span>
          <p className="mt-1.5 text-[12.5px] text-ink-dim leading-relaxed">
            One incoming record against {gate.index?.codes ?? 0} golden records — not
            against every raw record, and it stays that size as the estate grows.
            No model call: extraction runs offline, so nothing here needs internet.
          </p>
        </div>
      </div>

      <p className="mt-4 text-[11.5px] text-ink-faint max-w-2xl leading-relaxed">
        The gate recommends; it never decides. Above the threshold it proposes a code
        and a human still accepts it — a gate that silently refused to issue codes
        would be the fastest way to have the system switched off.
      </p>
    </div>
  )
}
