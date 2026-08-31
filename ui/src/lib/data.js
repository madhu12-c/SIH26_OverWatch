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
export const blocked = results.blocked ?? []
export const blockedByRule = results.blocked_by_rule ?? {}
export const savings = results.savings ?? []
export const savingsSummary = results.savings_summary ?? {}

export const isStub = meta.precision == null && clusters.length <= 1
