import { FormEvent, useState } from 'react';
import { Bell, CheckCircle2, Loader2, Plus, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/states';
import { useCreateNotification, useMarkNotificationRead, useNotifications } from '@/hooks/useNotifications';
import { PageHeader, Btn, StatusBadge } from "@/components/ui/fabric";
import { safeAsync } from '@/lib/async';
import { toast } from 'sonner';

export default function NotificationsPage() {
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [type, setType] = useState('manual_validation');
  const [accountId, setAccountId] = useState('');

  const notifications = useNotifications();
  const createNotification = useCreateNotification();
  const markRead = useMarkNotificationRead();

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedTitle = title.trim();
    const trimmedMessage = message.trim();
    const trimmedType = type.trim();
    if (!trimmedTitle || !trimmedMessage || !trimmedType) return;

    try {
      await createNotification.mutateAsync({
        type: trimmedType,
        title: trimmedTitle,
        message: trimmedMessage,
        account_id: accountId.trim() || undefined,
        subject_type: 'notification',
      });
      setTitle('');
      setMessage('');
    } catch {
      toast.error('Failed to create notification. Please try again.');
    }
  };

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-5xl px-6 py-8">
        <PageHeader
          title="Notifications"
          subtitle="Persisted in-app feed for workflow events, review reminders, and collaboration updates."
          actions={
            <Btn variant="outline" onClick={() => safeAsync(notifications.refetch(), "notifications.refetch")} disabled={notifications.isFetching}>
              {notifications.isFetching ? <Loader2 size={14} className="mr-1.5 animate-spin" /> : <RefreshCw size={14} className="mr-1.5" />}
              Refresh
            </Btn>
          }
        />

        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="text-base">Create Notification</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="grid gap-4 md:grid-cols-[1fr_180px_180px]" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <Label htmlFor="notification-title">Notification title</Label>
                <Input
                  id="notification-title"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="Review requested"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="notification-type">Type</Label>
                <Input id="notification-type" value={type} onChange={(event) => setType(event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="notification-account">Account ID</Label>
                <Input
                  id="notification-account"
                  value={accountId}
                  onChange={(event) => setAccountId(event.target.value)}
                  placeholder="Optional"
                />
              </div>
              <div className="space-y-2 md:col-span-3">
                <Label htmlFor="notification-message">Message</Label>
                <textarea
                  id="notification-message"
                  className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="Jordan Lee requested review on the business case."
                />
              </div>
              <div className="md:col-span-3">
                <Button
                  type="submit"
                  disabled={createNotification.isPending || !title.trim() || !message.trim() || !type.trim()}
                >
                  {createNotification.isPending ? <Loader2 size={14} className="mr-1.5 animate-spin" /> : <Plus size={14} className="mr-1.5" />}
                  Create Notification
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <section className="mt-6 space-y-3" aria-label="Persisted notifications">
          <div className="text-sm text-muted-foreground">
            Unread notifications: {notifications.data?.unread_count ?? 0}
          </div>
          {notifications.isLoading ? (
            <Card>
              <CardContent className="py-8 text-sm text-muted-foreground">Loading notifications...</CardContent>
            </Card>
          ) : notifications.isError ? (
            <Card>
              <CardContent className="py-8 text-sm text-destructive">Unable to load notifications.</CardContent>
            </Card>
          ) : notifications.data?.items.length ? (
            notifications.data.items.map((notification) => (
              <Card key={notification.id}>
                <CardContent className="flex flex-col gap-3 py-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <Bell size={14} className="text-muted-foreground" />
                      <h2 className="text-sm font-semibold">{notification.title}</h2>
                      <StatusBadge status={notification.read ? 'completed' : 'pending'} />
                    </div>
                    <p className="mt-1 text-sm text-foreground">{notification.message}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Type: {notification.type}
                      {notification.account_id ? ` · Account: ${notification.account_id}` : ''}
                    </p>
                  </div>
                  <Btn
                    variant="outline"
                    disabled={notification.read || markRead.isPending}
                    onClick={async () => {
                      try {
                        await markRead.mutateAsync(notification.id);
                      } catch {
                        toast.error('Failed to mark notification as read. Please try again.');
                      }
                    }}
                  >
                    <CheckCircle2 size={14} className="mr-1.5" />
                    {notification.read ? 'Read' : 'Mark Read'}
                  </Btn>
                </CardContent>
              </Card>
            ))
          ) : (
            <EmptyState
              title="No notifications yet"
              description="Create or trigger a notification to prove the feed persists through the backend and survives reload."
              icon={Bell}
            />
          )}
        </section>
      </div>
    </main>
  );
}
