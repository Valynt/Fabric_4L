import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle, Home } from "lucide-react";
import { useNavigation } from "@/hooks";
import { useI18n } from "@/i18n";

export default function NotFound() {
  const { t } = useI18n();
  const { navigateTo } = useNavigation();

  const handleGoHome = () => {
    navigateTo('root');
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-muted to-muted/80">
      <Card className="w-full max-w-lg mx-4 shadow-lg border-0 bg-card/80 backdrop-blur-sm">
        <CardContent className="pt-8 pb-8 text-center">
          <div className="flex justify-center mb-6">
            <div className="relative">
              <div className="absolute inset-0 bg-destructive/10 rounded-full animate-pulse" />
              <AlertCircle className="relative h-16 w-16 text-destructive" />
            </div>
          </div>

          <h1 className="text-4xl font-bold text-foreground mb-2">404</h1>

          <h2 className="text-xl font-semibold text-foreground mb-4">
            {t("notFound.title")}
          </h2>

          <p className="text-muted-foreground mb-8 leading-relaxed">
            {t("notFound.message")}
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button
              onClick={handleGoHome}
              className="bg-primary hover:bg-primary/90 text-primary-foreground px-6 py-2.5 rounded-lg transition-all duration-200 shadow-md hover:shadow-lg"
            >
              <Home className="w-4 h-4 mr-2" />
              {t("notFound.cta")}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
