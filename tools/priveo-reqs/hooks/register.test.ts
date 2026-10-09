import { test, expect } from 'claude-code/testing'
import { breakdown, roleLine } from './status-pane'
import { parse, integrity, reconcile, tally, featureLine, serialize } from './register'

const doc = (rows: string[]) => parse('docs/reqs/admin-functional-requirements.md', rows.join('\n'))

test('first run approves every ID, later changes and new IDs go to Draft', () => {
  const first = reconcile(undefined, [doc(['| ADM-ACC-01 | one | Owner |', '| ADM-ACC-02 | two | Owner |'])])
  expect(tally(first.store).by.backlog).toBe(2)
  first.store.features['ADM-ACC-01'].stage = 'dev'
  const next = reconcile(first.store, [
    doc(['| ADM-ACC-01 | one, edited | Owner |', '| ADM-ACC-02 | two | Owner |', '| ADM-ACC-03 | three | Derived |']),
  ])
  expect(next.toDraft).toEqual(['ADM-ACC-01'])
  expect(next.added).toEqual(['ADM-ACC-03'])
  expect(next.store.features['ADM-ACC-02'].stage).toBe('backlog')
  expect(featureLine(next.store)).toBe('Draft 2 · Backlog 1 · Bugs 0')
})

test('spacing changes do not move a feature to Draft', () => {
  const first = reconcile(undefined, [doc(['| ADM-ACC-01 | one two | Owner |'])])
  const next = reconcile(first.store, [doc(['|  ADM-ACC-01  |  one   two  |  Owner  |'])])
  expect(next.toDraft).toEqual([])
  expect(serialize(next.store)).toBe(serialize(first.store))
})

test('integrity finds duplicates and undefined citations', () => {
  const a = parse(
    'docs/reqs/admin-functional-requirements.md',
    '| ADM-ACC-01 | x, see AUTH-01 and AUTH-99 | Owner |\n| ADM-ACC-01 | y | Owner |',
  )
  const b = parse('docs/reqs/customer-app-functional-requirements.md', '| AUTH-01 | z | Owner |')
  const r = integrity([a, b])
  expect(r.dupes.map(d => d[0])).toEqual(['ADM-ACC-01'])
  expect(r.missing).toEqual(['AUTH-99 (admin:1)'])
})

test('breakdown names the areas and groups them by role', () => {
  const areas = breakdown({ 'AUTH-01': { bugs: 0 }, 'AUTH-02': { bugs: 1 }, 'ADM-PAY-01': {}, 'CRW-SCH-01': {}, 'ZZZ-01': {} })
  expect(areas.map(a => a.role)).toEqual(['Customer', 'Customer', 'Crew', 'Admin'])
  expect(areas[0]).toMatchObject({ area: 'AUTH', name: 'Sign-in and authentication', total: 2, bugs: 1 })
  expect(areas.find(a => a.area === 'ADM-PAY')!.name).toBe('Payments')
  expect(roleLine(areas)).toBe('Customer 3, Crew 1, Admin 1')
})
