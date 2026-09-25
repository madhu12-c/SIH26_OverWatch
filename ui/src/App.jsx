import { useState, useEffect, useCallback } from 'react'
import { AnimatePresence, motion, MotionConfig } from 'framer-motion'
import { reviewQueue } from './lib/data'
import { useSession, useAudit, can, decisionsFrom, pairKey, ROLES } from './lib/store'
import { PageContext } from './lib/page'
import { Icon } from './components/Icons'
import Shell from './components/Shell'
import Login from './screens/Login'
import Dashboard from './screens/Dashboard'
import Analytics from './screens/Analytics'
import Catalogue from './screens/Catalogue'
import Item from './screens/Item'
import Gate from './screens/Gate'
import Migration from './screens/Migration'
import ReviewQueue from './screens/ReviewQueue'
import MatchCase from './screens/MatchCase'
import BlockCase from './screens/BlockCase'
import Savings from './screens/Savings'
import Units from './screens/Units'
import Audit from './screens/Audit'
import RealText from './screens/RealText'

/*
 * The application: sign in, then a portal with a grouped menu.
 *
 * Pages are addressed by the URL hash - #dashboard, #review, #item/NMC-... -
 * so any page can be opened directly, a reload lands where it left off, and
 * the demo video can be recorded one page at a time. Number keys 1-9 open the
 * first nine menu items, so a presenter never hunts for a link mid-sentence.
 *
 * There is no server. Signing in picks a role (see lib/store.js); the role
 * decides what each page lets you do.
 */

const PAGES = [
  { id: 'dashboard', label: 'Dashboard', icon: 'dashboard', group: 'Overview', el: Dashboard },
  { id: 'analytics', label: 'Analytics', icon: 'chart', group: 'Overview', el: Analytics },
  { id: 'catalogue', label: 'National Catalogue', icon: 'search', group: 'Registry', el: Catalogue },
  { id: 'gate', label: 'Creation Gate', icon: 'gate', group: 'Registry', el: Gate },
  { id: 'migration', label: 'Migration', icon: 'migrate', group: 'Registry', el: Migration },
  { id: 'review', label: 'Review Queue', icon: 'review', group: 'Matching', el: ReviewQueue },
  { id: 'match', label: 'Case: The Match', icon: 'match', group: 'Matching', el: MatchCase },
  { id: 'block', label: 'Case: The Block', icon: 'block', group: 'Matching', el: BlockCase },
  { id: 'real', label: 'Real Tender Text', icon: 'file', group: 'Matching', el: RealText },
  { id: 'savings', label: 'Savings', icon: 'rupee', group: 'Procurement', el: Savings },
  { id: 'units', label: 'Units', icon: 'units', group: 'Procurement', el: Units },
  { id: 'audit', label: 'Audit Trail', icon: 'audit', group: 'Governance', el: Audit },
]

function routeFromHash() {
  const raw = decodeURIComponent(window.location.hash.replace(/^#\/?/, ''))
  const [page, ...rest] = raw.split('/')
  if (page === 'item' && rest.length) return { page: 'item', param: rest.join('/') }
  return { page: PAGES.some((p) => p.id === page) ? page : 'dashboard', param: null }
}

export default function App() {
  const session = useSession()
  const audit = useAudit()
  const [route, setRoute] = useState(routeFromHash)

  const go = useCallback((to) => {
    window.location.hash = to
    setRoute(routeFromHash())
    window.scrollTo({ top: 0 })
  }, [])

  // Every change of page starts at the top - whether it came from the menu,
  // a pasted link, or the browser's back button. Without this a page opened
  // by link keeps the previous page's scroll and appears half-way down.
  useEffect(() => { window.scrollTo(0, 0) }, [route.page, route.param, session?.role, session?.org])

  useEffect(() => {
    const onHash = () => setRoute(routeFromHash())
    const onKey = (e) => {
      const tag = e.target.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target.isContentEditable) return
      if (e.ctrlKey || e.metaKey || e.altKey || !session) return
      const i = parseInt(e.key, 10)
      const ids = ROLES[session.role]?.pages ?? []
      if (i >= 1 && i <= 9 && ids[i - 1]) go(ids[i - 1])
    }
    window.addEventListener('hashchange', onHash)
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('hashchange', onHash)
      window.removeEventListener('keydown', onKey)
    }
  }, [go, session])

  if (!session) {
    return (
      <MotionConfig reducedMotion="user">
        <Shell bare go={go} nav={PAGES} crumbs={[{ label: 'Home' }, { label: 'Sign in' }]}>
          <Login />
        </Shell>
      </MotionConfig>
    )
  }

  // Menu badges are live: the review count falls as decisions are taken.
  const decided = decisionsFrom(audit)
  const pending = reviewQueue.filter((p) => can(session, 'decide_pair', p).ok && !decided[pairKey(p)]).length
  // Each role sees its own menu, in its own order (lib/store.js ROLES).
  const role = ROLES[session.role]
  const nav = role.pages.map((id) => PAGES.find((p) => p.id === id)).filter(Boolean).map((p) => ({
    ...p,
    badge: p.id === 'review' ? pending : p.id === 'audit' ? audit.length : null,
  }))

  const page = route.page === 'item' ? null : PAGES.find((p) => p.id === route.page)
  const allowed = route.page === 'item' || role.pages.includes(route.page)
  const Screen = allowed ? (page?.el ?? Dashboard) : null
  const home = { label: role.workspace, to: 'dashboard' }
  const crumbs = route.page === 'item'
    ? [home, { label: 'National Catalogue', to: 'catalogue' }, { label: route.param }]
    : route.page === 'dashboard'
      ? [{ label: 'Home', to: 'dashboard' }, { label: role.workspace }]
      : [home, { label: page.group }, { label: page.label }]
  const ctx = route.page === 'item'
    ? { group: 'Registry', icon: 'search' }
    : route.page === 'dashboard' ? { group: role.workspace, icon: 'dashboard', tone: role.tone } : page

  return (
    <MotionConfig reducedMotion="user">
      <Shell nav={nav} active={route.page === 'item' ? 'catalogue' : route.page} go={go}
             session={session} crumbs={crumbs}>
        <AnimatePresence mode="wait">
          <motion.div
            key={`${route.page}/${route.param ?? ''}/${session.role}/${session.org}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
          >
            <PageContext.Provider value={ctx}>
              {route.page === 'item'
                ? <Item code={route.param} session={session} go={go} />
                : Screen
                  ? <Screen session={session} go={go} />
                  : <Restricted page={page} role={role} go={go} />}
            </PageContext.Provider>
          </motion.div>
        </AnimatePresence>
      </Shell>
    </MotionConfig>
  )
}

/* A page outside the signed-in role's workspace, opened by a pasted link.
   Said plainly, not hidden behind a blank screen. */
function Restricted({ page, role, go }) {
  return (
    <div className="card p-8 text-center max-w-xl mx-auto mt-6">
      <span className="w-12 h-12 rounded-full bg-warn-bg text-warn inline-flex items-center justify-center">
        <Icon name="lock" size={22} />
      </span>
      <h1 className="mt-3 text-[20px] font-bold text-heading">{page.label} is not part of the {role.workspace}</h1>
      <p className="mt-2 text-[14px] text-ink-dim leading-relaxed">
        A {role.label} does not use this page. Each role sees only the pages its work needs.
      </p>
      <button onClick={() => go('dashboard')}
              className="mt-5 inline-flex items-center gap-1.5 px-4 py-2 rounded bg-accent text-onaccent font-semibold text-[13.5px]">
        Back to {role.workspace}
      </button>
    </div>
  )
}
