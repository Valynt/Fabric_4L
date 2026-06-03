---
workflow_id: code-quality-improvement
name: Code Quality Improvement
version: 1.0.0
description: Systematic code quality improvement workflow for transforming functional code into production-grade output through inspection, analysis, and targeted fixes
pattern: circuit-breaker
risk_level: low
---

# Code Quality Improvement Workflow

This workflow transforms "working" code into production-grade output through systematic inspection, analysis, and targeted fixes. It applies to both general code refinement and React component self-review.

## When to Use

- Code is functional but feels rough or incomplete
- Before marking a task as complete
- After implementing a feature and verifying it works
- When code review reveals quality gaps
- Periodic cleanup of technical debt
- Preparing code for handoff or release
- After React component generation (component-specific mode)

## When to Stop

- Diminishing returns: remaining issues are cosmetic
- Risk of breaking working functionality exceeds benefit
- Time budget exhausted (refinement can be infinite)
- Code is now "obviously correct" to a fresh reader

## Workflow Steps

### 1. Inspect the Implementation
// turbo
- Read all files touched by the recent work
- Identify the core logic, edge cases, and error handling
- Look for TODO comments, FIXME markers, or placeholders
- Check test coverage; if <80% or missing edge cases, strengthen tests first

**For React Components (Component Mode):**
- Review original Requirements Definition and Concept Design if available
- Compare generated code against proposed Component Hierarchy
- Verify State Management matches the design (props vs. state decisions)
- Check Styling Strategy adherence (did shortcuts occur?)

### 2. Identify Weaknesses

Scan for these specific issue categories:

**Incorrectness** (P0 - Critical)
- Unit tests fail
- Assertions missing
- Validation logic absent
- Logic errors

**Incompleteness** (P0 - Critical)
- Uncovered branches in tests
- Missing None/null checks
- Partial error handling
- Edge cases not handled

**Fragility** (P1 - High)
- Hardcoded strings/numbers
- No retry loops
- Direct dependency instantiation
- Missing error boundaries

**Inelegance** (P2 - Medium)
- Functions >50 lines
- Nested conditionals >3 levels
- Duplicate code blocks
- Poor naming

**Performance** (P3 - Low)
- Loops calling external services
- Unbounded queries
- No caching
- Unnecessary re-renders (React)

**Maintainability** (P2 - Medium)
- Missing type hints
- Unclear variable names
- No docstrings
- Magic numbers/strings

**For React Components (Component Mode):**
- **Performance**: Unnecessary re-renders, expensive computations not cached, no lazy loading, large lists lack virtualization
- **Accessibility (a11y)**: WCAG 2.1 compliance, ARIA attributes, keyboard navigation, focus management, loading/error states
- **Maintainability**: Component coupling, TypeScript type robustness, Single Responsibility Principle, prop drilling, magic values

### 3. Prioritize Fixes
- P0: Bugs and incorrect behavior (fix immediately)
- P1: Fragility that will cause production issues
- P2: Maintainability and clarity improvements
- P3: Performance and elegance refinements

### 4. Make Concrete Fixes by Category

**Incorrectness** (P0):
- Add missing validation
- Fix logic errors
- Add assertions
- Complete partial implementations

**Incompleteness** (P0):
- Handle the edge case
- Add the missing error branch
- Complete partial implementation
- Add missing None/null checks

**Fragility** (P1):
- Replace hardcoded values with constants
- Add retry logic with backoff
- Inject dependencies
- Add error boundaries (React)

**Inelegance** (P2):
- Extract function when code repeats 2+ times
- Flatten nested conditionals with early-return pattern
- Rename unclear vars (length >20 or <3 chars)
- Split functions >50 lines

**Performance** (P3):
- Batch external calls
- Add caching
- Make I/O async
- Memoize expensive computations (React: useMemo, useCallback)
- Lazy load heavy components (React: React.lazy, Suspense)

**Maintainability** (P2):
- Add type hints to public functions
- Add docstrings to non-obvious logic
- Replace magic numbers with named constants
- Extract constants to shared files

**For React Components (Component Mode):**
- Memoize expensive calculations with useMemo
- Add useCallback for event handlers
- Implement proper loading states
- Add error boundaries
- Improve accessibility (ARIA labels, keyboard nav, focus management)

### 5. Verify Improvements
// turbo
- Run all tests to ensure nothing broke
- Test edge cases that were previously unhandled
- Review the diff to confirm changes are focused (<100 lines ideally)
- Ensure the code is now "obviously correct" to a fresh reader
- Check test coverage improved or stayed same

**For React Components (Component Mode):**
- Run `run_type_check` to verify TypeScript strictness
- Run `run_linter` to check code style and unused imports
- Execute component tests if they exist
- Verify accessibility with a11y audit tools if available

### 6. Final Polish
- Check file organization and imports
- Verify consistent style with surrounding codebase
- Ensure no debug code or print statements remain
- Confirm all TODOs are resolved or ticketed
- Commit changes with descriptive message: "Refine: [specific improvement made]"

## Success Criteria (Definition of Done)

- Code passes all tests including new edge cases
- No P0 or P1 issues remain
- At least one measurable improvement made (coverage up, complexity down, clarity up)
- Changes are focused and reviewable in <15 minutes
- Code is "obviously correct" without needing explanation

**For React Components (Component Mode):**
- TypeScript strictness verified (no implicit `any`)
- Linter passes with no errors
- Component props API stable
- Accessibility requirements met (WCAG AA minimum)

## Concrete Actions Checklist

Use this to ensure you're making direct improvements, not just analyzing:

- [ ] Fixed at least one bug or incorrect behavior
- [ ] Added validation for at least one edge case
- [ ] Improved at least one variable or function name
- [ ] Extracted or simplified at least one complex block
- [ ] Added or strengthened at least one test
- [ ] Removed at least one piece of dead code
- [ ] Improved error handling in at least one location
- [ ] Committed with descriptive message explaining the refinement

**For React Components (Component Mode):**
- [ ] Requirements vs. Design vs. Code alignment verified
- [ ] Performance, a11y, maintainability analyzed
- [ ] TypeScript and lint checks run
- [ ] At least 3 specific enhancements identified

## Anti-Patterns to Avoid

- **Don't**: Write lengthy explanations of what's wrong without fixing it
- **Don't**: Suggest refactorings that don't address actual problems
- **Don't**: Add abstractions that increase complexity
- **Don't**: Ignore flaky tests or work around them
- **Don't**: Leave TODOs for "future cleanup"
- **Don't**: Make generic feedback like "improve UX" - be specific

## Example Commands

**General Code:**
```
"Refine the error handling in the ingestion pipeline"
"Harden the state machine against race conditions"
"Clean up the API response formatting code"
"Strengthen tests for the knowledge graph queries"
"Polish the agent workflow implementation"
"Remove technical debt from the extraction layer"
```

**React Components:**
```
"Review the GraphExplorer component for performance and accessibility"
"Self-review the newly generated AccountSettings component"
"Improve the DataTable component's maintainability"
"Audit the ValuePackEditor for a11y compliance"
```

## Execution Prompt Template (React Component Mode)

```
Execute the Code Quality Improvement Workflow on the component I just generated.

**COMPONENT LOCATION:**
- File path: [path to .tsx file]
- Test file: [path to .test.tsx if exists]

**ORIGINAL REQUIREMENTS & DESIGN:**
[Paste or reference the Phase 1 and Phase 2 artifacts if not in agent memory]

**FOCUS AREAS (optional):**
- Priority on: [performance / accessibility / maintainability]
- Known concerns: [any specific areas you want reviewed]

**AGENT DIRECTIVES:**
You MUST use run_type_check and run_linter to validate the current implementation.
Present exactly 3 high-impact enhancements with implementation plans. Do not
provide generic feedback—every suggestion must be specific and actionable.
```

## Relationship to Other Workflows

- **Preceded by:** `/react_component_design` (generates the component to review)
- **Followed by:** Implementation of selected enhancements
- **Alternative use:** Standalone audit of legacy components or general code
