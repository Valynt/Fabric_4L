import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { WorkspaceLayoutWrapper } from './GlobalLayout';

function TestChild() {
  return <div data-testid="child">content</div>;
}

function renderAtRoute(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route
          path="*"
          element={
            <WorkspaceLayoutWrapper>
              <TestChild />
            </WorkspaceLayoutWrapper>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

describe('WorkspaceLayoutWrapper', () => {
  it('renders without crashing on a regular route', () => {
    renderAtRoute('/home');
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('renders without crashing on an intelligence workspace route', () => {
    renderAtRoute('/t/acme/accounts/acc-123/intelligence/signals');
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('renders without crashing on a studio workspace route', () => {
    renderAtRoute('/t/acme/accounts/acc-123/studio/action-plan');
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('renders without crashing on a deliverables workspace route', () => {
    renderAtRoute('/t/acme/accounts/acc-123/deliverables/business-cases');
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('renders without crashing on an accounts route', () => {
    renderAtRoute('/t/acme/accounts');
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('renders without crashing on a settings route', () => {
    renderAtRoute('/settings/team');
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('maintains stable hook count when route changes between workspace and non-workspace', () => {
    // This test specifically guards against React "Rendered more hooks than during
    // the previous render" errors caused by calling useMatch() conditionally.
    // Re-rendering at a different route must not change the number of hooks called.
    const { rerender } = render(
      <MemoryRouter initialEntries={['/t/acme/accounts/acc-123/intelligence/signals']}>
        <Routes>
          <Route
            path="*"
            element={
              <WorkspaceLayoutWrapper>
                <TestChild />
              </WorkspaceLayoutWrapper>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByTestId('child')).toBeInTheDocument();

    // Change to a non-workspace route — if useMatch was called inside a short-circuit
    // expression, this would throw a hooks-order error.
    rerender(
      <MemoryRouter initialEntries={['/home']}>
        <Routes>
          <Route
            path="*"
            element={
              <WorkspaceLayoutWrapper>
                <TestChild />
              </WorkspaceLayoutWrapper>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByTestId('child')).toBeInTheDocument();
  });
});
