import { useState, useEffect } from 'react'
import { AnimatePresence, motion, MotionConfig } from 'framer-motion'
import { meta } from './lib/data'
import Overview from './screens/Overview'
import MatchCase from './screens/MatchCase'
import BlockCase from './screens/BlockCase'
import ReviewQueue from './screens/ReviewQueue'
import Savings from './screens/Savings'
import Codes from './screens/Codes'

/*
 * Six screens, in demo order. Screens 01-03 and 05 make the video; 04 is the
 * actual product and 06 is the deliverable, and both get asked about in Q&A.
 *
 * Number keys 1-6 switch screens - a presenter should never hunt for a tab
 * mid-sentence.
 */

const SCREENS = [
  { id: 'overview', n: '01', label: 'Overview', el: Overview },
  { id: 'match', n: '02', label: 'The Match', el: MatchCase },
  { id: 'block', n: '03', label: 'The Block', el: BlockCase },
  { id: 'review', n: '04', label: 'Review Queue', el: ReviewQueue },
  { id: 'savings', n: '05', label: 'Savings', el: Savings },
  { id: 'codes', n: '06', label: 'Codes', el: Codes },
]

export default function App() {
  const [active, setActive] = useState('overview')
  const Screen = SCREENS.find((s) => s.id === active)?.el ?? Overview

  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === 'INPUT') return
      const i = parseInt(e.key, 10)
      if (i >= 1 && i <= SCREENS.length) setActive(SCREENS[i - 1].id)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <MotionConfig reducedMotion="user">
    <div className="min-h-full flex flex-col">
      <header className="border-b border-line sticky top-0 z-10 bg-base/95 backdrop-blur">
        <div className="max-w-5xl mx-auto px-5 pt-4 pb-0">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 mb-3">
            <span className="font-semibold tracking-tight">One Nation, One Material Code</span>
            <span className="text-[11.5px] text-ink-faint font-mono">SIH26099 · CPCL</span>
            <span className="ml-auto text-[11px] text-ink-faint font-mono">
              {meta.records} records · {meta.unique_items} unique
            </span>
          </div>

          <nav className="flex gap-0.5 -mb-px overflow-x-auto scroll-x">
            {SCREENS.map((s) => {
              const on = s.id === active
              return (
                <button
                  key={s.id}
                  onClick={() => setActive(s.id)}
                  className={`px-3 py-2 text-[13px] whitespace-nowrap border-b-2 transition-colors
                    ${on
                      ? 'border-accent text-ink'
                      : 'border-transparent text-ink-faint hover:text-ink-dim'}`}
                >
                  <span className="font-mono text-[10.5px] mr-1.5 opacity-60">{s.n}</span>
                  {s.label}
                </button>
              )
            })}
          </nav>
        </div>
      </header>

      <main className="flex-1 px-5 py-7">
        <AnimatePresence mode="wait">
          <motion.div
            key={active}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.22 }}
          >
            <Screen />
          </motion.div>
        </AnimatePresence>
      </main>

      <footer className="border-t border-line px-5 py-3">
        <div className="max-w-5xl mx-auto flex flex-wrap items-center gap-x-4 gap-y-1
                        text-[11.5px] text-ink-faint">
          <span>Team Overwatch</span>
          <span className="font-mono">generated {meta.generated}</span>
          <span className="ml-auto">press 1–6 to switch screens</span>
        </div>
      </footer>
    </div>
    </MotionConfig>
  )
}
