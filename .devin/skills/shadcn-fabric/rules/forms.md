# Forms & Inputs Rules

## Incorrect vs Correct

### Form Structure

**Incorrect:**
```tsx
<form onSubmit={handleSubmit}>
  <div className="space-y-4">
    <div>
      <Label htmlFor="email">Email</Label>
      <Input id="email" value={email} onChange={e => setEmail(e.target.value)} />
    </div>
    {errors.email && <span className="text-red-500">{errors.email}</span>}
  </div>
</form>
```

**Correct:**
```tsx
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"

const schema = z.object({
  email: z.string().email()
})

function MyForm() {
  const form = useForm({
    resolver: zodResolver(schema)
  })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </form>
    </Form>
  )
}
```

### Toggle Options

**Incorrect:**
```tsx
<div className="flex gap-2">
  {options.map(opt => (
    <Button
      key={opt}
      variant={selected === opt ? "default" : "outline"}
      onClick={() => setSelected(opt)}
    >
      {opt}
    </Button>
  ))}
</div>
```

**Correct:**
```tsx
<ToggleGroup type="single" value={selected} onValueChange={setSelected}>
  {options.map(opt => (
    <ToggleGroupItem key={opt} value={opt}>
      {opt}
    </ToggleGroupItem>
  ))}
</ToggleGroup>
```

### Loading State

**Incorrect:**
```tsx
<Button isLoading={isPending}>
  Save
</Button>
```

**Correct:**
```tsx
<Button disabled={isPending}>
  {isPending && <Spinner className="mr-2 h-4 w-4" />}
  Save
</Button>
```

### Form Field Loading

**Incorrect:**
```tsx
{isLoading ? (
  <div className="animate-pulse h-10 bg-muted rounded" />
) : (
  <Input {...field} />
)}
```

**Correct:**
```tsx
<FormControl>
  {isLoading ? (
    <Skeleton className="h-10 w-full" />
  ) : (
    <Input {...field} />
  )}
</FormControl>
```

## Key Takeaways

- Always use `Form` + `FormField` + react-hook-form + zod
- Use `FormMessage` for validation errors, never custom error display
- Use `ToggleGroup` for 2-7 option selections
- Compose loading states with `Spinner` + `disabled`, not `isLoading` prop
- Use `Skeleton` for field-level loading states
