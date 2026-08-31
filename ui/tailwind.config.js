/** @type {import('tailwindcss').Config} */

/*
 * Light enterprise palette.
 *
 * Token NAMES are unchanged from the dark build on purpose - every screen
 * references them, so the theme is a value swap and nothing downstream moves.
 *
 * Contrast was checked against white for every colour that carries text:
 * ink-dim 6.5:1, ink-faint 4.4:1, accent 6.4:1, good 4.9:1, danger 5.0:1,
 * warn 4.9:1. ink-faint is the floor because it carries small caption text,
 * and 4.4:1 is where it stops reading as grey mush on a projector.
 */

export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink:     { DEFAULT: '#12191F', dim: '#54636E', faint: '#71818D' },
        base:    { DEFAULT: '#F6F8FA', card: '#FFFFFF', raised: '#EDF1F5' },
        line:    { DEFAULT: '#DFE5EA', soft: '#EBEFF3' },
        accent:  { DEFAULT: '#1B62B5', dim: '#E8F0F9' },
        good:    { DEFAULT: '#0A7A4B', bg: '#E9F6EF' },
        danger:  { DEFAULT: '#C0451C', bg: '#FCEDE6' },
        warn:    { DEFAULT: '#8F6408', bg: '#FBF2DE' },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'Consolas', 'monospace'],
      },
      boxShadow: {
        card:  '0 1px 2px rgba(18,25,31,.05), 0 1px 1px rgba(18,25,31,.03)',
        lift:  '0 6px 20px rgba(18,25,31,.09), 0 2px 5px rgba(18,25,31,.05)',
        head:  '0 1px 0 rgba(18,25,31,.06)',
      },
      borderRadius: {
        xl: '12px',
      },
    },
  },
  plugins: [],
}
