import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Loader2, AlertTriangle, ArrowLeft, Link2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { resolveCode } from "@/lib/api";

export default function RedirectPage() {
  const { code } = useParams();
  const [error, setError] = useState(null);
  const [destination, setDestination] = useState(null);
  const ranRef = useRef(false);

  useEffect(() => {
    if (ranRef.current) return;
    ranRef.current = true;
    resolveCode(code)
      .then((res) => {
        setDestination(res.data.url);
        setTimeout(() => {
          window.location.replace(res.data.url);
        }, 400);
      })
      .catch((err) => {
        const status = err?.response?.status;
        setError(
          status === 410
            ? "This link has expired."
            : "This link doesn't exist or has expired."
        );
      });
  }, [code]);

  let domain = null;
  try {
    domain = destination ? new URL(destination).hostname : null;
  } catch {
    domain = null;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md rounded-xl">
        <CardContent className="flex flex-col items-start gap-4 p-6 sm:p-8">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Link2 className="h-5 w-5" />
          </span>
          {error ? (
            <div data-testid="redirect-error" className="space-y-3">
              <div className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="h-5 w-5" />
                <p className="font-heading text-lg font-semibold">Link unavailable</p>
              </div>
              <p className="text-sm text-muted-foreground">{error}</p>
              <Button asChild variant="outline" data-testid="redirect-back-home-button">
                <Link to="/">
                  <ArrowLeft className="mr-2 h-4 w-4" /> Back to LinkMint
                </Link>
              </Button>
            </div>
          ) : (
            <div data-testid="redirect-loading" className="space-y-2">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <p className="font-heading text-lg font-semibold">Resolving link…</p>
              </div>
              <p className="text-sm text-muted-foreground">
                {domain ? (
                  <>
                    Taking you to{" "}
                    <span data-testid="redirect-destination-domain" className="font-mono font-medium text-foreground">
                      {domain}
                    </span>
                  </>
                ) : (
                  <span className="font-mono">/{code}</span>
                )}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
