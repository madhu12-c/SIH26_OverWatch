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
  const tones = {
    accent: 'bg-accent',
    good: 'bg-good',
    danger: 'bg-danger',
    warn: 'bg-warn',
  }
  const textTones = {
    accent: 'text-accent',
    good: 'text-good',
    danger: 'text-danger',
    warn: 'text-warn',
  }
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5">
        <span className="label">{label}</span>
        <span className={`font-mono text-lg font-semibold tnum ${textTones[tone]}`}>
          {show ? <CountUp to={value} decimals={3} duration={0.7} /> : '—'}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-base-raised overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${tones[tone]}`}
          initial={{ width: 0 }}
          animate={{ width: show ? `${Math.min(1, value) * 100}%` : 0 }}
          transition={{ duration: 0.8, delay, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>
      {sub && <p className="mt-1.5 text-[12.5px] text-ink-faint leading-snug">{sub}</p>}
    </div>
  )
}

export function Chip({ children, tone = 'faint' }) {
  const tones = {
    good: 'text-good',
    danger: 'text-danger',
    warn: 'text-warn',
    accent: 'text-accent',
    faint: 'text-ink-faint',
  }
  return <span className={`chip ${tones[tone]}`}>{children}</span>
}

export function Stat({ value, label, sub, tone, decimals = 0, prefix, suffix }) {
  const tones = { good: 'text-good', danger: 'text-danger', warn: 'text-warn' }
  return (
    <div className="card p-4">
      <div className={`text-[28px] font-semibold leading-none tracking-tight ${tones[tone] || ''}`}>
        {typeof value === 'number'
          ? <CountUp to={value} decimals={decimals} prefix={prefix} suffix={suffix} />
          : <span className="tnum">{value}</span>}
      </div>
      <div className="mt-1.5 text-[12.5px] text-ink-dim">{label}</div>
      {sub && <div className="mt-0.5 text-[11.5px] text-ink-faint">{sub}</div>}
    </div>
  )
}

/* One material record as it arrives from a CPSE - the code in that company's
   own format, and the description exactly as it was written. */
export function RecordCard({ rec, accent = 'accent', children }) {
  const ring = { accent: 'border-accent/40', good: 'border-good/40', danger: 'border-danger/40' }
  return (
    <div className={`card p-4 border ${ring[accent] || 'border-line'}`}>
      <div className="flex items-center gap-2 mb-2.5">
        <span className="font-mono text-[11px] font-semibold text-accent">{rec?.cpse}</span>
        <span className="font-mono text-[11px] text-ink-faint">{rec?.source_code}</span>
        {rec?.uom && <span className="ml-auto font-mono text-[10.5px] text-ink-faint">{rec.uom}</span>}
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
      {eyebrow && <p className="label text-accent mb-1.5">{eyebrow}</p>}
      <h2 className="text-[22px] font-semibold tracking-tight leading-tight">{title}</h2>
      {sub && <p className="mt-1 text-[14px] text-ink-dim max-w-2xl">{sub}</p>}
    </div>
  )
}
