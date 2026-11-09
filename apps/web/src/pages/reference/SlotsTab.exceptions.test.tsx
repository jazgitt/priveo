import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ToastProvider } from '../../components';
import { withSite } from '../../site/testSite';
import { choose, confirmWith, PortalProviders } from '../../test/portal';
import { SlotsTab } from './SlotsTab';

// ADM-SVS-12: the exception form and list of the Slots tab.
const fetchMock = vi.fn();
let responses: Record<string, unknown>;
let clients: QueryClient[];
const EXCEPTIONS = '/v1/admin/directory/societies/s1/slot-exceptions';

function mount(ui: React.ReactElement, site = 's1') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  clients.push(client);
  render(<QueryClientProvider client={client}><MemoryRouter><ToastProvider><PortalProviders>{withSite(ui, site, site ? 'Lake' : '')}</PortalProviders></ToastProvider></MemoryRouter></QueryClientProvider>);
}
const calls = (path: string, method: string) =>
  fetchMock.mock.calls.filter(([url, init]) => String(url) === '/v1/admin/directory' + path && (init?.method ?? 'GET') === method);
async function saved(path: string, method = 'POST') {
  await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Save' }));
  await waitFor(() => expect(calls(path, method)).toHaveLength(1));
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  return JSON.parse(calls(path, method)[0][1].body);
}
const exception = (over: Record<string, unknown> = {}) => ({
  id: 'e1', society_id: 's1', service: 'Cleaning-External', start_date: '2026-11-11', end_date: '2026-11-17',
  days: ['Wednesday'], windows: [{ start: '06:00', end: '12:00' }], note: '', ...over,
});

beforeEach(() => {
  clients = []; responses = {}; fetchMock.mockReset();
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) =>
    new Response(JSON.stringify(responses[url] ?? ((init?.method ?? 'GET') === 'GET' ? [] : {})), { status: 200 }));
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => { clients.forEach((c) => c.clear()); vi.unstubAllGlobals(); });

it('adds an exception for a date range, its weekdays and its working times', async () => {
  responses[EXCEPTIONS] = [];
  mount(<SlotsTab />);
  await userEvent.click(await screen.findByRole('button', { name: 'Add an exception' }));
  const dialog = await screen.findByRole('dialog');
  expect(within(dialog).getByRole('button', { name: 'Save' })).toBeDisabled();
  await choose('Service', 'Cleaning-External');
  fireEvent.change(within(dialog).getByLabelText('Start date'), { target: { value: '2026-11-11' } });
  fireEvent.change(within(dialog).getByLabelText('End date'), { target: { value: '2026-11-17' } });
  // Dates alone are not enough: a day must be chosen.
  expect(within(dialog).getByRole('button', { name: 'Save' })).toBeDisabled();
  await userEvent.click(within(dialog).getByLabelText('Wednesday'));
  expect(within(dialog).getByRole('button', { name: 'Save' })).toBeEnabled();
  expect(await saved('/societies/s1/slot-exceptions')).toEqual({
    service: 'Cleaning-External', start_date: '2026-11-11', end_date: '2026-11-17',
    days: ['Wednesday'], windows: [{ start: '05:00', end: '11:00' }], note: '',
  });
});

it('sends no working times when every window is removed: the service is closed on those days', async () => {
  responses[EXCEPTIONS] = [];
  mount(<SlotsTab />);
  await userEvent.click(await screen.findByRole('button', { name: 'Add an exception' }));
  const dialog = within(await screen.findByRole('dialog'));
  await choose('Service', 'Deep Spa');
  fireEvent.change(dialog.getByLabelText('Start date'), { target: { value: '2026-11-15' } });
  fireEvent.change(dialog.getByLabelText('End date'), { target: { value: '2026-11-15' } });
  await userEvent.click(dialog.getByLabelText('Sunday'));
  await userEvent.click(dialog.getByRole('button', { name: 'Remove window 1' }));
  expect(dialog.getByText('No window: the service is closed on these days.')).toBeInTheDocument();
  expect(await saved('/societies/s1/slot-exceptions')).toMatchObject({ service: 'Deep Spa', days: ['Sunday'], windows: [] });
});

it('lists each exception with its dates, weekdays and working times, and shows a closed day', async () => {
  responses[EXCEPTIONS] = [exception(), exception({ id: 'e2', service: 'Deep Spa', windows: [], days: ['Sunday'], start_date: '2026-11-18', end_date: '2026-11-22' })];
  mount(<SlotsTab />);
  expect(await screen.findByText('11-Nov-26 to 17-Nov-26')).toBeInTheDocument();
  expect(screen.getByText('18-Nov-26 to 22-Nov-26')).toBeInTheDocument();
  expect(screen.getByText('06:00 to 12:00')).toBeInTheDocument();
  expect(screen.getByText('Closed')).toBeInTheDocument();
  expect(screen.getByText('Sun')).toBeInTheDocument();
});

it('edits an exception and sends its changed note with the other fields', async () => {
  responses[EXCEPTIONS] = [exception()];
  mount(<SlotsTab />);
  await userEvent.click(await screen.findByRole('button', { name: 'Edit' }));
  expect(await screen.findByRole('dialog')).toHaveTextContent('Edit exception');
  await userEvent.type(within(screen.getByRole('dialog')).getByLabelText('Note (optional)'), 'Festival week');
  expect(await saved('/slot-exceptions/e1', 'PATCH')).toMatchObject({
    note: 'Festival week', days: ['Wednesday'], windows: [{ start: '06:00', end: '12:00' }],
  });
});

it('deletes an exception only after the confirmation', async () => {
  responses[EXCEPTIONS] = [exception()];
  mount(<SlotsTab />);
  await userEvent.click(await screen.findByRole('button', { name: 'Delete' }));
  expect(calls('/slot-exceptions/e1', 'DELETE')).toHaveLength(0);
  await confirmWith('Delete');
  await waitFor(() => expect(calls('/slot-exceptions/e1', 'DELETE')).toHaveLength(1));
});
