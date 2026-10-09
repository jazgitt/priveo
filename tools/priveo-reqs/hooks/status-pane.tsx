import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

export const PANE = { id: 'priveo-status', title: 'Priveo status' }
const tick = atom({ plugin: 'priveo-reqs', key: 'tick' } as const, 0)

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
    const summary = `${Object.keys(store.features).length} requirements: ${lines.join(', ')}. Open bugs ${t.bugs}.`
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
    return (
      <Box flexDirection="column">
        <Text bold>{t.total} requirements</Text>
        {stages.map(([key, label]) => (
          <Text dimColor={t.by[key] === 0}>
            {label.padEnd(18)} {t.by[key]}
          </Text>
        ))}
        <Text color={t.bugs ? 'red' : undefined}>{'Open bugs'.padEnd(18)} {t.bugs}</Text>
      </Box>
    )
  })
}
