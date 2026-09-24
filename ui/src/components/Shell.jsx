import { useEffect, useState } from 'react'
import { useReducedMotion } from 'framer-motion'
import { meta, cases, blockedByRule, savingsSummary, real } from '../lib/data'
import { rupees, longDate } from '../lib/format'
import { ROLES, sessionLabel, signOut } from '../lib/store'
import { Icon, Logo } from './Icons'

/*
 * The frame every page sits in, laid out as an Indian government portal is
 * (GIGW 3.0): tricolour hairline, an accessibility bar, the masthead, a navy
 * bar, a "What's new" ticker, then a left menu and the page, then the footer.
 *
 * The accessibility controls are real: text size zooms the page, high
 * contrast swaps every colour token, the ticker pauses, the skip link moves
 * focus. It is labelled a prototype at the top and the bottom, and uses no
 * State Emblem, ministry logo or flag - those are restricted by law.
 */

function load(key, fallback) {
  try { return window.localStorage.getItem(key) ?? fallback } catch { return fallback }
}
function save(key, value) {
  try { window.localStorage.setItem(key, value) } catch { /* not persisted */ }
}

const ZOOMS = [
  { id: 'small', label: 'A-', value: 0.9, name: 'Decrease text size' },
  { id: 'normal', label: 'A', value: 1, name: 'Normal text size' },
  { id: 'large', label: 'A+', value: 1.12, name: 'Increase text size' },
]

export default function Shell({ nav = [], active, go, session, crumbs = [], children, bare = false }) {
  const [zoom, setZoom] = useState(() => load('nmcr.zoom', 'normal'))
  const [contrast, setContrast] = useState(() => load('nmcr.contrast', 'off') === 'on')
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    const z = ZOOMS.find((x) => x.id === zoom) ?? ZOOMS[1]
    document.documentElement.style.setProperty('--zoom', String(z.value))
    save('nmcr.zoom', z.id)
  }, [zoom])

  useEffect(() => {
    document.documentElement.classList.toggle('hc', contrast)
    save('nmcr.contrast', contrast ? 'on' : 'off')
  }, [contrast])

  const skip = (e) => {
    e.preventDefault()
    document.getElementById('main')?.focus()
  }

  const pick = (id) => { setMenuOpen(false); go(id) }

  return (
    <>
      <a href="#main" onClick={skip} className="skip-link">Skip to main content</a>
      <div className="page min-h-full flex flex-col">
        <div className="tricolour h-[5px]" />

        {/* accessibility bar */}
        <div className="bg-gov-deep text-white/90 text-[12px]">
          <div className="max-w-7xl mx-auto px-4 sm:px-5 min-h-[34px] flex flex-wrap items-center gap-x-4 gap-y-1 py-1">
            <span className="font-semibold text-white">Prototype</span>
            <span className="hidden sm:inline text-white/70">
              Smart India Hackathon 2026 · not an official Government of India website
            </span>
            <div className="ml-auto flex items-center gap-3">
              <a href="#main" onClick={skip} className="hidden md:inline hover:underline underline-offset-2">
                Skip to main content
              </a>
              <span className="hidden md:inline w-px h-3.5 bg-white/25" />
              <div role="group" aria-label="Text size" className="flex items-center">
                {ZOOMS.map((z) => (
                  <button key={z.id} onClick={() => setZoom(z.id)} aria-label={z.name}
                          aria-pressed={zoom === z.id}
                          className={`px-1.5 py-0.5 rounded-sm font-semibold leading-none
                            ${z.id === 'small' ? 'text-[11px]' : z.id === 'large' ? 'text-[14px]' : 'text-[12.5px]'}
                            ${zoom === z.id ? 'bg-white text-gov-deep' : 'hover:bg-white/15'}`}>
                    {z.label}
                  </button>
                ))}
              </div>
              <span className="w-px h-3.5 bg-white/25" />
              <button onClick={() => setContrast((c) => !c)} aria-pressed={contrast}
                      aria-label="High contrast" title="High contrast"
                      className={`flex items-center gap-1.5 px-1.5 py-0.5 rounded-sm
                        ${contrast ? 'bg-white text-gov-deep' : 'hover:bg-white/15'}`}>
                <Icon name="contrast" size={14} />
                <span className="hidden sm:inline">Contrast</span>
              </button>
            </div>
          </div>
        </div>

        {/* masthead */}
        <header className="bg-base-card border-b border-line">
          <div className="max-w-7xl mx-auto px-4 sm:px-5 py-3 flex items-center gap-3.5">
            <Logo size={52} />
            <div className="min-w-0">
              <p lang="hi" className="font-deva text-[15px] font-semibold text-heading leading-tight">
                राष्ट्रीय सामग्री कोड रजिस्ट्री
              </p>
              <p className="text-[18px] sm:text-[21px] font-bold text-heading leading-tight tracking-tight">
                National Material Code Registry
              </p>
              <p className="text-[12px] text-ink-dim mt-0.5 hidden sm:block">
                One Nation, One Material Code ·{' '}
                <span lang="hi" className="font-deva">एक राष्ट्र, एक सामग्री कोड</span>
              </p>
            </div>
            <div className="ml-auto flex items-center gap-3">
              {session ? (
                <>
                  <div className="hidden md:flex items-center gap-2.5 pl-4 border-l border-line">
                    <span className={`w-9 h-9 rounded-full ${ROLES[session.role]?.tone ?? 'bg-accent'} text-white flex items-center justify-center`}>
                      <Icon name="user" size={18} />
                    </span>
                    <div className="leading-tight">
                      <p className="text-[13.5px] font-semibold text-ink">{sessionLabel(session)}</p>
                      <p className="text-[11.5px] text-ink-faint">{ROLES[session.role]?.label} · demo sign-in</p>
                    </div>
                  </div>
                  <button onClick={signOut}
                          className="inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-accent
                                     border border-line rounded px-2.5 py-1.5 hover:bg-accent-dim">
                    <Icon name="logout" size={15} /> Sign out
                  </button>
                </>
              ) : (
                <div className="hidden md:block text-right pl-4 border-l border-line">
                  <p className="label">Problem statement</p>
                  <p className="text-[14px] font-semibold text-ink">SIH26099</p>
                  <p className="text-[12px] text-ink-dim">set by MoPNG · CPCL</p>
                  <p className="text-[11.5px] text-ink-faint mt-0.5">Team Overwatch</p>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* navy bar */}
        <div className="bg-gov sticky top-0 z-30 shadow-head">
          <div className="max-w-7xl mx-auto px-4 sm:px-5 h-11 flex items-center gap-3 text-white">
            {!bare && (
              <button onClick={() => setMenuOpen((o) => !o)} aria-expanded={menuOpen}
                      aria-label="Menu" className="lg:hidden -ml-1 p-1.5 rounded hover:bg-white/10">
                <Icon name={menuOpen ? 'close' : 'menu'} size={20} />
              </button>
            )}
            <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-[13px] min-w-0">
              {crumbs.map((c, i) => (
                <span key={c.label} className="flex items-center gap-2 min-w-0">
                  {i > 0 && <span className="text-white/45" aria-hidden="true">›</span>}
                  {c.to && i < crumbs.length - 1 ? (
                    <button onClick={() => go(c.to)} className="text-white/80 hover:text-white hover:underline underline-offset-2 truncate">
                      {c.label}
                    </button>
                  ) : (
                    <span className="font-semibold truncate" aria-current={i === crumbs.length - 1 ? 'page' : undefined}>
                      {c.label}
                    </span>
                  )}
                </span>
              ))}
            </nav>
            <span className="ml-auto hidden sm:inline font-mono text-[11px] text-white/60 tnum">
              {meta.records} records · {meta.unique_items} national codes · {(meta.cpses || []).length} CPSEs
            </span>
          </div>
        </div>

        <Ticker items={tickerItems()} />

        {bare ? (
          <main id="main" tabIndex={-1} className="flex-1 focus:outline-none">{children}</main>
        ) : (
          <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-5 py-6 flex gap-6">
            <aside className={`${menuOpen ? 'fixed inset-0 top-0 z-40 bg-black/40 lg:static lg:bg-transparent' : 'hidden'}
                               lg:block lg:w-[232px] shrink-0`}
                   onClick={(e) => { if (e.target === e.currentTarget) setMenuOpen(false) }}>
              <Sidebar nav={nav} active={active} go={pick} menuOpen={menuOpen} session={session} />
            </aside>
            <main id="main" tabIndex={-1} className="flex-1 min-w-0 focus:outline-none">{children}</main>
          </div>
        )}

        <Footer go={go} nav={nav} signedIn={!!session} />
      </div>
    </>
  )
}

function Sidebar({ nav, active, go, menuOpen, session }) {
  const role = ROLES[session?.role]
  const groups = []
  for (const item of nav) {
    const g = groups.find((x) => x.name === item.group)
    if (g) g.items.push(item)
    else groups.push({ name: item.group, items: [item] })
  }
  return (
    <nav aria-label="Main menu"
         className={`card overflow-hidden lg:sticky lg:top-[60px]
                     ${menuOpen ? 'w-[270px] h-full rounded-none lg:rounded-xl lg:h-auto lg:w-auto' : ''}`}>
      {role && (
        <div className={`${role.tone} text-white px-4 py-3.5 relative overflow-hidden`}>
          <div className="jaali absolute inset-0" aria-hidden="true" />
          <p className="relative text-[10.5px] font-bold uppercase tracking-[0.1em] text-white/75">Workspace</p>
          <p className="relative text-[15.5px] font-bold leading-tight mt-0.5">{role.workspace}</p>
          <p className="relative text-[12px] text-white/80 mt-1">{sessionLabel(session)}</p>
        </div>
      )}
      {groups.map((g) => (
        <div key={g.name} className="py-2 border-b border-line-soft last:border-0">
          <p className="px-4 pt-1.5 pb-1 text-[10.5px] font-bold uppercase tracking-[0.1em] text-saffron-ink">
            {g.name}
          </p>
          {g.items.map((item) => {
            const on = item.id === active
            return (
              <button key={item.id} onClick={() => go(item.id)}
                      aria-current={on ? 'page' : undefined}
                      className={`w-full flex items-center gap-2.5 px-4 py-2 text-left text-[13.5px]
                                  border-l-[3px] transition-colors
                        ${on ? 'border-saffron bg-accent-dim text-heading font-semibold'
                             : 'border-transparent text-ink-dim hover:bg-base-raised hover:text-ink'}`}>
                <Icon name={item.icon} size={17} className={on ? 'text-accent' : 'text-ink-faint'} />
                <span className="flex-1">{item.label}</span>
                {item.badge != null && (
                  <span className={`text-[10.5px] font-bold font-mono tnum px-1.5 py-0.5 rounded
                    ${on ? 'bg-accent text-onaccent' : 'bg-base-raised text-ink-dim'}`}>
                    {item.badge}
                  </span>
                )}
              </button>
            )
          })}
        </div>
      ))}
    </nav>
  )
}

/* Every line is a measured fact from results.json - no invented news. */
function tickerItems() {
  const refused = Object.values(blockedByRule || {}).reduce((s, n) => s + n, 0)
  const items = [
    `${meta.records} material records from ${(meta.cpses || []).length} CPSEs resolved to ${meta.unique_items} national codes`,
    `${refused} unsafe merges refused — material grade, pressure class and size are veto fields`,
  ]
  if (cases.block) items.push(`SS316 vs SS304: text similarity ${cases.block.text_sim}, merge blocked on material grade`)
  if (cases.match) items.push(`SKF vs FAG 6205 bearing: brands differ, specifications agree — matched at ${cases.match.final}`)
  if (real.lines) items.push(`Real tender text added: ${real.lines} lines from Oil India and NTPC`)
  if (savingsSummary.saving_realistic) {
    items.push(`${rupees(savingsSummary.saving_realistic)} realistic saving identified from buying together`)
  }
  return items
}

// The track holds the items twice so the loop is seamless; the second copy is
// hidden from screen readers so nothing is announced twice.
function TickerRow({ items, hidden }) {
  return (
    <span className="inline-flex" aria-hidden={hidden || undefined}>
      {items.map((t) => (
        <span key={t} className="inline-flex items-center">
          <span className="w-1.5 h-1.5 rounded-full bg-saffron mx-4" />
          {t}
        </span>
      ))}
    </span>
  )
}

function Ticker({ items }) {
  const reduce = useReducedMotion()
  const [paused, setPaused] = useState(false)
  const still = paused || reduce
  return (
    <div className="bg-saffron-bg border-b border-saffron/40">
      <div className="max-w-7xl mx-auto px-4 sm:px-5 flex items-center gap-3 h-9">
        <span className="shrink-0 bg-saffron-ink text-onaccent text-[11px] font-bold uppercase
                         tracking-wide px-2 py-1 rounded-sm">
          What's new
        </span>
        <div className="ticker flex-1 overflow-hidden text-[12.5px] text-ink" tabIndex={0} aria-label="Latest updates">
          {still ? (
            <div className="truncate">{items.join('   ·   ')}</div>
          ) : (
            <div className="ticker-track">
              <TickerRow items={items} />
              <TickerRow items={items} hidden />
            </div>
          )}
        </div>
        <button onClick={() => setPaused((p) => !p)} aria-label={paused ? 'Play updates' : 'Pause updates'}
                title={paused ? 'Play' : 'Pause'} className="shrink-0 p-1 rounded-sm text-saffron-ink hover:bg-saffron/20">
          <Icon name={paused ? 'play' : 'pause'} size={14} strokeWidth={2.2} />
        </button>
      </div>
    </div>
  )
}

function Footer({ go, nav, signedIn }) {
  return (
    <footer className="bg-gov-deep text-white/80 mt-6">
      <div className="tricolour h-[3px]" />
      <div className="max-w-7xl mx-auto px-4 sm:px-5 py-9 grid gap-8 sm:grid-cols-2 lg:grid-cols-4 text-[13px]">
        <div>
          <p className="text-white font-semibold mb-2.5">About the registry</p>
          <p className="leading-relaxed text-white/75">
            A prototype national registry that links every CPSE's own material codes under one
            National Material Code, by comparing specifications rather than spelling. No company's
            code is changed or deleted.
          </p>
        </div>
        <div>
          <p className="text-white font-semibold mb-2.5">{signedIn ? 'Pages' : 'Sign in to open'}</p>
          <ul className="grid grid-cols-2 gap-x-3 gap-y-1.5">
            {nav.slice(0, 12).map((s) => (
              <li key={s.id}>
                <button onClick={() => go(s.id)} className="text-left hover:text-white hover:underline underline-offset-2">
                  {s.label}
                </button>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-white font-semibold mb-2.5">Data sources</p>
          <ul className="space-y-2.5 leading-snug">
            <li>
              <span className="text-white">Test data</span>
              <span className="block text-white/65">
                {meta.records} synthetic records across {(meta.cpses || []).join(', ')}. Numbers on these
                pages are measured on it.
              </span>
            </li>
            {real.lines ? (
              <li>
                <span className="text-white">Real tender text</span>
                <span className="block text-white/65">
                  {real.lines} lines from Oil India and NTPC, derived from{' '}
                  <a href={real.url} target="_blank" rel="noopener noreferrer"
                     className="text-white underline underline-offset-2 hover:text-saffron inline-flex items-center gap-1">
                    {real.source}<Icon name="external" size={11} />
                  </a>{' '}
                  on Hugging Face, licensed {real.licence}.
                </span>
              </li>
            ) : null}
            <li>
              <span className="text-white">Classification</span>
              <span className="block text-white/65">UNSPSC, the international product and service code.</span>
            </li>
          </ul>
        </div>
        <div>
          <p className="text-white font-semibold mb-2.5">Rules the registry follows</p>
          <ul className="space-y-1.5 text-white/75">
            <li>Precision over recall</li>
            <li>Nothing is ever deleted</li>
            <li>Every merge is explained</li>
            <li>AI reads; rules decide</li>
            <li>Linking needs no permission; retiring a code is only its owner's decision</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/15">
        <div className="max-w-7xl mx-auto px-4 sm:px-5 py-3.5 flex flex-wrap gap-x-6 gap-y-1.5 text-[12px] text-white/65">
          <span>
            Prototype built for Smart India Hackathon 2026 by Team Overwatch. This is not an official
            Government of India website.
          </span>
          <span className="sm:ml-auto">Last updated: {longDate(meta.generated)}</span>
        </div>
      </div>
    </footer>
  )
}
