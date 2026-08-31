import { motion, useMotionValue, animate, useReducedMotion } from 'framer-motion'
import { useEffect, useState } from 'react'

/* Animated number. Digits are tabular so they do not jitter while counting.
 *
 * Jumps straight to the final value when the viewer asks for reduced motion.
 * That is the accessible behaviour, and it also means a number is never left
 * frozen partway through if the animation frame loop stalls - a screenshot or
 * a backgrounded tab must still show the real figure, not 7% of it. */
export function CountUp({ to, decimals = 0, duration = 0.9, prefix = '', suffix = '' }) {
  const target = Number(to) || 0
  const reduce = useReducedMotion()
  const mv = useMotionValue(reduce ? target : 0)
  const [text, setText] = useState(() => target.toFixed(decimals))

  useEffect(() => {
    if (reduce) {
      setText(target.toFixed(decimals))
      return
    }
    setText((0).toFixed(decimals))
    const controls = animate(mv, target, {
      duration,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setText(v.toFixed(decimals)),
      onComplete: () => setText(target.toFixed(decimals)),
    })
    return controls.stop
  }, [target, decimals, duration, mv, reduce])

  return <span className="tnum">{prefix}{text}{suffix}</span>
}

/* Horizontal meter. Used for the similarity scores, where the FILL is the
   argument - a bar that stops short says more than a number alone. */
export function Meter({ value, tone = 'accent', label, sub, delay = 0, show = true }) {
  const fill = {
    accent: 'bg-accent', good: 'bg-good', danger: 'bg-danger', warn: 'bg-warn',
  }
  const ink = {
    accent: 'text-accent', good: 'text-good', danger: 'text-danger', warn: 'text-warn',
  }
  return (
    <div>
      <div className="flex items-baseline justify-between gap-4 mb-2">
        <span className="label">{label}</span>
        <span className={`font-mono text-[22px] font-semibold tnum leading-none ${ink[tone]}`}>
          {show ? <CountUp to={value} decimals={3} duration={0.7} /> : '—'}
        </span>
      </div>
      <div className="h-2 rounded-full bg-base-raised border border-line-soft overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${fill[tone]}`}
          initial={{ width: 0 }}
          animate={{ width: show ? `${Math.min(1, value) * 100}%` : 0 }}
          transition={{ duration: 0.8, delay, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>
      {sub && <p className="mt-2 text-[12.5px] text-ink-dim leading-snug">{sub}</p>}
    </div>
  )
}

/* On a light ground a chip needs a fill as well as a border, or it reads as
   stray text with a hairline around it. */
export function Chip({ children, tone = 'faint' }) {
  const tones = {
    good:   'text-good   border-good/25   bg-good-bg',
    danger: 'text-danger border-danger/25 bg-danger-bg',
    warn:   'text-warn   border-warn/25   bg-warn-bg',
    accent: 'text-accent border-accent/25 bg-accent-dim',
    faint:  'text-ink-faint border-line bg-base-raised',
  }
  return <span className={`chip ${tones[tone] || tones.faint}`}>{children}</span>
}

/* Headline figure. The rule across the top is what makes a row of these read
   as one instrument panel rather than four unrelated boxes. */
export function Stat({ value, label, sub, tone, decimals = 0, prefix, suffix }) {
  const ink  = { good: 'text-good', danger: 'text-danger', warn: 'text-warn', accent: 'text-accent' }
  const rule = { good: 'bg-good',   danger: 'bg-danger',   warn: 'bg-warn',   accent: 'bg-accent' }
  return (
    <div className="card card-lift p-4 pt-[15px] relative overflow-hidden">
      <span className={`absolute inset-x-0 top-0 h-[3px] ${rule[tone] || 'bg-ink/20'}`} />
      <div className={`text-[30px] font-semibold leading-none tracking-tight ${ink[tone] || 'text-ink'}`}>
        {typeof value === 'number'
          ? <CountUp to={value} decimals={decimals} prefix={prefix} suffix={suffix} />
          : <span className="tnum">{value}</span>}
      </div>
      <div className="mt-2 text-[12.5px] font-medium text-ink-dim">{label}</div>
      {sub && <div className="mt-0.5 text-[11.5px] text-ink-faint">{sub}</div>}
    </div>
  )
}

/* One material record as it arrives from a CPSE - the code in that company's
   own format, and the description exactly as it was written.

   The colour sits in a bar down the left edge rather than in the whole
   border. A tinted border around a white card looks like a validation error;
   an edge bar reads as a label. */
export function RecordCard({ rec, accent = 'accent', children }) {
  const bar = { accent: 'bg-accent', good: 'bg-good', danger: 'bg-danger' }
  return (
    <div className="card p-4 pl-[17px] relative overflow-hidden">
      <span className={`absolute inset-y-0 left-0 w-[3px] ${bar[accent] || 'bg-line'}`} />
      <div className="flex items-center gap-2 mb-2.5">
        <span className="font-mono text-[11px] font-semibold text-accent">{rec?.cpse}</span>
        <span className="font-mono text-[11px] text-ink-faint">{rec?.source_code}</span>
        {rec?.uom && (
          <span className="ml-auto font-mono text-[10px] text-ink-faint px-1.5 py-0.5
                           rounded bg-base-raised border border-line-soft">
            {rec.uom}
          </span>
        )}
      </div>
      <p className="font-mono text-[13px] leading-snug text-ink break-words">
        {rec?.description}
      </p>
      {children}
    </div>
  )
}

export function SectionTitle({ eyebrow, title, sub }) {
  return (
    <div className="mb-5">
      {eyebrow && <p className="label text-accent mb-2">{eyebrow}</p>}
      <h2 className="text-[23px] font-semibold tracking-tight leading-tight text-ink">{title}</h2>
      {sub && <p className="mt-1.5 text-[14px] text-ink-dim max-w-2xl leading-relaxed">{sub}</p>}
    </div>
  )
}
