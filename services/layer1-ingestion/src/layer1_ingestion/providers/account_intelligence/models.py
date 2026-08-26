from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class TenantContext(BaseModel):
    tenant_id: UUID
    account_id: UUID | None = None
    correlation_id: str

class IdempotencyKey(BaseModel):
    key: str
    expires_at: datetime

# Minimal Cargo-specific types — stay inside cargo/ after this
class CargoMcpRequest(BaseModel):
    action: str
    params: dict[str, Any]
    tenant_id: UUID
