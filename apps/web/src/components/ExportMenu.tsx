import { useState } from "react";
import { FileDown, Loader2 } from "lucide-react";
import { apiPost } from "@/api/typedClient";
import { normalizeError } from "@/lib/errors";
import { toast } from "sonner";

interface ExportMenuProps {
  accountId: string;
  valueCaseId: string;
}

export function ExportMenu({ accountId, valueCaseId }: ExportMenuProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async (format: string) => {
    setLoading(format);
    setError(null);
    try {
      const response = await apiPost<{
        status: string;
        format: string;
        filename: string;
        download_url: string;
      }>("l4", `/accounts/${accountId}/value-case/${valueCaseId}/export?format=${format}`);
      if (response.data.status === "ready") {
        window.open(response.data.download_url, "_blank");
      }
    } catch (err: unknown) {
      const normalizedError = normalizeError(err, `Export failed for ${format}`);
      setError(normalizedError.message);
      toast.error(normalizedError.message);
    } finally {
      setLoading(null);
    }
  };

  const formats = [
    { key: "pdf", label: "PDF" },
    { key: "docx", label: "Word" },
    { key: "pptx", label: "Slides" },
  ];

  return (
    <div className="flex items-center gap-2">
      {formats.map((f) => (
        <button
          key={f.key}
          onClick={() => handleExport(f.key)}
          disabled={!!loading}
          className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-3 py-1.5 text-xs font-medium hover:bg-muted disabled:opacity-50"
        >
          {loading === f.key ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <FileDown className="h-3 w-3" />
          )}
          {f.label}
        </button>
      ))}
      {error && <span className="text-xs text-destructive ml-1">{error}</span>}
    </div>
  );
}
