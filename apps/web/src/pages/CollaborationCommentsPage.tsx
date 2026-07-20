import { FormEvent, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Loader2, MessageSquare, RefreshCw, Send } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { EmptyState, LoadingState, ErrorState } from '@/components/states';
import { useComments, useCreateComment } from '@/hooks/useComments';
import { PageHeader, Btn } from "@/components/ui/fabric";
import { Textarea } from '@/components/ui/textarea';
import { safeAsync } from '@/lib/async';

export default function CollaborationCommentsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [subjectType, setSubjectType] = useState(() => searchParams.get('subject_type') || 'account');
  const [subjectId, setSubjectId] = useState(() => searchParams.get('subject_id') || 'general');
  const [accountId, setAccountId] = useState(() => searchParams.get('account_id') || '');
  const [body, setBody] = useState('');

  const filters = {
    subjectType: subjectType.trim() || undefined,
    subjectId: subjectId.trim() || undefined,
    accountId: accountId.trim() || undefined,
  };
  const comments = useComments(filters);
  const createComment = useCreateComment();

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedBody = body.trim();
    const trimmedSubjectType = subjectType.trim();
    const trimmedSubjectId = subjectId.trim();
    if (!trimmedBody || !trimmedSubjectType || !trimmedSubjectId) return;

    await createComment.mutateAsync({
      account_id: accountId.trim() || undefined,
      subject_type: trimmedSubjectType,
      subject_id: trimmedSubjectId,
      body: trimmedBody,
    });
    const nextParams = new URLSearchParams();
    nextParams.set('subject_type', trimmedSubjectType);
    nextParams.set('subject_id', trimmedSubjectId);
    if (accountId.trim()) nextParams.set('account_id', accountId.trim());
    setSearchParams(nextParams, { replace: true });
    setBody('');
  };

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-5xl px-6 py-8">
        <PageHeader
          title="Collaboration Comments"
          subtitle="Create subject-scoped comments through the Layer 4 API and verify reload persistence."
          actions={
            <Btn variant="outline" onClick={() => safeAsync(comments.refetch(), "comments.refetch")} disabled={comments.isFetching}>
              {comments.isFetching ? <Loader2 size={14} className="mr-1.5 animate-spin" /> : <RefreshCw size={14} className="mr-1.5" />}
              Refresh
            </Btn>
          }
        />

        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="text-base">Post Comment</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="grid gap-4 md:grid-cols-[160px_180px_1fr]" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <Label htmlFor="comment-subject-type">Subject type</Label>
                <Input id="comment-subject-type" value={subjectType} onChange={(event) => setSubjectType(event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="comment-subject-id">Subject ID</Label>
                <Input id="comment-subject-id" value={subjectId} onChange={(event) => setSubjectId(event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="comment-account-id">Account ID</Label>
                <Input
                  id="comment-account-id"
                  value={accountId}
                  onChange={(event) => setAccountId(event.target.value)}
                  placeholder="Optional"
                />
              </div>
              <div className="space-y-2 md:col-span-3">
                <Label htmlFor="comment-body">Comment</Label>
                <Textarea
                  id="comment-body"
                  className="min-h-28"
                  value={body}
                  onChange={(event) => setBody(event.target.value)}
                  placeholder="Add review context, evidence notes, or teammate feedback"
                />
              </div>
              <div className="md:col-span-3">
                <Button
                  type="submit"
                  disabled={createComment.isPending || !body.trim() || !subjectType.trim() || !subjectId.trim()}
                >
                  {createComment.isPending ? <Loader2 size={14} className="mr-1.5 animate-spin" /> : <Send size={14} className="mr-1.5" />}
                  Post Comment
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <section className="mt-6 space-y-3" aria-label="Persisted comments">
          {comments.isLoading ? (
            <LoadingState message="Loading comments…" />
          ) : comments.isError ? (
            <ErrorState
              title="Unable to load comments"
              description="The comments feed could not be retrieved. Check your network connection and try again."
              error={comments.error}
              onRetry={() => safeAsync(comments.refetch(), "comments.refetch")}
            />
          ) : comments.data?.items.length ? (
            comments.data.items.map((comment) => (
              <Card key={comment.id}>
                <CardContent className="py-4">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <MessageSquare size={14} />
                    <span>{comment.subject_type}:{comment.subject_id}</span>
                    <span>by {comment.author}</span>
                    {comment.account_id ? <span>Account: {comment.account_id}</span> : null}
                  </div>
                  <p className="mt-2 text-sm text-foreground">{comment.body}</p>
                </CardContent>
              </Card>
            ))
          ) : (
            <EmptyState
              title="No comments yet"
              description="Post a comment to prove collaboration context persists through the backend and survives reload."
              icon={MessageSquare}
            />
          )}
        </section>
      </div>
    </main>
  );
}
