"use client";

import { useCallback, useEffect, useMemo, useState, type ElementType } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Database,
  Filter,
  RefreshCcw,
  Search,
  ShieldAlert,
  TicketCheck
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis
} from "recharts";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { fetchDashboard, fetchFilterOptions, fetchTickets, type DateRange, type TicketQuery } from "@/lib/api";
import type { FilterOptions, Insight, Ticket } from "@/types/api";

type DashboardData = Awaited<ReturnType<typeof fetchDashboard>>;

const COLORS = ["#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed", "#0891b2", "#4b5563", "#be123c"];

const defaultRange: DateRange = {
  startDate: "2026-07-01",
  endDate: "2026-07-31"
};

export function DashboardClient() {
  const [range, setRange] = useState<DateRange>(defaultRange);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await fetchDashboard(range);
      setData(next);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, [range]);

  useEffect(() => {
    void load();
  }, [load]);

  const kpis = useMemo(() => {
    if (!data) return [];
    return [
      {
        title: "Total Tickets",
        value: numberFormat(data.overview.total_tickets),
        delta: percentDelta(data.overview.total_tickets, data.overview.previous_total_tickets),
        icon: TicketCheck
      },
      {
        title: "SLA Compliance",
        value: `${safeFixed(data.overview.sla_compliance)}%`,
        delta: pointDelta(data.overview.sla_compliance, data.overview.previous_sla_compliance),
        icon: CheckCircle2
      },
      {
        title: "Avg Resolution",
        value: `${safeFixed(data.overview.avg_resolution_hours)}h`,
        delta: pointDelta(data.overview.previous_avg_resolution_hours ?? 0, data.overview.avg_resolution_hours),
        icon: Clock3
      },
      {
        title: "SLA Breaches",
        value: numberFormat(data.overview.sla_breaches),
        delta: percentDelta(data.overview.sla_breaches, data.overview.previous_sla_breaches),
        icon: ShieldAlert
      }
    ];
  }, [data]);

  if (loading && !data) {
    return <DashboardSkeleton />;
  }

  return (
    <main className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-4 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-xs font-medium uppercase text-muted-foreground">
              <Activity className="h-4 w-4 text-primary" />
              Support Operations
            </div>
            <h1 className="mt-1 text-2xl font-semibold tracking-normal">Support Ticket Analytics</h1>
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <DateInput label="Start" value={range.startDate ?? ""} onChange={(value) => setRange((current) => ({ ...current, startDate: value }))} />
            <DateInput label="End" value={range.endDate ?? ""} onChange={(value) => setRange((current) => ({ ...current, endDate: value }))} />
            <Button variant="outline" onClick={() => void load()} disabled={loading} title="Refresh data">
              <RefreshCcw className={cn("h-4 w-4", loading && "animate-spin")} />
              Refresh
            </Button>
            <div className="min-w-[170px] text-xs text-muted-foreground">
              Last updated
              <div className="font-medium text-foreground">{lastUpdated ? formatDateTime(lastUpdated.toISOString()) : "Not loaded"}</div>
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1500px] gap-4 px-4 py-4">
        {error ? <ErrorPanel message={error} onRetry={load} /> : null}

        {data ? (
          <>
            <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {kpis.map((kpi) => (
                <KpiCard key={kpi.title} {...kpi} />
              ))}
            </section>

            <section className="grid gap-4 xl:grid-cols-[2fr_1fr]">
              <Card>
                <CardHeader>
                  <CardTitle>Ticket Volume</CardTitle>
                  <CardDescription>Daily intake and SLA breach count</CardDescription>
                </CardHeader>
                <CardContent className="h-[310px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.trends}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="date" tickFormatter={shortDate} tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <RechartsTooltip labelFormatter={formatDate} />
                      <Legend />
                      <Area type="monotone" dataKey="tickets" name="Tickets" stroke="#2563eb" fill="#dbeafe" />
                      <Line type="monotone" dataKey="breaches" name="Breaches" stroke="#dc2626" strokeWidth={2} dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Data Quality</CardTitle>
                  <CardDescription>Operational trust indicators</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-3">
                  <QualityRow label="Likely duplicates" value={data.quality.duplicate_records} tone={data.quality.duplicate_records > 0 ? "warning" : "positive"} />
                  <QualityRow label="Missing root causes" value={data.quality.missing_root_causes} tone={data.quality.missing_root_causes > 100 ? "warning" : "positive"} />
                  <QualityRow label="Invalid records" value={data.quality.invalid_records} tone={data.quality.invalid_records > 0 ? "critical" : "positive"} />
                  <div className="flex items-center justify-between border-t pt-3 text-sm">
                    <span className="flex items-center gap-2 text-muted-foreground"><Database className="h-4 w-4" /> Freshness</span>
                    <span className="font-medium">{formatDateTime(data.quality.data_freshness)}</span>
                  </div>
                </CardContent>
              </Card>
            </section>

            <section className="grid gap-4 xl:grid-cols-3">
              <ChartCard title="Resolution Performance" description="Average resolution hours by category" className="xl:col-span-2">
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={data.categories.slice(0, 10)} layout="vertical" margin={{ left: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis type="number" tick={{ fontSize: 12 }} />
                    <YAxis dataKey="subcategory" type="category" width={92} tick={{ fontSize: 12 }} />
                    <RechartsTooltip />
                    <Bar dataKey="avg_resolution_hours" name="Avg hours" fill="#2563eb" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Priority Distribution" description="Ticket mix by operational urgency">
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={data.priorities}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="priority" />
                    <YAxis />
                    <RechartsTooltip />
                    <Bar dataKey="tickets" fill="#059669" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            </section>

            <section className="grid gap-4 xl:grid-cols-3">
              <ChartCard title="SLA Performance" description="Compliance versus breach rate">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={data.sla.byCategory.slice(0, 8)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="label" tickFormatter={(value) => String(value).split(" / ")[1] ?? value} tick={{ fontSize: 11 }} />
                    <YAxis />
                    <RechartsTooltip />
                    <Legend />
                    <Bar dataKey="compliance" name="Compliance %" fill="#059669" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="breach_rate" name="Breach %" fill="#dc2626" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Root Causes" description="Recurring RCA themes">
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie data={data.rootCauses.slice(0, 8)} dataKey="tickets" nameKey="root_cause" innerRadius={58} outerRadius={94} paddingAngle={2}>
                      {data.rootCauses.slice(0, 8).map((_, index) => (
                        <Cell key={index} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                    <Legend layout="vertical" verticalAlign="middle" align="right" wrapperStyle={{ fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Shift Performance" description="SLA compliance by support shift">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={data.shifts}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="shift" />
                    <YAxis />
                    <RechartsTooltip />
                    <Bar dataKey="sla_compliance" name="SLA compliance %" fill="#2563eb" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            </section>

            <section className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
              <Card>
                <CardHeader>
                  <CardTitle>Operational Insights</CardTitle>
                  <CardDescription>Calculated from current analytics endpoints</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-3">
                  {data.insights.length ? data.insights.map((insight) => <InsightRow key={`${insight.title}-${insight.description}`} insight={insight} />) : <EmptyState label="No insights for this period" />}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Anomaly/Risk Panel</CardTitle>
                  <CardDescription>Open SLA risk, outliers, and category spikes</CardDescription>
                </CardHeader>
                <CardContent className="grid max-h-[360px] gap-3 overflow-auto">
                  {data.anomalies.length ? data.anomalies.slice(0, 8).map((item) => (
                    <div key={`${item.type}-${item.title}`} className="rounded-md border p-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-medium">{item.title}</p>
                        <Badge variant={item.severity}>{item.severity}</Badge>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">{item.description}</p>
                    </div>
                  )) : <EmptyState label="No anomalies detected" />}
                </CardContent>
              </Card>
            </section>

            <Card>
              <CardHeader>
                <CardTitle>Daily Operations Summary</CardTitle>
                <CardDescription>{data.summary.recommendedInvestigation}</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3 text-sm sm:grid-cols-2 xl:grid-cols-4">
                <SummaryMetric label="Tickets created" value={numberFormat(data.summary.ticketsCreated)} />
                <SummaryMetric label="SLA compliance" value={`${safeFixed(data.summary.slaCompliance)}%`} />
                <SummaryMetric label="Average resolution" value={`${safeFixed(data.summary.averageResolutionHours)}h`} />
                <SummaryMetric label="Current SLA risks" value={numberFormat(data.summary.currentSlaRisks)} />
              </CardContent>
            </Card>

            <TicketExplorer range={range} />
          </>
        ) : (
          <EmptyState label="No dashboard data available" />
        )}
      </div>
    </main>
  );
}

function TicketExplorer({ range }: { range: DateRange }) {
  const [filters, setFilters] = useState<TicketQuery>({ page: 1, pageSize: 15, sortBy: "created_at", direction: "desc", ...range });
  const [options, setOptions] = useState<FilterOptions | null>(null);
  const [ticketPage, setTicketPage] = useState<{ rows: Ticket[]; total: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Ticket | null>(null);

  useEffect(() => {
    setFilters((current) => ({ ...current, ...range, page: 1 }));
  }, [range]);

  useEffect(() => {
    void fetchFilterOptions().then(setOptions).catch(() => setOptions(null));
  }, []);

  const loadTickets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setTicketPage(await fetchTickets(filters));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load tickets.");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void loadTickets();
  }, [loadTickets]);

  const totalPages = Math.max(1, Math.ceil((ticketPage?.total ?? 0) / (filters.pageSize ?? 15)));

  function updateFilter(key: keyof TicketQuery, value: string) {
    setFilters((current) => ({ ...current, [key]: value || undefined, page: 1 }));
  }

  function sortBy(key: string) {
    setFilters((current) => ({
      ...current,
      sortBy: key,
      direction: current.sortBy === key && current.direction === "desc" ? "asc" : "desc"
    }));
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <CardTitle>Ticket Explorer</CardTitle>
            <CardDescription>Search, filter, sort, and inspect support tickets</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <div className="relative w-full sm:w-64">
              <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input className="pl-8" placeholder="Search tickets" value={filters.search ?? ""} onChange={(event) => updateFilter("search", event.target.value)} />
            </div>
            <Button variant="outline" onClick={() => void loadTickets()} title="Refresh tickets">
              <RefreshCcw className={cn("h-4 w-4", loading && "animate-spin")} />
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-3">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
          <SelectControl icon={Filter} value={filters.category ?? ""} onChange={(value) => updateFilter("category", value)} options={options?.categories ?? []} placeholder="Category" />
          <SelectControl value={filters.priority ?? ""} onChange={(value) => updateFilter("priority", value)} options={options?.priorities ?? []} placeholder="Priority" />
          <SelectControl value={filters.status ?? ""} onChange={(value) => updateFilter("status", value)} options={options?.statuses ?? []} placeholder="Status" />
          <SelectControl value={filters.shift ?? ""} onChange={(value) => updateFilter("shift", value)} options={options?.shifts ?? []} placeholder="Shift" />
          <SelectControl value={filters.slaStatus ?? ""} onChange={(value) => updateFilter("slaStatus", value)} options={["Breached", "Compliant"]} placeholder="SLA status" />
          <SelectControl value={String(filters.pageSize ?? 15)} onChange={(value) => setFilters((current) => ({ ...current, pageSize: Number(value), page: 1 }))} options={["15", "25", "50", "100"]} placeholder="Rows" includeAll={false} />
        </div>

        {error ? <ErrorPanel message={error} onRetry={loadTickets} /> : null}

        <div className="overflow-hidden rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <SortableHead label="Ticket ID" sortKey="created_at" onSort={sortBy} />
                <SortableHead label="Category" sortKey="category" onSort={sortBy} />
                <SortableHead label="Priority" sortKey="priority" onSort={sortBy} />
                <SortableHead label="Status" sortKey="status" onSort={sortBy} />
                <TableHead>Agent</TableHead>
                <TableHead>Created</TableHead>
                <SortableHead label="Resolution" sortKey="resolution_hours" onSort={sortBy} />
                <SortableHead label="SLA" sortKey="sla" onSort={sortBy} />
                <TableHead>Root Cause</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={9} className="h-24 text-center text-muted-foreground">Loading tickets...</TableCell></TableRow>
              ) : ticketPage?.rows.length ? ticketPage.rows.map((ticket) => (
                <TableRow key={ticket.ticket_id} className="cursor-pointer" onClick={() => setSelected(ticket)}>
                  <TableCell className="font-medium">{ticket.ticket_id}</TableCell>
                  <TableCell>{ticket.category}</TableCell>
                  <TableCell><PriorityBadge priority={ticket.priority} /></TableCell>
                  <TableCell>{ticket.status}</TableCell>
                  <TableCell>{ticket.agent_name}</TableCell>
                  <TableCell>{formatDate(ticket.created_at)}</TableCell>
                  <TableCell>{ticket.resolution_hours === "" ? `${safeFixed(ticket.hours_open)}h open` : `${safeFixed(ticket.resolution_hours)}h`}</TableCell>
                  <TableCell><Badge variant={ticket.sla_breached ? "critical" : "positive"}>{ticket.sla_breached ? "Breached" : "Compliant"}</Badge></TableCell>
                  <TableCell>{ticket.root_cause || "Missing"}</TableCell>
                </TableRow>
              )) : (
                <TableRow><TableCell colSpan={9} className="h-24 text-center text-muted-foreground">No tickets match the current filters.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        <div className="flex flex-col gap-2 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>{numberFormat(ticketPage?.total ?? 0)} tickets found</span>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" disabled={(filters.page ?? 1) <= 1} onClick={() => setFilters((current) => ({ ...current, page: (current.page ?? 1) - 1 }))}>Previous</Button>
            <span>Page {filters.page ?? 1} of {totalPages}</span>
            <Button variant="outline" size="sm" disabled={(filters.page ?? 1) >= totalPages} onClick={() => setFilters((current) => ({ ...current, page: (current.page ?? 1) + 1 }))}>Next</Button>
          </div>
        </div>
      </CardContent>

      <Dialog open={Boolean(selected)} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent>
          {selected ? (
            <>
              <DialogHeader>
                <DialogTitle>{selected.ticket_id}</DialogTitle>
                <DialogDescription>{selected.category} ticket owned by {selected.agent_name}</DialogDescription>
              </DialogHeader>
              <div className="grid gap-3 text-sm sm:grid-cols-2">
                <Detail label="Priority" value={selected.priority} />
                <Detail label="Status" value={selected.status} />
                <Detail label="Shift" value={selected.shift} />
                <Detail label="Customer impact" value={selected.customer_impact} />
                <Detail label="Created" value={formatDateTime(selected.created_at)} />
                <Detail label="First response" value={formatDateTime(selected.first_response_at)} />
                <Detail label="Resolved" value={formatDateTime(selected.resolved_at)} />
                <Detail label="SLA hours" value={`${selected.sla_hours}h`} />
                <Detail label="Resolution type" value={selected.resolution_type || "Unresolved"} />
                <Detail label="Root cause" value={selected.root_cause || "Missing"} />
              </div>
              <div className="rounded-md border p-3 text-sm">
                <div className="mb-1 font-medium">Description</div>
                <p className="text-muted-foreground">{selected.description}</p>
              </div>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </Card>
  );
}

function KpiCard({ title, value, delta, icon: Icon }: { title: string; value: string; delta: { value: string; positive: boolean; neutral: boolean }; icon: ElementType }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase text-muted-foreground">{title}</p>
            <p className="mt-2 text-2xl font-semibold">{value}</p>
          </div>
          <div className="rounded-md bg-secondary p-2">
            <Icon className="h-5 w-5 text-primary" />
          </div>
        </div>
        <div className={cn("mt-3 flex items-center gap-1 text-xs", delta.neutral ? "text-muted-foreground" : delta.positive ? "text-emerald-700" : "text-red-700")}>
          {delta.neutral ? null : delta.positive ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />}
          {delta.value} vs previous period
        </div>
      </CardContent>
    </Card>
  );
}

function ChartCard({ title, description, children, className }: { title: string; description: string; children: React.ReactNode; className?: string }) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function DateInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="grid gap-1 text-xs font-medium text-muted-foreground">
      {label}
      <div className="relative">
        <CalendarDays className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4" />
        <Input type="date" className="w-[158px] pl-8 text-foreground" value={value} onChange={(event) => onChange(event.target.value)} />
      </div>
    </label>
  );
}

function SelectControl({ value, onChange, options, placeholder, icon: Icon, includeAll = true }: { value: string; onChange: (value: string) => void; options: string[]; placeholder: string; icon?: ElementType; includeAll?: boolean }) {
  return (
    <div className="relative">
      {Icon ? <Icon className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" /> : null}
      <select
        className={cn("h-9 w-full rounded-md border border-input bg-card px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring", Icon && "pl-8")}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {includeAll ? <option value="">{placeholder}</option> : null}
        {options.map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
    </div>
  );
}

function InsightRow({ insight }: { insight: Insight }) {
  return (
    <div className="flex items-start gap-3 rounded-md border p-3">
      <Badge variant={insight.type}>{insight.type}</Badge>
      <div>
        <p className="text-sm font-medium">{insight.title}</p>
        <p className="mt-1 text-sm text-muted-foreground">{insight.description}</p>
      </div>
    </div>
  );
}

function QualityRow({ label, value, tone }: { label: string; value: number; tone: "positive" | "warning" | "critical" }) {
  return (
    <div className="flex items-center justify-between rounded-md border p-3 text-sm">
      <span>{label}</span>
      <Badge variant={tone}>{numberFormat(value)}</Badge>
    </div>
  );
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}

function SortableHead({ label, sortKey, onSort }: { label: string; sortKey: string; onSort: (key: string) => void }) {
  return (
    <TableHead>
      <button className="inline-flex items-center gap-1 font-semibold" onClick={() => onSort(sortKey)} type="button">
        {label}
        <ArrowUpDown className="h-3.5 w-3.5" />
      </button>
    </TableHead>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const variant = priority === "P1" ? "critical" : priority === "P2" ? "warning" : priority === "P3" ? "info" : "default";
  return <Badge variant={variant}>{priority}</Badge>;
}

function Detail({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="rounded-md border p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 font-medium">{value || "Not available"}</div>
    </div>
  );
}

function ErrorPanel({ message, onRetry }: { message: string; onRetry: () => void | Promise<void> }) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-4 w-4" />
        <p className="text-sm">{message}</p>
      </div>
      <Button variant="outline" size="sm" onClick={() => void onRetry()}>Retry</Button>
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">{label}</div>;
}

function DashboardSkeleton() {
  return (
    <main className="mx-auto grid max-w-[1500px] gap-4 px-4 py-4">
      <div className="h-24 animate-pulse rounded-lg bg-secondary" />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => <div key={index} className="h-32 animate-pulse rounded-lg bg-secondary" />)}
      </div>
      <div className="h-[360px] animate-pulse rounded-lg bg-secondary" />
    </main>
  );
}

function percentDelta(current?: number | null, previous?: number | null) {
  if (!previous) return { value: "No comparison", positive: true, neutral: true };
  const value = ((current ?? 0) - previous) / previous * 100;
  return { value: `${Math.abs(value).toFixed(1)}%`, positive: value >= 0, neutral: false };
}

function pointDelta(current?: number | null, previous?: number | null) {
  if (current == null || previous == null) return { value: "No comparison", positive: true, neutral: true };
  const value = current - previous;
  return { value: `${Math.abs(value).toFixed(1)} pts`, positive: value >= 0, neutral: false };
}

function numberFormat(value: number) {
  return new Intl.NumberFormat("en-US").format(value ?? 0);
}

function safeFixed(value?: number | string | null) {
  const numeric = Number(value ?? 0);
  return Number.isFinite(numeric) ? numeric.toFixed(1) : "0.0";
}

function shortDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : `${date.getMonth() + 1}/${date.getDate()}`;
}

function formatDate(value?: string | null) {
  if (!value) return "Not available";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

function formatDateTime(value?: string | null) {
  if (!value) return "Not available";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}
