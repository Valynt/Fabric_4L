/**
 * EvidenceTab — "What supports the case?"
 *
 * The most trust-heavy view: a provenance ledger where each claim maps back to a
 * source with a confidence and verification status. Prevents the case from
 * becoming a black box.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, GitBranch, ExternalLink } from "lucide-react";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { CenteredLoader } from "@/components/CenteredLoader";
import { ErrorState } from "@/components/states/ErrorState";
import { Btn } from "@/components/ui/fabric";
import { cn } from "@/lib/utils";
import { useEvidenceDecisionMutation } from "@/hooks/useWorkspaceCase";
import {
  ConfidenceBar,
  DetailPanel,
  ScreenHeader,
  Tag,
  WorkspaceEmpty,
} from "../_shared/primitives";
import { VerificationBadge } from "../_shared/badges";
import { useTabLink } from "../_shared/useTabLink";
import { useWorkspaceCaseId, useEvidenceData } from "../_shared/useWorkspaceData";
import type { WorkspaceEvidenceItem } from "../_shared/types";

export default function EvidenceTab() {
  const tabLink = useTabLink();
  const { accountId, caseId, isLoading: caseLoading } = useWorkspaceCaseId();
  const { items: evidence, isLoading, error } = useEvidenceData(caseId);
  const decision = useEvidenceDecisionMutation();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selected = evidence.find((e) => e.id === selectedId) ?? null;

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }
  if (caseLoading || isLoading) {
    return <CenteredLoader message="Loading evidence…" />;
  }
  if (error) {
    return (
      <ErrorState
        title="Failed to load evidence"
        description="The evidence data could not be retrieved."
        error={error}
        fullPage
      />
    );
  }

  const handleDecision = (item: WorkspaceEvidenceItem, value: "accepted" | "rejected") => {
    if (!caseId) return;
    decision.mutate({ evidenceId: item.id, accountId, caseId, decision: value });
  };

  return (
    <div>
      <ScreenHeader
        title="Evidence"
        description="Source-backed provenance for every claim. Each item traces back to a file, quote, transcript, or web source — and shows how confident and verified it is."
      />

      {evidence.length === 0 ? (
        <WorkspaceEmpty
          icon={ShieldCheck}
          title="No evidence yet"
          purpose="This screen prevents Fabric from becoming a black box — it shows exactly why the case says what it says."
          bullets={[
            "Evidence types: CRM field, customer quote, transcript, document, web source, benchmark",
            "Each item records its source location, confidence, and verification status",
            "Attach evidence to the drivers it supports to strengthen the case",
          ]}
        />
      ) : (
        <div className="flex gap-4">
          <div className="flex-1 overflow-hidden rounded-xl border border-border">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-left">
                  <Th>Claim</Th>
                  <Th>Source</Th>
                  <Th>Verification</Th>
                  <Th>Confidence</Th>
                  <Th>In case</Th>
                </tr>
              </thead>
              <tbody>
                {evidence.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => setSelectedId(item.id)}
                    className={cn(
                      "cursor-pointer border-b border-border last:border-0 transition-colors hover:bg-accent/40",
                      selectedId === item.id && "bg-accent/40"
                    )}
                  >
                    <Td>
                      <span className="font-medium text-foreground">{item.claim ?? item.title}</span>
                    </Td>
                    <Td>
                      <span className="vf-text-caption text-muted-foreground">
                        {item.source ?? item.type ?? "—"}
                      </span>
                    </Td>
                    <Td><VerificationBadge state={item.verification} /></Td>
                    <Td><ConfidenceBar value={item.confidence ?? (item.matchScore != null ? item.matchScore / 100 : undefined)} /></Td>
                    <Td>
                      {item.usedInCase ? (
                        <Tag className="bg-success/10 text-success">Yes</Tag>
                      ) : (
                        <Tag>No</Tag>
                      )}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {selected && (
            <DetailPanel
              eyebrow="Evidence provenance"
              title={selected.title}
              onClose={() => setSelectedId(null)}
              footer={
                <div className="flex flex-wrap gap-2">
                  <Btn
                    variant="primary"
                    onClick={() => handleDecision(selected, "accepted")}
                    disabled={decision.isPending || !caseId}
                  >
                    Approve
                  </Btn>
                  <Btn
                    variant="outline"
                    onClick={() => handleDecision(selected, "rejected")}
                    disabled={decision.isPending || !caseId}
                  >
                    Mark weak
                  </Btn>
                  <Link to={tabLink("drivers")}>
                    <Btn variant="ghost">
                      <GitBranch className="mr-1 h-3.5 w-3.5" /> Linked driver
                    </Btn>
                  </Link>
                </div>
              }
            >
              {selected.claim && (
                <Block label="Claim supported">
                  <p className="vf-text-caption text-foreground">{selected.claim}</p>
                </Block>
              )}
              {selected.excerpt && (
                <Block label="Source excerpt">
                  <p className="rounded-md border border-border bg-muted/30 p-2 vf-text-caption italic text-foreground">
                    “{selected.excerpt}”
                  </p>
                </Block>
              )}
              <Block label="Source type">
                <span className="vf-text-caption text-foreground">{selected.source ?? selected.type ?? "—"}</span>
              </Block>
              {selected.sourceLocation && (
                <Block label="Source location">
                  <span className="vf-text-caption text-foreground">{selected.sourceLocation}</span>
                </Block>
              )}
              <Block label="Verification"><VerificationBadge state={selected.verification} /></Block>
              <Block label="Confidence"><ConfidenceBar value={selected.confidence ?? (selected.matchScore != null ? selected.matchScore / 100 : undefined)} /></Block>
              {selected.linkedDriver && (
                <Block label="Linked driver">
                  <span className="vf-text-caption text-foreground">{selected.linkedDriver}</span>
                </Block>
              )}
              <a
                href="#"
                onClick={(e) => e.preventDefault()}
                className="inline-flex items-center gap-1 vf-text-micro font-medium text-primary hover:underline"
              >
                <ExternalLink className="h-3 w-3" /> View source
              </a>
              {decision.isError && (
                <p className="vf-text-micro text-destructive">Could not save your decision. Try again.</p>
              )}
            </DetailPanel>
          )}
        </div>
      )}
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-4 py-2.5 vf-text-micro font-medium uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

function Td({ children }: { children: React.ReactNode }) {
  return <td className="px-4 py-3 align-middle vf-text-caption">{children}</td>;
}

function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="vf-text-micro font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
      <div className="mt-1">{children}</div>
    </div>
  );
}
