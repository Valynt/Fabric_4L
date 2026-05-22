# Runtime Secret Inventory

| Runtime secret (K8s target) | Backend source-of-truth path | Rotation owner |
|---|---|---|
| `openai-secret` | `value-fabric/llm#openai-api-key` | Platform Security + AI Platform |
| `anthropic-secret` | `value-fabric/llm#anthropic-api-key` | Platform Security + AI Platform |
| `pinecone-secret` | `value-fabric/search#pinecone-api-key` | Search Platform |
| `browserbase-secret` | `value-fabric/providers#browserbase-api-key` | Integrations Team |
| `firecrawl-secret` | `value-fabric/providers#firecrawl-api-key` | Integrations Team |
| `neo4j-secret` | `value-fabric/database#neo4j-auth` | Data Platform |
| `postgres-secret` | `value-fabric/database#postgres-password` | Data Platform |
| `jwt-secret` | `value-fabric/auth#jwt-secret` | Identity/Security |
| `api-key-hmac-secret` | `value-fabric/auth#api-key-hmac-secret` | Identity/Security |
| `keycloak-secrets` | `value-fabric/auth#keycloak-bootstrap` | Identity/Security |
| `keycloak-frontend-client-secret` | `value-fabric/auth#keycloak-frontend-client-secret` | Identity/Security |
| `keycloak-api-client-secret` | `value-fabric/auth#keycloak-api-client-secret` | Identity/Security |
