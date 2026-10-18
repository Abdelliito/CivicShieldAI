import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './auth';
import { session } from './api';

function Probe() {
  const { user, loading } = useAuth();
  return <p>{loading ? 'Restoring account' : user ? `Signed in as ${user.name}` : 'Sign in required'}</p>;
}
function show() {
  return render(<QueryClientProvider client={new QueryClient()}><AuthProvider><Probe /></AuthProvider></QueryClientProvider>);
}
beforeEach(() => session.set('saved-valid-session'));
afterEach(() => { session.clear(); vi.unstubAllGlobals(); });

it('preserves a saved session through a transport failure and restores it on retry', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Navigation interrupted the request')));
  const first = show();
  await screen.findByText('Sign in required');
  expect(session.get()).toBe('saved-valid-session');
  first.unmount();
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 1, name: 'Ayesha', role: 'citizen' }), { status: 200 })));
  show();
  expect(await screen.findByText('Signed in as Ayesha')).toBeVisible();
});

it('still clears an expired session when the server explicitly returns 401', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Session expired' }), { status: 401 })));
  show();
  expect(await screen.findByText('Sign in required')).toBeVisible();
  expect(session.get()).toBeNull();
});
