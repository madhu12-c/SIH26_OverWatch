import { useState } from 'react'
import { motion } from 'framer-motion'
import { clusters } from '../lib/data'
import { SectionTitle, Chip } from '../components/Primitives'

/*
 * Screen 06 - the deliverable itself.
 *
 * Nobody changes their code. The national code sits ABOVE the existing codes
 * and links them, the way Aadhaar and UPI added a layer without replacing what
 * was underneath. CPCL's storekeeper keeps typing 100001445 forever.
 */

export default function Codes() {
  const [open, setOpen] = useState(clusters?.[0]?.national_code ?? null)
  const items = [...(clusters || [])].sort((a, b) => b.member_count - a.member_count)

  return (
    <div className="max-w-4xl mx-auto">
      <SectionTitle
        eyebrow="National codes"
        title="One code per physical item, every source code mapped"
        sub="The standard description is generated from the extracted specifications — noun first, then modifiers in significance order, the way industry writes it."
      />

      <div className="space-y-2">
        {items.map((c, idx) => {
          const isOpen = open === c.national_code
          return (
            <motion.div
              key={c.national_code}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(idx * 0.04, 0.4), duration: 0.3 }}
              className="card overflow-hidden"
            >
              <button
                onClick={() => setOpen(isOpen ? null : c.national_code)}
                className="w-full text-left px-4 py-3 hover:bg-base-raised transition-colors"
              >
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span className="font-mono text-[11.5px] text-accent">{c.national_code}</span>
                  <Chip tone={c.band === 'auto' ? 'good' : 'warn'}>{c.band}</Chip>
                  <span className="text-[11px] text-ink-faint">
                    {c.member_count} codes · {c.cpse_count} CPSE
                  </span>
                  <span className="ml-auto text-[11px] text-ink-faint font-mono">
                    UNSPSC {c.unspsc}
                  </span>
                </div>
                <p className="font-mono text-[13px] text-ink break-words">
                  {c.std_description}
                </p>
              </button>

              {isOpen && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  transition={{ duration: 0.25 }}
                  className="border-t border-line-soft"
                >
                  <div className="px-4 py-2 bg-base-raised">
                    <span className="label">mapped source codes — all still active</span>
                  </div>
                  <div className="scroll-x">
                    <table className="w-full text-[12.5px]">
                      <tbody className="font-mono">
                        {(c.members || []).map((m) => (
                          <tr key={m.record_id} className="border-b border-line-soft last:border-0">
                            <td className="py-2 px-4 text-accent whitespace-nowrap">{m.cpse}</td>
                            <td className="py-2 pr-4 whitespace-nowrap">{m.source_code}</td>
                            <td className="py-2 pr-4 text-ink-dim">{m.description}</td>
                            <td className="py-2 pr-4 text-ink-faint whitespace-nowrap">{m.uom}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="px-4 py-2.5 text-[11.5px] text-ink-faint border-t border-line-soft">
                    Nothing was deleted. Every original code stays active and in use —
                    the national code is an additional layer above it, and the merge
                    is reversible.
                  </p>
                </motion.div>
              )}
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
