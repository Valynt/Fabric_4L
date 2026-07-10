/**
 * Card Stories — shadcn/ui
 * ==========================
 *
 * Covers Card composition patterns:
 *   - Simple card with content
 *   - Card with header, content, and footer
 *   - Card with interactive elements (buttons, links)
 *   - Card skeleton / loading state
 *   - Stacked card layout
 *
 * DESIGN.md § Components: "Provides reusable Card primitive"
 */

import type { Meta, StoryObj } from "@storybook/react";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Bell, CheckCircle, AlertTriangle, ArrowRight } from "lucide-react";

// ---------------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------------

const meta: Meta<typeof Card> = {
  title: "UI/Card",
  component: Card,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
  },
  argTypes: {
    className: {
      control: "text",
      description: "Additional Tailwind classes",
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

// ---------------------------------------------------------------------------
// Basic variants
// ---------------------------------------------------------------------------

export const Simple: Story = {
  render: () => (
    <Card className="w-[350px]">
      <CardContent className="pt-6">
        <p className="text-sm text-muted-foreground">
          A simple card with only content. Useful for alerts, callouts, or
          standalone information panels.
        </p>
      </CardContent>
    </Card>
  ),
};

export const WithHeader: Story = {
  render: () => (
    <Card className="w-[350px]">
      <CardHeader>
        <CardTitle>Notification Preferences</CardTitle>
        <CardDescription>
          Choose how you want to be notified about account activity.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-3">
          <Bell className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm">Push notifications are enabled</span>
        </div>
      </CardContent>
    </Card>
  ),
};

export const WithFooter: Story = {
  render: () => (
    <Card className="w-[350px]">
      <CardHeader>
        <CardTitle>Confirm Action</CardTitle>
        <CardDescription>
          This will permanently delete the selected workflow.
        </CardDescription>
      </CardHeader>
      <CardFooter className="flex justify-between">
        <Button variant="ghost">Cancel</Button>
        <Button variant="destructive">Delete</Button>
      </CardFooter>
    </Card>
  ),
};

export const Complete: Story = {
  render: () => (
    <Card className="w-[380px]">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>Workflow Status</CardTitle>
            <CardDescription>Last updated 2 minutes ago</CardDescription>
          </div>
          <Badge variant="secondary">Running</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Stage</span>
            <span>Data Extraction</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span>67%</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">ETA</span>
            <span>~4 min</span>
          </div>
        </div>
      </CardContent>
      <CardFooter className="flex gap-2">
        <Button variant="outline" size="sm" className="flex-1">
          View Logs
        </Button>
        <Button size="sm" className="flex-1">
          Details <ArrowRight className="ml-2 h-3 w-3" />
        </Button>
      </CardFooter>
    </Card>
  ),
};

// ---------------------------------------------------------------------------
// Status variants
// ---------------------------------------------------------------------------

export const Success: Story = {
  render: () => (
    <Card className="w-[350px] border-green-200 bg-green-50/50 dark:border-green-900 dark:bg-green-950/20">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
          <CardTitle className="text-green-800 dark:text-green-200">
            All Clear
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-green-700 dark:text-green-300">
          All workflows completed successfully. No action required.
        </p>
      </CardContent>
    </Card>
  ),
};

export const Warning: Story = {
  render: () => (
    <Card className="w-[350px] border-yellow-200 bg-yellow-50/50 dark:border-yellow-900 dark:bg-yellow-950/20">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
          <CardTitle className="text-yellow-800 dark:text-yellow-200">
            Attention Needed
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-yellow-700 dark:text-yellow-300">
          One workflow has been running longer than expected. Review the logs
          for details.
        </p>
      </CardContent>
      <CardFooter>
        <Button variant="outline" size="sm">
          View Details
        </Button>
      </CardFooter>
    </Card>
  ),
};

// ---------------------------------------------------------------------------
// Loading state
// ---------------------------------------------------------------------------

export const Loading: Story = {
  render: () => (
    <Card className="w-[350px]">
      <CardHeader>
        <Skeleton className="h-5 w-[200px]" />
        <Skeleton className="h-4 w-[280px]" />
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-[90%]" />
        <Skeleton className="h-4 w-[80%]" />
      </CardContent>
      <CardFooter>
        <Skeleton className="h-9 w-[100px]" />
      </CardFooter>
    </Card>
  ),
};

// ---------------------------------------------------------------------------
// Composition: Card list
// ---------------------------------------------------------------------------

export const CardList: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <div className="flex flex-col gap-3 w-[400px]">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Data Ingestion</CardTitle>
        </CardHeader>
        <CardContent className="pb-2">
          <p className="text-sm text-muted-foreground">
            Scheduled ingestion from CRM pipeline
          </p>
        </CardContent>
        <CardFooter>
          <Badge variant="outline">Daily</Badge>
        </CardFooter>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Entity Extraction</CardTitle>
        </CardHeader>
        <CardContent className="pb-2">
          <p className="text-sm text-muted-foreground">
            NLP processing of uploaded documents
          </p>
        </CardContent>
        <CardFooter>
          <Badge variant="outline">On-demand</Badge>
        </CardFooter>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Knowledge Graph Sync</CardTitle>
        </CardHeader>
        <CardContent className="pb-2">
          <p className="text-sm text-muted-foreground">
            Incremental graph updates from verified extractions
          </p>
        </CardContent>
        <CardFooter>
          <Badge variant="outline">Real-time</Badge>
        </CardFooter>
      </Card>
    </div>
  ),
};
