---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Roles API

Query and manage roles and permission assignments.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/roles` | List roles |
| GET | `/v1/roles/{id}` | Get a role |
| GET | `/v1/roles/{id}/permissions` | Get role permissions |
| POST | `/v1/roles/{id}/assign` | Assign role to user |
| DELETE | `/v1/roles/{id}/assign` | Remove role from user |

## List roles

```http
GET /v1/roles
```

Response includes system roles and custom roles:

```json
{
  "data": [
    {
      "id": "role_viewer",
      "name": "Viewer",
      "type": "system",
      "permissions": ["initiatives:read", "business_cases:read"]
    },
    {
      "id": "role_custom_1",
      "name": "Analyst",
      "type": "custom",
      "permissions": ["initiatives:read", "analytics:read", "benefits:write"]
    }
  ]
}
```

## Assign role to user

```http
POST /v1/roles/role_admin/assign
Content-Type: application/json

{
  "user_id": "usr_abc123"
}
```

## Permissions

| Action | Required Permission |
|--------|---------------------|
| List | `admin:roles` |
| Get | `admin:roles` |
| Assign | `admin:roles` |

## Related pages

- [API Overview](../overview.md)
- [Administration → Role Management](../../administration/role-management/index.md)
