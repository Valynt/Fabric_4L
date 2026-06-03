---
description: Generate and maintain professional technical documentation
tier: 4
category: content_generation
---

# Technical Documentation Skill

Generate, update, and validate professional technical documentation from source code and specifications.

## Tool Schema

```python
{
  "name": "technical_documentation",
  "description": "Create or update technical documentation for systems, APIs, and architectures",
  "parameters": {
    "doc_type": "API_REFERENCE | ARCHITECTURE | DEPLOYMENT | RUNBOOK | CHANGELOG | README | ADR",
    "target_audience": "DEVELOPER | ARCHITECT | DEVOPS | EXECUTIVE | PRODUCT_MANAGER",
    "subject": "string - Component, system, or feature identifier",
    "source_files": ["string - Paths to source files or directories"],
    "existing_docs": "string - Path to existing documentation (optional)",
    "update_mode": "CREATE | UPDATE | REFRESH (default: CREATE)",
    "output_format": "MARKDOWN | HTML | CONFLUENCE | NOTION (default: MARKDOWN)",
    "max_depth": "integer 1-5 - Analysis depth for source files (default: 3)"
  },
  "returns": "Documentation artifact with metadata, content, and validation report"
}
```

## Returns Schema

```python
{
  "content": "string - Complete documentation content",
  "metadata": {
    "doc_type": "string",
    "subject": "string",
    "version": "string",
    "last_updated": "ISO8601 datetime",
    "author": "string",
    "files_analyzed": ["string"]
  },
  "sections": ["string - List of documented sections"],
  "validation": {
    "accuracy_score": "float 0.0-1.0",
    "completeness_score": "float 0.0-1.0",
    "issues": ["string - List of warnings or gaps"]
  },
  "file_path": "string - Path where documentation was saved"
}
```

## Execution Steps

1. **Locate Sources**
   - Read all `source_files` paths
   - If directory, recursively find relevant files (*.py, *.ts, *.yaml, etc.)
   - Load `existing_docs` if provided

2. **Extract Specifications**
   - Parse function signatures, classes, endpoints
   - Extract docstrings and type hints
   - Identify configuration parameters
   - Map dependencies and relationships

3. **Analyze Gaps**
   - Compare extracted specs against `existing_docs`
   - Flag undocumented public APIs
   - Identify outdated examples
   - Note missing error cases

4. **Generate Structure**
   - Apply `doc_type` template
   - Order sections by `target_audience` priority
   - Include required metadata headers

5. **Write Content**
   - Document each spec with examples
   - Add mermaid diagrams for architectures
   - Create tables for config/options
   - Document all error responses

6. **Validate**
   - Cross-check against source accuracy
   - Ensure all links resolve
   - Verify code examples execute
   - Score completeness

7. **Deliver**
   - Write to appropriate directory
   - Update indexes if needed
   - Return artifact with validation report

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `SourceNotFound` | `source_files` path invalid | Verify path, check permissions |
| `NoExtractableSpecs` | No public APIs found | Increase `max_depth`, check file types |
| `ValidationFailed` | Accuracy score < 0.7 | Add more source files, clarify subject |
| `InvalidDocType` | Unknown doc_type enum | Use supported type from schema |

## Quality Checklist

- [ ] All public functions/classes documented
- [ ] Code examples compile/execute
- [ ] No broken internal links
- [ ] Metadata includes version and date
- [ ] Appropriate for target_audience level
- [ ] Error cases documented
- [ ] Diagrams render correctly

## Example Uses

```
Create API reference for Layer 5 Ground Truth endpoints from services/layer5-ground-truth/src/api/router.py
Update README for layer2-extraction with new env vars from .env.example
Generate ADR for Neo4j migration in docs/architecture/decisions/
Create runbook for database failover from src/operations/recovery.py
```
