/** @type {import('tailwindcss').Config} */

/*
 * Government portal palette.
 *
 * Every colour is a CSS variable holding bare RGB channels (see index.css), so
 * one class on <html> swaps the whole site into high-contrast mode - a GIGW
 * accessibility requirement, not decoration. The `<alpha-value>` form keeps
 * Tailwind's opacity modifiers (border-good/25, bg-base-card/90) working.
 *
 * Token NAMES are unchanged from the previous build on purpose: every screen
 * references them, so the theme is a value swap and nothing downstream moves.
 * New tokens: gov (the navy of the header, menu and footer), saffron and
 * flag green (decoration only - never body text), heading (navy titles that
 * must turn light in high contrast), onaccent (text on an accent fill).
 *
 * Contrast against white, measured, for every colour that carries text:
 * ink-dim 7.7:1, ink-faint 5.0:1, accent 8.3:1, good 6.4:1, danger 6.6:1,
 * warn 6.3:1, saffron-ink 5.9:1, heading 13.9:1. On the #F3F5F9 page ground
 * the weakest, ink-faint, is 4.6:1 - still above the 4.5:1 AA floor.
 */

const v = (name) => `rgb(var(--${name}) / <alpha-value>)`

export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink:     { DEFAULT: v('ink'), dim: v('ink-dim'), faint: v('ink-faint') },
        base:    { DEFAULT: v('base'), card: v('base-card'), raised: v('base-raised') },
        line:    { DEFAULT: v('line'), soft: v('line-soft') },
        accent:  { DEFAULT: v('accent'), dim: v('accent-dim') },
        good:    { DEFAULT: v('good'), bg: v('good-bg') },
        danger:  { DEFAULT: v('danger'), bg: v('danger-bg') },
        warn:    { DEFAULT: v('warn'), bg: v('warn-bg') },
        gov:     { DEFAULT: v('gov'), deep: v('gov-deep'), soft: v('gov-soft') },
        saffron: { DEFAULT: v('saffron'), ink: v('saffron-ink'), bg: v('saffron-bg') },
        flag:    { green: v('flag-green') },
        teal:    v('teal'),
        maroon:  v('maroon'),
        heading: v('heading'),
        onaccent: v('on-accent'),
      },
      fontFamily: {
        sans: ['"Noto Sans"', '"Noto Sans Devanagari"', '"Segoe UI"', 'system-ui', 'sans-serif'],
        deva: ['"Noto Sans Devanagari"', '"Nirmala UI"', 'Mangal', '"Noto Sans"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'Consolas', 'monospace'],
      },
      boxShadow: {
        card:  '0 1px 2px rgba(10,42,94,.06), 0 1px 1px rgba(10,42,94,.04)',
        lift:  '0 6px 18px rgba(10,42,94,.10), 0 2px 5px rgba(10,42,94,.06)',
        head:  '0 2px 6px rgba(6,28,64,.18)',
      },
      // Government portals are square-edged. Rounded pills read as a startup.
      borderRadius: {
        sm: '2px',
        DEFAULT: '3px',
        md: '4px',
        lg: '5px',
        xl: '6px',
      },
    },
  },
  plugins: [],
}
