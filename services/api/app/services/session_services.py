from __future__ import annotations

from dataclasses import dataclass

from app.repositories.session_store import ImpersonationSessionRepository, ShareLinkRepository


@dataclass
class ShareLinkService:
    repo: ShareLinkRepository


@dataclass
class ImpersonationSessionService:
    repo: ImpersonationSessionRepository
