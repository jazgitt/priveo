import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { AutomaticPlanningSettings } from './AutomaticPlanningSettings';

afterEach(() => vi.unstubAllGlobals());

it('starts disabled, requires a time to enable and saves the IST setting', async () => {
  let saved: unknown;
  vi.stubGlobal('fetch', vi.fn(async (_path: string, options?: RequestInit) => {
    if (options?.method === 'PUT') saved = JSON.parse(options.body as string);
    return new Response(JSON.stringify(saved ?? { enabled: false, time_ist: '' }), { status: 200 });
  }));
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={qc}><AutomaticPlanningSettings /></QueryClientProvider>);
  const toggle = await screen.findByRole('switch');
  expect(toggle).not.toBeChecked();
  fireEvent.click(toggle);
  expect(screen.getByText('Save automatic planning')).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Planning time (IST)'), { target: { value: '18:05' } });
  fireEvent.click(screen.getByText('Save automatic planning'));
  await screen.findByText('Automatic planning settings saved.');
  expect(saved).toEqual({ enabled: true, time_ist: '18:05' });
  qc.clear();
});
