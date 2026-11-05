import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { AutomaticPlanningSettings } from './AutomaticPlanningSettings';

afterEach(() => vi.unstubAllGlobals());

it('has no on/off switch, links to Scheduled jobs and saves the IST time', async () => {
  let saved: unknown;
  vi.stubGlobal('fetch', vi.fn(async (_path: string, options?: RequestInit) => {
    if (options?.method === 'PUT') saved = JSON.parse(options.body as string);
    return new Response(JSON.stringify(saved ?? { time_ist: '' }), { status: 200 });
  }));
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<MemoryRouter><QueryClientProvider client={qc}><AutomaticPlanningSettings /></QueryClientProvider></MemoryRouter>);
  const input = await screen.findByLabelText('Planning time (IST)');
  expect(screen.queryByRole('switch')).toBeNull();
  expect(screen.getByRole('link', { name: 'Scheduled jobs' })).toHaveAttribute('href', '/scheduled-jobs');
  fireEvent.change(input, { target: { value: '18:05' } });
  fireEvent.click(screen.getByText('Save automatic planning'));
  await screen.findByText('Automatic planning settings saved.');
  expect(saved).toEqual({ time_ist: '18:05' });
  qc.clear();
});
