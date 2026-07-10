/**
 * Button Stories — shadcn/ui
 * ============================
 *
 * Covers all visual variants of the shadcn/ui Button component:
 *   - Variants: default, destructive, outline, ghost, link
 *   - Sizes: default, sm, lg, icon
 *   - States: loading, disabled
 *   - With icons (leading / trailing)
 *
 * DESIGN.md § Components: "Provides reusable Button primitive"
 * DESIGN.md § Typography: Inter font family for UI text
 */

import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "@/components/ui/button";
import { Loader2, Plus, Trash2, ArrowRight, Check } from "lucide-react";

// ---------------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------------

const meta: Meta<typeof Button> = {
  title: "UI/Button",
  component: Button,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    a11y: {
      // Buttons must have accessible names
      test: "error",
    },
  },
  argTypes: {
    variant: {
      control: "select",
      options: ["default", "destructive", "outline", "ghost", "link"],
      description: "Visual style variant",
      table: {
        type: { summary: "string" },
        defaultValue: { summary: "default" },
      },
    },
    size: {
      control: "select",
      options: ["default", "sm", "lg", "icon"],
      description: "Size preset",
      table: {
        type: { summary: "string" },
        defaultValue: { summary: "default" },
      },
    },
    asChild: {
      control: "boolean",
      description: "Render as child element (polymorphic)",
    },
    disabled: {
      control: "boolean",
      description: "Disabled state",
    },
    children: {
      control: "text",
      description: "Button label or content",
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

// ---------------------------------------------------------------------------
// Variants
// ---------------------------------------------------------------------------

export const Default: Story = {
  args: {
    children: "Button",
    variant: "default",
  },
};

export const Destructive: Story = {
  args: {
    children: "Delete",
    variant: "destructive",
  },
};

export const Outline: Story = {
  args: {
    children: "Outline",
    variant: "outline",
  },
};

export const Ghost: Story = {
  args: {
    children: "Ghost",
    variant: "ghost",
  },
};

export const Link: Story = {
  args: {
    children: "Link style",
    variant: "link",
  },
};

// ---------------------------------------------------------------------------
// Sizes
// ---------------------------------------------------------------------------

export const Small: Story = {
  args: {
    children: "Small",
    size: "sm",
  },
};

export const Large: Story = {
  args: {
    children: "Large",
    size: "lg",
  },
};

export const Icon: Story = {
  args: {
    size: "icon",
    children: <Plus className="h-4 w-4" />,
  },
};

// ---------------------------------------------------------------------------
// States
// ---------------------------------------------------------------------------

export const Disabled: Story = {
  args: {
    children: "Disabled",
    disabled: true,
  },
};

export const Loading: Story = {
  args: {
    children: (
      <>
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        Saving...
      </>
    ),
    disabled: true,
  },
};

// ---------------------------------------------------------------------------
// With icons
// ---------------------------------------------------------------------------

export const WithLeadingIcon: Story = {
  args: {
    children: (
      <>
        <Plus className="mr-2 h-4 w-4" />
        Add Item
      </>
    ),
  },
};

export const WithTrailingIcon: Story = {
  args: {
    children: (
      <>
        Next
        <ArrowRight className="ml-2 h-4 w-4" />
      </>
    ),
  },
};

export const IconOnly: Story = {
  args: {
    variant: "outline",
    size: "icon",
    children: <Trash2 className="h-4 w-4" />,
    "aria-label": "Delete item",
  },
};

// ---------------------------------------------------------------------------
// Composition: All variants grid
// ---------------------------------------------------------------------------

export const AllVariants: Story = {
  parameters: {
    docs: {
      description: {
        story: "Grid of all Button variants for quick visual scanning.",
      },
    },
    // Disable individual controls for the composition story
    controls: { disable: true },
  },
  render: () => (
    <div className="flex flex-col gap-4 items-start">
      <div className="flex gap-2 flex-wrap">
        <Button variant="default">Default</Button>
        <Button variant="destructive">Destructive</Button>
        <Button variant="outline">Outline</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="link">Link</Button>
      </div>
      <div className="flex gap-2 flex-wrap items-center">
        <Button size="sm">Small</Button>
        <Button size="default">Default</Button>
        <Button size="lg">Large</Button>
        <Button size="icon" aria-label="Add">
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex gap-2 flex-wrap items-center">
        <Button disabled>Disabled</Button>
        <Button disabled>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Loading
        </Button>
      </div>
      <div className="flex gap-2 flex-wrap items-center">
        <Button>
          <Check className="mr-2 h-4 w-4" />
          Confirm
        </Button>
        <Button variant="outline">
          Next <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
        <Button variant="destructive" size="icon" aria-label="Delete">
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  ),
};
