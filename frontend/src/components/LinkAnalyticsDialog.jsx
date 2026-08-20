import { useState } from "react";
import { toast } from "sonner";
import { BarChart3, Loader2 } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { getLinkAnalytics } from "@/lib/api";

const formatTick = (dateStr) => {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
};

export const LinkAnalyticsDialog = ({ code, iconOnly = true }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleOpenChange = async (open) => {
    if (!open) return;
    setLoading(true);
    try {
      const res = await getLinkAnalytics(code, 30);
      setData(res.data);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Could not load analytics");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const hasClicks = data && data.series.some((p) => p.clicks > 0);

  return (
    <Dialog onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button
          size={iconOnly ? "icon" : "sm"}
          variant="ghost"
          aria-label={`Analytics for /${code}`}
          data-testid="links-row-analytics-button"
        >
          <BarChart3 className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg" data-testid="analytics-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading tracking-tight">
            Clicks over time · <span className="font-mono text-primary">/{code}</span>
          </DialogTitle>
        </DialogHeader>
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-4 w-40" />
          </div>
        ) : !data ? (
          <p className="text-sm text-muted-foreground">Analytics unavailable.</p>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground" data-testid="analytics-total-clicks">
              <span className="font-heading text-2xl font-semibold text-foreground">{data.total_clicks}</span>{" "}
              total click{data.total_clicks === 1 ? "" : "s"} · last 30 days shown
            </p>
            {hasClicks ? (
              <div className="h-56 w-full" data-testid="analytics-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.series} margin={{ top: 6, right: 6, bottom: 0, left: -18 }}>
                    <defs>
                      <linearGradient id="clicksFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="hsl(var(--chart-1))" stopOpacity={0.28} />
                        <stop offset="100%" stopColor="hsl(var(--chart-1))" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="date"
                      tickFormatter={formatTick}
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      tickLine={false}
                      axisLine={false}
                      minTickGap={28}
                    />
                    <YAxis
                      allowDecimals={false}
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <RechartsTooltip
                      labelFormatter={formatTick}
                      formatter={(value) => [value, "Clicks"]}
                      contentStyle={{
                        borderRadius: 8,
                        border: "1px solid hsl(var(--border))",
                        background: "hsl(var(--card))",
                        fontSize: 12,
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="clicks"
                      stroke="hsl(var(--chart-1))"
                      strokeWidth={2}
                      fill="url(#clicksFill)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div
                className="flex h-40 items-center justify-center rounded-lg border border-dashed"
                data-testid="analytics-empty-state"
              >
                <p className="text-sm text-muted-foreground">No click data yet — share the link to see trends.</p>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
