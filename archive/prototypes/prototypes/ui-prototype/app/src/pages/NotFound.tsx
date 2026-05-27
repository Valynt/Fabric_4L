import { FileQuestion, ArrowLeft, Home } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function NotFound() {
  const navigate = useNavigate();

  return (
    <main className="min-h-[60vh] flex items-center justify-center p-6" aria-label="Page not found">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mx-auto">
          <FileQuestion className="w-8 h-8 text-muted-foreground" />
        </div>

        <div>
          <h1 className="text-7xl font-bold text-foreground tracking-tight">404</h1>
          <p className="text-lg font-semibold text-foreground mt-2">Page not found</p>
          <p className="text-sm text-muted-foreground mt-1">
            The page you are looking for does not exist or has been moved.
          </p>
        </div>

        <div className="flex items-center justify-center gap-3 pt-2">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 px-4 py-2.5 bg-card border border-border text-foreground rounded-lg text-sm font-medium hover:bg-muted"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90"
          >
            <Home className="w-4 h-4" />
            Dashboard
          </button>
        </div>
      </div>
    </main>
  );
}
