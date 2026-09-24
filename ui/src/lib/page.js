import { createContext, useContext } from 'react'

/*
 * Which page is open, for components deep inside it. SectionTitle reads this
 * to paint the page banner in its section's colour, so moving from Registry
 * to Matching is visible at a glance instead of every page looking alike.
 *
 * Class names are written out in full so Tailwind finds them.
 */

export const SECTION = {
  Overview:    { bg: 'bg-gov',         text: 'text-gov',         tint: 'bg-accent-dim' },
  Registry:    { bg: 'bg-teal',        text: 'text-teal',        tint: 'bg-accent-dim' },
  Matching:    { bg: 'bg-maroon',      text: 'text-maroon',      tint: 'bg-danger-bg' },
  Procurement: { bg: 'bg-saffron-ink', text: 'text-saffron-ink', tint: 'bg-saffron-bg' },
  Governance:  { bg: 'bg-good',        text: 'text-good',        tint: 'bg-good-bg' },
}

export const PageContext = createContext(null)
export const usePage = () => useContext(PageContext)
