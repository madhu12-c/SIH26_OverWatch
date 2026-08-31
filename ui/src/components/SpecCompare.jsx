import { motion, AnimatePresence } from 'framer-motion'
import { spec, fieldLabel } from '../lib/format'

/*
 * The field-by-field specification comparison.
 *
 * This component IS the argument. Rows land one at a time rather than all at
 * once, because the sequence is the explanation - the audience has to watch
 * the specs agree, field by field, after being told the text does not.
 *
 * The brand row lands LAST and greys out. That single row is the whole
 * technical idea: functional equivalence does not care who made it.
 *
 * On a phone the two records stack instead of sitting side by side - two
 * columns squeezed onto 390px is unreadable, and the phone build is the
 * backup that has to work when the laptop does not.
 */

function verdict(name, { matched, ignored, blockedBy }) {
  if (ignored?.includes(name)) return 'ignored'
  if (name === blockedBy) return 'block'
  if (matched?.includes(name)) return 'match'
  return 'differ'
}

const MARK = {
  match: { sign: '✓', cls: 'text-good' },
  block: { sign: '✕', cls: 'text-danger' },
  ignored: { sign: '⊗', cls: 'text-ink-faint' },
  differ: { sign: '·', cls: 'text-ink-faint' },
  missing: { sign: '·', cls: 'text-ink-faint' },
}

export default function SpecCompare({ a, b, matched, ignored, blockedBy, hardFields = [], play }) {
  const names = [...new Set([...Object.keys(a?.attributes || {}), ...Object.keys(b?.attributes || {})])]

  // Ordinary fields first, ignored fields last. The brand row landing at the
  // end is deliberate staging, not alphabetical accident.
  const ordered = [
    ...names.filter((n) => !ignored?.includes(n)).sort(),
    ...names.filter((n) => ignored?.includes(n)).sort(),
  ]

  return (
    <div className="card overflow-hidden">
      <div className="grid grid-cols-[1fr_auto_1fr] gap-x-3 px-4 py-2.5 bg-base-raised border-b border-line">
        <span className="label">{a?.cpse}</span>
        <span className="label text-center w-6">·</span>
        <span className="label text-right">{b?.cpse}</span>
      </div>

      <AnimatePresence>
        {play && ordered.map((name, i) => {
          const v = verdict(name, { matched, ignored, blockedBy })
          const mark = MARK[v]
          const isHard = hardFields.includes(name)
          const av = a?.attributes?.[name]
          const bv = b?.attributes?.[name]
          const dim = v === 'ignored'

          return (
            <motion.div
              key={name}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.12, duration: 0.28, ease: 'easeOut' }}
              className={`grid grid-cols-[1fr_auto_1fr] gap-x-3 items-center px-4 py-2
                          border-b border-line-soft last:border-0
                          ${v === 'block' ? 'bg-danger-bg' : ''}`}
            >
              <div className={`min-w-0 ${dim ? 'opacity-40' : ''}`}>
                <div className="flex items-baseline gap-1.5">
                  {isHard && <span className="text-danger text-[11px] leading-none">*</span>}
                  <span className="text-[11px] text-ink-faint truncate">{fieldLabel(name)}</span>
                </div>
                <div className={`font-mono text-[13px] truncate ${dim ? 'line-through' : ''}`}>
                  {spec(av)}
                </div>
              </div>

              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: [0, 1.15, 1] }}
                transition={{ delay: i * 0.12 + 0.18, duration: 0.3 }}
                className={`w-6 text-center text-[15px] font-semibold ${mark.cls}`}
              >
                {mark.sign}
              </motion.span>

              <div className={`min-w-0 text-right ${dim ? 'opacity-40' : ''}`}>
                <div className="text-[11px] text-ink-faint truncate">{fieldLabel(name)}</div>
                <div className={`font-mono text-[13px] truncate ${dim ? 'line-through' : ''}`}>
                  {spec(bv)}
                </div>
              </div>

              {v === 'ignored' && (
                <div className="col-span-3 -mt-0.5 text-center">
                  <span className="text-[10.5px] text-ink-faint tracking-wide uppercase">
                    ignored — brand never counts toward a match
                  </span>
                </div>
              )}
              {v === 'block' && (
                <div className="col-span-3 mt-1 text-center">
                  <span className="text-[10.5px] text-danger tracking-wide uppercase font-semibold">
                    veto field — instant zero, whatever else agrees
                  </span>
                </div>
              )}
            </motion.div>
          )
        })}
      </AnimatePresence>

      <div className="px-4 py-2 border-t border-line-soft">
        <span className="text-[10.5px] text-ink-faint">
          <span className="text-danger">*</span> hard blocker — a mismatch here is an instant zero
        </span>
      </div>
    </div>
  )
}
