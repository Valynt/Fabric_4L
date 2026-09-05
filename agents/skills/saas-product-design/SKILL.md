---
name: saas-product-design
version: 2026-05-06
triggers: ["SaaS", "multi-tenant", "onboarding", "navigation", "dashboard", "UI design", "accessibility", "AI integration", "tenant isolation", "Time-to-Value", "TTV", "command palette", "dark mode", "WCAG"]
tools: [bash, memory_reflect]
preconditions: []
constraints: ["prioritize tenant data isolation", "enforce tenant-aware authorization", "target sub-5-minute TTV", "use interactive walkthroughs over static tours", "implement command palette for power users", "apply calm design principles", "prepare for WCAG 3.0 compliance", "integrate AI as invisible infrastructure"]
category: design
---

# SaaS Product Design & Architecture

Core competencies for building scalable, high-retention multi-tenant SaaS products, focusing on architecture, onboarding, navigation, and modern UI design.

## Multi-Tenant Architecture

Designing secure and scalable backend foundations for multi-tenant software.

### Directives

- **Implement appropriate tenant data isolation strategies**: Choose between Silo (dedicated database), Pool (shared database with tenant IDs), or Bridge (schema-per-tenant) models based on security and scalability requirements.
- **Enforce tenant-aware authorization**: Ensure Role-Based Access Control (RBAC) and authentication are strictly evaluated within the tenant's specific context to prevent cross-tenant data access.
- **Automate tenant onboarding pipelines**: Provision infrastructure, assign identifiers, and initialize data without manual engineering intervention to enable rapid tenant provisioning.

## Frictionless Onboarding

Driving user activation and reducing churn through guided first experiences.

### Directives

- **Target a Time-to-Value (TTV) of under 5 minutes**: Get users to their first meaningful outcome as quickly as possible to maximize activation rates.
- **Replace static product tours with interactive walkthroughs**: Guide users through performing real actions, which has been shown to cut TTV by 40% compared to passive tours.
- **Personalize onboarding flows**: Adapt flows based on user role or intent, and utilize visual progress bars alongside 5-7 item checklists to increase completion rates.

## SaaS Navigation and Hierarchy

Structuring information architecture to match user mental models and accelerate discoverability.

### Directives

- **Choose appropriate navigation pattern**: Use object-oriented navigation for managing entities (like CRMs) or workflow-oriented navigation for sequential processes and task completion.
- **Implement a Command Palette (Cmd+K)**: Provide this as a standard feature to unify search and actions, removing navigation friction for power users.
- **Adapt navigation dynamically**: Show only features relevant to users' roles and permissions to reduce cognitive load and focus on daily tasks.

## Dashboard and UI Design

Creating actionable, data-driven, and minimalist interfaces for daily usage.

### Directives

- **Apply 'Calm Design' and strategic minimalism**: Default to generous whitespace and hide advanced settings behind progressive disclosure to reduce cognitive overload.
- **Design dashboards for fast scanning**: Maintain clear visual hierarchy, use metric cards, and always provide context for numbers (e.g., comparison trends rather than raw data).
- **Implement dark mode correctly**: Use a dedicated elevation model where surfaces get lighter as they stack, rather than simply inverting light mode colors.

## Accessibility and AI Integration

Building inclusive and intelligent software experiences.

### Directives

- **Prepare for WCAG 3.0 compliance**: Adopt the Advanced Perceptual Contrast Algorithm (APCA) for color contrast, moving beyond the traditional 4.5:1 ratio.
- **Integrate AI as invisible infrastructure**: Use AI for inline suggestions, contextual autocomplete, and other subtle enhancements rather than presenting it as a separate, obtrusive feature or chatbot.

## Self-rewrite hook

After every 10 uses OR on any failure:
1. Review if new SaaS patterns or 2026+ trends have emerged that should be added.
2. Check if any directives are being consistently violated in practice.
3. Update triggers based on new terminology or patterns users are using.
4. Commit: `skill-update: saas-product-design, <one-line reason>`.
