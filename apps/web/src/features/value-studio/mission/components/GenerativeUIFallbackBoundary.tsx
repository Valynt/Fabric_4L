/**
 * Value Studio (mission-led) — generative-UI fallback boundary (contract §11.4,
 * FE-SUC-010).
 *
 * Error boundary around surfaces that may be backed by generative UI in later
 * phases. On failure it reports through telemetry (`captureException`) and the
 * §14 fallback event, then renders ONLY the static fallback notice — the
 * broken subtree is never partially rendered (FE-SUC-011).
 */

import { Component, type ReactNode } from "react";
import { captureException } from "@/lib/telemetry";
import { VALUE_STUDIO_EVENTS, trackValueStudioEvent } from "../analyticsEvents";
import { StaticGenerativeUIFallback } from "./StaticGenerativeUIFallback";

export interface GenerativeUIFallbackBoundaryProps {
  readonly componentName: string;
  readonly children: ReactNode;
}

interface GenerativeUIFallbackBoundaryState {
  readonly failed: boolean;
}

export class GenerativeUIFallbackBoundary extends Component<
  GenerativeUIFallbackBoundaryProps,
  GenerativeUIFallbackBoundaryState
> {
  override state: GenerativeUIFallbackBoundaryState = { failed: false };

  static getDerivedStateFromError(): GenerativeUIFallbackBoundaryState {
    return { failed: true };
  }

  override componentDidCatch(error: Error): void {
    captureException(error, {
      feature: "value-studio-mission",
      component: this.props.componentName,
    });
    trackValueStudioEvent(VALUE_STUDIO_EVENTS.generativeUiFallbackUsed, {
      component: this.props.componentName,
      failureClass: "render_error",
    });
  }

  override render(): ReactNode {
    if (this.state.failed) {
      return (
        <StaticGenerativeUIFallback
          componentName={this.props.componentName}
          failureClass="render_error"
        />
      );
    }
    return this.props.children;
  }
}
