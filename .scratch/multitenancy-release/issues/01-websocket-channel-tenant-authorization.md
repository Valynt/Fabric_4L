# 01: Real-Time WebSocket Channel Tenant Authorization

**What to build:**
Ensure all real-time WebSocket connection multiplexing, channel subscription requests, and event streaming in the API gateway and web frontend strictly validate the client's authenticated JWT tenant claims against the requested channel namespace. Subscribing or listening to unauthorized tenant channels must fail closed with immediate termination or rejection.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] WebSocket connection handshake verifies valid tenant identity from authenticated session tokens.
- [ ] Channel subscription requests for any tenant other than the authenticated tenant return an explicit permission denial and reject subscription.
- [ ] Broadcast dispatchers prevent event leakage across tenant topic boundaries.
- [ ] End-to-end hostile tests verify Tenant A cannot receive or intercept stream events intended for Tenant B.
