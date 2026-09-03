/**
 * Value Studio (mission-led) — analytics event names (contract §14).
 *
 * Phase 1 emits through the feature logger only: the consent and
 * product-analytics policy gate (contract §14 closing note) is not yet wired,
 * so these events are NOT sent to a product-analytics backend in this slice.
 * Payloads exclude evidence text, prompts, personal data, and model payloads.
 */

import { createFeatureLogger } from "@/lib/telemetry";

const logger = createFeatureLogger("value-studio-mission");

export const VALUE_STUDIO_EVENTS = {
  viewed: "value_studio_viewed",
  lensChanged: "lens_changed",
  decisionRailOpened: "decision_rail_opened",
  decisionIntentPreviewed: "decision_intent_previewed",
  evidenceOpened: "evidence_opened",
  steerFloOpened: "steer_flo_opened",
  activityEventExpanded: "activity_event_expanded",
  generativeUiFallbackUsed: "generated_ui_fallback_used",
} as const;

export type ValueStudioEventName =
  (typeof VALUE_STUDIO_EVENTS)[keyof typeof VALUE_STUDIO_EVENTS];

export function trackValueStudioEvent(
  name: ValueStudioEventName,
  payload: Record<string, string | number>,
): void {
  logger.info("analytics-event", { event: name, ...payload });
}
