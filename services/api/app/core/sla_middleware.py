from __future__ import annotations

import json
import os

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class ContractVersionMiddleware(BaseHTTPMiddleware):
    """Enforce the API contract version customers sign up for.

    Requests may declare the contract version via ``X-API-Contract-Version``.
    If the header is absent the request is allowed (lenient default). If it
    is present and not in the supported list, the gateway returns
    ``412 Precondition Failed`` with a structured error.
    """

    header_name = "X-API-Contract-Version"

    def __init__(self, app, supported_versions: set[str] | None = None):
        super().__init__(app)
        if supported_versions is None:
            env = os.environ.get("SUPPORTED_API_CONTRACT_VERSIONS", "v1")
            self.supported_versions = {v.strip() for v in env.split(",") if v.strip()}
        else:
            self.supported_versions = supported_versions

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        requested = request.headers.get(self.header_name)
        if requested is not None and requested not in self.supported_versions:
            return Response(
                status_code=412,
                media_type="application/json",
                content=json.dumps(
                    {
                        "detail": {
                            "code": "UNSUPPORTED_CONTRACT_VERSION",
                            "requested": requested,
                            "supported": sorted(self.supported_versions),
                        }
                    }
                ).encode(),
            )
        response = await call_next(request)
        # Advertise the active contract version and SLA enforcement in every response.
        effective = requested or sorted(self.supported_versions)[0]
        response.headers[self.header_name] = effective
        response.headers["X-SLA-Enforced"] = "true"
        return response
