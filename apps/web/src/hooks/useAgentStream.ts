/**
 * Suggested-action helpers originally part of the legacy `useAgentStream` hook.
 *
 * `getDefaultSuggestedActions` is still consumed by `useAgentEvents` from `@/agui`,
 * so this module is retained as a shared utility. The `useAgentStream` hook itself
 * has been removed; prefer `useAgentEvents` for new code.
 */
import type { AgentAction } from "@/components/workspace/RightRail";

// ── Suggested Actions by Tab ─────────────────────────────────────────────────

export function getDefaultSuggestedActions(
  activeTab: string,
  sendMessage?: (input: string) => void,
): AgentAction[] {
  const send = sendMessage ?? (() => {});
  switch (activeTab) {
    case "signals":
      return [
        { label: "Generate value driver tree", onClick: () => send("Generate a value driver tree from the current signals") },
        { label: "Summarize evidence", onClick: () => send("Summarize the evidence for the top signals") },
        { label: "Draft action plan", onClick: () => send("Draft an action plan based on these signals") },
        { label: "Compare all signals", onClick: () => send("Compare all signals by confidence and impact") },
      ];
    case "drivers":
      return [
        { label: "Map to product capabilities", onClick: () => send("Map these drivers to our product capabilities") },
        { label: "Find missing drivers", onClick: () => send("Are there any missing drivers we should consider?") },
        { label: "Prioritize by impact", onClick: () => send("Prioritize the drivers by estimated business impact") },
      ];
    case "evidence":
      return [
        { label: "Find more evidence", onClick: () => send("Find additional evidence to support our claims") },
        { label: "Audit weak claims", onClick: () => send("Audit the claims and flag any that need stronger evidence") },
        { label: "Export evidence summary", onClick: () => send("Create an evidence summary I can export") },
      ];
    case "stakeholders":
      return [
        { label: "Suggest messaging angles", onClick: () => send("Suggest messaging angles for each stakeholder") },
        { label: "Identify missing buyers", onClick: () => send("Identify any missing buyer personas we should engage") },
        { label: "Map influence network", onClick: () => send("Map the influence network among these stakeholders") },
      ];
    case "action-plan":
      return [
        { label: "Strengthen proof points", onClick: () => send("Strengthen the proof points in this action plan") },
        { label: "Re-prioritize recommendations", onClick: () => send("Re-prioritize the recommendations by urgency") },
        { label: "Add custom recommendation", onClick: () => send("Suggest a custom recommendation for this account") },
      ];
    case "value-model":
      return [
        { label: "Run sensitivity analysis", onClick: () => send("Run a sensitivity analysis on the value model") },
        { label: "Compare scenarios", onClick: () => send("Compare the optimistic, pessimistic, and base case scenarios") },
        { label: "Validate assumptions", onClick: () => send("Validate the key assumptions in this value model") },
      ];
    case "narrative":
      return [
        { label: "Adjust for CFO audience", onClick: () => send("Adjust this narrative for a CFO audience") },
        { label: "Shorten executive summary", onClick: () => send("Shorten the executive summary to under 100 words") },
        { label: "Add competitive positioning", onClick: () => send("Add competitive positioning to the narrative") },
      ];
    default:
      return [];
  }
}
