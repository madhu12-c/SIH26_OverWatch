import { useState, useEffect } from 'react'
import { AnimatePresence, motion, MotionConfig } from 'framer-motion'
import { meta } from './lib/data'
import Overview from './screens/Overview'
import MatchCase from './screens/MatchCase'
import BlockCase from './screens/BlockCase'
import ReviewQueue from './screens/ReviewQueue'
import Savings from './screens/Savings'
import Units from './screens/Units'
import Gate from './screens/Gate'
import Codes from './screens/Codes'

/*
 * Eight screens, in demo order.
 *
 * The tab order IS the demo order, left to right, so a presenter never has to
 * jump. 01-03 carry the thesis and make the video. 04 is the actual product.
 * 05-06 are the findings a procurement audience cares about. 07 is the
 * deliverable. 08 ends on the only forward-looking screen - the answer to
 * "what stops the mess coming back" - because that is the beat worth leaving
 * a judge with, and a mapping table is not.
 *
 * Number keys 1-8 switch screens - a presenter should never hunt for a tab
 * mid-sentence. The id, not the number, is what the URL hash carries, so
 * reordering this list never breaks a saved link.
 */

const SCREENS = [
  { id: 'overview', n: '01', label: 'Overview', el: Overview },
  { id: 'match', n: '02', label: 'The Match', el: MatchCase },
  { id: 'block', n: '03', label: 'The Block', el: BlockCase },
  { id: 'review', n: '04', label: 'Review Queue', el: ReviewQueue },
  { id: 'savings', n: '05', label: 'Savings', el: Savings },
  { id: 'units', n: '06', label: 'Units', el: Units },
  { id: 'codes', n: '07', label: 'Codes', el: Codes },
  { id: 'gate', n: '08', label: 'Creation Gate', el: Gate },
]

// The screen is kept in the URL hash so a reload lands where it left off and
// a screen can be opened directly - which is how the demo video gets recorded
// one screen at a time without a presenter clicking on camera.
function screenFromHash() {
  const id = window.location.hash.replace('#', '')
  return SCREENS.some((s) => s.id === id) ? id : 'overview'
}

export default function App() {
  const [active, setActive] = useState(screenFromHash)
  const Screen = SCREENS.find((s) => s.id === active)?.el ?? Overview

  const go = (id) => {
    setActive(id)
    window.location.hash = id
  }

  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === 'INPUT') return
      const i = parseInt(e.key, 10)
      if (i >= 1 && i <= SCREENS.length) go(SCREENS[i - 1].id)
    }
    const onHash = () => setActive(screenFromHash())
    window.addEventListener('keydown', onKey)
    window.addEventListener('hashchange', onHash)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('hashchange', onHash)
    }
  }, [])

  return (
    <MotionConfig reducedMotion="user">
    <div className="min-h-full flex flex-col">
      {/* The header sits on white rather than the page ground, so the sticky
          bar reads as a surface above the content instead of a band of the
          same paper with a line under it. */}
      <header className="border-b border-line sticky top-0 z-10
                         bg-base-card/90 backdrop-blur shadow-head">
        <div className="max-w-5xl mx-auto px-5 pt-3.5 pb-0">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 mb-3">
            <span className="inline-flex items-center justify-center w-[22px] h-[22px] shrink-0
                             rounded-md bg-accent text-white font-mono text-[11px] font-semibold">
              N
            </span>
            <span className="font-semibold tracking-tight text-[15px]">
              One Nation, One Material Code
            </span>
            <span className="font-mono text-[10.5px] text-ink-faint px-1.5 py-[2px]
                             rounded border border-line bg-base-raised">
              SIH26099 · CPCL
            </span>
            <span className="ml-auto text-[11px] text-ink-faint font-mono tnum">
              {meta.records} records · {meta.unique_items} unique
            </span>
          </div>

          <nav className="flex gap-0.5 -mb-px overflow-x-auto scroll-x">
            {SCREENS.map((s) => {
              const on = s.id === active
              return (
                <button
                  key={s.id}
                  onClick={() => go(s.id)}
                  className={`px-3 py-2 text-[13px] whitespace-nowrap rounded-t-md
                              border-b-2 transition-colors
                    ${on
                      ? 'border-accent text-ink font-medium bg-accent-dim/60'
                      : 'border-transparent text-ink-faint hover:text-ink-dim hover:bg-base-raised'}`}
                >
                  <span className={`font-mono text-[10.5px] mr-1.5 ${on ? 'text-accent' : 'opacity-60'}`}>
                    {s.n}
                  </span>
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

      <footer className="border-t border-line bg-base-card px-5 py-3">
        <div className="max-w-5xl mx-auto flex flex-wrap items-center gap-x-4 gap-y-1
                        text-[11.5px] text-ink-faint">
          <span>Team Overwatch</span>
          <span className="font-mono">generated {meta.generated}</span>
          <span className="ml-auto">press 1–8 to switch screens</span>
        </div>
      </footer>
    </div>
    </MotionConfig>
  )
}
