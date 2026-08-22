# Frontend Governance Rule

The `DESIGN.md` file at repository root is the canonical visual and interaction design contract.

## Invariants
1. **Design System**: Use tokens, typography, and component patterns defined in `DESIGN.md`. Do not invent ad-hoc colors, fonts, or arbitrary paddings.
2. **Component Reuse**: Reuse shared UI primitives (`PageShell`, `PageHeader`, `Card`, `Button`, `Table`, `Dialog`, `Drawer`).
3. **No Forbidden Tropes**: Strictly avoid dashboard overuse, purple-on-dark themes, colored border glowing accents, textureless surfaces, and icon-stuffed bento boxes.
4. **Data Separation**: React components consume domain/view models, never raw API DTOs directly. Use adapters to map DTOs.
5. **No `any`**: TypeScript strict typing is mandatory with no `any`.
