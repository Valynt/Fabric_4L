"""Contract-aware HTTP transports shared across Value Fabric services.

Every entry here is the single authoritative home for one upstream service's
endpoint literals and transport behavior (URL construction, auth headers,
serialization, timeout, HTTP status boundary).  Consumers keep their own
domain-level error translation and request construction.
"""