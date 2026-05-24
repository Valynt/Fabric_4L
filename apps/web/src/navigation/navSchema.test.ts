import { describe, expect, it } from 'vitest';
import { resolveBreadcrumbs } from './navSchema';

describe('resolveBreadcrumbs', () => {
  it('resolves intelligence workspace breadcrumbs with canonical paths', () => {
    expect(
      resolveBreadcrumbs('/t/acme/accounts/acct-123/intelligence/signals').map((c) => c.label)
    ).toEqual(['Accounts', 'Intelligence', 'Signals']);
  });

  it('resolves studio workspace breadcrumbs with canonical paths', () => {
    expect(
      resolveBreadcrumbs('/t/acme/accounts/acct-123/studio/action-plan').map((c) => c.label)
    ).toEqual(['Accounts', 'Value Studio', 'Action Plan']);
  });

  it('resolves deliverables workspace breadcrumbs with canonical paths', () => {
    expect(
      resolveBreadcrumbs('/t/acme/accounts/acct-123/deliverables/business-cases').map((c) => c.label)
    ).toEqual(['Accounts', 'Deliverables', 'Business Cases']);
  });

  it('hides opaque ids by design', () => {
    expect(
      resolveBreadcrumbs('/t/acme/accounts/12345678-abcd-1234-abcd-1234567890ab').map((c) => c.label)
    ).toEqual(['Accounts']);
  });

  it('handles accounts list route', () => {
    expect(resolveBreadcrumbs('/t/acme/accounts').map((c) => c.label)).toEqual(['Accounts']);
  });

  it('handles home route', () => {
    expect(resolveBreadcrumbs('/home').map((c) => c.label)).toEqual(['Home']);
  });

  it('handles settings route', () => {
    expect(resolveBreadcrumbs('/settings/team').map((c) => c.label)).toEqual(['Settings', 'Team']);
  });

  it('handles governance route', () => {
    expect(resolveBreadcrumbs('/t/acme/governance/audit').map((c) => c.label)).toEqual([
      'Governance',
      'Audit',
    ]);
  });
});
