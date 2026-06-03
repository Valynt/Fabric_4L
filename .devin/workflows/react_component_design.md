---
workflow_id: react-component-design
name: React Component Design
version: 1.0.0
description: Three-phase React component design workflow with chain-of-thought rigor
pattern: circuit-breaker
risk_level: low
---

# React Component Design Workflow

Use this workflow when creating new React components to ensure high-quality, production-ready output through rigorous planning before coding.

## Available Agent Skills

This workflow leverages Windsurf's tool-calling capabilities for autonomous, self-validating component development:

### 1. Codebase Interaction Skills (Context Gathering)
- **read_package_json**: Check dependencies (Tailwind, React Query, Redux, etc.) to inform design decisions
- **search_codebase**: Find existing reusable components (e.g., `<CustomButton />` vs. writing raw `<button>`)
- **read_file**: Examine global styles, routing configs, and TypeScript definitions for seamless integration

### 2. External Research Skills (Anti-Hallucination)
- **web_search**: Look up modern UI patterns, accessibility standards (WCAG), or library-specific edge cases
- **fetch_documentation**: Scrape latest library docs (e.g., Framer Motion hooks, React Query v5 patterns) for correct syntax

### 3. Validation & Self-Correction Skills
- **run_type_check**: Execute `tsc --noEmit` on generated code; if errors found, fix and re-run until passing
- **run_linter**: Run ESLint/Ruff; auto-fix issues before presenting final code
- **run_tests**: Execute Jest/React Testing Library tests for generated components

### 4. Output Skills
- **write_file**: Create `.tsx`, `.css`, `.test.ts` files directly in the project directory

## Prerequisites

- Clear feature requirements or user stories
- Understanding of the component's place in the application hierarchy
- Access to existing component patterns in the codebase

## Phase 1: Requirements Definition Reflection

**Objective:** Analyze requirements thoroughly before writing any code.

**Deliverables:**
1. **Core Objectives** - Document the primary problem this component solves
2. **Edge Cases & Constraints** - Identify:
   - Failure states (error handling)
   - Loading states (skeletons, spinners)
   - Empty states (no data scenarios)
   - Performance constraints (large lists, re-renders)
   - Accessibility requirements (a11y)
3. **Missing Information** - List ambiguities or assumptions being made

**Verification Questions:**
- What data does this component need?
- What actions can users take?
- What are the error scenarios?
- Are there responsive design requirements?
- What accessibility standards apply (WCAG level)?

## Phase 2: React Component Concept Design

**Objective:** Design the technical architecture based on Phase 1 analysis and existing codebase patterns.

**MANDATORY SKILL USAGE:**
- **BEFORE designing components**: Use `search_codebase` to identify existing reusable components (buttons, inputs, cards, etc.) that should be imported rather than rewritten
- **BEFORE defining styling strategy**: Use `read_file` on `package.json` and existing global style files to determine if the project uses Tailwind, Styled Components, or CSS Modules
- **IF using external libraries**: Use `fetch_documentation` or `web_search` to verify latest API patterns and best practices

**Deliverables:**
1. **Component Hierarchy** - Map parent-child relationships if multiple components needed
2. **State & Props Definition** - Document:
   - Props interface (inputs from parent)
   - Local state requirements
   - Derived state vs. stored state decisions
3. **Hooks & Side Effects** - Identify:
   - `useEffect` for data fetching
   - `useMemo` for expensive computations
   - `useCallback` for event handlers
   - Custom hooks needed
4. **Styling Strategy** - Define:
   - Tailwind classes / CSS Modules / Styled Components
   - Responsive breakpoints
   - Design system tokens to use

**Verification Questions:**
- Is state lifted to the appropriate level?
- Are props minimal and well-typed?
- Are side effects isolated and documented?
- Does the styling approach match the codebase?

## Phase 3: Component Code Generation

**Objective:** Write production-ready React code based strictly on Phase 2 design, then self-validate.

**Code Standards:**
- Functional components with hooks (no class components)
- TypeScript interfaces for all Props and State
- Clean error handling with ErrorBoundary consideration
- Loading state implementation
- Inline comments for complex logic
- JSDoc for public component interfaces

**MANDATORY SELF-VALIDATION LOOP:**
1. Write initial component code
2. **Run** `run_type_check` (e.g., `tsc --noEmit`)
3. **If errors found**: Read error messages, fix code, return to step 2
4. **If passing**: **Run** `run_linter` (ESLint/Ruff)
5. **If lint errors found**: Fix issues, return to step 4
6. **If both passing**: Present final code and **Run** `write_file` to create files

**Before Submitting Code:**
- Run TypeScript check: `tsc --noEmit`
- Verify no `any` types (use `unknown` if needed)
- Check accessibility (labels, keyboard navigation)
- Ensure no prop drilling (use context if appropriate)

## Execution Prompt Template

When invoking this skill-enabled workflow, use the following structure:

```
Execute the React Component Design Workflow with these requirements:

**INPUT REQUIREMENTS:**
[Describe the component: purpose, user interactions, data sources, design constraints]

**CONTEXT:**
- Target file location: [path]
- Related components: [list]
- Data hooks available: [list]
- Styling approach: [Tailwind/CSS Modules/etc]

**AGENT DIRECTIVES:**
During Phase 2, you MUST use your search_codebase tool to identify existing reusable components before designing new ones. After Phase 3, you MUST use your run_type_check tool to validate your code. If the check fails, fix the code and run it again until it passes.
```

**How This Changes the Output:**
- Without skills: Agent relies on training data; may write raw `<button>` instead of finding your `<CustomButton />`
- With skills: Agent searches codebase, imports existing components, validates its own TypeScript, and iterates until passing

## Example Output Structure

**Phase 1: Requirements Definition Reflection**
- Core Objectives: [documented]
- Edge Cases: [documented]
- Missing Information: [documented]

**Phase 2: Component Concept Design**
- Component Hierarchy: [documented]
- Props Interface: [documented]
- State Management: [documented]
- Hooks Required: [documented]
- Styling Strategy: [documented]

**Phase 3: Component Code**
```tsx
// Complete, production-ready component code
```

## Quality Checklist

- [ ] Phase 1 and 2 completed before any code written
- [ ] TypeScript types defined for all props
- [ ] Error boundaries or error states implemented
- [ ] Loading states handled
- [ ] Accessibility attributes included
- [ ] No performance anti-patterns (inline objects, unmemoized callbacks)
- [ ] Follows existing codebase patterns
- [ ] JSDoc comments for public API
