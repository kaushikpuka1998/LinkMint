import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Layers, Loader2, Copy, UserRound, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { bulkShorten, shortUrlFor } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

const copyText = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
};

export const BulkShorten = ({ onDone }) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [results, setResults] = useState(null);

  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);

  if (!user) {
    return (
      <div className="flex flex-col items-start gap-3 rounded-lg border border-dashed p-6" data-testid="bulk-signin-prompt">
        <p className="font-heading text-base font-medium">Bulk shortening is for members</p>
        <p className="text-sm text-muted-foreground">
          Sign in to paste a whole list of URLs and shorten them all in one go.
        </p>
        <Button data-testid="bulk-signin-button" onClick={() => navigate("/auth")}>
          <UserRound className="mr-1.5 h-4 w-4" /> Sign in to use bulk mode
        </Button>
      </div>
    );
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (lines.length === 0) {
      toast.error("Paste at least one URL");
      return;
    }
    if (lines.length > 50) {
      toast.error("Maximum 50 URLs per batch");
      return;
    }
    setSubmitting(true);
    setResults(null);
    try {
      const res = await bulkShorten(lines);
      setResults(res.data);
      toast.success(`Created ${res.data.created} short link${res.data.created === 1 ? "" : "s"}`);
      onDone?.();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Bulk shortening failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopyAll = async () => {
    const all = results.results.filter((r) => r.code).map((r) => shortUrlFor(r.code)).join("\n");
    if (await copyText(all)) toast.success("All short links copied");
    else toast.error("Copy failed");
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="bulk-urls">One URL per line</Label>
          <span className="text-xs text-muted-foreground" data-testid="bulk-url-count">
            {lines.length} URL{lines.length === 1 ? "" : "s"} · max 50
          </span>
        </div>
        <Textarea
          id="bulk-urls"
          data-testid="bulk-urls-textarea"
          placeholder={"https://example.com/first\nhttps://example.com/second\nexample.com/third"}
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={6}
          className="font-mono text-sm"
        />
      </div>
      <Button type="submit" disabled={submitting} data-testid="bulk-submit-button">
        {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Layers className="mr-2 h-4 w-4" />}
        Shorten all
      </Button>

      {results && (
        <div className="result-enter space-y-2 rounded-lg border border-primary/30 bg-accent/60 p-4" data-testid="bulk-results">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-accent-foreground">
              {results.created} created{results.failed > 0 ? ` · ${results.failed} failed` : ""}
            </p>
            {results.created > 0 && (
              <Button type="button" size="sm" variant="outline" onClick={handleCopyAll} data-testid="bulk-copy-all-button">
                <Copy className="mr-1.5 h-3.5 w-3.5" /> Copy all
              </Button>
            )}
          </div>
          <ul className="max-h-48 space-y-1.5 overflow-y-auto">
            {results.results.map((r, idx) => (
              <li key={idx} className="flex items-center gap-2 text-xs" data-testid={`bulk-result-row-${idx}`}>
                {r.code ? (
                  <>
                    <Badge variant="secondary" className="shrink-0 font-mono">/{r.code}</Badge>
                    <span className="truncate font-mono text-muted-foreground">{r.url}</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-3.5 w-3.5 shrink-0 text-destructive" />
                    <span className="truncate font-mono text-muted-foreground">{r.url}</span>
                    <span className="shrink-0 text-destructive">{r.error}</span>
                  </>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </form>
  );
};
