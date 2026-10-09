import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

export const PANE = { id: 'priveo-status', title: 'Priveo status' }
const tick = atom({ plugin: 'priveo-reqs', key: 'tick' } as const, 0)

// Area names are labels taken from the section titles of the requirements files.
const AREA_NAMES: Record<string, string> = {
  AUTH: 'Sign-in and authentication', ONB: 'Onboarding details', PAY: 'Subscription purchase and payment', HOME: 'Home',
  CAL: 'Service calendar', SVC: 'Service details and proof', HIST: 'Service history', SKIP: 'Skip a date',
  PAUSE: 'Pause service', SCHED: 'Schedule change cutoff', ACC: 'Account', SET: 'Settings', NOTIF: 'Notifications',
  SUB: 'My subscription', VEH: 'My vehicles', ADD: 'Add-ons (Deep Spa)', SUP: 'Help and support',
  ISS: 'Report an issue', CMP: 'My complaints', FDBK: 'Feedback', CHK: 'Monthly check-in', NAV: 'Navigation',
  'ADM-ACC': 'Access and roles', 'ADM-CUS': 'Customer onboarding', 'ADM-SUB': 'Subscription start and status',
  'ADM-CRW': 'Crew onboarding', 'ADM-SVS': 'Services and working slots', 'ADM-CAP': 'Capacity', 'ADM-PAY': 'Payments',
  'ADM-SCH': 'Run the scheduler', 'ADM-PRF': 'Scheduler preferences', 'ADM-CMP': 'Complaints',
  'ADM-OPS': 'Visits skipped by operations', 'ADM-CNC': 'Visits crew could not complete',
  'ADM-FDB': 'Feedback, ratings and check-ins', 'ADM-REF': 'Reference data', 'ADM-SET': 'Settings',
  'ADM-CHK': 'Service checklists and proof minimums', 'ADM-ADD': 'Add-ons',
  'CRW-ACC': 'Access and login', 'CRW-PRF': 'Profile', 'CRW-SCH': 'My schedule', 'CRW-MGR': 'Manager features',
  'CRW-SVC': 'Performing a service', 'CRW-CNC': 'Could not complete', 'CRW-RAT': 'Ratings received', 'CRW-NOT': 'Notifications',
}
const ROLES = ['Customer', 'Crew', 'Admin']
const roleOf = (area: string) => (area.startsWith('ADM-') ? 'Admin' : area.startsWith('CRW-') ? 'Crew' : 'Customer')

type Area = { role: string; area: string; name: string; total: number; bugs: number }
export const breakdown = (features: Record<string, { bugs?: number }>): Area[] => {
  const by: Record<string, Area> = {}
  for (const [id, f] of Object.entries(features)) {
    const area = id.replace(/-\d+$/, '')
    const a = (by[area] ??= { role: roleOf(area), area, name: AREA_NAMES[area] ?? area, total: 0, bugs: 0 })
    a.total++
    a.bugs += f.bugs ?? 0
  }
  return Object.values(by).sort(
    (x, y) => ROLES.indexOf(x.role) - ROLES.indexOf(y.role) || y.total - x.total || x.name.localeCompare(y.name),
  )
}
export const roleLine = (areas: Area[]) =>
  ROLES.map(r => `${r} ${areas.filter(a => a.role === r).reduce((n, a) => n + a.total, 0)}`).join(', ')

type Tally = { by: Record<string, number>; bugs: number }
type Deps = {
  stages: readonly (readonly [string, string, string])[]
  tally: (store: { features: Record<string, unknown> }) => Tally
}

// Side pane (register.ts registers the command and opens it at session.start) for the feature lifecycle. Called from register.ts so the plugin keeps one hooks module.
export const registerPane = (on: Parameters<Register>[0], { stages, tally }: Deps) => {
  on('command.run', { command: 'priveo-status' }, async $ => {
    const opened = await $.ui.open(PANE)
    const store = JSON.parse(await $.fs.read('docs/feature-status.json'))
    const t = tally(store)
    const lines = stages.filter(s => t.by[s[0]] > 0).map(s => `${s[1]} ${t.by[s[0]]}`)
    const summary = `${Object.keys(store.features).length} requirements: ${lines.join(', ')}. Open bugs ${t.bugs}. By role: ${roleLine(breakdown(store.features))}.`
    return { text: opened.isPlaced ? `Priveo status pane opened. ${summary}` : `This screen shows no side panes. ${summary}` }
  }).catch(() => ({ text: '/priveo-status failed.' }))

  // Redraw after each tool call, since edits may change the status file.
  on('tool.call', async ($, e, next) => {
    const ran = await next(e)
    await update($, tick, n => n + 1)
    return ran
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'Pane', requestId: 'priveo-status' }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    await read($, tick)
    let store
    try {
      store = JSON.parse(await $.fs.read('docs/feature-status.json'))
    } catch {
      return <Text dimColor>docs/feature-status.json not found.</Text>
    }
    const t = { ...tally(store), total: Object.keys(store.features).length }
    const areas = breakdown(store.features)
    const room = Math.max(3, Math.floor(((e.viewport?.rows ?? 40) - stages.length - 12) / 3))
    return (
      <Box flexDirection="column">
        <Text bold>{t.total} requirements</Text>
        {stages.map(([key, label]) => (
          <Text dimColor={t.by[key] === 0}>
            {label.padEnd(18)} {t.by[key]}
          </Text>
        ))}
        <Text color={t.bugs ? 'red' : undefined}>{'Open bugs'.padEnd(18)} {t.bugs}</Text>
        {ROLES.map(role => {
          const mine = areas.filter(a => a.role === role)
          const ids = mine.reduce((n, a) => n + a.total, 0)
          const bugs = mine.reduce((n, a) => n + a.bugs, 0)
          return (
            <Box flexDirection="column" marginTop={1}>
              <Text bold>
                {role} · {ids} IDs · {mine.length} areas{bugs ? ` · ${bugs} bugs` : ''}
              </Text>
              {mine.slice(0, room).map(a => (
                <Text color={a.bugs ? 'red' : undefined}>
                  {String(a.total).padStart(3)}  {a.name} <Text dimColor>{a.area}</Text>
                </Text>
              ))}
            </Box>
          )
        })}
      </Box>
    )
  })
}
