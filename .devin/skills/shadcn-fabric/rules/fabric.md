# Fabric Domain Component Rules

Fabric-specific components in `@/components/ui/fabric/` provide consistent patterns for the Value Fabric product.

## Components

### FabricCard

**Purpose**: Entity display cards with consistent layout

**Incorrect:**
```tsx
<Card>
  <CardContent>
    <h3>{entity.name}</h3>
    <p>{entity.description}</p>
    <div className="flex gap-2 mt-4">
      <Button>Edit</Button>
      <Button variant="destructive">Delete</Button>
    </div>
  </CardContent>
</Card>
```

**Correct:**
```tsx
<FabricCard
  title={entity.name}
  description={entity.description}
  actions={[
    { label: "Edit", onClick: handleEdit },
    { label: "Delete", variant: "destructive", onClick: handleDelete }
  ]}
>
  <EntityDetails entity={entity} />
</FabricCard>
```

### FabricDialog

**Purpose**: Confirmation dialogs with Fabric styling

**Incorrect:**
```tsx
<AlertDialog>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Delete?</AlertDialogTitle>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel>Cancel</AlertDialogCancel>
      <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

**Correct:**
```tsx
<FabricDialog
  open={open}
  onOpenChange={setOpen}
  title="Delete Entity"
  description="This will permanently delete the entity and all associated data."
  confirmLabel="Delete"
  confirmVariant="destructive"
  onConfirm={handleDelete}
/>
```

### DataTable

**Purpose**: Tabular data with sorting, filtering, pagination

**Incorrect:**
```tsx
<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Name</TableHead>
      <TableHead>Status</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {data.map(row => (
      <TableRow key={row.id}>
        <TableCell>{row.name}</TableCell>
        <TableCell>{row.status}</TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
<div className="flex justify-between mt-4">
  <Button onClick={() => setPage(p => p - 1)}>Previous</Button>
  <Button onClick={() => setPage(p => p + 1)}>Next</Button>
</div>
```

**Correct:**
```tsx
<DataTable
  data={data}
  columns={[
    { accessorKey: "name", header: "Name" },
    { accessorKey: "status", header: "Status", cell: ({ row }) => (
      <StatusBadge status={row.original.status} />
    )}
  ]}
  pagination
  sorting
  filtering
/>
```

### StatusBadge

**Purpose**: Standardized status indicators

**Incorrect:**
```tsx
<span className={cn(
  "px-2 py-1 rounded-full text-sm",
  status === "active" && "bg-green-100 text-green-800",
  status === "pending" && "bg-yellow-100 text-yellow-800",
  status === "error" && "bg-red-100 text-red-800"
)}>
  {status}
</span>
```

**Correct:**
```tsx
<StatusBadge status={status} />
// or with label override
<StatusBadge status={status} label={customLabel} />
```

**Status Values**: `active`, `pending`, `error`, `warning`, `inactive`, `success`

### FilterBar

**Purpose**: Standardized list filter layout

**Incorrect:**
```tsx
<div className="flex gap-4 mb-6">
  <Input placeholder="Search..." value={search} onChange={setSearch} />
  <Select value={filter} onValueChange={setFilter}>
    <SelectTrigger>Filter</SelectTrigger>
    <SelectContent>...</SelectContent>
  </Select>
  <Button onClick={handleRefresh}>Refresh</Button>
</div>
```

**Correct:**
```tsx
<FilterBar
  search={{ value: search, onChange: setSearch, placeholder: "Search entities..." }}
  filters={[
    { label: "Status", value: statusFilter, options: statusOptions, onChange: setStatusFilter },
    { label: "Type", value: typeFilter, options: typeOptions, onChange: setTypeFilter }
  ]}
  actions={[
    { label: "Refresh", icon: RefreshIcon, onClick: handleRefresh },
    { label: "Create", icon: PlusIcon, onClick: handleCreate, variant: "default" }
  ]}
/>
```

### PageHeader

**Purpose**: Consistent page structure with breadcrumbs, title, actions

**Incorrect:**
```tsx
<div className="mb-6">
  <div className="text-sm text-muted-foreground">Settings / General</div>
  <h1 className="text-2xl font-bold mt-2">Platform Settings</h1>
  <p className="text-muted-foreground">Manage your platform configuration</p>
  <div className="flex gap-2 mt-4">
    <Button>Save</Button>
  </div>
</div>
```

**Correct:**
```tsx
<PageHeader
  breadcrumbs={[{ label: "Settings", href: "/settings" }, { label: "General" }]}
  title="Platform Settings"
  description="Manage your platform configuration"
  actions={[{ label: "Save", onClick: handleSave }]}
/>
```

## Key Takeaways

- Use `FabricCard` for all entity display cards
- Use `FabricDialog` for confirmation dialogs
- Use `DataTable` for all tabular data (sorting, filtering, pagination built-in)
- Use `StatusBadge` for status indicators (standardized colors)
- Use `FilterBar` for list filter layouts
- Use `PageHeader` for page structure (breadcrumbs, title, actions)
