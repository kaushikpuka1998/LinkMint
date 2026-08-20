import { useCallback, useEffect, useState } from "react";
import { format } from "date-fns";
import { toast } from "sonner";
import {
  Link2,
  MousePointerClick,
  Activity,
  Copy,
  ExternalLink,
  Trash2,
  CalendarIcon,
  X,
  Scissors,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { shortenUrl, getLinks, getStats, getHealth, deleteLink, shortUrlFor } from "@/lib/api";

const copyText = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  }
};

const truncate = (str, n = 52) => (str.length > n ? str.slice(0, n) + "…" : str);

export default function HomePage() {
  const [longUrl, setLongUrl] = useState("");
  const [alias, setAlias] = useState("");
  const [expiry, setExpiry] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [links, setLinks] = useState(null);
  const [stats, setStats] = useState(null);
  const [redisOk, setRedisOk] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [linksRes, statsRes] = await Promise.all([getLinks(), getStats()]);
      setLinks(linksRes.data);
      setStats(statsRes.data);
    } catch {
      setLinks((prev) => prev ?? []);
      toast.error("Could not load links");
    }
  }, []);

  useEffect(() => {
    refresh();
    getHealth()
      .then((res) => setRedisOk(res.data.redis === "ok"))
      .catch(() => setRedisOk(false));
  }, [refresh]);

  const handleShorten = async (e) => {
    e.preventDefault();
    if (!longUrl.trim()) {
      toast.error("Paste a URL first");
      return;
    }
    setSubmitting(true);
    try {
      const payload = { url: longUrl.trim() };
      if (alias.trim()) payload.custom_alias = alias.trim();
      if (expiry) {
        const end = new Date(expiry);
        end.setHours(23, 59, 59, 999);
        payload.expires_at = end.toISOString();
      }
      const res = await shortenUrl(payload);
      setResult(res.data);
      toast.success("Short link created");
      refresh();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Could not shorten URL");
    } finally {
      setSubmitting(false);
    }
  };

  const handleClear = () => {
    setLongUrl("");
    setAlias("");
    setExpiry(null);
    setResult(null);
  };

  const handleCopy = async (code) => {
    const ok = await copyText(shortUrlFor(code));
    if (ok) toast.success("Copied. Share it anywhere.");
    else toast.error("Copy failed");
  };

  const handleDelete = async (code) => {
    try {
      await deleteLink(code);
      toast.success(`Deleted /${code}`);
      if (result?.code === code) setResult(null);
      refresh();
    } catch {
      toast.error("Could not delete link");
    }
  };

  const statCards = [
    { title: "Total links", value: stats?.total_links, icon: Link2, testId: "stats-total-links" },
    { title: "Total clicks", value: stats?.total_clicks, icon: MousePointerClick, testId: "stats-total-clicks" },
    { title: "Active links", value: stats?.active_links, icon: Activity, testId: "stats-active-links" },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Top bar */}
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
          <a href="/" data-testid="topbar-brand-link" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Link2 className="h-4 w-4" />
            </span>
            <span className="font-heading text-lg font-semibold tracking-tight">LinkMint</span>
          </a>
          <Badge
            variant="outline"
            data-testid="topbar-status-pill"
            className="gap-1.5 rounded-full px-3 py-1 text-xs font-normal text-muted-foreground"
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                redisOk === null ? "bg-muted-foreground" : redisOk ? "bg-emerald-500" : "bg-amber-500"
              }`}
            />
            {redisOk === null ? "Checking cache…" : redisOk ? "Redis cache: ok" : "Cache offline — Mongo fallback"}
          </Badge>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        {/* Hero */}
        <section className="hero-mesh -mx-4 rounded-none px-4 py-10 sm:-mx-6 sm:rounded-2xl sm:px-6 sm:py-12 lg:-mx-8 lg:px-8">
          <h1 className="font-heading text-4xl font-semibold tracking-tight sm:text-5xl">
            Short links, <span className="text-primary">long reach.</span>
          </h1>
          <p className="mt-3 max-w-xl text-base text-muted-foreground sm:text-lg">
            Paste a long URL, get a clean short link with click tracking. Powered by FastAPI, MongoDB and Redis.
          </p>
        </section>

        {/* Bento: form + stats */}
        <div className="mt-6 grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-12">
          <Card className="rounded-xl shadow-[0_1px_0_rgba(15,23,42,0.04),0_10px_30px_rgba(15,23,42,0.06)] lg:col-span-7">
            <CardHeader className="pb-4">
              <CardTitle className="font-heading text-xl tracking-tight">Shorten a URL</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleShorten} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="long-url">Paste a long URL</Label>
                  <Input
                    id="long-url"
                    data-testid="shorten-form-long-url-input"
                    placeholder="https://example.com/very/long/path?with=params"
                    value={longUrl}
                    onChange={(e) => setLongUrl(e.target.value)}
                    className="font-mono text-sm"
                  />
                </div>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="custom-alias">Custom alias (optional)</Label>
                    <Input
                      id="custom-alias"
                      data-testid="shorten-form-custom-alias-input"
                      placeholder="my-campaign"
                      value={alias}
                      onChange={(e) => setAlias(e.target.value)}
                      className="font-mono text-sm"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Expiration (optional)</Label>
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button
                          type="button"
                          variant="outline"
                          data-testid="shorten-form-expiration-trigger"
                          className="w-full justify-start text-left font-normal"
                        >
                          <CalendarIcon className="mr-2 h-4 w-4 text-muted-foreground" />
                          {expiry ? format(expiry, "PPP") : <span className="text-muted-foreground">No expiry</span>}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0" align="start">
                        <Calendar
                          mode="single"
                          selected={expiry}
                          onSelect={setExpiry}
                          disabled={(date) => date < new Date(new Date().setHours(0, 0, 0, 0))}
                          initialFocus
                        />
                      </PopoverContent>
                    </Popover>
                  </div>
                </div>
                <div className="flex items-center gap-2 pt-1">
                  <Button
                    type="submit"
                    data-testid="shorten-form-submit-button"
                    disabled={submitting}
                    className="bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Scissors className="mr-2 h-4 w-4" />}
                    Shorten
                  </Button>
                  <Button type="button" variant="ghost" data-testid="shorten-form-clear-button" onClick={handleClear}>
                    <X className="mr-2 h-4 w-4" />
                    Clear
                  </Button>
                </div>
              </form>

              {result && (
                <div
                  data-testid="shorten-result-card"
                  className="result-enter mt-5 rounded-lg border border-primary/30 bg-accent/60 p-4"
                >
                  <p className="text-xs font-medium uppercase tracking-wide text-accent-foreground">Your short link</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span data-testid="shorten-result-short-url" className="font-mono text-sm font-medium text-foreground sm:text-base">
                      {shortUrlFor(result.code)}
                    </span>
                    <div className="flex items-center gap-1">
                      <Button
                        size="sm"
                        variant="outline"
                        data-testid="shorten-result-copy-button"
                        onClick={() => handleCopy(result.code)}
                        aria-label="Copy short link"
                      >
                        <Copy className="mr-1.5 h-3.5 w-3.5" /> Copy
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        data-testid="shorten-result-open-button"
                        aria-label="Open short link in new tab"
                        onClick={() => window.open(shortUrlFor(result.code), "_blank", "noopener")}
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                  <p className="mt-1.5 truncate text-xs text-muted-foreground">→ {result.url}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Stats */}
          <div className="grid grid-cols-1 content-start gap-4 sm:grid-cols-3 lg:col-span-5 lg:grid-cols-1">
            {statCards.map(({ title, value, icon: Icon, testId }) => (
              <Card key={testId} className="rounded-xl border bg-card/90">
                <CardContent className="flex items-center gap-4 p-4 sm:p-5">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                    <Icon className="h-5 w-5" />
                  </span>
                  <div>
                    <p className="text-xs text-muted-foreground">{title}</p>
                    <p data-testid={testId} className="font-heading text-2xl font-semibold tracking-tight">
                      {value ?? "—"}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Recent links */}
        <section className="mt-8">
          <h2 className="font-heading text-xl font-semibold tracking-tight sm:text-2xl">Recent links</h2>
          <Card className="mt-4 rounded-xl">
            <CardContent className="p-0">
              {links === null ? (
                <div className="space-y-3 p-4 sm:p-6">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-2/3" />
                </div>
              ) : links.length === 0 ? (
                <div className="flex flex-col items-start gap-3 p-6 sm:p-8" data-testid="links-empty-state">
                  <p className="font-heading text-lg font-medium">No links yet</p>
                  <p className="text-sm text-muted-foreground">
                    Shorten your first URL above — it'll show up here with click counts.
                  </p>
                  <Button
                    variant="outline"
                    data-testid="links-empty-cta-button"
                    onClick={() => document.getElementById("long-url")?.focus()}
                  >
                    Paste a URL
                  </Button>
                </div>
              ) : (
                <>
                  {/* Desktop table */}
                  <div className="hidden md:block">
                    <Table data-testid="links-table">
                      <TableHeader>
                        <TableRow>
                          <TableHead>Short</TableHead>
                          <TableHead>Original</TableHead>
                          <TableHead className="text-right">Clicks</TableHead>
                          <TableHead>Created</TableHead>
                          <TableHead>Expiry</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {links.map((link) => (
                          <TableRow key={link.id} data-testid={`links-row-${link.code}`} className="hover:bg-muted/60">
                            <TableCell>
                              <a
                                href={`/${link.code}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-mono text-sm font-medium text-primary hover:underline"
                                data-testid={`links-row-short-${link.code}`}
                              >
                                /{link.code}
                              </a>
                            </TableCell>
                            <TableCell className="max-w-[280px]">
                              <span className="block truncate font-mono text-xs text-muted-foreground" title={link.url}>
                                {truncate(link.url)}
                              </span>
                            </TableCell>
                            <TableCell className="text-right">
                              <Badge variant="secondary" data-testid={`links-row-clicks-${link.code}`}>
                                {link.clicks}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-sm text-muted-foreground">
                              {link.created_at ? format(new Date(link.created_at), "MMM d, yyyy") : "—"}
                            </TableCell>
                            <TableCell>
                              {link.expires_at ? (
                                link.is_expired ? (
                                  <Badge variant="destructive">Expired</Badge>
                                ) : (
                                  <Badge variant="outline">{format(new Date(link.expires_at), "MMM d, yyyy")}</Badge>
                                )
                              ) : (
                                <span className="text-sm text-muted-foreground">—</span>
                              )}
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex justify-end gap-1">
                                <Button
                                  size="icon"
                                  variant="ghost"
                                  aria-label={`Copy /${link.code}`}
                                  data-testid="links-row-copy-button"
                                  onClick={() => handleCopy(link.code)}
                                >
                                  <Copy className="h-4 w-4" />
                                </Button>
                                <DeleteButton code={link.code} onConfirm={handleDelete} />
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                  {/* Mobile cards */}
                  <div className="space-y-3 p-4 md:hidden" data-testid="links-mobile-list">
                    {links.map((link) => (
                      <div key={link.id} className="rounded-lg border p-3">
                        <div className="flex items-center justify-between gap-2">
                          <a
                            href={`/${link.code}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-mono text-sm font-medium text-primary"
                          >
                            /{link.code}
                          </a>
                          <Badge variant="secondary">{link.clicks} clicks</Badge>
                        </div>
                        <p className="mt-1 truncate font-mono text-xs text-muted-foreground">{link.url}</p>
                        <div className="mt-2 flex items-center justify-between">
                          <span className="text-xs text-muted-foreground">
                            {link.expires_at
                              ? link.is_expired
                                ? "Expired"
                                : `Expires ${format(new Date(link.expires_at), "MMM d")}`
                              : "No expiry"}
                          </span>
                          <div className="flex gap-1">
                            <Button size="icon" variant="ghost" aria-label="Copy" onClick={() => handleCopy(link.code)}>
                              <Copy className="h-4 w-4" />
                            </Button>
                            <DeleteButton code={link.code} onConfirm={handleDelete} />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </section>

        <footer className="mt-10 border-t pt-6 text-xs text-muted-foreground">
          LinkMint — FastAPI · MongoDB · Redis. Links resolve at {window.location.origin}/&lt;code&gt;
        </footer>
      </main>
    </div>
  );
}

const DeleteButton = ({ code, onConfirm }) => (
  <AlertDialog>
    <AlertDialogTrigger asChild>
      <Button
        size="icon"
        variant="ghost"
        aria-label={`Delete /${code}`}
        data-testid="links-row-delete-button"
        className="text-muted-foreground hover:text-destructive"
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </AlertDialogTrigger>
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>Delete /{code}?</AlertDialogTitle>
        <AlertDialogDescription>
          This short link will stop working immediately. This action cannot be undone.
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel data-testid="delete-dialog-cancel-button">Cancel</AlertDialogCancel>
        <AlertDialogAction
          data-testid="delete-dialog-confirm-button"
          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          onClick={() => onConfirm(code)}
        >
          Delete
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
);
