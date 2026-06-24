import { PageShell } from "@/components";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useNavigation } from "@/hooks/useNavigation";
import { ShieldX } from "lucide-react";

export default function ForbiddenPage() {
  const { navigateToHome } = useNavigation();

  return (
    <PageShell>
      <div className="mx-auto flex h-full w-full max-w-md items-center justify-center px-4 py-12">
        <Card className="w-full">
          <CardHeader className="text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
              <ShieldX className="h-6 w-6 text-destructive" />
            </div>
            <CardTitle className="mt-4 text-lg">Permission denied</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-center">
            <p className="text-sm text-muted-foreground">
              You do not have access to this resource. If you believe this is a mistake, contact your workspace administrator.
            </p>
            <Button onClick={navigateToHome} variant="outline" className="w-full">
              Return home
            </Button>
          </CardContent>
        </Card>
      </div>
    </PageShell>
  );
}
