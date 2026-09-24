/*
 * Line icons, drawn inline so the single-file build needs no icon font and no
 * network. 24-unit grid, stroke in currentColor, so every icon follows the
 * text colour - including into high-contrast mode.
 */

const PATHS = {
  home: <><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9.5V21h14V9.5" /><path d="M10 21v-6h4v6" /></>,
  match: <><circle cx="6" cy="6" r="2.5" /><circle cx="6" cy="18" r="2.5" /><circle cx="18" cy="12" r="2.5" /><path d="M8.5 6.5c3.5.5 4.5 3.5 7 5M8.5 17.5c3.5-.5 4.5-3.5 7-5" /></>,
  block: <><circle cx="12" cy="12" r="9" /><path d="m5.6 5.6 12.8 12.8" /></>,
  review: <><path d="M4 6h11M4 12h11M4 18h6" /><path d="m14.5 17.5 2.2 2.2 4.3-4.7" /></>,
  rupee: <><path d="M6 4h12M6 9h12" /><path d="M9 4c4.5 0 6 2 6 5s-2.5 5-6 5H7l8 7" /></>,
  units: <><rect x="3" y="7" width="18" height="10" rx="1" /><path d="M7 7v3.5M11 7v5M15 7v3.5M18.5 7v5" /></>,
  codes: <><path d="M4 5v14M7.5 5v14M11 5v14M13.5 5v14M17 5v14M20 5v14" /></>,
  gate: <><path d="M12 3 4.5 6v6c0 4.5 3.2 7.8 7.5 9 4.3-1.2 7.5-4.5 7.5-9V6z" /><path d="m8.5 12 2.5 2.5 4.5-5" /></>,
  pause: <><path d="M9 5v14M15 5v14" /></>,
  play: <><path d="M7 5l12 7-12 7z" /></>,
  contrast: <><circle cx="12" cy="12" r="9" /><path d="M12 3a9 9 0 0 0 0 18z" fill="currentColor" /></>,
  arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
  external: <><path d="M14 4h6v6M20 4l-9 9" /><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" /></>,
  data: <><ellipse cx="12" cy="6" rx="7" ry="3" /><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6" /><path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3" /></>,
  file: <><path d="M14 3H6v18h12V7z" /><path d="M14 3v4h4M9 12h6M9 16h6" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7.5v.5" /></>,
  dashboard: <><rect x="3" y="3" width="7.5" height="9" rx="1" /><rect x="13.5" y="3" width="7.5" height="5" rx="1" /><rect x="13.5" y="11" width="7.5" height="10" rx="1" /><rect x="3" y="15" width="7.5" height="6" rx="1" /></>,
  chart: <><path d="M4 20V10M10 20V4M16 20v-7M21 20H3" /></>,
  search: <><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4.5 4.5" /></>,
  migrate: <><path d="M4 8h13M13 4l4 4-4 4" /><path d="M20 16H7M11 12l-4 4 4 4" /></>,
  audit: <><path d="M8 4h8v3H8z" /><path d="M8 5.5H6a1 1 0 0 0-1 1V20a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V6.5a1 1 0 0 0-1-1h-2" /><path d="M9 12h6M9 16h4" /></>,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21c1-4 4.5-6 8-6s7 2 8 6" /></>,
  logout: <><path d="M14 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4" /><path d="M10 16l-4-4 4-4M6 12h10" /></>,
  menu: <><path d="M4 6h16M4 12h16M4 18h16" /></>,
  lock: <><rect x="5" y="10.5" width="14" height="10" rx="1.5" /><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" /></>,
  download: <><path d="M12 4v11M7 10l5 5 5-5" /><path d="M4 19h16" /></>,
  flag: <><path d="M5 21V4M5 4h11l-2 4 2 4H5" /></>,
  close: <><path d="M6 6l12 12M18 6 6 18" /></>,
  check: <><path d="m5 12.5 4.5 4.5L19 7.5" /></>,
}

export function Icon({ name, size = 18, className = '', strokeWidth = 1.8 }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={`shrink-0 ${className}`}
    >
      {PATHS[name]}
    </svg>
  )
}

/*
 * The registry's own mark: many company codes on the left, one national code
 * on the right. Deliberately NOT the State Emblem, the Ashoka Chakra or the
 * flag - using those is restricted by law, and this is a prototype, not a
 * government body.
 */
export function Logo({ size = 52 }) {
  return (
    <svg viewBox="0 0 52 52" width={size} height={size} aria-hidden="true" className="shrink-0">
      <circle cx="26" cy="26" r="24.5" fill="none" stroke="rgb(var(--saffron))" strokeWidth="2" />
      <circle cx="26" cy="26" r="21" fill="rgb(var(--gov))" />
      <circle cx="26" cy="26" r="21" fill="none" stroke="rgb(var(--line))" strokeOpacity=".35" />
      {[15, 23, 31].map((y) => (
        <rect key={y} x="12" y={y} width="7" height="6" rx="1" fill="#fff" fillOpacity=".92" />
      ))}
      <path d="M20 18c4 0 5 8 9 8M20 26h9M20 34c4 0 5-8 9-8" fill="none"
            stroke="#fff" strokeOpacity=".75" strokeWidth="1.5" strokeLinecap="round" />
      <rect x="29" y="20" width="12" height="12" rx="1.5" fill="rgb(var(--saffron))" />
      <path d="m32 26 2.2 2.2 4-4.6" fill="none" stroke="#061C40" strokeWidth="1.8"
            strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
