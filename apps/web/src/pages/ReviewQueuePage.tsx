import { useState } from "react";
import { useParams } from "react-router-dom";
import { CheckCircle, XCircle, MessageCircle, Clock, Send, Inbox } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { useAccountContextStore } from "@/stores/accountContextStore";
import {
  useReviewRequests,
  useCreateReviewRequest,
  useUpdateReviewRequest,
  useAddReviewComment,
} from "@/hooks/useGates";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader } from "@/components/ui/fabric";
import { PageShell } from "@/components";
import { ErrorState, EmptyState } from "@/components/states";

export default function ReviewQueuePage() {
  const { accountId: paramAccountId } = useParams<{ accountId: string }>();
  const selectedAccountId = useAccountContextStore((s) => s.selectedAccountId);
  const accountId = paramAccountId || selectedAccountId;
  const [commentText, setCommentText] = useState("");
  const [activeReviewId, setActiveReviewId] = useState<string | null>(null);

  const {
    data: reviews,
    isLoading,
    isError,
    error,
  } = useReviewRequests(accountId);
  const createReview = useCreateReviewRequest();
  const updateReview = useUpdateReviewRequest();
  const addComment = useAddReviewComment();

  if (!accountId) {
    return (
      <PageShell className="max-w-5xl">
        <div className="bg-warning/10 border border-warning/20 rounded-lg p-4 text-warning">
          No account selected. Please select an account to view its review queue.
        </div>
      </PageShell>
    );
  }

  if (isLoading) {
    return (
      <PageShell className="max-w-5xl">
        <div className="space-y-4">
          <Skeleton className="h-8 w-64" />
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      </PageShell>
    );
  }

  if (isError) {
    return (
      <PageShell className="max-w-5xl">
        <ErrorState
          title="Failed to load review queue"
          description={error?.message || "Could not load review requests for this account."}
          error={error}
        />
      </PageShell>
    );
  }

  const handleSubmitForReview = () => {
    createReview.mutate({ accountId, scope: "business_case" });
  };

  const handleStatusChange = (reviewId: string, status: string) => {
    updateReview.mutate({ accountId, reviewId, status });
  };

  const handleAddComment = () => {
    if (!activeReviewId || !commentText.trim()) return;
    addComment.mutate({
      accountId,
      reviewId: activeReviewId,
      comment: {
        id: crypto.randomUUID(),
        text: commentText.trim(),
        author_id: "current-user",
      },
    });
    setCommentText("");
  };

  return (
    <PageShell className="max-w-5xl">
      <PageHeader title="Review Queue" subtitle={`Account: ${accountId}`} />

      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {reviews?.length ?? 0} review request{(reviews?.length ?? 0) !== 1 ? "s" : ""}
        </p>
        <button
          onClick={handleSubmitForReview}
          disabled={createReview.isPending}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
          Submit for Review
        </button>
      </div>

      <div className="space-y-4">
        {reviews?.map((review) => (
          <SectionCard key={review.id} title={`Review: ${review.scope}`}>
            <div className="flex items-center gap-2 mb-2">
              {review.status === "pending" && (
                <Clock className="h-4 w-4 text-warning" />
              )}
              {review.status === "approved" && (
                <CheckCircle className="h-4 w-4 text-success" />
              )}
              {review.status === "rejected" && (
                <XCircle className="h-4 w-4 text-destructive" />
              )}
              <span className="text-sm font-medium capitalize">{review.status}</span>
              <span className="text-xs text-muted-foreground ml-auto">
                {new Date(review.created_at).toLocaleDateString()}
              </span>
            </div>

            {review.comments.length > 0 && (
              <div className="space-y-2 mb-3">
                {review.comments.map((c) => (
                  <div key={c.id} className="rounded bg-muted p-2 text-sm">
                    <p className="text-xs text-muted-foreground mb-1">{c.author_id}</p>
                    <p>{c.text}</p>
                  </div>
                ))}
              </div>
            )}

            {review.status === "pending" && (
              <div className="flex items-center gap-2 mb-3">
                <button
                  onClick={() => handleStatusChange(review.id, "approved")}
                  className="inline-flex items-center gap-1 rounded-md bg-success px-3 py-1.5 text-xs font-medium text-success-foreground hover:bg-success/90"
                >
                  <CheckCircle className="h-3 w-3" /> Approve
                </button>
                <button
                  onClick={() => handleStatusChange(review.id, "changes_requested")}
                  className="inline-flex items-center gap-1 rounded-md bg-warning px-3 py-1.5 text-xs font-medium text-warning-foreground hover:bg-warning/90"
                >
                  <MessageCircle className="h-3 w-3" /> Request Changes
                </button>
                <button
                  onClick={() => handleStatusChange(review.id, "rejected")}
                  className="inline-flex items-center gap-1 rounded-md bg-destructive px-3 py-1.5 text-xs font-medium text-destructive-foreground hover:bg-destructive/90"
                >
                  <XCircle className="h-3 w-3" /> Reject
                </button>
              </div>
            )}

            {review.status === "pending" && (
              <div className="flex items-center gap-2">
                <Input
                  type="text"
                  value={activeReviewId === review.id ? commentText : ""}
                  onChange={(e) => {
                    setActiveReviewId(review.id);
                    setCommentText(e.target.value);
                  }}
                  placeholder="Add a comment..."
                  className="flex-1"
                />
                <button
                  onClick={handleAddComment}
                  disabled={addComment.isPending || !commentText.trim()}
                  className="rounded-md bg-secondary px-3 py-1.5 text-xs font-medium hover:bg-secondary/80 disabled:opacity-50"
                >
                  Comment
                </button>
              </div>
            )}
          </SectionCard>
        ))}

        {(!reviews || reviews.length === 0) && (
          <EmptyState
            icon={Inbox}
            title="No review requests yet"
            description="Submit this account for review to start the approval workflow."
            action={
              <button
                onClick={handleSubmitForReview}
                disabled={createReview.isPending}
                className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
                Submit for Review
              </button>
            }
          />
        )}
      </div>
    </PageShell>
  );
}
