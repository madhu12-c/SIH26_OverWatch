/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink:     { DEFAULT: '#e6ecf3', dim: '#93a3b4', faint: '#61728a' },
        base:    { DEFAULT: '#0a0e13', card: '#121a23', raised: '#1a242f' },
        line:    { DEFAULT: '#233040', soft: '#1b2530' },
        accent:  { DEFAULT: '#4b9fe1', dim: '#17324a' },
        good:    { DEFAULT: '#46c98b', bg: '#10291f' },
        danger:  { DEFAULT: '#e5734a', bg: '#2c1a12' },
        warn:    { DEFAULT: '#d9a441', bg: '#2a2113' },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
