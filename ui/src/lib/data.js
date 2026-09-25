// The whole dataset, imported at BUILD time.
//
// No fetch, no server, no API. That is deliberate: it is what lets the built
// dist/ folder open by double-clicking, on a laptop or a phone, with no
// internet - and it means there is nothing that can fail on stage.
//
// Regenerate with:  python src/results.py     (or --stub before the pipeline runs)
import results from '../results.json'

export default results

export const meta = results.meta ?? {}
export const cases = results.cases ?? {}
export const clusters = results.clusters ?? []
export const reviewQueue = results.review_queue ?? []
// The same queue grouped the way a reviewer meets it: one record, its candidates.
export const reviewRecords = results.review_records ?? []
export const blocked = results.blocked ?? []
export const blockedByRule = results.blocked_by_rule ?? {}
export const savings = results.savings ?? []
export const savingsSummary = results.savings_summary ?? {}

// Optional stages. Absent until src/uom.py and src/gate.py have run, so every
// consumer checks before rendering rather than assuming the key is there.
export const uom = results.uom ?? {}
export const uomSummary = results.uom?.summary ?? {}
export const uomFamilies = results.uom?.families ?? []
export const uomConflicts = results.uom?.conflicts ?? []
export const gate = results.gate ?? {}
export const gateScenarios = results.gate?.scenarios ?? []

// Counts of the real Oil India / NTPC tender lines - from the unlabelled
// candidate text only. Empty until results.py has run with data/real present.
export const real = results.real ?? {}

// The Real text page: dev-half lines with what the reader took from each.
export const realText = results.real_text ?? {}

// Headline numbers from every dataset, stamped with where they came from (src/evidence.py).
export const evidence = results.evidence ?? {}

export const isStub = meta.precision == null && clusters.length <= 1
