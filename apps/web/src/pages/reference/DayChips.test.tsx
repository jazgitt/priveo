import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { DayChips } from './DayChips';

// Item 14: working days are green, the others grey, and a screen reader hears which is which.
it('marks each working weekday green and every other weekday grey', () => {
  const { container } = render(<DayChips days={['Monday', 'Wednesday']} />);
  const chips = [...container.querySelectorAll('[data-day]')];
  expect(chips.map((c) => c.getAttribute('data-day'))).toEqual(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']);
  expect(chips.map((c) => c.getAttribute('data-working'))).toEqual(['true', 'false', 'true', 'false', 'false', 'false', 'false']);
  expect(chips[0].className).toContain('bg-green-100');
  expect(chips[1].className).not.toContain('bg-green-100');
  expect(chips[1].className).toContain('bg-muted');
});

it('says working or not working for every day to a screen reader', () => {
  render(<DayChips days={['Sunday']} />);
  expect(screen.getByText('Sun, working')).toBeInTheDocument();
  expect(screen.getByText('Mon, not working')).toBeInTheDocument();
});

it('shows every day grey when there are no working days', () => {
  const { container } = render(<DayChips days={[]} />);
  expect(container.querySelectorAll('[data-working="true"]')).toHaveLength(0);
  expect(container.querySelectorAll('[data-working="false"]')).toHaveLength(7);
});
