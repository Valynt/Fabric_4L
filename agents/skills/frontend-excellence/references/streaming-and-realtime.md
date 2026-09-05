# Streaming & Realtime Plumbing

**Destination:** Agentic UIs that stream progressive output (tokens, tool-call updates, partial results) so the interface never feels like a blocked spinner, with clean cleanup and graceful degradation.

## When to Use Which

| Need | Mechanism |
|---|---|
| One-way stream of agent tokens / progress | Server-Sent Events (SSE) |
| Bidirectional (agent ↔ user messages, live tool state) | WebSocket |
| Long-running job with polling already present | Poll + Progress |
| Adapter/fallback when SSE unsupported | Poll with backoff |

Prefer SSE for agent output (simple, auto-reconnect, works over plain HTTP, no protocol upgrade in proxies). Reach for WebSocket only when the server needs to push to the client unprompted.

## Steps

1. **Define the event contract.** A typed union of event types (`token`, `tool_start`, `tool_end`, `plan`, `done`, `error`), each with a stable shape. This is a contract — put it in the OpenAPI/DTO layer and validate on receipt.
2. **Use a hook to own the connection.** Encapsulate connect, reconnect, buffering, and cleanup in one typed hook (see `templates/hook.ts` pattern). Components consume parsed events, never the raw socket.
3. **Handle lifecycle.** Close on unmount, abort in-flight requests, reconnect with backoff, surface a "connection lost / retrying" state rather than silently hanging.
4. **Race conditions.** Ignore/terminate stale streams when the request param changes. Buffer events that arrive before the handler subscribes.
5. **Progressive UI ≠ fake progress.** Show real partial data with shimmer/skeleton; never fake a loading bar for an unknown duration.
6. **Failure mode.** On error, emit a typed `error` event with a code and safe message; do not expose raw provider errors.

## Common Failure

**Leaked or unterminated stream.** A component unmounts (route change) but the EventSource/WebSocket stays open, causing duplicate subscriptions and memory leaks in a SPA. Always close in a cleanup function keyed to the component/hook lifecycle.

## Verification

```bash
pnpm --dir apps/web run typecheck
# Component/e2e test asserting subscribe → open → event → clean unsubscribe
pnpm --dir apps/web run test:contracts
```