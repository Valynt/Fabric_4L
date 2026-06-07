---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Release Notes Framework

How ValuePact versions, communicates, and documents releases.

## Versioning

ValuePact follows [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH
```

| Component | When it increments | Example |
|-----------|-------------------|---------|
| MAJOR | Breaking changes | 1.0.0 → 2.0.0 |
| MINOR | New features, backward compatible | 1.1.0 → 1.2.0 |
| PATCH | Bug fixes, backward compatible | 1.2.0 → 1.2.1 |

## Release types

### Major releases

- Quarterly cadence
- 30-day advance notice
- May include breaking API changes
- Requires migration planning for admins

### Minor releases

- Bi-weekly cadence
- New features and enhancements
- Backward compatible
- Announced via in-app notification

### Patch releases

- As needed
- Bug fixes and security patches
- No advance notice
- Deployed automatically

### Hotfix releases

- Emergency fixes
- Bypass normal release process
- Deployed immediately
- Documented retroactively

## Communication channels

| Audience | Channel | Timing |
|----------|---------|--------|
| All users | In-app notification | Release day |
| Admins | Email + in-app | 7 days before major |
| Developers | API changelog + email | 30 days before breaking API changes |
| Enterprise | Account manager call | 14 days before major |

## Related pages

- [Release Notes Overview](index.md)
- [Templates](templates/index.md)
