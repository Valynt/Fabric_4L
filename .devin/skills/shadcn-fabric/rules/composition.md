# Component Structure & Composition Rules

## Incorrect vs Correct

### Dialog with Title

**Incorrect:**
```tsx
<Dialog open={open} onOpenChange={setOpen}>
  <DialogContent>
    <div>Content without title</div>
  </DialogContent>
</Dialog>
```

**Correct:**
```tsx
<Dialog open={open} onOpenChange={setOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Confirm Action</DialogTitle>
      <DialogDescription>
        This action cannot be undone.
      </DialogDescription>
    </DialogHeader>
    <div>Content</div>
    <DialogFooter>
      <Button variant="outline" onClick={() => setOpen(false)}>
        Cancel
      </Button>
      <Button onClick={handleConfirm}>Confirm</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Card Composition

**Incorrect:**
```tsx
<Card>
  <CardContent className="p-6">
    <h3 className="text-lg font-semibold">Title</h3>
    <p className="text-muted-foreground">Description</p>
    <div className="mt-4">Content</div>
    <div className="mt-4 flex justify-end">
      <Button>Action</Button>
    </div>
  </CardContent>
</Card>
```

**Correct:**
```tsx
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent>Content</CardContent>
  <CardFooter className="flex justify-end">
    <Button>Action</Button>
  </CardFooter>
</Card>
```

### Select Items

**Incorrect:**
```tsx
<Select>
  <SelectTrigger />
  <SelectContent>
    <SelectItem value="a">A</SelectItem>
    <SelectItem value="b">B</SelectItem>
  </SelectContent>
</Select>
```

**Correct:**
```tsx
<Select>
  <SelectTrigger />
  <SelectContent>
    <SelectGroup>
      <SelectLabel>Group Label</SelectLabel>
      <SelectItem value="a">A</SelectItem>
      <SelectItem value="b">B</SelectItem>
    </SelectGroup>
  </SelectContent>
</Select>
```

### Tabs Structure

**Incorrect:**
```tsx
<Tabs>
  <TabsTrigger value="tab1">Tab 1</TabsTrigger>
  <TabsTrigger value="tab2">Tab 2</TabsTrigger>
  <TabsContent value="tab1">Content 1</TabsContent>
  <TabsContent value="tab2">Content 2</TabsContent>
</Tabs>
```

**Correct:**
```tsx
<Tabs>
  <TabsList>
    <TabsTrigger value="tab1">Tab 1</TabsTrigger>
    <TabsTrigger value="tab2">Tab 2</TabsTrigger>
  </TabsList>
  <TabsContent value="tab1">Content 1</TabsContent>
  <TabsContent value="tab2">Content 2</TabsContent>
</Tabs>
```

### Avatar with Fallback

**Incorrect:**
```tsx
<Avatar>
  <AvatarImage src={src} />
</Avatar>
```

**Correct:**
```tsx
<Avatar>
  <AvatarImage src={src} />
  <AvatarFallback>JD</AvatarFallback>
</Avatar>
```

### Custom Trigger

**Incorrect:**
```tsx
<Dialog>
  <button onClick={() => setOpen(true)}>Open</button>
  <DialogContent>...</DialogContent>
</Dialog>
```

**Correct:**
```tsx
<Dialog>
  <DialogTrigger asChild>
    <Button variant="outline">Open</Button>
  </DialogTrigger>
  <DialogContent>...</DialogContent>
</Dialog>
```

## Key Takeaways

- Always include `DialogTitle` (use `className="sr-only"` if hidden)
- Use full Card composition: Header, Title, Description, Content, Footer
- Wrap SelectItems in SelectGroup with SelectLabel
- TabsTrigger must be inside TabsList
- Avatar always needs AvatarFallback
- Use `asChild` for custom triggers
