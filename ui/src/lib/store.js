import { useSyncExternalStore } from 'react'

/*
 * Session and audit log - the two pieces of state that make the demo a
 * working system rather than a set of slides.
 *
 * There is no server (docs/02-decisions/009), so both live in the browser.
 * SIGNING IN IS NOT AUTHENTICATION. It picks a role, and the role decides what
 * the screens let you do - which is how the consent model is demonstrated:
 * linking needs the registrar, retiring a code needs the company that owns
 * it, anyone affected may dispute.
 *
 * Every action a person takes is appended to the audit log. Nothing is ever
 * edited or removed from it except by "clear demo log", which is itself the
 * first entry of the fresh log.
 */

const KEY_SESSION = 'nmcr.session'
const KEY_AUDIT = 'nmcr.audit'
const MAX_EVENTS = 400

function read(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}
function write(key, value) {
  try { window.localStorage.setItem(key, JSON.stringify(value)) } catch { /* not persisted */ }
}

let state = { session: read(KEY_SESSION, null), audit: read(KEY_AUDIT, []) }
const listeners = new Set()
const emit = () => listeners.forEach((l) => l())
const subscribe = (l) => { listeners.add(l); return () => listeners.delete(l) }

export const useSession = () => useSyncExternalStore(subscribe, () => state.session)
export const useAudit = () => useSyncExternalStore(subscribe, () => state.audit)

/* ---------------------------------------------------------------- roles */

/* Each role has its own workspace: its own name, colour and menu. A page not
   in a role's menu is not reachable from its menu, and opening it by link
   shows why - so four sign-ins are four different portals, not one portal
   with a different name in the corner. Item pages are open to every role. */

export const ROLES = {
  registrar: {
    workspace: 'Registrar Desk',
    tone: 'bg-gov',
    pages: ['dashboard', 'review', 'catalogue', 'gate', 'match', 'block', 'real', 'analytics', 'migration', 'audit'],
    label: 'National Registrar',
    short: 'Registrar',
    org: 'Registry',
    blurb: 'Issues national codes and decides every link between two companies.',
    rights: ['Decide links between companies', 'See every company', 'Cannot retire a company\'s code'],
  },
  reviewer: {
    workspace: 'Reviewer Workspace',
    tone: 'bg-good',
    pages: ['dashboard', 'review', 'catalogue', 'migration', 'units', 'gate', 'match', 'block', 'real', 'audit'],
    label: 'CPSE Reviewer',
    short: 'Reviewer',
    needsOrg: true,
    blurb: 'Clears duplicates inside its own company, disputes links, retires only its own codes.',
    rights: ['Decide pairs inside own company', 'Dispute any link to own codes', 'Retire own codes only'],
  },
  procurement: {
    workspace: 'Buying Desk',
    tone: 'bg-saffron-ink',
    pages: ['dashboard', 'savings', 'analytics', 'catalogue', 'migration', 'units'],
    label: 'Procurement Officer',
    short: 'Procurement',
    needsOrg: true,
    blurb: 'Sees savings and price benchmarks — never another company\'s raw price.',
    rights: ['See own prices in full', 'See other companies only as a benchmark', 'Download own mapping file'],
  },
  ministry: {
    workspace: 'National Overview',
    tone: 'bg-maroon',
    pages: ['dashboard', 'analytics', 'savings', 'catalogue', 'real', 'audit'],
    label: 'Ministry Viewer',
    short: 'Ministry',
    org: 'Ministry (read-only)',
    blurb: 'Read-only dashboards, analytics and the audit trail.',
    rights: ['See every dashboard', 'Read the audit trail', 'Change nothing'],
  },
}

export function sessionLabel(s) {
  if (!s) return ''
  return ROLES[s.role]?.needsOrg ? `${s.org} ${ROLES[s.role].short}` : ROLES[s.role]?.label
}

/* What a role may do. Every screen asks this instead of checking roles
   itself, so the rules live in one place - the same place a real system
   would enforce them. Returns { ok, why }. */
export function can(session, action, target = {}) {
  const role = session?.role
  const org = session?.org
  const no = (why) => ({ ok: false, why })
  const yes = { ok: true, why: '' }

  switch (action) {
    case 'decide_pair': {
      const cross = target.a?.cpse !== target.b?.cpse
      if (role === 'registrar') return cross ? yes : no('Pairs inside one company go to that company\'s reviewer.')
      if (role === 'reviewer') {
        if (!cross && target.a?.cpse === org) return yes
        return cross ? no('A link between two companies is decided by the national registrar. You can dispute it once issued.')
                     : no(`This pair belongs to ${target.a?.cpse}'s reviewer.`)
      }
      return no('Your role can view the queue but not decide pairs.')
    }
    case 'dispute': {
      if (role !== 'reviewer') return no('Only a company reviewer can dispute a link.')
      return (target.cpses || []).includes(org) ? yes : no('You can dispute only links that include your company\'s codes.')
    }
    case 'retire': {
      if (role !== 'reviewer') return no('Only the company that owns a code can retire it.')
      return target.cpse === org ? yes : no(`Only ${target.cpse} can retire ${target.cpse}'s code.`)
    }
    case 'export': {
      if (role === 'registrar' || role === 'ministry') return yes
      return target.cpse === org ? yes : no('You can download only your own company\'s file.')
    }
    case 'see_prices': {
      if (role === 'registrar' || role === 'ministry') return yes
      return target.cpse === org ? yes : no('Another company\'s price is shown only as a benchmark.')
    }
    case 'clear_log':
      return role === 'registrar' ? yes : no('Only the registrar can reset the demo log.')
    default:
      return no('Not permitted.')
  }
}

/* ---------------------------------------------------------------- actions */

let counter = 0
export function log(verb, detail = {}) {
  const s = state.session
  const event = {
    id: `${Date.now().toString(36)}-${(counter++).toString(36)}`,
    ts: new Date().toISOString(),
    actor: s ? sessionLabel(s) : 'System',
    role: s?.role ?? 'system',
    org: s?.org ?? '',
    verb,
    ...detail,
  }
  state = { ...state, audit: [event, ...state.audit].slice(0, MAX_EVENTS) }
  write(KEY_AUDIT, state.audit)
  emit()
  return event
}

export function signIn(role, org) {
  const session = { role, org: ROLES[role].needsOrg ? org : ROLES[role].org, since: new Date().toISOString() }
  state = { ...state, session }
  write(KEY_SESSION, session)
  log('SIGN_IN', { object: sessionLabel(session) })
}

export function signOut() {
  log('SIGN_OUT', { object: sessionLabel(state.session) })
  state = { ...state, session: null }
  write(KEY_SESSION, null)
  emit()
}

export function clearAudit() {
  state = { ...state, audit: [] }
  write(KEY_AUDIT, [])
  log('LOG_RESET', { object: 'demo audit log', note: 'All earlier demo events removed by the registrar.' })
}

/* How each audit verb reads to a person, and its tone. */
export const VERBS = {
  SIGN_IN: { text: 'signed in', tone: 'faint' },
  SIGN_OUT: { text: 'signed out', tone: 'faint' },
  ACCEPT: { text: 'approved a match', tone: 'good' },
  REJECT: { text: 'rejected a match', tone: 'danger' },
  SKIP: { text: 'skipped a pair', tone: 'faint' },
  DISPUTE: { text: 'disputed a link', tone: 'warn' },
  RETIRE_PROPOSED: { text: 'proposed retiring its own code', tone: 'warn' },
  EXPORT: { text: 'downloaded a mapping file', tone: 'accent' },
  AUDIT_EXPORT: { text: 'downloaded the audit log', tone: 'accent' },
  DENIED: { text: 'was refused an action', tone: 'danger' },
  LOG_RESET: { text: 'reset the demo log', tone: 'faint' },
}

/* Decisions taken on review pairs, keyed by the pair, so the queue, the
   dashboard and the audit trail all agree on what has been decided. */
export function pairKey(p) {
  return [p.a?.record_id, p.b?.record_id].sort().join('~')
}
export function decisionsFrom(audit) {
  const out = {}
  for (let i = audit.length - 1; i >= 0; i--) {         // oldest first, so the latest wins
    const e = audit[i]
    if (e.pair && ['ACCEPT', 'REJECT', 'SKIP'].includes(e.verb)) out[e.pair] = e.verb
  }
  return out
}
