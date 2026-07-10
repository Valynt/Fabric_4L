/**
 * TenantSelector Stories — Domain Component
 * ============================================
 *
 * Covers the tenant switcher dropdown used in the app shell:
 *   - Default state (single tenant)
 *   - Multi-tenant dropdown open
 *   - Tenant with long name / truncation
 *   - Loading state
 *   - Empty state (no tenants)
 *   - Tenant badge variants (active, trial, enterprise)
 *
 * DESIGN.md § State: "Zustand only for cross-route client state"
 * DESIGN.md § Tenancy: tenant context is a boundary — never bypass validation
 */

import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Building2, Check, ChevronDown, Plus, Settings } from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Tenant {
  id: string;
  name: string;
  slug: string;
  tier: "free" | "trial" | "pro" | "enterprise";
  isActive: boolean;
}

// ---------------------------------------------------------------------------
// Mock TenantSelector component
// ---------------------------------------------------------------------------

interface TenantSelectorProps {
  tenants: Tenant[];
  activeTenantId: string;
  onSwitch: (tenantId: string) => void;
  onCreate?: () => void;
  onManage?: () => void;
  loading?: boolean;
}

function TenantSelector({
  tenants,
  activeTenantId,
  onSwitch,
  onCreate,
  onManage,
  loading,
}: TenantSelectorProps) {
  const [open, setOpen] = useState(false);
  const activeTenant = tenants.find((t) => t.id === activeTenantId);

  const tierBadge = (tier: Tenant["tier"]) => {
    const variantMap = {
      free: "secondary",
      trial: "default",
      pro: "default",
      enterprise: "outline",
    } as const;
    return (
      <Badge variant={variantMap[tier]} className="ml-2 text-[10px] px-1 py-0">
        {tier}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-3 py-2">
        <Skeleton className="h-4 w-4 rounded-full" />
        <Skeleton className="h-4 w-[140px]" />
      </div>
    );
  }

  if (tenants.length === 0) {
    return (
      <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={onCreate}>
        <Plus className="mr-2 h-4 w-4" />
        Create workspace
      </Button>
    );
  }

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="justify-between min-w-[200px] max-w-[280px]">
          <div className="flex items-center gap-2 truncate">
            <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="truncate">{activeTenant?.name ?? "Select workspace"}</span>
            {activeTenant && tierBadge(activeTenant.tier)}
          </div>
          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground ml-2" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-[280px]" align="start">
        <DropdownMenuLabel>Workspaces</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {tenants.map((tenant) => (
          <DropdownMenuItem
            key={tenant.id}
            className="flex items-center justify-between cursor-pointer"
            onClick={() => {
              onSwitch(tenant.id);
              setOpen(false);
            }}
          >
            <div className="flex items-center gap-2 min-w-0">
              <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="truncate">{tenant.name}</span>
              {tierBadge(tenant.tier)}
            </div>
            {tenant.id === activeTenantId && (
              <Check className="h-4 w-4 text-primary shrink-0 ml-2" />
            )}
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onCreate} className="cursor-pointer">
          <Plus className="mr-2 h-4 w-4" />
          Create workspace
        </DropdownMenuItem>
        <DropdownMenuItem onClick={onManage} className="cursor-pointer">
          <Settings className="mr-2 h-4 w-4" />
          Manage workspaces
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const mockTenants: Tenant[] = [
  { id: "t-1", name: "Acme Corp", slug: "acme", tier: "enterprise", isActive: true },
  { id: "t-2", name: "BetaLabs", slug: "betalabs", tier: "pro", isActive: false },
  { id: "t-3", name: "GammaStartup", slug: "gamma", tier: "trial", isActive: false },
  { id: "t-4", name: "Delta Industries — Very Long Name That Truncates", slug: "delta", tier: "free", isActive: false },
];

// ---------------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------------

const meta: Meta<typeof TenantSelector> = {
  title: "Domain/TenantSelector",
  component: TenantSelector,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
  },
  argTypes: {
    tenants: { control: "object" },
    activeTenantId: { control: "text" },
    loading: { control: "boolean" },
    onSwitch: { action: "switch" },
    onCreate: { action: "create" },
    onManage: { action: "manage" },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

// ---------------------------------------------------------------------------
// Stories
// ---------------------------------------------------------------------------

export const Default: Story = {
  args: {
    tenants: mockTenants,
    activeTenantId: "t-1",
    loading: false,
  },
};

export const SingleTenant: Story = {
  args: {
    tenants: [mockTenants[0]],
    activeTenantId: "t-1",
  },
};

export const ManyTenants: Story = {
  args: {
    tenants: [
      ...mockTenants,
      { id: "t-5", name: "EpsilonCo", slug: "epsilon", tier: "pro", isActive: false },
      { id: "t-6", name: "ZetaGroup", slug: "zeta", tier: "enterprise", isActive: false },
      { id: "t-7", name: "EtaVentures", slug: "eta", tier: "trial", isActive: false },
    ],
    activeTenantId: "t-1",
  },
};

export const LongName: Story = {
  args: {
    tenants: [
      {
        id: "t-long",
        name: "Supercalifragilisticexpialidocious Corporation International",
        slug: "supercorp",
        tier: "enterprise",
        isActive: true,
      },
      ...mockTenants.slice(1),
    ],
    activeTenantId: "t-long",
  },
  parameters: {
    docs: {
      description: {
        story: "Verifies text truncation for very long tenant names.",
      },
    },
  },
};

export const Loading: Story = {
  args: {
    tenants: [],
    activeTenantId: "",
    loading: true,
  },
};

export const Empty: Story = {
  args: {
    tenants: [],
    activeTenantId: "",
    loading: false,
  },
};

// ---------------------------------------------------------------------------
// Tier variants
// ---------------------------------------------------------------------------

export const TierVariants: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <div className="flex flex-col gap-4">
      {(["free", "trial", "pro", "enterprise"] as const).map((tier) => (
        <TenantSelector
          key={tier}
          tenants={[
            {
              id: `t-${tier}`,
              name: `${tier.charAt(0).toUpperCase() + tier.slice(1)} Workspace`,
              slug: tier,
              tier,
              isActive: true,
            },
          ]}
          activeTenantId={`t-${tier}`}
          onSwitch={() => {}}
        />
      ))}
    </div>
  ),
};

// ---------------------------------------------------------------------------
// Open state (simulated)
// ---------------------------------------------------------------------------

export const DropdownOpen: Story = {
  parameters: {
    controls: { disable: true },
    docs: {
      description: {
        story:
          "Shows the dropdown in its open state. In Storybook, click the trigger to open interactively.",
      },
    },
  },
  render: () => (
    <div className="flex gap-8 items-start">
      <TenantSelector
        tenants={mockTenants}
        activeTenantId="t-1"
        onSwitch={() => {}}
        onCreate={() => {}}
        onManage={() => {}}
      />
    </div>
  ),
  play: async ({ canvasElement }) => {
    // Programmatically open the dropdown for the screenshot
    const trigger = canvasElement.querySelector('[role="combobox"]') as HTMLButtonElement;
    trigger?.click();
  },
};
