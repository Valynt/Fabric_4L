<!-- Migrated from services/ADRs/ during legacy path cleanup. -->

# ADR-013: Repository Pattern for Data Access

**Status:** Accepted  
**Date:** April 2026  
**Authors:** Distinguished Engineering Team  
**Reviewers:** Data Architecture Committee

---

## Context

Value Fabric has multiple data storage systems:
- PostgreSQL for transactional data
- Neo4j for graph data
- Redis for caching and sessions
- MinIO for object storage

We need consistent patterns for:
- Data access across different storage systems
- Testability with mock implementations
- Transaction management
- Query optimization
- Multi-tenancy enforcement

We evaluated:
1. **Repository Pattern** (Abstract data access layer)
2. **Active Record** (Model-centric data access)
3. **Data Mapper** (Separate mapping layer)
4. **Direct ORM Usage** (SQLAlchemy/Django ORM directly)

## Decision

We chose **Repository Pattern** with the following structure:

```python
# Abstract repository interface
class Repository[T](ABC):
    """Abstract base for all repositories."""
    
    @abstractmethod
    async def get(self, id: UUID) -> Optional[T]: ...
    
    @abstractmethod
    async def list(
        self,
        filters: Optional[dict] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]: ...
    
    @abstractmethod
    async def create(self, entity: T) -> T: ...
    
    @abstractmethod
    async def update(self, entity: T) -> T: ...
    
    @abstractmethod
    async def delete(self, id: UUID) -> bool: ...

# Concrete implementation
class AccountRepository(Repository[Account]):
    """PostgreSQL implementation with RLS."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
```

## Rationale

### Why Repository Pattern?

1. **Separation of Concerns**: Domain logic independent of storage
   ```python
   # Service layer focuses on business logic
   class AccountService:
       def __init__(self, repository: AccountRepository):
           self._repo = repository
       
       async def create_account(
           self,
           tenant_id: UUID,
           data: AccountCreate,
       ) -> Account:
           # Business logic here
           account = Account(...)
           return await self._repo.create(account)
   ```

2. **Testability**: Easy to mock for unit tests
   ```python
   class InMemoryAccountRepository(AccountRepository):
       """Test double with no database."""
       
       def __init__(self):
           self._accounts: dict[UUID, Account] = {}
       
       async def get(self, id: UUID) -> Optional[Account]:
           return self._accounts.get(id)
   
   # Unit test
   async def test_create_account():
       repo = InMemoryAccountRepository()
       service = AccountService(repo)
       account = await service.create_account(...)
       assert await repo.get(account.id) is not None
   ```

3. **Storage Flexibility**: Swap implementations without changing service code
   ```python
   # PostgreSQL for production
   account_repo = PostgreSQLAccountRepository(db_session)
   
   # In-memory for testing
   account_repo = InMemoryAccountRepository()
   
   # Same service code works with both
   service = AccountService(account_repo)
   ```

4. **Query Optimization**: Centralized in repository layer
   ```python
   class AccountRepository:
       async def get_with_relations(
           self,
           account_id: UUID,
       ) -> Optional[AccountWithRelations]:
           # Optimized query with joins
           result = await self._session.execute(
               select(Account)
               .options(
                   joinedload(Account.contacts),
                   joinedload(Account.opportunities),
               )
               .where(Account.id == account_id)
           )
           return result.unique().scalar_one_or_none()
   ```

5. **Multi-Tenancy Enforcement**: Centralized tenant scoping
   ```python
   class TenantScopedRepository[T]:
       """Base class for tenant-scoped repositories."""
       
       async def _apply_tenant_filter(
           self,
           query: Select,
       ) -> Select:
           """Apply mandatory tenant filter."""
           return query.where(
               self._model.tenant_id == self._tenant_id
           )
   ```

### Why Not Active Record?

- Tight coupling between domain model and persistence
- Harder to test (requires database for model operations)
- Limited flexibility for complex queries
- Violates Single Responsibility Principle

### Why Not Data Mapper?

- More complex than needed for our use case
- Additional mapping layer overhead
- SQLAlchemy 2.0 provides sufficient abstraction

### Why Not Direct ORM?

- Query logic scattered across codebase
- Difficult to test without database
- No abstraction for swapping storage
- Inconsistent query patterns

## Trade-offs

### Positive
- Clear separation of concerns
- Easy testing with mocks
- Storage flexibility
- Centralized query optimization
- Consistent multi-tenancy enforcement

### Negative
- Additional abstraction layer
- More boilerplate code
- Potential over-abstraction for simple cases
- Learning curve for new developers

## Mitigations

| Risk | Mitigation |
|------|-----------|
| Over-abstraction | Only use for complex domains, allow direct ORM for simple cases |
| Boilerplate | Code generation for CRUD repositories |
| Learning curve | Documentation, examples, code review guidelines |
| Performance | Repository methods can optimize queries behind interface |

## Implementation

### Repository Hierarchy

```python
# Base repository with common functionality
class BaseRepository[T](ABC):
    """Abstract base with common repository functionality."""
    
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self._session = session
        self._tenant_id = tenant_id
    
    @abstractmethod
    def _get_model_class(self) -> type[T]: ...
    
    async def _apply_tenant_scope(
        self,
        query: Select,
    ) -> Select:
        """Apply mandatory tenant filter."""
        model = self._get_model_class()
        return query.where(model.tenant_id == self._tenant_id)

# Concrete repository
class AccountRepository(BaseRepository[Account]):
    """Account repository with PostgreSQL storage."""
    
    def _get_model_class(self) -> type[Account]:
        return Account
    
    async def get(self, account_id: UUID) -> Optional[Account]:
        """Get account by ID with tenant scoping."""
        query = select(Account).where(Account.id == account_id)
        query = await self._apply_tenant_scope(query)
        
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
    
    async def list(
        self,
        filters: Optional[AccountFilters] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Account]:
        """List accounts with filtering and pagination."""
        query = select(Account)
        query = await self._apply_tenant_scope(query)
        
        if filters:
            if filters.status:
                query = query.where(Account.status == filters.status)
            if filters.search:
                query = query.where(
                    Account.name.ilike(f"%{filters.search}%")
                )
        
        query = query.limit(limit).offset(offset)
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    async def create(self, account: Account) -> Account:
        """Create new account."""
        # Enforce tenant ownership
        account.tenant_id = self._tenant_id
        
        self._session.add(account)
        await self._session.flush()
        await self._session.refresh(account)
        return account
    
    async def update(self, account: Account) -> Account:
        """Update existing account."""
        # Verify ownership
        existing = await self.get(account.id)
        if not existing:
            raise NotFoundError(f"Account {account.id} not found")
        
        # Merge and save
        merged = await self._session.merge(account)
        await self._session.flush()
        return merged
    
    async def delete(self, account_id: UUID) -> bool:
        """Soft delete account."""
        account = await self.get(account_id)
        if not account:
            return False
        
        account.deleted_at = datetime.utcnow()
        account.is_active = False
        await self._session.flush()
        return True
```

### In-Memory Repository for Testing

```python
class InMemoryAccountRepository(AccountRepository):
    """In-memory implementation for unit tests."""
    
    def __init__(self, tenant_id: UUID):
        # Don't call super().__init__ (no session needed)
        self._tenant_id = tenant_id
        self._accounts: dict[UUID, Account] = {}
        self._next_id = 0
    
    async def get(self, account_id: UUID) -> Optional[Account]:
        account = self._accounts.get(account_id)
        if account and account.tenant_id == self._tenant_id:
            return account
        return None
    
    async def list(
        self,
        filters: Optional[AccountFilters] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Account]:
        accounts = [
            a for a in self._accounts.values()
            if a.tenant_id == self._tenant_id
        ]
        
        if filters:
            if filters.status:
                accounts = [a for a in accounts if a.status == filters.status]
        
        return accounts[offset:offset + limit]
    
    async def create(self, account: Account) -> Account:
        account.id = account.id or uuid4()
        account.tenant_id = self._tenant_id
        account.created_at = datetime.utcnow()
        self._accounts[account.id] = account
        return account
    
    async def update(self, account: Account) -> Account:
        if account.id not in self._accounts:
            raise NotFoundError(f"Account {account.id} not found")
        
        existing = self._accounts[account.id]
        if existing.tenant_id != self._tenant_id:
            raise NotFoundError(f"Account {account.id} not found")
        
        account.updated_at = datetime.utcnow()
        self._accounts[account.id] = account
        return account
    
    async def delete(self, account_id: UUID) -> bool:
        account = self._accounts.get(account_id)
        if not account or account.tenant_id != self._tenant_id:
            return False
        
        account.deleted_at = datetime.utcnow()
        account.is_active = False
        return True
    
    # Test helper methods
    def clear(self) -> None:
        """Clear all accounts (for test cleanup)."""
        self._accounts.clear()
    
    def seed(self, accounts: list[Account]) -> None:
        """Seed with test data."""
        for account in accounts:
            self._accounts[account.id] = account
```

### Dependency Injection

```python
# FastAPI dependency
def get_account_repository(
    db: AsyncSession = Depends(get_db_with_tenant),
) -> AccountRepository:
    """Factory for account repository."""
    return AccountRepository(db)

# Service injection
class AccountService:
    def __init__(self, repository: AccountRepository):
        self._repository = repository

# Route usage
@router.get("/api/v1/accounts/{account_id}")
async def get_account(
    account_id: UUID,
    repo: AccountRepository = Depends(get_account_repository),
) -> AccountResponse:
    """Get account by ID."""
    account = await repo.get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return AccountResponse.from_model(account)
```

## Consequences

### Accepted
- Additional abstraction layer overhead
- More initial boilerplate
- Learning curve for new team members

### Mitigated
- Boilerplate via code generation and base classes
- Learning via documentation and examples
- Overhead minimal compared to benefits

## Related Decisions

- ADR-003: PostgreSQL + RLS for multi-tenancy
- ADR-008: Repository pattern complements RLS enforcement

---

**Last Updated:** April 21, 2026
