---
skill_id: memory-context
name: memory-context
version: 1.0.0
description: Vector store and knowledge graph integration for semantic memory, conversation context management, and cross-session persistence
side_effects: none
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# Memory and Context Management

Use this skill when implementing:
- Vector-based semantic search for document retrieval
- Knowledge graph queries for relationship traversal
- Conversation context window management
- Cross-session user memory persistence

## Core Patterns

### Vector Store Abstraction
```python
from layer3_knowledge.src.retrieval.vector_store import VectorStore

class SemanticMemory:
    def __init__(self, store: VectorStore):
        self.store = store
    
    async def remember(
        self, 
        content: str, 
        metadata: dict,
        namespace: str = "conversations"
    ) -> str:
        """Store in vector DB with embedding."""
        embedding = await self.embed(content)
        return await self.store.upsert(
            vectors=[{
                "id": str(uuid4()),
                "values": embedding,
                "metadata": {**metadata, "content": content}
            }],
            namespace=namespace
        )
    
    async def recall(
        self, 
        query: str, 
        top_k: int = 5,
        namespace: str = "conversations"
    ) -> List[dict]:
        """Semantic search across stored memories."""
        embedding = await self.embed(query)
        return await self.store.query(
            vector=embedding,
            top_k=top_k,
            namespace=namespace
        )
```

### Knowledge Graph Context
```python
from layer3_knowledge.src.retrieval.graph_rag import GraphRAG

async def get_entity_context(entity_id: str, depth: int = 2) -> dict:
    """Retrieve entity neighborhood from graph."""
    cypher = """
    MATCH path = (e:Entity {id: $id})-[:RELATES_TO*1..$depth]-(connected)
    RETURN e, relationships(path), nodes(path)
    """
    result = await graph_rag.query(cypher, {"id": entity_id, "depth": depth})
    return build_context_graph(result)
```

### Context Window Management
```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ContextWindow:
    max_tokens: int = 128000
    reserved_tokens: int = 4000  # For response
    messages: List[dict] = None
    
    def add_message(self, role: str, content: str, token_count: int):
        """Add message with automatic pruning if over limit."""
        available = self.max_tokens - self.reserved_tokens
        current = sum(m.get("tokens", 0) for m in self.messages)
        
        if current + token_count > available:
            self._prune_oldest(current + token_count - available)
        
        self.messages.append({
            "role": role,
            "content": content,
            "tokens": token_count
        })
    
    def _prune_oldest(self, tokens_to_remove: int):
        """Remove oldest non-system messages."""
        while tokens_to_remove > 0 and len(self.messages) > 1:
            removed = self.messages.pop(1)  # Keep system message
            tokens_to_remove -= removed.get("tokens", 0)
```

### Cross-Session Memory
```python
class UserMemory:
    """Persistent memory keyed by user/tenant."""
    
    async def save_user_fact(
        self, 
        user_id: str,
        fact_type: str,  # e.g., "preference", "fact", "goal"
        content: str,
        ttl_days: Optional[int] = None
    ):
        """Store user-specific fact in Ground Truth layer."""
        from layer5_ground_truth.src.services.truth_service import create_truth_object
        
        return await create_truth_object(
            claim=content,
            claim_type=fact_type,
            applies_to={"user_id": user_id, "tenant_id": get_current_tenant()},
            freshness_ttl_days=ttl_days,
            sources=["user_conversation"]
        )
```

## Project-Specific Conventions

- **Vector Store**: Use `layer3-knowledge/src/retrieval/vector_store.py` abstraction
- **Graph Queries**: All Cypher queries centralized in `layer3-knowledge/src/schema/queries.py`
- **Ground Truth**: Store verified facts via `layer5-ground-truth/src/services/`
- **Namespaces**: Use format `{tenant_id}/{resource_type}` for multi-tenancy

## Integration Points

```python
# Layer 3 Knowledge Graph for entity relationships
from layer3_knowledge.src.agents.whitespace_analysis import WhitespaceAnalyzer

# Layer 5 Ground Truth for verified facts
from layer5_ground_truth.src.services.truth_service import get_truth_objects

# Redis for ephemeral context
from layer4_agents.src.engine.state_manager import StateManager
```

## Anti-Patterns to Avoid

- Don't store large documents in graph nodes (use vector store + reference)
- Don't mix tenant data without namespace isolation
- Don't rely on conversation history without summarization
- Don't store PII in unencrypted vector metadata
