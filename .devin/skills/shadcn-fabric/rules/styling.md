# Styling & Tailwind Rules

## Incorrect vs Correct

### Layout Spacing

**Incorrect:**
```tsx
<div className="space-y-4">
  <Input />
  <Button />
</div>
```

**Correct:**
```tsx
<div className="flex flex-col gap-4">
  <Input />
  <Button />
</div>
```

### Equal Dimensions

**Incorrect:**
```tsx
<Avatar className="w-10 h-10" />
```

**Correct:**
```tsx
<Avatar className="size-10" />
```

### Conditional Classes

**Incorrect:**
```tsx
<div className={`p-4 ${isActive ? 'bg-primary' : 'bg-muted'} ${isLarge ? 'text-lg' : ''}`}>
```

**Correct:**
```tsx
import { cn } from "@/lib/utils"

<div className={cn("p-4", isActive && "bg-primary", !isActive && "bg-muted", isLarge && "text-lg")}>
```

### Semantic Colors

**Incorrect:**
```tsx
<div className="bg-blue-500 text-white dark:bg-blue-900">
  <span className="text-gray-600 dark:text-gray-400">Label</span>
</div>
```

**Correct:**
```tsx
<div className="bg-primary text-primary-foreground">
  <span className="text-muted-foreground">Label</span>
</div>
```

### Truncate

**Incorrect:**
```tsx
<span className="overflow-hidden text-ellipsis whitespace-nowrap">
```

**Correct:**
```tsx
<span className="truncate">
```

### Component Styling Override

**Incorrect:**
```tsx
<Button className="bg-emerald-500 hover:bg-emerald-600 text-white">
  Save
</Button>
```

**Correct:**
```tsx
<Button variant="default">
  Save
</Button>
```

## Key Takeaways

- Always use semantic color tokens (`bg-primary`, `text-muted-foreground`)
- Use `gap-*` for spacing, never `space-x-*` or `space-y-*`
- Use `size-*` for equal width/height
- Use `truncate` shorthand
- Use `cn()` for conditional classes
- Don't override component colors with raw Tailwind colors
