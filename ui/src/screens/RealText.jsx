import { useMemo, useState } from 'react'
import { realText } from '../lib/data'
import { SectionTitle, Chip } from '../components/Primitives'
import { prettyField } from '../lib/format'

/*
 * Real tender text - the reader at work on lines nobody wrote for us.
 *
 * Every line here is from a published Oil India or NTPC tender document, from
 * the DEVELOPMENT half of the real set: examples, never a result. Each value
 * was read by rules with no model call, and the highlighted words are where
 * it was read - the evidence span. A value with no highlight was filled in
 * from a standard (ISO 15, ASME B36.10M), and says so.
 */

// One tint per field, in the order the reader found them. Written out in full
// so Tailwind keeps the classes.
const TINTS = [
  'bg-accent-dim ring-accent/30',
  'bg-good-bg ring-good/30',
  'bg-saffron-bg ring-saffron/40',
  'bg-warn-bg ring-warn/30',
  'bg-danger-bg ring-danger/25',
]

function tintFor(fields) {
  const map = {}
  fields.forEach((f, i) => { map[f.name] = TINTS[i % TINTS.length] })
  return map
}

// The line with every evidence span marked. Spans can overlap (one number can
// give both a size and, through the weight, a wall), so the text is cut at
// every boundary and each piece lists the fields that cover it.
function Highlighted({ line, tints }) {
  const spans = line.read.filter((f) => f.span).map((f) => ({ name: f.name, s: f.span[0], e: f.span[1] }))
  const cuts = [...new Set([0, line.text.length, ...spans.flatMap((x) => [x.s, x.e])])]
    .filter((c) => c >= 0 && c <= line.text.length)
    .sort((a, b) => a - b)
  const pieces = []
  for (let i = 0; i < cuts.length - 1; i++) {
    const [s, e] = [cuts[i], cuts[i + 1]]
    const cover = spans.filter((x) => x.s <= s && x.e >= e)
    pieces.push({ s, e, cover })
  }
  return (
    <p className="font-mono text-[13px] leading-[1.9] text-ink break-words">
      {pieces.map(({ s, e, cover }) =>
        cover.length ? (
          <mark
            key={s}
            title={cover.map((c) => prettyField(c.name)).join(' · ')}
            className={`rounded-[3px] px-[1px] ring-1 text-ink ${tints[cover[0].name]}`}
          >
            {line.text.slice(s, e)}
          </mark>
        ) : (
          <span key={s}>{line.text.slice(s, e)}</span>
        ),
      )}
    </p>
  )
}

function value(v) {
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : String(+v.toFixed(3))
  return String(v).replace(/_/g, ' ')
}

function Fields({ line, tints }) {
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {line.read.map((f) => (
        <span key={f.name} className={`text-[11.5px] px-1.5 py-[2px] rounded ring-1 ${tints[f.name]}`}>
          <span className="text-ink-faint">{prettyField(f.name)}</span>{' '}
          <span className="font-mono text-ink">{value(f.value)}</span>
          {f.ignored && <span className="text-ink-faint"> · never matched on</span>}
        </span>
      ))}
      {line.filled.map((f) => (
        <span key={f.name} className="text-[11.5px] px-1.5 py-[2px] rounded border border-dashed border-line text-ink-dim"
              title="Not in the line - filled in from a standard">
          <span className="text-ink-faint">{prettyField(f.name)}</span>{' '}
          <span className="font-mono">{value(f.value)}</span>
          <span className="text-ink-faint"> · from the standard</span>
        </span>
      ))}
    </div>
  )
}

function Line({ line, compact }) {
  const tints = tintFor(line.read)
  return (
    <div className={compact ? '' : 'py-3 border-b border-line-soft last:border-0'}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[11px] font-semibold text-accent">{line.org.replace(' Limited', '')}</span>
        <span className="text-[11px] text-ink-faint font-mono">line {line.id}</span>
        <span className="ml-auto text-[11px] text-ink-faint">read as {line.category}</span>
      </div>
      <Highlighted line={line} tints={tints} />
      <Fields line={line} tints={tints} />
    </div>
  )
}

const BAND = {
  auto: { tone: 'good', label: 'merged automatically' },
  review: { tone: 'warn', label: 'sent to a reviewer' },
  blocked: { tone: 'danger', label: 'refused' },
  apart: { tone: 'faint', label: 'left apart' },
}

export default function RealText() {
  const v = realText
  const cats = useMemo(() => [...new Set((v.lines ?? []).map((l) => l.category))], [v])
  const [cat, setCat] = useState('all')

  if (!v.lines) {
    return (
      <div className="max-w-5xl mx-auto">
        <SectionTitle eyebrow="Real tender text" title="Not generated yet"
                      sub="Run python src/results.py with data/real present." />
      </div>
    )
  }

  const shown = v.lines.filter((l) => cat === 'all' || l.category === cat)
  const orgs = Object.entries(v.by_org ?? {}).filter(([, n]) => n > 5)

  return (
    <div className="max-w-5xl mx-auto">
      <SectionTitle
        eyebrow="Real tender text · Oil India and NTPC"
        title="Read the way companies actually write"
        sub={`${v.lines_total} real material lines from published tender documents — ${orgs
          .map(([o, n]) => `${n} ${o.replace(' Limited', '')}`)
          .join(', ')}. Every value was read by rules, with no model call. The highlighted words are where it was read.`}
      />

      <div className="well px-4 py-2.5 mb-6 text-[12.5px] text-ink-dim leading-relaxed">
        <span className="font-semibold text-ink">Examples, not a result.</span> These lines are from the
        development half of the real set, the half the reader was built against. The reported number comes
        from the other half, held back and scored once with the code frozen.
      </div>

      {/* One item, several spellings */}
      <h2 className="text-[15px] font-semibold text-ink mb-1">One item, written differently</h2>
      <p className="text-[12.5px] text-ink-dim mb-3 max-w-3xl">
        The same item in different tender documents. The lines share few words; the specifications agree.
        {v.groups_total ? ` All ${v.groups_found} of ${v.groups_total} same-item groups in this half are found.` : ''}
      </p>
      <div className="space-y-3 mb-8">
        {v.groups.map((g) => {
          const band = BAND[g.pair.band]
          return (
            <div key={g.group} className="card p-4">
              <div className="space-y-3">
                {g.lines.map((l) => <Line key={l.id} line={l} compact />)}
              </div>
              <div className="mt-3 pt-3 border-t border-line-soft flex flex-wrap items-center gap-2 text-[12px]">
                <Chip tone={band.tone}>{band.label}</Chip>
                <span className="font-mono tnum text-ink">{g.pair.final}</span>
                <span className="text-ink-faint">words in common {Math.round(g.pair.text_sim * 100)}%</span>
                <span className="text-ink-dim">
                  agreed on {g.pair.matched.map((m) => prettyField(m).toLowerCase()).join(', ')}
                </span>
                {g.pair.review_reason && (
                  <span className="w-full text-[11.5px] text-ink-faint">
                    Why a person still looks: {g.pair.review_reason.replace(/_/g, ' ')}.
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Near misses */}
      <h2 className="text-[15px] font-semibold text-ink mb-1">Alike on paper, different items</h2>
      <p className="text-[12.5px] text-ink-dim mb-3 max-w-3xl">
        Lines that share most of their words and are not the same item. Each is refused on a safety field.
      </p>
      <div className="grid md:grid-cols-2 gap-3 mb-8">
        {v.near_misses.map((p) => (
          <div key={`${p.a}-${p.b}`} className="card p-4 border-danger/25">
            <div className="space-y-3">
              {p.lines.map((l) => <Line key={l.id} line={l} compact />)}
            </div>
            <div className="mt-3 pt-3 border-t border-line-soft text-[12px]">
              <div className="flex flex-wrap items-center gap-2">
                <Chip tone="danger">refused</Chip>
                <span className="text-ink-faint">words in common {Math.round(p.text_sim * 100)}%</span>
              </div>
              <p className="mt-1.5 font-mono text-[12px] text-danger">
                {prettyField(p.blocked_by)}: {p.reason}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Browse */}
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <h2 className="text-[15px] font-semibold text-ink mr-2">Browse the lines</h2>
        {['all', ...cats].map((c) => (
          <button
            key={c}
            onClick={() => setCat(c)}
            className={`px-2.5 py-1 rounded-md text-[12px] border transition-colors ${
              c === cat ? 'bg-accent-dim border-accent/30 text-ink font-medium'
                        : 'bg-base-card border-line text-ink-faint hover:text-ink'}`}
          >
            {c}
          </button>
        ))}
      </div>
      <p className="text-[12px] text-ink-faint mb-2">
        Solid tags were read from the words highlighted in the same colour. Dashed tags were filled in from a
        standard — a 6205 is 25 × 52 × 15 mm whether or not the line says so.
      </p>
      <div className="card px-4">
        {shown.map((l) => <Line key={l.id} line={l} />)}
      </div>
    </div>
  )
}
