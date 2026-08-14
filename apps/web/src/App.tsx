import { RouterProvider } from "react-router-dom";
import { MotionConfig } from "framer-motion";
import { ErrorBoundary } from "@/components";
import { OfflineBanner } from "@/components/OfflineBanner";
import { Toaster } from "@/components/ui/sonner";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { AuthProvider } from "@/contexts/AuthContext";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ClerkAuthBridge } from "@/auth/ClerkAuthBridge";
import { AuthorizationProvider } from "@/auth/AuthorizationProvider";
import { router } from "./shell/router";

export default function App() {
  return (
    <ErrorBoundary>
      <MotionConfig reducedMotion="user">
        <ThemeProvider defaultTheme="light" switchable>
          <AuthProvider>
            <TooltipProvider>
              <OfflineBanner />
              <ClerkAuthBridge>
                <AuthorizationProvider>
                  <Toaster />
                  <RouterProvider router={router} />
                </AuthorizationProvider>
              </ClerkAuthBridge>
            </TooltipProvider>
          </AuthProvider>
        </ThemeProvider>
      </MotionConfig>
    </ErrorBoundary>
  );
}
