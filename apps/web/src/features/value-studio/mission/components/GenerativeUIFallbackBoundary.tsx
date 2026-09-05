/**
 * Value Studio (mission-led) — generative-UI fallback boundary (contract §11.4,
 * FE-SUC-010).
 *
 * Error boundary around surfaces that may be backed by generative UI in later
 * phases. On failure it reports through telemetry (`captureException`) and the
 * §14 fallback event, then renders ONLY the static fallback notice — the
 * broken subtree is never partially rendered (FE-SUC-011).
 *
 * Recovery: the failed state is NOT latched forever. Callers pass a `resetKey`
 * identifying the rendered projection; when the key changes (refetch, fixture
 * switch, new projection version), the boundary resets and retries the child.
 */

import { Component, type ReactNode } from "react";
import { captureException } from "@/lib/telemetry";
import { VALUE_STUDIO_EVENTS, trackValueStudioEvent } from "../analyticsEvents";
import { StaticGenerativeUIFallback } from "./StaticGenerativeUIFallback";

export interface GenerativeUIFallbackBoundaryProps {
  readonly componentName: string;
  /** Identity of the content being rendered. A change resets a latched
   *  failure so a recovered projection is not stuck behind the fallback. */
  readonly resetKey?: string;
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

  override componentDidUpdate(
    prevProps: GenerativeUIFallbackBoundaryProps,
  ): void {
    if (prevProps.resetKey !== this.props.resetKey && this.state.failed) {
      this.setState({ failed: false });
    }
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
