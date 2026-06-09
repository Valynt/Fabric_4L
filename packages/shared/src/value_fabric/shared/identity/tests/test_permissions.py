"""Tests for Role/Permission definitions (shared/identity/permissions.py)."""


from ..permissions import (
    ROLE_RANK,
    Permission,
    Role,
    ROLE_PERMISSIONS,
    can_grant_role,
    get_role_permissions,
    get_role_rank,
    role_has_permission,
)


class TestPermissionEnum:
    """Tests for the Permission enum."""

    def test_all_permissions_are_strings(self):
        """Every Permission value is a colon-namespaced string."""
        for p in Permission:
            assert ":" in p.value, f"{p.name} missing colon namespace"

    def test_unique_values(self):
        """All permission values are unique."""
        values = [p.value for p in Permission]
        assert len(values) == len(set(values))

    def test_read_permissions_exist(self):
        """Expected read permissions are present."""
        reads = [p for p in Permission if p.value.startswith("read:")]
        assert len(reads) >= 8  # At least 8 read perms


class TestRoleEnum:
    """Tests for the Role enum."""

    def test_expected_roles(self):
        role_names = {r.value for r in Role}
        assert "super_admin" in role_names
        assert "tenant_admin" in role_names
        assert "content_admin" in role_names
        assert "analyst" in role_names
        assert "read_only" in role_names
        assert "system" in role_names


class TestRolePermissionsMapping:
    """Tests for the ROLE_PERMISSIONS mapping."""

    def test_all_roles_mapped(self):
        """Every Role has an entry in ROLE_PERMISSIONS."""
        for role in Role:
            assert role in ROLE_PERMISSIONS, f"{role} not in ROLE_PERMISSIONS"

    def test_permissions_are_frozenset(self):
        """All permission sets are immutable frozensets."""
        for role, rp in ROLE_PERMISSIONS.items():
            assert isinstance(rp.permissions, frozenset), f"{role} perms not frozenset"

    def test_read_only_has_limited_permissions(self):
        """READ_ONLY has read-only access only."""
        perms = ROLE_PERMISSIONS[Role.READ_ONLY].permissions
        for p in perms:
            assert p.value.startswith("read:"), f"READ_ONLY has non-read perm: {p}"

    def test_role_hierarchy_subset(self):
        """Lower roles are subsets of higher roles in the hierarchy."""
        hierarchy = [
            Role.READ_ONLY,
            Role.ANALYST,
            Role.CONTENT_ADMIN,
            Role.TENANT_ADMIN,
            Role.SUPER_ADMIN,
        ]
        for i in range(len(hierarchy) - 1):
            lower = ROLE_PERMISSIONS[hierarchy[i]].permissions
            higher = ROLE_PERMISSIONS[hierarchy[i + 1]].permissions
            assert lower.issubset(higher), (
                f"{hierarchy[i].value} permissions not subset of "
                f"{hierarchy[i+1].value}: {lower - higher}"
            )

    def test_super_admin_has_all_permissions(self):
        """SUPER_ADMIN has every Permission."""
        all_perms = frozenset(Permission)
        super_perms = ROLE_PERMISSIONS[Role.SUPER_ADMIN].permissions
        assert all_perms == super_perms

    def test_system_has_all_permissions(self):
        """SYSTEM has every Permission (same as super_admin)."""
        all_perms = frozenset(Permission)
        system_perms = ROLE_PERMISSIONS[Role.SYSTEM].permissions
        assert all_perms == system_perms


class TestGetRolePermissions:
    """Tests for get_role_permissions()."""

    def test_returns_frozenset(self):
        result = get_role_permissions(Role.ANALYST)
        assert isinstance(result, frozenset)

    def test_matches_mapping(self):
        for role in Role:
            assert get_role_permissions(role) == ROLE_PERMISSIONS[role].permissions


class TestRoleHasPermission:
    """Tests for role_has_permission()."""

    def test_positive(self):
        assert role_has_permission(Role.ANALYST, Permission.READ_SEARCH) is True

    def test_negative(self):
        assert role_has_permission(Role.READ_ONLY, Permission.WRITE_INGESTION) is False

    def test_super_admin_has_everything(self):
        for p in Permission:
            assert role_has_permission(Role.SUPER_ADMIN, p) is True


class TestRoleRank:
    """Tests for ROLE_RANK and get_role_rank()."""

    def test_role_rank_values(self):
        """Rank hierarchy must be strictly decreasing."""
        assert ROLE_RANK[Role.SUPER_ADMIN.value] == 100
        assert ROLE_RANK[Role.TENANT_ADMIN.value] == 80
        assert ROLE_RANK[Role.CONTENT_ADMIN.value] == 60
        assert ROLE_RANK[Role.ANALYST.value] == 40
        assert ROLE_RANK[Role.READ_ONLY.value] == 20

    def test_get_role_rank_with_enum(self):
        assert get_role_rank(Role.TENANT_ADMIN) == 80

    def test_get_role_rank_with_string(self):
        assert get_role_rank("analyst") == 40

    def test_get_role_rank_unknown_returns_zero(self):
        assert get_role_rank("unknown_role") == 0


class TestCanGrantRole:
    """Tests for can_grant_role() (F-11 escalation guard)."""

    def test_higher_can_grant_lower(self):
        assert can_grant_role(Role.TENANT_ADMIN, Role.ANALYST) is True
        assert can_grant_role(Role.TENANT_ADMIN, Role.CONTENT_ADMIN) is True
        assert can_grant_role(Role.SUPER_ADMIN, Role.TENANT_ADMIN) is True
        assert can_grant_role(Role.ANALYST, Role.READ_ONLY) is True

    def test_equal_rank_blocked(self):
        assert can_grant_role(Role.TENANT_ADMIN, Role.TENANT_ADMIN) is False
        assert can_grant_role(Role.ANALYST, Role.ANALYST) is False

    def test_lower_cannot_grant_higher(self):
        assert can_grant_role(Role.ANALYST, Role.TENANT_ADMIN) is False
        assert can_grant_role(Role.READ_ONLY, Role.ANALYST) is False

    def test_unknown_inviter_blocked(self):
        assert can_grant_role("unknown", Role.ANALYST) is False

    def test_unknown_invitee_blocked(self):
        assert can_grant_role(Role.TENANT_ADMIN, "unknown") is False
