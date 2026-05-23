import { FormEvent, useState } from 'react';
import { CheckCircle2, Loader2, Plus, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/states';
import { useCreateTask, useTasks, useUpdateTask, type TaskRecord } from '@/hooks/useTasks';
import { PageHeader, Btn, StatusBadge } from "@/components/ui/fabric";
import { safeAsync } from '@/lib/async';
import { toast } from 'sonner';

function TaskStatusBadge({ status }: { status: TaskRecord['status'] }) {
  if (status === 'completed') return <StatusBadge status="completed" />;
  if (status === 'in_progress') return <StatusBadge status="processing" />;
  return <StatusBadge status="pending" />;
}

export default function TasksPage() {
  const [title, setTitle] = useState('');
  const [assignee, setAssignee] = useState('Avery Stone');
  const [stage, setStage] = useState('evidence');
  const [accountId, setAccountId] = useState('');

  const tasks = useTasks();
  const createTask = useCreateTask();
  const updateTask = useUpdateTask();

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedTitle = title.trim();
    if (!trimmedTitle) return;
    try {
      await createTask.mutateAsync({
        title: trimmedTitle,
        assignee: assignee.trim() || undefined,
        stage: stage.trim() || undefined,
        account_id: accountId.trim() || undefined,
      });
      setTitle('');
    } catch {
      toast.error('Failed to create task. Please try again.');
    }
  };

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-5xl px-6 py-8">
        <PageHeader
          title="Tasks"
          subtitle="Create, assign, complete, and reload tenant-scoped workflow tasks."
          actions={
            <Btn variant="outline" onClick={() => safeAsync(tasks.refetch(), "tasks.refetch")} disabled={tasks.isFetching}>
              {tasks.isFetching ? <Loader2 size={14} className="mr-1.5 animate-spin" /> : <RefreshCw size={14} className="mr-1.5" />}
              Refresh
            </Btn>
          }
        />

        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="text-base">Create Task</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="grid gap-4 md:grid-cols-[1fr_180px_160px_auto]" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <Label htmlFor="task-title">Task title</Label>
                <Input
                  id="task-title"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="Attach benchmark source"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="task-assignee">Owner</Label>
                <Input id="task-assignee" value={assignee} onChange={(event) => setAssignee(event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="task-stage">Stage</Label>
                <Input id="task-stage" value={stage} onChange={(event) => setStage(event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="task-account">Account ID</Label>
                <Input
                  id="task-account"
                  value={accountId}
                  onChange={(event) => setAccountId(event.target.value)}
                  placeholder="Optional"
                />
              </div>
              <div className="md:col-span-4">
                <Button type="submit" disabled={createTask.isPending || !title.trim()}>
                  {createTask.isPending ? <Loader2 size={14} className="mr-1.5 animate-spin" /> : <Plus size={14} className="mr-1.5" />}
                  Create Task
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <section className="mt-6 space-y-3" aria-label="Persisted tasks">
          {tasks.isLoading ? (
            <Card>
              <CardContent className="py-8 text-sm text-muted-foreground">Loading tasks...</CardContent>
            </Card>
          ) : tasks.isError ? (
            <Card>
              <CardContent className="py-8 text-sm text-destructive">Unable to load tasks.</CardContent>
            </Card>
          ) : tasks.data?.items.length ? (
            tasks.data.items.map((task) => (
              <Card key={task.id}>
                <CardContent className="flex flex-col gap-3 py-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-sm font-semibold">{task.title}</h2>
                      <TaskStatusBadge status={task.status} />
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Owner: {task.assignee || 'Unassigned'} · Stage: {task.stage || 'None'}
                      {task.account_id ? ` · Account: ${task.account_id}` : ''}
                    </p>
                  </div>
                  <Btn
                    variant="outline"
                    disabled={task.status === 'completed' || updateTask.isPending}
                    onClick={() => updateTask.mutate({ taskId: task.id, status: 'completed' })}
                  >
                    <CheckCircle2 size={14} className="mr-1.5" />
                    {task.status === 'completed' ? 'Completed' : 'Mark Complete'}
                  </Btn>
                </CardContent>
              </Card>
            ))
          ) : (
            <EmptyState
              title="No tasks yet"
              description="Create a task to prove the workflow persists through the backend and survives reload."
              icon={CheckCircle2}
            />
          )}
        </section>
      </div>
    </main>
  );
}
