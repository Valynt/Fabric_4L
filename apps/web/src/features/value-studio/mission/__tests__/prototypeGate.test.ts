/**
 * Prototype gating (P1a): the mission-led route is hidden from navigation and
 * guarded at the router unless its prototype flag is enabled; the ?fixture=
 * selector is a dev/test-only affordance.
 *
 * In the vitest environment the prototype is enabled (non-production build),
 * which is exactly the build-time contract these tests assert.
 */

import { describe, expect, it } from "vitest";

import { NAV_SCHEMA, isNavNodeEnabled, type NavSchemaNode } from "@/navigation/navSchema";

import {
  isValueStudioFixtureSelectorEnabled,
  isValueStudioMissionPrototypeEnabled,
} from "../prototype";

function findNavNode(nodes: NavSchemaNode[], id: string): NavSchemaNode | null {
  for (const node of nodes) {
    if (node.id === id) return node;
    if (node.children) {
      const hit = findNavNode(node.children, id);
      if (hit) return hit;
    }
  }
  return null;
}

describe("value studio mission prototype gate", () => {
  it("marks the mission child as prototypeOnly in NAV_SCHEMA", () => {
    const mission = findNavNode(NAV_SCHEMA, "studio-mission");
    expect(mission).not.toBeNull();
    expect(mission?.prototypeOnly).toBe(true);
  });

  it("gates a prototypeOnly node on its flag", () => {
    const mission = findNavNode(NAV_SCHEMA, "studio-mission");
    expect(isNavNodeEnabled(mission as NavSchemaNode)).toBe(
      isValueStudioMissionPrototypeEnabled,
    );
  });

  it("does not gate ordinary nodes", () => {
    const actionPlan = findNavNode(NAV_SCHEMA, "studio-action-plan");
    expect(actionPlan?.prototypeOnly).toBeUndefined();
    expect(isNavNodeEnabled(actionPlan as NavSchemaNode)).toBe(true);
  });

  it("enables the prototype in non-production builds", () => {
    // vitest is never a production build.
    expect(isValueStudioMissionPrototypeEnabled).toBe(true);
    expect(isValueStudioFixtureSelectorEnabled).toBe(true);
  });
});
