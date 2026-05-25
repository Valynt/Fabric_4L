import { RouterProvider } from "react-router-dom";
import { ErrorBoundary } from "@/components";
import { Toaster } from "@/components/ui/sonner";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { AuthProvider } from "@/contexts/AuthContext";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ClerkAuthBridge } from "@/auth/ClerkAuthBridge";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";
import { router } from "./shell/router";

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="light" switchable>
        <AuthProvider>
          <TooltipProvider>
            {isClerkAuthEnabled() && <ClerkAuthBridge />}
            <Toaster />
            <RouterProvider router={router} />
          </TooltipProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
