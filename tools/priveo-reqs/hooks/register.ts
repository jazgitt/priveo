import type { Register } from 'claude-code'

const REQS = [
  'docs/reqs/customer-app-functional-requirements.md',
  'docs/reqs/admin-functional-requirements.md',
  'docs/reqs/crew-functional-requirements.md',
]
const ID = /\b[A-Z]{2,6}(?:-[A-Z]{2,6})?-\d{2,3}\b/g
const ROW = /^\|\s*([A-Z]{2,6}(?:-[A-Z]{2,6})?-\d{2,3})\s*\|/
const REQS_FILE = /docs\/reqs\/[^/]+\.md$/
const PROTOTYPE = /(^|\/)docs\/prototype\//
const ENV_FILE = /(^|\/)\.env(\.(?!example$|sample$|template$)[^/]*)?$/

const norm = (p: string) => p.replace(/\\/g, '/')
const short = (p: string) => p.replace('docs/reqs/', '').replace('-functional-requirements.md', '')

type Row = { id: string; line: number; text: string; status: string; raw: string }
type Parsed = { file: string; rows: Row[]; cites: { id: string; line: number }[]; lines: string[] }

export function parse(file: string, text: string): Parsed {
  const lines = text.split(/\r?\n/)
  const rows: Row[] = []
  const cites: { id: string; line: number }[] = []
  lines.forEach((l, i) => {
    const m = ROW.exec(l)
    if (m) {
      const cells = l.split('|').map(c => c.trim())
      rows.push({ id: m[1], line: i + 1, text: cells[2] ?? '', status: cells[cells.length - 2] ?? '', raw: l })
    }
    for (const c of l.matchAll(ID)) cites.push({ id: c[0], line: i + 1 })
  })
  return { file, rows, cites, lines }
}

export function integrity(all: Parsed[]) {
  const defs = new Map<string, string[]>()
  for (const p of all)
    for (const r of p.rows) defs.set(r.id, [...(defs.get(r.id) ?? []), `${short(p.file)}:${r.line}`])
  const dupes = [...defs].filter(([, w]) => w.length > 1)
  const missing: string[] = []
  for (const p of all)
    for (const c of p.cites) if (!defs.has(c.id)) missing.push(`${c.id} (${short(p.file)}:${c.line})`)
  return { defs, dupes, missing: [...new Set(missing)] }
}

async function load($: any): Promise<Parsed[]> {
  const out: Parsed[] = []
  for (const f of REQS) out.push(parse(f, await $.fs.read(f).catch(() => '')))
  return out
}

function ids(all: Parsed[]): string {
  const { defs, dupes, missing } = integrity(all)
  const out = [`${defs.size} IDs defined.`]
  for (const p of all) {
    const g = new Map<string, number>()
    for (const r of p.rows) {
      const k = r.id.replace(/-\d+$/, '')
      g.set(k, (g.get(k) ?? 0) + 1)
    }
    out.push(`${short(p.file)}: ${p.rows.length} rows. ` + [...g].map(([k, n]) => `${k} ${n}`).join(', '))
  }
  out.push(
    dupes.length
      ? 'Defined twice:\n' + dupes.map(([i, w]) => `  ${i}: ${w.join(', ')}`).join('\n')
      : 'No duplicate IDs.',
  )
  out.push(
    missing.length
      ? 'Cited but not defined:\n' + missing.map(m => `  ${m}`).join('\n')
      : 'No undefined citations.',
  )
  return out.join('\n')
}

function open(all: Parsed[]): string {
  const out: string[] = []
  const cut = (s: string) => (s.length > 90 ? s.slice(0, 87) + '...' : s)
  for (const word of ['Open', 'Derived']) {
    const re = new RegExp(`\\b${word}\\b`)
    const hits = all.flatMap(p =>
      p.rows
        .filter(r => re.test(r.status) && (word === 'Derived' ? !/\bOpen\b/.test(r.status) : true))
        .map(r => ({ p, r })),
    )
    out.push(`${word}: ${hits.length}`)
    for (const { p, r } of hits) out.push(`  ${r.id} (${short(p.file)}:${r.line}) ${cut(r.text)}`)
  }
  for (const p of all) {
    const h = p.lines.findIndex(l => /^##\s.*open questions/i.test(l))
    if (h < 0) continue
    out.push(`Open questions, ${short(p.file)} (line ${h + 1}):`)
    for (const l of p.lines.slice(h + 1)) {
      if (/^(##\s|---)/.test(l) || /^Answered/.test(l)) break
      if (/^\d+\./.test(l)) out.push('  ' + cut(l))
    }
  }
  return out.join('\n')
}

async function syncCheck($: any, now: Parsed[]): Promise<string> {
  const git = (args: string[]) => $.process.run(['git', ...args], { cwd: 'docs/reqs' })
  const st = await git(['diff', '--name-only', 'HEAD', '--', '.'])
  if (st.exitCode !== 0) return 'git diff failed: ' + st.stderr.trim()
  const changed = st.stdout.split('\n').map((s: string) => norm(s.trim())).filter((s: string) => s.endsWith('.md'))
  const files = REQS.filter(f => changed.some((c: string) => f.endsWith(c)))
  if (!files.length) return 'No uncommitted changes in docs/reqs. Nothing to sync.'
  const out = [`Changed: ${files.map(short).join(', ')}`]
  const before = new Map<string, Set<string>>()
  for (const f of files) {
    const name = f.replace('docs/reqs/', '')
    const old = await git(['show', `HEAD:./${name}`])
    before.set(f, new Set(parse(f, old.exitCode === 0 ? old.stdout : '').rows.map(r => r.id)))
    const diff = await git(['diff', 'HEAD', '--', name])
    if (!/^\+\*\*Status:\*\*/m.test(diff.stdout))
      out.push(`  ${short(f)}: version line (**Status:**) not changed. Bump it.`)
  }
  const defs = integrity(now).defs
  for (const f of files) {
    const p = now.find(x => x.file === f)!
    const old = before.get(f)!
    const added = p.rows.filter(r => !old.has(r.id)).map(r => r.id)
    const gone = [...old].filter(i => !defs.has(i))
    if (gone.length) out.push(`  ${short(f)}: IDs removed (never renumber or delete): ${gone.join(', ')}`)
    for (const id of added) {
      const elsewhere = now
        .filter(x => x.file !== f && x.cites.some(c => c.id === id))
        .map(x => short(x.file))
      out.push(`  ${short(f)}: new ${id}, cited in: ${elsewhere.join(', ') || 'no other file'}`)
    }
  }
  const others = REQS.filter(f => !files.includes(f)).map(short)
  if (others.length) out.push(`Unchanged, check by hand: ${others.join(', ')}`)
  out.push(
    'Also check: statuses, notifications (NOTIF-), business rules, data entities, admin section 12 (needed by / covered by), section 13 and deferred list, README prototype differences.',
  )
  return out.join('\n')
}

// Feature lifecycle. A feature is one requirement ID. State lives in STATUS_FILE.
const STATUS_FILE = 'docs/feature-status.json'
const STAGES = [
  ['draft', 'Draft', 'Draft'],
  ['approved', 'Approved', 'Approved'],
  ['ready', 'Ready for Dev', 'Ready'],
  ['dev', 'In Dev', 'InDev'],
  ['unit', 'Unit Tested >95%', 'Unit>95'],
  ['functional', 'Functional Tested', 'Functional'],
  ['security', 'Security Test', 'Security'],
] as const
export type Stage = (typeof STAGES)[number][0]
export type Feature = { stage: Stage; hash: string; bugs: number }
export type Store = { version: 1; features: Record<string, Feature> }

const ALIAS: Record<string, Stage> = {
  draft: 'draft',
  approved: 'approved',
  ready: 'ready',
  dev: 'dev',
  indev: 'dev',
  unit: 'unit',
  functional: 'functional',
  func: 'functional',
  security: 'security',
  sec: 'security',
}
const label = (s: Stage) => STAGES.find(x => x[0] === s)![1]
const USAGE =
  'Usage: /fstatus | /fstatus list <stage|bugs> | /fstatus set <stage> <all|PREFIX|ID...> | /fstatus bugs <ID> <n>\nStages: ' +
  Object.keys(ALIAS).join(', ')

// A requirement row changed when its text, normalised for spacing, changes.
export function hash(raw: string): string {
  const s = raw.replace(/\s+/g, ' ').trim()
  let h = 0x811c9dc5
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 0x01000193)
  return `${(h >>> 0).toString(16)}-${s.length}`
}

// First run (no previous store): every ID is Approved. After that: a new ID or a changed row is Draft.
export function reconcile(prev: Store | undefined, all: Parsed[]) {
  const features: Record<string, Feature> = {}
  const toDraft: string[] = []
  const added: string[] = []
  for (const p of all)
    for (const r of p.rows) {
      const h = hash(r.raw)
      const old = prev?.features[r.id]
      if (!prev) features[r.id] = { stage: 'approved', hash: h, bugs: 0 }
      else if (!old) {
        features[r.id] = { stage: 'draft', hash: h, bugs: 0 }
        added.push(r.id)
      } else if (old.hash !== h) {
        features[r.id] = { ...old, stage: 'draft', hash: h }
        if (old.stage !== 'draft') toDraft.push(r.id)
      } else features[r.id] = old
    }
  return { store: { version: 1, features } as Store, toDraft, added }
}

export function serialize(store: Store): string {
  const rows = Object.entries(store.features).map(([id, f]) => `    ${JSON.stringify(id)}: ${JSON.stringify(f)}`)
  return `{\n  "version": 1,\n  "features": {\n${rows.join(',\n')}\n  }\n}\n`
}

export function tally(store: Store, ids?: string[]) {
  const by = Object.fromEntries(STAGES.map(s => [s[0], 0])) as Record<Stage, number>
  let bugs = 0
  for (const id of ids ?? Object.keys(store.features)) {
    const f = store.features[id]
    by[f.stage]++
    bugs += f.bugs
  }
  return { by, bugs }
}

export function featureLine(store: Store, ids?: string[]): string {
  const { by, bugs } = tally(store, ids)
  const parts = STAGES.filter(s => by[s[0]] > 0).map(s => `${s[2]} ${by[s[0]]}`)
  return [...parts, `Bugs ${bugs}`].join(' · ')
}

export function statusText(all: Parsed[], store?: Store): string {
  const { dupes, missing } = integrity(all)
  const n = dupes.length + missing.length
  const open = all.reduce((sum, p) => sum + p.rows.filter(r => /\bOpen\b/.test(r.status)).length, 0)
  const head = `${n ? `IDs: ${n} problem${n > 1 ? 's' : ''}` : 'IDs: OK'} · ${open} open`
  return `${head} | ${store ? featureLine(store) : 'features: status file unreadable'}`
}

async function readStore($: any): Promise<Store | undefined> {
  if (!(await $.fs.exists(STATUS_FILE))) return undefined
  const s = JSON.parse(await $.fs.read(STATUS_FILE))
  if (s?.version !== 1 || typeof s.features !== 'object' || s.features === null) throw new Error('bad status file')
  return s
}

// Reads the status file, moves new or changed IDs to Draft, writes it back when anything moved.
async function sync($: any, all: Parsed[]) {
  try {
    const prev = await readStore($)
    const r = reconcile(prev, all)
    if (!prev || serialize(prev) !== serialize(r.store)) await $.fs.write(STATUS_FILE, serialize(r.store))
    return r
  } catch {
    return { store: undefined, toDraft: [] as string[], added: [] as string[] }
  }
}

function matchIds(store: Store, target: string): string[] {
  const t = target.toUpperCase()
  const all = Object.keys(store.features)
  return t === 'ALL' ? all : all.filter(id => id === t || id.startsWith(t + '-'))
}

function summary(store: Store): string {
  const out = [`${Object.keys(store.features).length} features: ${featureLine(store)}`]
  const groups = new Map<string, string[]>()
  for (const id of Object.keys(store.features)) {
    const g = id.replace(/-\d+$/, '')
    groups.set(g, [...(groups.get(g) ?? []), id])
  }
  for (const [g, ids] of groups) out.push(`  ${g} (${ids.length}): ${featureLine(store, ids)}`)
  return out.join('\n')
}

async function fstatus($: any, args: string, all: Parsed[]): Promise<string> {
  const r = await sync($, all)
  const store = r.store
  if (!store) return `${STATUS_FILE} is unreadable. Fix or delete it (deleting re-seeds every ID as Approved).`
  const [cmd, ...rest] = args.trim().split(/\s+/).filter(Boolean)
  let text: string
  if (!cmd) text = summary(store)
  else if (cmd === 'list') {
    const want = rest[0]?.toLowerCase()
    const stage = ALIAS[want ?? '']
    const ids = Object.entries(store.features)
      .filter(([, f]) => (want === 'bugs' ? f.bugs > 0 : f.stage === stage))
      .map(([id, f]) => (want === 'bugs' ? `${id} (${f.bugs})` : id))
    if (want !== 'bugs' && !stage) return USAGE
    text = ids.length ? `${ids.length}: ${ids.join(', ')}` : 'None.'
  } else if (cmd === 'set') {
    const stage = ALIAS[rest[0]?.toLowerCase() ?? '']
    const targets = rest.slice(1)
    if (!stage || !targets.length) return USAGE
    const ids = [...new Set(targets.flatMap(t => matchIds(store, t)))]
    if (!ids.length) return `No IDs match ${targets.join(', ')}.`
    for (const id of ids) store.features[id] = { ...store.features[id], stage }
    await $.fs.write(STATUS_FILE, serialize(store))
    text = `${ids.length} feature${ids.length > 1 ? 's' : ''} set to ${label(stage)}.`
  } else if (cmd === 'bugs') {
    const id = rest[0]?.toUpperCase() ?? ''
    const n = Number(rest[1])
    if (!store.features[id] || !Number.isInteger(n) || n < 0) return USAGE
    store.features[id] = { ...store.features[id], bugs: n }
    await $.fs.write(STATUS_FILE, serialize(store))
    text = `${id}: ${n} open bug${n === 1 ? '' : 's'}.`
  } else return USAGE
  $.ui.status(statusText(all, store))
  return text
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    for (const [name, description] of [
      ['ids', 'List requirement IDs, duplicates and undefined citations'],
      ['open', 'List Open and Derived requirements and open questions'],
      ['synccheck', 'Check uncommitted requirement edits for cross-file follow-ups'],
      ['fstatus', 'Feature lifecycle: summary, list, set <stage> <IDs>, bugs <ID> <n>'],
    ])
      await $.command.register({ name, description })
    try {
      const all = await load($)
      $.ui.status(statusText(all, (await sync($, all)).store))
    } catch {}
    return next(e)
  })

  on('command.run', { command: 'ids' }, async $ => ({ text: ids(await load($)) })).catch(() => ({ text: '/ids failed.' }))
  on('command.run', { command: 'open' }, async $ => ({ text: open(await load($)) })).catch(() => ({ text: '/open failed.' }))
  on('command.run', { command: 'synccheck' }, async $ => ({
    text: await syncCheck($, await load($)),
  })).catch(() => ({ text: '/synccheck failed.' }))
  on('command.run', { command: 'fstatus' }, async ($, e) => ({
    text: await fstatus($, e.args, await load($)),
  })).catch(() => ({ text: '/fstatus failed.' }))

  for (const tool of ['Edit', 'Write'] as const) {
    on('tool.call', { tool }, async ($, e, next) => {
      const p = norm(e.file_path)
      if (PROTOTYPE.test(p)) return { deny: 'docs/prototype is read-only source material.' }
      if (ENV_FILE.test(p)) return { deny: `${p}: .env files are never written from here.` }
      const ran = await next(e)
      if (REQS_FILE.test(p) && ran.deny === undefined && ran.isError !== true) {
        const all = await load($)
        const { dupes, missing } = integrity(all)
        const n = dupes.length + missing.length
        const synced = await sync($, all)
        $.ui.status(statusText(all, synced.store))
        const moved = [...synced.toDraft, ...synced.added]
        if (moved.length)
          $.ui.toast(`${moved.length} to Draft: ${moved.slice(0, 3).join(', ')}${moved.length > 3 ? '...' : ''}`)
        if (n)
          $.ui.toast(
            `${dupes.length} duplicate, ${missing.length} undefined: ${[...dupes.map(d => d[0]), ...missing]
              .slice(0, 3)
              .join(', ')}. Run /ids`,
          )
      }
      return ran
    }).catch(($, e, next) =>
      next.called ? next(e) : { deny: 'priveo-reqs: its guard failed.' },
    )
  }

  on('tool.call', { tool: 'Read' }, ($, e, next) => {
    const p = norm(e.file_path)
    if (PROTOTYPE.test(p) && /\.html?$/.test(p) && e.limit === undefined)
      return { deny: 'The prototype HTML is about 1 MB. Search it with Grep, or Read with offset and limit.' }
    if (ENV_FILE.test(p)) return { deny: '.env files are not read from here.' }
    return next(e)
  }).catch(($, e, next) => (next.called ? next(e) : { deny: 'priveo-reqs: its guard failed.' }))
}
