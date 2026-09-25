// Indian rupee formatting - lakh and crore, not million and billion. A
// ministry audience reads Rs 3.3 cr instantly and $400K not at all.
export function rupees(amount) {
  if (amount == null) return '—'
  const n = Number(amount)
  if (Math.abs(n) >= 1e7) return `₹${(n / 1e7).toFixed(2)} cr`
  if (Math.abs(n) >= 1e5) return `₹${(n / 1e5).toFixed(1)} L`
  if (Math.abs(n) >= 1e3) return `₹${(n / 1e3).toFixed(1)}k`
  return `₹${n.toFixed(0)}`
}

export function rupeesExact(amount) {
  if (amount == null) return '—'
  return '₹' + Number(amount).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

// "2026-09-24" -> "24 September 2026", the way Indian government pages write
// a "Last updated" date. Parsed by hand: new Date('2026-09-24') is UTC
// midnight and can print as the 23rd in a western time zone.
export function longDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '')
  if (!m) return iso || '—'
  const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                  'August', 'September', 'October', 'November', 'December']
  return `${Number(m[3])} ${months[Number(m[2]) - 1]} ${m[1]}`
}

export function pct(value, digits = 1) {
  if (value == null) return '—'
  return `${(Number(value) * 100).toFixed(digits)}%`
}

export function num(value) {
  if (value == null) return '—'
  return Number(value).toLocaleString('en-IN')
}

// 25.0 reads as 25 in a specification. Trailing .0 looks like noise.
export function spec(value) {
  if (value == null || value === '') return '—'
  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : String(value)
  }
  return String(value).replace(/_/g, ' ')
}

export function fieldLabel(name) {
  return String(name).replace(/_/g, ' ')
}

// Field names as a refinery person says them, not as the code stores them.
const PRETTY = {
  iso_designation: 'ISO designation', bore_mm: 'Bore (mm)', od_mm: 'Outside diameter (mm)',
  width_mm: 'Width (mm)', nominal_size_in: 'Nominal size (in)', pressure_class: 'Pressure class',
  material_grade: 'Material grade', body_material: 'Body material', end_connection: 'End connection',
  sub_type: 'Type', seal_type: 'Seal', gasket_type: 'Gasket type', valve_type: 'Valve type',
  part_number: 'Maker part number', length_mm: 'Length (mm)', shaft_dia_mm: 'Shaft diameter (mm)',
  dial_size_mm: 'Dial size (mm)', range_min: 'Range from', range_max: 'Range to', power_hp: 'Power (hp)',
  speed_rpm: 'Speed (rpm)', voltage_v: 'Voltage (V)', wetted_material: 'Wetted material',
  wall_mm: 'Wall (mm)', weight_ppf: 'Weight (lb/ft)', schedule: 'Schedule', construction: 'Construction',
  end_type: 'Ends', finish: 'Finish', standard: 'Standard', voltage_kv: 'Voltage (kV)',
  cross_section_mm2: 'Cross-section (mm²)', cores: 'Cores', conductor: 'Conductor', insulation: 'Insulation',
  armour: 'Armour', cable_type: 'Cable type', power_kw: 'Power (kW)', poles: 'Poles',
  pressure_rating_psi: 'Pressure rating (psi)', thickness_mm: 'Thickness (mm)', noun: 'Item',
  quantities: 'Quantities', equipment_type: 'Equipment', instrument_type: 'Instrument', filler: 'Filler',
  operation: 'Operation', face_type: 'Face', thread: 'Thread', head_type: 'Head',
}
export function prettyField(name) {
  const s = PRETTY[name] ?? fieldLabel(name)
  return s.charAt(0).toUpperCase() + s.slice(1)
}

// Score bands mirror scorer.py exactly. If those thresholds move, move these.
export const AUTO_MERGE = 0.90
export const REVIEW_LOW = 0.70

export function band(score) {
  if (score == null) return 'none'
  if (score >= AUTO_MERGE) return 'auto'
  if (score >= REVIEW_LOW) return 'review'
  return 'low'
}

export const bandColor = {
  auto: 'text-good',
  review: 'text-warn',
  low: 'text-ink-faint',
  none: 'text-ink-faint',
}

export const bandLabel = {
  auto: 'auto-merge',
  review: 'needs review',
  low: 'kept separate',
  none: '—',
}
