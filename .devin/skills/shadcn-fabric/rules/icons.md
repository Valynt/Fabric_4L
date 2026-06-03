# Icons Rules

## Incorrect vs Correct

### Icon Import

**Incorrect:**
```tsx
import { Search } from "lucide-react"
// or
import SearchIcon from "@/assets/icons/search.svg"
// or
<Icon name="search" />
```

**Correct:**
```tsx
import { SearchIcon } from "lucide-react"
```

### Icon in Button

**Incorrect:**
```tsx
<Button>
  <SearchIcon className="w-4 h-4 mr-2" />
  Search
</Button>
```

**Correct:**
```tsx
<Button>
  <SearchIcon data-icon="inline-start" />
  Search
</Button>
```

### Icon Only Button

**Incorrect:**
```tsx
<Button>
  <SearchIcon className="w-4 h-4" />
</Button>
```

**Correct:**
```tsx
<Button size="icon" aria-label="Search">
  <SearchIcon />
</Button>
```

### Standalone Icon

**Incorrect:**
```tsx
<div>
  <SearchIcon className="w-5 h-5 text-muted-foreground" />
</div>
```

**Correct:**
```tsx
<div>
  <SearchIcon className="size-5 text-muted-foreground" />
</div>
```

### Icon as Prop

**Incorrect:**
```tsx
<MenuItem icon="search">Search</MenuItem>
// or
<MenuItem icon={<SearchIcon className="w-4 h-4" />}>Search</MenuItem>
```

**Correct:**
```tsx
<MenuItem icon={SearchIcon}>Search</MenuItem>
```

## Key Takeaways

- Use `lucide-react` icons only
- Import icons as named exports: `import { SearchIcon }`
- Don't add sizing classes to icons inside components (components handle sizing)
- Use `data-icon="inline-start"` or `data-icon="inline-end"` in buttons
- Pass icons as components (`icon={SearchIcon}`), not strings or JSX
- Use `size-*` for standalone icon sizing
- Always provide `aria-label` for icon-only buttons
