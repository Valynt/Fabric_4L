# Semantic Memory

Cross-session, persistent rules and patterns distilled from episodic logs. **Versioned in Git.**

## Structure

```
semantic/
  rules/
    auto-generated/     # Rules from distillation pipeline
    curated/            # Human-authored rules
  patterns/
    anti-patterns/      # Known bad practices with fixes
    good-practices/     # Verified effective patterns
```

## Rule Format

Every rule is a markdown file with YAML frontmatter:

```markdown
---
rule_id: auto-generated-XXXX
created_at: YYYY-MM-DD
derived_from: ["episode-uuid-1"]
confidence: 0.0-1.0
applies_to:
  - "glob/pattern/**/*.py"
tags: ["tag1", "tag2"]
---

# Rule Title

## Pattern
What triggers this rule.

## Rule
What to do.

## Rationale
Why this matters.

## Example
Code example.
```

## Confidence Threshold

- **>= 0.90:** Auto-injected into all relevant sessions
- **0.70 - 0.89:** Suggested, agent decides
- **< 0.70:** Archive to `archive/semantic/` for review

## Quarterly Review

Every 90 days:
1. Review all rules in `semantic/rules/auto-generated/`
2. Archive rules with confidence < 0.70
3. Promote well-validated rules to `semantic/rules/curated/`
4. Update `registry/rules.json` if rule categories changed
