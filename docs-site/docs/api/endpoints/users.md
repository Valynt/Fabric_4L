---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Users API

Manage user profiles and organization membership.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/users` | List users |
| GET | `/v1/users/{id}` | Get a user |
| PUT | `/v1/users/{id}` | Update a user |
| POST | `/v1/users/{id}/deactivate` | Deactivate a user |
| GET | `/v1/users/me` | Get current user |

## List users

```http
GET /v1/users?role=admin&status=active
```

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `role` | string | Filter by role |
| `status` | string | `active`, `inactive`, `pending` |
| `group` | string | Filter by group membership |

## Deactivate a user

```http
POST /v1/users/usr_abc123/deactivate
Content-Type: application/json

{
  "reason": "Offboarding",
  "transfer_ownership_to": "usr_def456"
}
```

!!! warning "Data ownership transfer"
    When deactivating, specify a user to transfer initiative ownership to. Without this, initiatives remain owned by the deactivated user.

## Permissions

| Action | Required Permission |
|--------|---------------------|
| List | `admin:users` |
| Get | `admin:users` or self |
| Update | `admin:users` or self |
| Deactivate | `admin:users` |

## Limits

<span class="vp-badge vp-badge--limit">Limit</span> Maximum users per tenant varies by plan (Starter: 25, Professional: 100, Enterprise: 500, Enterprise Plus: custom).

## Related pages

- [API Overview](../overview.md)
- [Administration → User Management](../../administration/user-management/index.md)
