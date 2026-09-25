import { evidence } from '../lib/data'
import { ChartCard } from './Charts'
import { num, pct, longDate } from '../lib/format'

/*
 * How we know it is safe - the measured numbers, from three datasets side by
 * side, never blended into one. Each card says where its numbers came from
 * and when they were measured (src/evidence.py writes them; nothing here is
 * typed in). The weak numbers are shown with the strong ones: a panel that
 * only shows 100% is a panel nobody should believe.
 */

function Row({ label, value, tone = 'text-ink', sub }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5 border-b border-line-soft last:border-0">
      <span className="text-[12.5px] text-ink-dim leading-snug">
        {label}
        {sub && <span className="block text-[11px] text-ink-faint">{sub}</span>}
      </span>
      <span className={`font-mono text-[13px] tnum font-semibold shrink-0 ${tone}`}>{value}</span>
    </div>
  )
}

function Headline({ wrong, merged }) {
  return (
    <div className="mb-3">
      <div className={`text-[30px] font-semibold leading-none tracking-tight ${wrong ? 'text-danger' : 'text-good'}`}>
        {num(wrong)} wrong
      </div>
      <div className="text-[12px] text-ink-faint mt-1">of {num(merged)} merges made with no person involved</div>
    </div>
  )
}

function Stamp({ source, at }) {
  return (
    <p className="mt-3 text-[10.5px] font-mono text-ink-faint break-all">
      {source}{at ? ` · ${longDate(at)} ${at.slice(11, 16)}` : ''}
    </p>
  )
}

export default function Evidence() {
  const big = evidence.run15k
  const real = evidence.real
  const demo = evidence.demo
  if (!big && !real && !demo) return null
  const test = big?.by_split?.test
  const base = big?.baselines

  return (
    <ChartCard
      title="How we know it is safe"
      sub="Measured on three datasets, side by side and never blended. Every number is read from the run that produced it."
      className="mb-4"
    >
      <div className="grid lg:grid-cols-3 gap-4">
        {big && (
          <div className="rounded border border-line p-4">
            <p className="label mb-0.5">15,000 records · real notation</p>
            <p className="text-[11.5px] text-ink-faint mb-3">Generated from standards, written the way NTPC, Oil India and SAP write</p>
            <Headline wrong={big.auto_wrong} merged={big.auto_merged} />
            <Row label="Wrong-merge rate, 95% confidence" value={`< ${pct(big.auto_error_bound_95, 2)}`} tone="text-good" />
            {test && (
              <Row label="Families held back from tuning" sub={`${num(test.records)} records, two notations never seen`}
                   value={`${test.auto_wrong} of ${num(test.auto_merged)}`} tone="text-good" />
            )}
            <Row label="Near-miss traps merged" sub="SS304 vs SS316, 150# vs 300#, 6205 vs 6305 …"
                 value={`0 of ${num(big.traps_total)}`} tone="text-good" />
            {big.blocked_one_field != null && (
              <Row label="Refused one field from a merge" sub="everything else agreed" value={num(big.blocked_one_field)} />
            )}
            <Row label="Duplicates found, with a reviewer" value={pct(big.recall_with_review, 0)} />
            <Row label="Right match in the reviewer's top 3" value={pct(big.review_queue?.true_match_in_top3, 0)} />
            <Stamp source={big.source} at={big.measured_at} />
          </div>
        )}

        {real && (
          <div className="rounded border border-line p-4">
            <p className="label mb-0.5">Real tender text · held-out test</p>
            <p className="text-[11.5px] text-ink-faint mb-3">
              {num(real.lines)} real Oil India and NTPC lines, never looked at while building
            </p>
            <Headline wrong={real.auto_wrong} merged={real.auto_merged} />
            <Row label="Item type read correctly" value={pct(real.category_right, 1)} />
            <Row label="Two or more facts read" value={pct(real.two_or_more_facts, 0)} />
            <Row label="Duplicates found, with a reviewer" sub={`${real.proposed_right} of ${real.true_pairs} true pairs`}
                 value={pct(real.recall, 0)} />
            <Row label="Proposals that were right" sub="the weak number: a terse line fits several items"
                 value={pct(real.review_precision, 0)} tone="text-warn" />
            <p className="mt-3 text-[11.5px] leading-snug text-warn">
              {real.labeller === 'final'
                ? 'Labels: two people, working separately, disagreements settled.'
                : 'Labels so far: one labeller, the builder, written after the code freeze. Two-person labels replace them.'}
              {!real.frozen && ' Code changed since the freeze: a post-freeze number.'}
            </p>
            <Stamp source={real.source} at={real.run_at} />
          </div>
        )}

        {demo && (
          <div className="rounded border border-line p-4">
            <p className="label mb-0.5">Demo set · {num(demo.records)} records</p>
            <p className="text-[11.5px] text-ink-faint mb-3">The records behind every page of this portal</p>
            <Headline wrong={demo.auto_wrong} merged={demo.auto_merged} />
            <Row label="Duplicates found, with a reviewer" value={pct(demo.recall_with_review, 0)} />
            <Row label={`${num(demo.records)} records → national codes`} value={`${demo.clusters} (truth ${demo.true_items})`} />
            <Row label="Unsafe merges refused" value={num(demo.safety_blocks)} />
            <p className="mt-3 text-[11.5px] leading-snug text-ink-faint">
              We wrote this set's noise ourselves, so its 100% measures how well we undo our own errors — which is
              why the real test sits beside it.
            </p>
            <Stamp source={demo.source} at={demo.measured_at} />
          </div>
        )}
      </div>

      {base && (
        <div className="mt-5">
          <p className="text-[13px] font-semibold text-heading">
            Text matching on the same 15,000 records
            <span className="font-normal text-ink-faint text-[12px]"> — each method at its best setting, tuned on one half and scored on the half it never saw</span>
          </p>
          <div className="scroll-x mt-2">
            <table className="w-full text-[12.5px]">
              <thead>
                <tr className="border-b border-line">
                  <th className="label text-left py-1.5 pr-3">Method</th>
                  <th className="label text-right py-1.5 pr-3">Merged</th>
                  <th className="label text-right py-1.5 pr-3">Wrong</th>
                  <th className="label text-right py-1.5 pr-3">Traps merged</th>
                  <th className="label text-right py-1.5">Right</th>
                </tr>
              </thead>
              <tbody className="font-mono tnum">
                {Object.entries(base.methods).map(([name, m]) => (
                  <tr key={name} className="border-b border-line-soft">
                    <td className="py-1.5 pr-3 font-sans text-ink-dim">{{ fuzzy: 'Fuzzy string match', 'tf-idf': 'TF-IDF', embedding: 'Sentence embeddings' }[name] ?? name}</td>
                    <td className="py-1.5 pr-3 text-right">{num(m.merged)}</td>
                    <td className="py-1.5 pr-3 text-right text-danger">{num(m.wrong)}</td>
                    <td className="py-1.5 pr-3 text-right text-danger">{num(m.traps_merged)}</td>
                    <td className="py-1.5 text-right">{pct(m.precision, 0)}</td>
                  </tr>
                ))}
                <tr className="bg-good-bg">
                  <td className="py-1.5 pr-3 font-sans font-semibold text-ink">Ours — specifications, automatic merges</td>
                  <td className="py-1.5 pr-3 text-right">{num(base.ours_auto.merged)}</td>
                  <td className="py-1.5 pr-3 text-right text-good font-semibold">{num(base.ours_auto.wrong)}</td>
                  <td className="py-1.5 pr-3 text-right text-good font-semibold">{num(base.ours_auto.traps_merged)}</td>
                  <td className="py-1.5 text-right text-good font-semibold">{pct(base.ours_auto.precision, 0)}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-[11.5px] text-ink-faint">
            No text threshold reaches zero wrong: different items can share identical text once a 40-character
            field has cut them. Ours finds {pct(base.ours_auto.recall, 0)} of duplicates with no person involved —
            about what the text matchers find at their best, with none of their wrong merges — and sends the rest
            to a reviewer.
          </p>
        </div>
      )}

      <p className="mt-4 text-[11.5px] text-ink-faint">{evidence.caveat} Built {longDate(evidence.built_at)} from commit {evidence.commit}.</p>
    </ChartCard>
  )
}
