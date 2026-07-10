import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { axe, toHaveNoViolations } from "jest-axe";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SkipLink } from "@/components/ui/skip-link";
import { EmptyState } from "@/components/states/EmptyState";
import { VirtualList } from "@/components/ui/virtual-list";
import { OptimizedImage } from "@/components/ui/optimized-image";
import { DataTable } from "@/components/ui/fabric/DataTable";

expect.extend(toHaveNoViolations);

describe("component accessibility smoke tests", () => {
  it("button and input expose accessible roles and labels", () => {
    render(
      <main>
        <h1>Accessibility fixture</h1>
        <label htmlFor="customer-name">Customer name</label>
        <Input id="customer-name" placeholder="Type a name" />
        <Button type="button">Save</Button>
      </main>,
    );

    expect(screen.getByRole("heading", { name: /accessibility fixture/i })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /customer name/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save/i })).toBeInTheDocument();
  });

  it("select dropdown exposes accessible roles", () => {
    render(
      <main>
        <label htmlFor="value-driver">Value Driver</label>
        <Select>
          <SelectTrigger id="value-driver">
            <SelectValue placeholder="Select a value driver" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="revenue_retention">Revenue Retention</SelectItem>
            <SelectItem value="cost_reduction">Cost Reduction</SelectItem>
          </SelectContent>
        </Select>
      </main>,
    );

    expect(screen.getByRole("combobox", { name: /value driver/i })).toBeInTheDocument();
  });

  it("buttons have accessible names", () => {
    render(
      <main>
        <Button variant="primary">Submit Form</Button>
        <Button variant="secondary" aria-label="Cancel action">Cancel</Button>
      </main>,
    );

    expect(screen.getByRole("button", { name: /submit form/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel action/i })).toBeInTheDocument();
  });

  it("form controls have associated labels", () => {
    render(
      <main>
        <form>
          <label htmlFor="email">Email address</label>
          <Input id="email" type="email" placeholder="user@example.com" />
          <label htmlFor="password">Password</label>
          <Input id="password" type="password" />
        </form>
      </main>,
    );

    expect(screen.getByRole("textbox", { name: /email address/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("icon-only button has aria-label and passes axe", async () => {
    const { container } = render(
      <Button size="icon" aria-label="Close dialog">
        <span aria-hidden>×</span>
      </Button>,
    );

    expect(screen.getByRole("button", { name: /close dialog/i })).toBeInTheDocument();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("input with label passes axe", async () => {
    const { container } = render(
      <div>
        <Label htmlFor="email">Email address</Label>
        <Input id="email" type="email" placeholder="you@example.com" />
      </div>,
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("dialog has accessible title and passes axe", async () => {
    const { container } = render(
      <Dialog open>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Action</DialogTitle>
            <DialogDescription>
              Are you sure you want to proceed?
            </DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>,
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /confirm action/i })).toBeInTheDocument();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("select has listbox role and passes axe", async () => {
    const { container } = render(
      <Select>
        <SelectTrigger aria-label="Choose a fruit">
          <SelectValue placeholder="Select a fruit" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="apple">Apple</SelectItem>
          <SelectItem value="banana">Banana</SelectItem>
        </SelectContent>
      </Select>,
    );

    expect(screen.getByRole("combobox")).toBeInTheDocument();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("skip link is focusable and passes axe", async () => {
    const { container } = render(
      <>
        <SkipLink targetId="content" />
        <main id="content" tabIndex={-1}>
          <h1>Page content</h1>
        </main>
      </>,
    );

    const skipLink = screen.getByRole("link", { name: /skip to content/i });
    expect(skipLink).toBeInTheDocument();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("empty state passes axe", async () => {
    const { container } = render(
      <EmptyState
        title="No items"
        description="There are no items to display."
        action={<Button>Create item</Button>}
      />,
    );

    expect(screen.getByRole("heading", { name: /no items/i })).toBeInTheDocument();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  // ── P2/P3 Fix Accessibility Tests ─────────────────────────────────────────

  it("virtual list single-column passes axe", async () => {
    const { container } = render(
      <div style={{ height: "200px" }}>
        <VirtualList
          items={[
            { id: "1", label: "First" },
            { id: "2", label: "Second" },
            { id: "3", label: "Third" },
          ]}
          estimateSize={50}
          renderItem={(item) => <div>{item.label}</div>}
        />
      </div>
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("virtual list multi-column grid passes axe", async () => {
    const { container } = render(
      <div style={{ height: "200px" }}>
        <VirtualList
          items={[
            { id: "1", label: "A" },
            { id: "2", label: "B" },
            { id: "3", label: "C" },
          ]}
          estimateSize={80}
          columns={3}
          renderItem={(item) => <div>{item.label}</div>}
        />
      </div>
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("optimized image has alt text and passes axe", async () => {
    const { container } = render(
      <OptimizedImage
        src="/test-image.png"
        alt="Test description"
        className="w-10 h-10"
      />
    );

    const img = screen.getByRole("img", { name: /test description/i });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("loading", "lazy");
    expect(img).toHaveAttribute("decoding", "async");
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("variable insert chip passes axe", async () => {
    const { container } = render(
      <div>
        <div
          role="button"
          tabIndex={0}
          aria-label="Insert variable revenue"
          title="Insert revenue into formula"
          onClick={() => {}}
          onKeyDown={() => {}}
        >
          <span>revenue</span>
          <span>api</span>
        </div>
      </div>
    );

    const chip = screen.getByRole("button", { name: /insert variable revenue/i });
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveAttribute("tabIndex", "0");
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("shadcn select in filter bar passes axe", async () => {
    const { container } = render(
      <div>
        <span id="status-label">Status</span>
        <Select>
          <SelectTrigger aria-labelledby="status-label">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
          </SelectContent>
        </Select>
      </div>
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("clickable data table rows activate with Enter and Space", async () => {
    const user = userEvent.setup();
    const selected: string[] = [];

    render(
      <DataTable
        data={[{ id: "acme", name: "Acme Corp", status: "Active" }]}
        columns={[
          { key: "name", header: "Account" },
          { key: "status", header: "Status" },
        ]}
        keyExtractor={(item) => item.id}
        onRowClick={(item) => selected.push(item.id)}
      />,
    );

    const row = screen.getByRole("button", { name: /acme corp active/i });
    row.focus();
    expect(row).toHaveFocus();

    await user.keyboard("{Enter}");
    await user.keyboard(" ");

    expect(selected).toEqual(["acme", "acme"]);
  });

  it("dialog trigger is keyboard reachable and Escape returns focus", async () => {
    const user = userEvent.setup();

    render(
      <Dialog>
        <DialogTrigger asChild>
          <Button type="button">Open governance review</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Governance review</DialogTitle>
            <DialogDescription>Review pending policy evidence.</DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>,
    );

    const trigger = screen.getByRole("button", { name: /open governance review/i });
    trigger.focus();
    await user.keyboard("{Enter}");

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(trigger).toHaveFocus();
  });
});
